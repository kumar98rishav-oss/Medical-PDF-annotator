import json
import logging
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from ..database import get_db
from ..db_models import UploadedPDF
from ..errors import NotFoundError

router = APIRouter(prefix="/api", tags=["Search"])
logger = logging.getLogger(__name__)

@router.get("/pdf/{pdf_id}/search")
async def search_pdf(pdf_id: str, q: str = Query(..., min_length=2), db: Session = Depends(get_db)):
    pdf = db.query(UploadedPDF).filter(UploadedPDF.id == pdf_id).first()
    if not pdf:
        raise NotFoundError("PDF not found")

    if not pdf.extracted_text:
        return {
            "query": q,
            "total_matches": 0,
            "results": []
        }

    try:
        pages = json.loads(pdf.extracted_text)
    except Exception as e:
        logger.error(f"Failed to parse extracted text for search: {e}")
        return {
            "query": q,
            "total_matches": 0,
            "results": []
        }

    q_lower = q.lower()
    results = []
    total_matches = 0

    for idx, page_text in enumerate(pages):
        page_num = idx + 1
        page_lower = page_text.lower()
        match_count = page_lower.count(q_lower)
        
        if match_count > 0:
            total_matches += match_count
            
            # Extract snippet from first match
            first_idx = page_lower.find(q_lower)
            start_idx = max(0, first_idx - 80)
            end_idx = min(len(page_text), first_idx + len(q) + 80)
            
            # Try to get clean snippet matching word boundaries roughly
            snippet = page_text[start_idx:end_idx].replace('\n', ' ')
            
            if start_idx > 0:
                snippet = "..." + snippet
            if end_idx < len(page_text):
                snippet = snippet + "..."
                
            results.append({
                "page": page_num,
                "snippet": snippet,
                "match_count": match_count
            })

    return {
        "query": q,
        "total_matches": total_matches,
        "results": results
    }
