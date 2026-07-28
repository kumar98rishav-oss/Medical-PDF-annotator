"""
Smart Text Extractor with OCR fallback for scanned pages.
"""
import fitz  # PyMuPDF
import logging

logger = logging.getLogger(__name__)

try:
    import pytesseract
    from PIL import Image
    import os
    import sys
    from pathlib import Path
    
    def _find_tesseract():
        """Find tesseract.exe on Windows, checking multiple common locations."""
        if os.name != 'nt':
            return None  # On Linux/Mac, tesseract is usually in PATH already
        
        candidates = [
            r'C:\Program Files\Tesseract-OCR\tesseract.exe',
            r'C:\Program Files (x86)\Tesseract-OCR\tesseract.exe',
        ]
        
        if getattr(sys, 'frozen', False):
            # PyInstaller frozen mode — check bundled locations
            exe_dir = Path(sys.executable).parent
            meipass = Path(getattr(sys, '_MEIPASS', str(exe_dir)))
            candidates.extend([
                str(exe_dir / 'Tesseract-OCR' / 'tesseract.exe'),
                str(exe_dir / '_internal' / 'Tesseract-OCR' / 'tesseract.exe'),
                str(meipass / 'Tesseract-OCR' / 'tesseract.exe'),
                str(exe_dir / 'tesseract.exe'),
            ])
        else:
            # Dev mode: check project root venv and backend venv
            this_dir = Path(__file__).parent
            project_root = this_dir.parent.parent  # backend/app -> backend -> project root
            candidates.extend([
                str(project_root / 'venv' / 'Scripts' / 'tesseract.exe'),
                str(this_dir.parent / 'venv' / 'Scripts' / 'tesseract.exe'),
            ])
        
        for path in candidates:
            if os.path.exists(path):
                return path
        return None
    
    def _setup_tessdata(tess_exe_path):
        """Set TESSDATA_PREFIX env var so both pytesseract and PyMuPDF find tessdata."""
        tessdata_dir = Path(tess_exe_path).parent / 'tessdata'
        if not tessdata_dir.exists():
            # Also check one level up (e.g. Scripts/../share/tessdata)
            tessdata_dir = Path(tess_exe_path).parent.parent / 'share' / 'tessdata'
        if tessdata_dir.exists():
            os.environ['TESSDATA_PREFIX'] = str(tessdata_dir)
            logger.info(f"TESSDATA_PREFIX set to: {tessdata_dir}")
    
    tess_path = _find_tesseract()
    if tess_path:
        pytesseract.pytesseract.tesseract_cmd = tess_path
        _setup_tessdata(tess_path)
        logger.info(f"Tesseract OCR found at: {tess_path}")
    else:
        logger.warning("Tesseract binary not found in common locations. OCR may fail unless tesseract is in PATH.")
        
    OCR_AVAILABLE = True
except ImportError:
    OCR_AVAILABLE = False
    logger.warning("pytesseract or Pillow not installed. OCR will be disabled for scanned pages.")

class TextExtractor:
    """Extracts text from PDF pages, detecting native vs scanned pages and applying OCR if needed."""
    
    def __init__(self, pdf_path: str):
        self.pdf_path = pdf_path

    def _is_digital_page(self, text: str) -> bool:
        """Determines if a page is digital (has enough native text)."""
        stripped_text = text.strip()
        # > 50 meaningful non-whitespace characters
        return len(stripped_text) > 50

    def _extract_native(self, page) -> str:
        """Extracts native text from a page."""
        return page.get_text("text").strip()

    def _extract_ocr(self, page) -> str:
        """Extracts text using OCR if available."""
        if not OCR_AVAILABLE:
            return ""
        try:
            # Render at 300 DPI for OCR
            pix = page.get_pixmap(dpi=300)
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            text = pytesseract.image_to_string(img)
            return text.strip()
        except Exception as e:
            logger.warning(f"OCR failed for page: {str(e)}")
            return ""
    def extract_specific_pages_ocr(self, start_page: int, end_page: int) -> dict:
        """Forces OCR extraction on a specific range of 1-indexed pages."""
        if not OCR_AVAILABLE:
            raise Exception("OCR is not available. Please install python dependencies (pytesseract, Pillow) and the Tesseract engine on your machine.")
            
        results = {}
        with fitz.open(self.pdf_path) as doc:
            for i in range(start_page - 1, end_page):
                if 0 <= i < doc.page_count:
                    page = doc[i]
                    text = self._extract_ocr(page)
                    if text:
                        results[i] = text
        return results

    def extract_all_pages(self) -> dict:
        """
        Extracts text for all pages.
        Returns dict with "pages" list, "document_type" (digital|scanned|hybrid), and "total_pages".
        """
        pages_result = []
        digital_count = 0
        scanned_count = 0

        with fitz.open(self.pdf_path) as doc:
            total_pages = doc.page_count
            for i, page in enumerate(doc):
                native_text = self._extract_native(page)
                
                if self._is_digital_page(native_text):
                    method = "native"
                    text = native_text
                    digital_count += 1
                else:
                    method = "ocr"
                    text = self._extract_ocr(page)
                    scanned_count += 1

                pages_result.append({
                    "page_num": i + 1,
                    "text": text,
                    "method": method,
                    "char_count": len(text)
                })

        if digital_count == total_pages:
            doc_type = "digital"
        elif scanned_count == total_pages:
            doc_type = "scanned"
        else:
            doc_type = "hybrid"

        return {
            "pages": pages_result,
            "document_type": doc_type,
            "total_pages": total_pages
        }
