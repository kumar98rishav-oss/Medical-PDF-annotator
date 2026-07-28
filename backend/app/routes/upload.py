from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, Query, BackgroundTasks
from fastapi.responses import FileResponse, Response
from sqlalchemy.orm import Session
from ..database import get_db, SessionLocal
from ..db_models import UploadedPDF
from ..models import PDFUploadResponse, PDFInfoResponse, PDFListItem, PDFStatusResponse
from ..services.upload_service import UploadService
from ..processors.pdf_reader import PDFReader
import json
import io
import os
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from pydantic import BaseModel
from PIL import Image as PILImage

from ..text_extractor import TextExtractor
from ..config import THUMBNAILS_DIR
import fitz

router = APIRouter(prefix="/api", tags=["PDFs"])


class LocalPathUpload(BaseModel):
    file_path: str
    filename: str


def _render_page_batch(pdf_path: str, pdf_dir: Path, page_indices: list):
    """Render thumbnails for a batch of pages — each call opens its own fitz doc.
    Also pre-generates the zoom=1.5 cache (default viewer zoom) by resizing the
    150 DPI base image with Pillow — faster than a second PDF render.
    """
    try:
        with fitz.open(pdf_path) as doc:
            for i in page_indices:
                if i >= doc.page_count:
                    break
                page = doc[i]

                # 72 DPI thumbnail for sidebar
                thumb_pix = page.get_pixmap(dpi=72)
                thumb_pix.save(str(pdf_dir / f"thumb_{i+1}.png"))

                # 150 DPI base — used as source for fast resize to any zoom ≤ 2.0
                full_pix = page.get_pixmap(dpi=150)
                base_path = pdf_dir / f"page_{i+1}.png"
                full_pix.save(str(base_path))

                # Pre-generate zoom=1.5 cache (default) via fast Pillow resize
                # scale = target_dpi / base_dpi = (1.5 * 72) / 150 = 0.72
                try:
                    scale = (1.5 * 72) / 150  # 0.72
                    with PILImage.open(str(base_path)) as img:
                        new_w = max(1, round(img.width * scale))
                        new_h = max(1, round(img.height * scale))
                        resized = img.resize((new_w, new_h), PILImage.LANCZOS)
                        buf = io.BytesIO()
                        resized.save(buf, format="PNG")
                        (pdf_dir / f"page_{i+1}_z15.png").write_bytes(buf.getvalue())
                except Exception:
                    pass
    except Exception:
        pass


def preprocess_pdf_background(pdf_id: str, pdf_path: str):
    """Background task: extract text + render thumbnails in parallel."""
    db = SessionLocal()
    pdf = None
    try:
        pdf = db.query(UploadedPDF).filter(UploadedPDF.id == pdf_id).first()
        if not pdf:
            return

        # ── Step 1: Extract text ──
        pdf.preprocessing_status = "extracting_text"
        db.commit()

        extractor = TextExtractor(pdf_path)
        extract_result = extractor.extract_all_pages()

        pdf.extracted_text = json.dumps([p["text"] for p in extract_result["pages"]])
        pdf.is_digital = (extract_result["document_type"] in ("digital", "hybrid"))
        pdf.text_extraction_method = extract_result["document_type"]

        # ── Step 2: Render thumbnails in parallel ──
        pdf.preprocessing_status = "rendering_thumbnails"
        db.commit()

        pdf_dir = THUMBNAILS_DIR / pdf_id
        pdf_dir.mkdir(parents=True, exist_ok=True)

        with fitz.open(pdf_path) as doc_check:
            page_count = doc_check.page_count

        # Render page 1 immediately so the viewer is usable right away
        _render_page_batch(pdf_path, pdf_dir, [0])

        # Parallel render of remaining pages — cap at 4 workers to stay responsive
        if page_count > 1:
            max_workers = min(4, os.cpu_count() or 2)
            remaining = list(range(1, page_count))
            chunk_size = max(1, (len(remaining) + max_workers - 1) // max_workers)
            chunks = [remaining[i:i + chunk_size] for i in range(0, len(remaining), chunk_size)]

            with ThreadPoolExecutor(max_workers=max_workers) as pool:
                futures = [pool.submit(_render_page_batch, pdf_path, pdf_dir, chunk) for chunk in chunks]
                for f in as_completed(futures):
                    f.result()

        pdf.preprocessing_status = "complete"
        db.commit()

    except Exception as e:
        if pdf:
            pdf.preprocessing_status = f"error: {str(e)}"
            db.commit()
    finally:
        db.close()


@router.post("/upload", response_model=PDFUploadResponse)
async def upload_pdf(background_tasks: BackgroundTasks, file: UploadFile = File(...), db: Session = Depends(get_db)):
    pdf_record = UploadService.process_upload(db, file.filename, file.file)
    background_tasks.add_task(preprocess_pdf_background, pdf_id=pdf_record.id, pdf_path=pdf_record.file_path)
    return PDFUploadResponse(
        id=pdf_record.id,
        filename=pdf_record.original_filename,
        page_count=pdf_record.page_count,
        file_size=pdf_record.file_size,
    )


@router.post("/upload/local-path", response_model=PDFUploadResponse)
async def upload_pdf_local_path(background_tasks: BackgroundTasks, payload: LocalPathUpload, db: Session = Depends(get_db)):
    """Fast upload for local files — copies directly on disk instead of streaming through HTTP."""
    source = Path(payload.file_path)
    if not source.exists():
        raise HTTPException(400, "File not found at the specified path")
    if source.suffix.lower() != ".pdf":
        raise HTTPException(400, "File must be a PDF")

    pdf_record = UploadService.process_local_upload(db, payload.filename or source.name, str(source))
    background_tasks.add_task(preprocess_pdf_background, pdf_id=pdf_record.id, pdf_path=pdf_record.file_path)
    return PDFUploadResponse(
        id=pdf_record.id,
        filename=pdf_record.original_filename,
        page_count=pdf_record.page_count,
        file_size=pdf_record.file_size,
    )

@router.get("/pdfs", response_model=list[PDFListItem])
async def list_pdfs(db: Session = Depends(get_db)):
    pdfs = db.query(UploadedPDF).order_by(UploadedPDF.uploaded_at.desc()).all()
    return [
        PDFListItem(
            id=p.id,
            filename=p.original_filename,
            page_count=p.page_count,
            file_size=p.file_size,
            uploaded_at=p.uploaded_at,
            visit_count=len(p.visits),
        )
        for p in pdfs
    ]

@router.get("/pdf/{pdf_id}/info", response_model=PDFInfoResponse)
async def get_pdf_info(pdf_id: str, db: Session = Depends(get_db)):
    pdf = db.query(UploadedPDF).filter(UploadedPDF.id == pdf_id).first()
    if not pdf:
        raise HTTPException(404, "PDF not found")

    marked = set()
    total_visit_pages = 0
    for v in pdf.visits:
        for p in range(v.start_page, v.end_page + 1):
            marked.add(p)
        total_visit_pages += v.end_page - v.start_page + 1

    return PDFInfoResponse(
        id=pdf.id,
        filename=pdf.original_filename,
        page_count=pdf.page_count,
        file_size=pdf.file_size,
        uploaded_at=pdf.uploaded_at,
        visit_count=len(pdf.visits),
        marked_pages=len(marked),
        total_visit_pages=total_visit_pages,
    )

@router.get("/pdf/{pdf_id}/status", response_model=PDFStatusResponse)
async def get_pdf_status(pdf_id: str, db: Session = Depends(get_db)):
    pdf = db.query(UploadedPDF).filter(UploadedPDF.id == pdf_id).first()
    if not pdf:
        raise HTTPException(404, "PDF not found")
        
    sugs = json.loads(pdf.auto_suggestions) if pdf.auto_suggestions else []
    
    # ensure is_digital is boolean in sqlite too
    is_digital = bool(pdf.is_digital) 
    
    return PDFStatusResponse(
        preprocessing_status=pdf.preprocessing_status or "pending",
        is_digital=is_digital,
        text_extraction_method=pdf.text_extraction_method,
        suggestions_count=len(sugs)
    )

@router.delete("/pdf/{pdf_id}")
async def delete_pdf(pdf_id: str, db: Session = Depends(get_db)):
    success = UploadService.delete_pdf(db, pdf_id)
    if not success:
        raise HTTPException(404, "PDF not found")
    return {"status": "deleted", "id": pdf_id}

@router.get("/pdf/{pdf_id}/file")
async def serve_pdf_file(pdf_id: str, db: Session = Depends(get_db)):
    pdf = db.query(UploadedPDF).filter(UploadedPDF.id == pdf_id).first()
    if not pdf:
        raise HTTPException(404, "PDF not found")

    return FileResponse(pdf.file_path, media_type="application/pdf", filename=pdf.original_filename)

@router.get("/pdf/{pdf_id}/page/{page_num}/image")
async def get_page_image(pdf_id: str, page_num: int, zoom: float = Query(default=1.5, ge=0.3, le=5.0), db: Session = Depends(get_db)):
    pdf = db.query(UploadedPDF).filter(UploadedPDF.id == pdf_id).first()
    if not pdf:
        raise HTTPException(404, "PDF not found")

    pdf_dir = THUMBNAILS_DIR / pdf_id
    zoom_key = int(round(zoom * 10))

    # ── Zoom-specific cache (fastest path — serves any previously computed zoom) ──
    zoom_cached = pdf_dir / f"page_{page_num}_z{zoom_key}.png"
    if zoom_cached.exists():
        return FileResponse(str(zoom_cached), headers={"Cache-Control": "public, max-age=3600"}, media_type="image/png")

    img_bytes: bytes | None = None

    # ── For zoom ≤ 2.0: resize the pre-rendered 150 DPI base image with Pillow ──
    # This avoids re-rendering the PDF and is ~10-50× faster.
    base_cached = pdf_dir / f"page_{page_num}.png"
    if zoom <= 2.0 and base_cached.exists():
        try:
            # target pixel width = base_width * (zoom * 72) / 150
            scale = (zoom * 72) / 150
            with PILImage.open(str(base_cached)) as img:
                new_w = max(1, round(img.width * scale))
                new_h = max(1, round(img.height * scale))
                resized = img.resize((new_w, new_h), PILImage.LANCZOS)
                buf = io.BytesIO()
                resized.save(buf, format="PNG")
                img_bytes = buf.getvalue()
        except Exception:
            img_bytes = None  # fall through to PDF render

    # ── Fallback: render directly from PDF (zoom > 2.0 or cache missing) ──
    if img_bytes is None:
        img_bytes = PDFReader.render_page_image(pdf.file_path, page_num, zoom)

    # Persist for next request
    zoom_cached.parent.mkdir(parents=True, exist_ok=True)
    zoom_cached.write_bytes(img_bytes)

    return Response(
        content=img_bytes,
        media_type="image/png",
        headers={"Cache-Control": "public, max-age=3600", "X-Page-Number": str(page_num)},
    )

@router.get("/pdf/{pdf_id}/thumbnail/{page_num}")
async def get_thumbnail(pdf_id: str, page_num: int, db: Session = Depends(get_db)):
    pdf = db.query(UploadedPDF).filter(UploadedPDF.id == pdf_id).first()
    if not pdf:
        raise HTTPException(404, "PDF not found")
        
    thumb_path = THUMBNAILS_DIR / pdf_id / f"thumb_{page_num}.png"
    if thumb_path.exists():
        return FileResponse(str(thumb_path), headers={"Cache-Control": "public, max-age=3600"}, media_type="image/png")
    
    img_bytes = PDFReader.render_page_image(pdf.file_path, page_num, zoom=0.5)
    return Response(content=img_bytes, media_type="image/png", headers={"Cache-Control": "public, max-age=3600"})

@router.get("/pdf/{pdf_id}/thumbnails")
async def get_all_thumbnails(pdf_id: str, db: Session = Depends(get_db)):
    pdf = db.query(UploadedPDF).filter(UploadedPDF.id == pdf_id).first()
    if not pdf:
        raise HTTPException(404, "PDF not found")
        
    urls = []
    for i in range(pdf.page_count):
         urls.append(f"/api/pdf/{pdf_id}/thumbnail/{i+1}")
         
    return urls