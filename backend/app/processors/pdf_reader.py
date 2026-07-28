"""
PDF Reader Engine
- Renders pages as images for the viewer
- Inspection utilities
"""

import fitz  # PyMuPDF
from pathlib import Path
from ..errors import ProcessingError

class PDFReader:
    """Handles rendering operations for PDFs."""

    @staticmethod
    def get_page_count(pdf_path: str) -> int:
        try:
            with fitz.open(pdf_path) as doc:
                return doc.page_count
        except Exception as e:
            raise ProcessingError("Failed to get page count", internal_detail=str(e))

    @staticmethod
    def get_file_size(pdf_path: str) -> int:
        return Path(pdf_path).stat().st_size

    @staticmethod
    def render_page_image(
        pdf_path: str,
        page_num: int,
        zoom: float = 1.5
    ) -> bytes:
        """
        Render a single page as PNG.
        page_num is 1-indexed.
        """
        try:
            with fitz.open(pdf_path) as doc:
                if page_num < 1 or page_num > doc.page_count:
                    raise ValueError(
                        f"Page {page_num} out of range (1-{doc.page_count})"
                    )
                page = doc[page_num - 1]
                mat = fitz.Matrix(zoom, zoom)
                pix = page.get_pixmap(matrix=mat, alpha=False)
                return pix.tobytes("png")
        except ValueError as ve:
            raise ve
        except Exception as e:
            raise ProcessingError("Failed to render page image", internal_detail=str(e))
