from pathlib import Path
from ..errors import ValidationError
import fitz

class PDFValidator:
    """Validator for uploaded PDFs."""

    @staticmethod
    def validate_file(filename: str, file_path: Path):
        """Validate PDF file integrity, extension, and return page count and size."""
        if not filename:
            raise ValidationError("No filename provided")

        if not filename.lower().endswith(".pdf"):
            raise ValidationError("Only PDF files are accepted")

        if not file_path.exists():
            raise ValidationError("File not found on disk after upload")

        try:
            with fitz.open(str(file_path)) as doc:
                page_count = doc.page_count
                
            if page_count == 0:
                raise ValidationError("PDF has 0 pages")
                
            file_size = file_path.stat().st_size
            return page_count, file_size
        except Exception as e:
            raise ValidationError(f"Invalid or corrupted PDF: {e}", internal_detail=str(e))
