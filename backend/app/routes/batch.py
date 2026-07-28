from fastapi import APIRouter, Depends, UploadFile, File, BackgroundTasks
from pydantic import BaseModel
from typing import List
from sqlalchemy.orm import Session

from ..database import get_db
from ..db_models import UploadedPDF
from ..models import BatchUploadResponse, BatchProcessResponse
from ..services.upload_service import UploadService
from .upload import preprocess_pdf_background
from .process import process_pdf
from ..errors import NotFoundError

router = APIRouter(prefix="/api", tags=["Batch"])

class BatchProcessRequest(BaseModel):
    pdf_ids: List[str]
    mode: str = "combined"

@router.post("/batch/upload", response_model=BatchUploadResponse)
async def batch_upload(background_tasks: BackgroundTasks, files: List[UploadFile] = File(...), db: Session = Depends(get_db)):
    """Upload multiple PDF files at once. Each gets background text extraction + thumbnails."""
    uploaded_ids = []
    
    for file in files:
        pdf_record = UploadService.process_upload(db, file.filename, file.file)
        background_tasks.add_task(preprocess_pdf_background, pdf_id=pdf_record.id, pdf_path=pdf_record.file_path)
        uploaded_ids.append(pdf_record.id)
        
    return BatchUploadResponse(
        uploaded=len(uploaded_ids),
        pdf_ids=uploaded_ids
    )

@router.post("/batch/process", response_model=BatchProcessResponse)
async def batch_process(background_tasks: BackgroundTasks, request: BatchProcessRequest, db: Session = Depends(get_db)):
    """Kick off async processing for multiple PDFs."""
    jobs = []
    
    for pdf_id in request.pdf_ids:
        try:
            res = await process_pdf(
                background_tasks=background_tasks,
                pdf_id=pdf_id,
                mode=request.mode,
                db=db
            )
            jobs.append(res.model_dump() if hasattr(res, 'model_dump') else res)
        except Exception as e:
            jobs.append({"pdf_id": pdf_id, "error": str(e)})
            
    return BatchProcessResponse(jobs=jobs)
