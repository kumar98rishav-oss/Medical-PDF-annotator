import uuid
import json
from pathlib import Path
from fastapi import APIRouter, Depends, Query, BackgroundTasks
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from ..database import get_db, SessionLocal
from ..db_models import UploadedPDF, ProcessedPDF, VisitAnnotation
from ..models import JobStatusResponse, VisitResponse
from ..config import PROCESSED_DIR
from ..services.process_service import ProcessService
from ..processors.combined_builder import CombinedBuilder
from ..processors.split_builder import SplitBuilder
from ..errors import NotFoundError, ValidationError, ProcessingError

router = APIRouter(prefix="/api", tags=["Processing"])

def process_pdf_background(pdf_id: str, job_id: str, mode: str):
    db: Session = SessionLocal()
    try:
        job = db.query(ProcessedPDF).filter(ProcessedPDF.id == job_id).first()
        if not job:
            return

        job.status = "processing"
        db.commit()

        pdf = db.query(UploadedPDF).filter(UploadedPDF.id == pdf_id).first()
        if not pdf:
            job.status = "error"
            job.error_message = "Source PDF not found"
            db.commit()
            return
            
        if not pdf.visits:
            job.status = "error"
            job.error_message = "No annotations found"
            db.commit()
            return

        visits_models = [VisitResponse.model_validate(v) for v in pdf.visits]
        deduped_visits = ProcessService.deduplicate_visits(visits_models)
        
        if not deduped_visits:
             job.status = "error"
             job.error_message = "No unique pages left to process after deduplication."
             db.commit()
             return

        def update_progress(processed_count, total_visits):
            job.progress = f"{processed_count}/{total_visits}"
            db.commit()

        total_v = len(deduped_visits)
        job.total_visits = total_v
        
        if mode == "combined":
            output_filename = f"{job_id}.pdf"
            output_path = PROCESSED_DIR / output_filename
            builder = CombinedBuilder()
            result = builder.build(source_path=pdf.file_path, visits=deduped_visits, output_path=str(output_path), progress_callback=update_progress)
        else:
            output_filename = f"{job_id}.zip"
            output_path = PROCESSED_DIR / output_filename
            builder = SplitBuilder()
            result = builder.build(source_path=pdf.file_path, visits=deduped_visits, output_zip_path=str(output_path), progress_callback=update_progress)

        job.status = "complete"
        job.download_url = f"/api/download/{job_id}"
        job.total_pages_extracted = result["page_count"]
        job.file_path = str(output_path)
        job.page_count = result["page_count"]
        job.visit_count = result["visit_count"]
        job.facilities_json = json.dumps(result["facilities"])
        
        db.commit()

    except Exception as e:
        job.status = "error"
        job.error_message = str(e)
        if 'output_path' in locals():
            Path(output_path).unlink(missing_ok=True)
        db.commit()
    finally:
        db.close()


@router.post("/pdf/{pdf_id}/process", response_model=JobStatusResponse)
async def process_pdf(background_tasks: BackgroundTasks, pdf_id: str, mode: str = Query("combined", pattern="^(combined|split)$"), db: Session = Depends(get_db)):
    pdf = db.query(UploadedPDF).filter(UploadedPDF.id == pdf_id).first()
    if not pdf:
        raise NotFoundError("PDF not found")

    if not pdf.visits:
        raise ValidationError("No visits annotated. Add at least one visit before processing.")

    process_id = str(uuid.uuid4())
    
    # Create queued record
    processed = ProcessedPDF(
        id=process_id,
        source_pdf_id=pdf_id,
        file_path="",  # will be filled later
        page_count=0,
        visit_count=0,
        facilities_json="[]",
        status="queued",
    )
    db.add(processed)
    db.commit()

    background_tasks.add_task(process_pdf_background, pdf_id=pdf_id, job_id=process_id, mode=mode)
    
    return JobStatusResponse(
        job_id=process_id,
        status="queued",
        poll_url=f"/api/process/status/{process_id}",
    )

@router.get("/process/status/{job_id}")
async def get_process_status(job_id: str, db: Session = Depends(get_db)):
    processed = db.query(ProcessedPDF).filter(ProcessedPDF.id == job_id).first()
    if not processed:
        raise NotFoundError("Job not found")
        
    return {
        "job_id": processed.id,
        "status": processed.status,
        "progress": processed.progress,
        "download_url": processed.download_url,
        "error_message": processed.error_message
    }

@router.get("/download/{job_id}")
async def download_processed_file(job_id: str, db: Session = Depends(get_db)):
    processed = db.query(ProcessedPDF).filter(ProcessedPDF.id == job_id).first()
    if not processed:
        raise NotFoundError("Processed PDF not found")

    if not processed.file_path or not Path(processed.file_path).exists():
        raise NotFoundError("Processed file missing from disk")

    source = db.query(UploadedPDF).filter(UploadedPDF.id == processed.source_pdf_id).first()
    original_name = source.original_filename if source else "output"
    stem = Path(original_name).stem
    
    is_zip = processed.file_path.endswith(".zip")
    extension = ".zip" if is_zip else ".pdf"
    media_type = "application/zip" if is_zip else "application/pdf"
    download_name = f"{stem}{extension}"

    return FileResponse(processed.file_path, media_type=media_type, filename=download_name)

@router.get("/processed/{process_id}/download")
async def download_processed_pdf_old(process_id: str, db: Session = Depends(get_db)):
    # Legacy endpoint to support existing clients that use this URL
    return await download_processed_file(process_id, db)

@router.get("/pdf/{pdf_id}/processed")
async def list_processed_versions(pdf_id: str, db: Session = Depends(get_db)):
    versions = db.query(ProcessedPDF).filter(ProcessedPDF.source_pdf_id == pdf_id).order_by(ProcessedPDF.processed_at.desc()).all()
    return [
        {
            "id": v.id,
            "page_count": v.page_count,
            "visit_count": v.visit_count,
            "facilities": json.loads(v.facilities_json) if v.facilities_json else [],
            "processed_at": v.processed_at.isoformat(),
            "download_url": v.download_url or f"/api/download/{v.id}",
            "status": v.status,
            "progress": v.progress
        }
        for v in versions
    ]