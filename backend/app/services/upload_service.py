import uuid
import shutil
from pathlib import Path
from sqlalchemy.orm import Session
from ..db_models import UploadedPDF
from ..config import UPLOAD_DIR
from ..errors import StorageError
from ..validators.pdf_validator import PDFValidator

class UploadService:
    """Handles logic for receiving and storing uploaded PDFs."""

    @staticmethod
    def process_local_upload(db: Session, file_name: str, source_path: str) -> UploadedPDF:
        """Fast path for local files: OS-level copy instead of HTTP streaming."""
        pdf_id = str(uuid.uuid4())
        file_path = UPLOAD_DIR / f"{pdf_id}.pdf"

        try:
            shutil.copy2(source_path, file_path)
        except Exception as e:
            raise StorageError("Failed to copy local file", internal_detail=str(e))

        try:
            page_count, file_size = PDFValidator.validate_file(file_name, file_path)
        except Exception as e:
            file_path.unlink(missing_ok=True)
            raise e

        pdf_record = UploadedPDF(
            id=pdf_id,
            original_filename=file_name,
            file_path=str(file_path),
            page_count=page_count,
            file_size=file_size,
        )
        db.add(pdf_record)
        db.commit()
        db.refresh(pdf_record)
        return pdf_record

    @staticmethod
    def process_upload(db: Session, file_name: str, file_stream) -> UploadedPDF:
        pdf_id = str(uuid.uuid4())
        safe_filename = f"{pdf_id}.pdf"
        file_path = UPLOAD_DIR / safe_filename

        try:
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(file_stream, buffer)
        except Exception as e:
            raise StorageError(f"Failed to save file to disk", internal_detail=str(e))

        try:
            page_count, file_size = PDFValidator.validate_file(file_name, file_path)
        except Exception as e:
            file_path.unlink(missing_ok=True)
            raise e

        pdf_record = UploadedPDF(
            id=pdf_id,
            original_filename=file_name,
            file_path=str(file_path),
            page_count=page_count,
            file_size=file_size,
        )
        db.add(pdf_record)
        db.commit()
        db.refresh(pdf_record)

        return pdf_record

    @staticmethod
    def delete_pdf(db: Session, pdf_id: str):
        pdf = db.query(UploadedPDF).filter(UploadedPDF.id == pdf_id).first()
        if not pdf:
            return False

        try:
            Path(pdf.file_path).unlink(missing_ok=True)
        except Exception:
            pass

        db.delete(pdf)
        db.commit()
        return True
