import uuid
import json
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from ..database import get_db
from ..db_models import UploadedPDF, VisitAnnotation, FacilityPattern
from ..models import VisitCreate, VisitUpdate, VisitResponse, FacilitySuggestion, VisitCreateResponse, QuickAnnotateRequest, QuickAnnotateResponse, AIExtractRequest
from ..auto_annotator import SuggestionExtractor
from ..text_extractor import TextExtractor
from ..smart_matcher import SmartMatcher
from ..services.annotation_service import AnnotationService
from ..services.llm_extraction import LLMExtractionService
from ..validators.annotation_validator import AnnotationValidator
from ..errors import NotFoundError, ValidationError

router = APIRouter(prefix="/api", tags=["Annotations"])

@router.post("/pdf/{pdf_id}/visits", response_model=VisitCreateResponse, status_code=status.HTTP_201_CREATED)
async def create_visit(pdf_id: str, visit: VisitCreate, db: Session = Depends(get_db)):
    pdf = db.query(UploadedPDF).filter(UploadedPDF.id == pdf_id).first()
    if not pdf:
        raise NotFoundError("PDF not found")

    try:
        AnnotationValidator.validate_page_range(visit, pdf.page_count)
    except ValueError as e:
        raise ValidationError(str(e))
        
    overlaps = AnnotationValidator.detect_overlaps(visit, pdf.visits)

    annotation = VisitAnnotation(
        id=str(uuid.uuid4()),
        pdf_id=pdf_id,
        start_page=visit.start_page,
        end_page=visit.end_page,
        date_of_service=visit.date_of_service,
        facility_name=visit.facility_name,
        provider_name=visit.provider_name,
        document_type=visit.document_type,
        section_type=visit.section_type,
        notes=visit.notes,
        allow_overlap=bool(visit.allow_overlap),
        version=1
    )
    db.add(annotation)

    AnnotationService.learn_facility(db, visit)
    db.commit()
    db.refresh(annotation)
    
    visit_resp = VisitResponse.model_validate(annotation)
    AnnotationService.log_audit(db, "create_visit", "visit", annotation.id, visit_resp.model_dump(mode='json'))
    db.commit()

    return VisitCreateResponse(visit=visit_resp, warnings=overlaps if overlaps else None)

@router.get("/pdf/{pdf_id}/visits", response_model=List[VisitResponse])
async def get_visits(pdf_id: str, db: Session = Depends(get_db)):
    pdf = db.query(UploadedPDF).filter(UploadedPDF.id == pdf_id).first()
    if not pdf:
        raise NotFoundError("PDF not found")
    return [VisitResponse.model_validate(v) for v in pdf.visits]

@router.put("/pdf/{pdf_id}/visits/{visit_id}", response_model=VisitCreateResponse)
async def update_visit(pdf_id: str, visit_id: str, update: VisitUpdate, db: Session = Depends(get_db)):
    annotation = db.query(VisitAnnotation).filter(VisitAnnotation.id == visit_id, VisitAnnotation.pdf_id == pdf_id).first()
    if not annotation:
        raise NotFoundError("Visit annotation not found")

    old_snapshot = VisitResponse.model_validate(annotation).model_dump(mode='json')
    update_data = update.model_dump(exclude_unset=True)

    # Need a full VisitCreate for overlap detection
    merged_data = {
        "start_page": annotation.start_page,
        "end_page": annotation.end_page,
        "date_of_service": annotation.date_of_service,
        "facility_name": annotation.facility_name,
        "provider_name": annotation.provider_name,
        "document_type": annotation.document_type,
        "notes": annotation.notes
    }
    merged_data.update(update_data)
    
    pdf = db.query(UploadedPDF).filter(UploadedPDF.id == pdf_id).first()
    try:
        AnnotationValidator.validate_page_range(VisitCreate(**merged_data), pdf.page_count)
    except ValueError as e:
        raise ValidationError(str(e))
        
    overlaps = AnnotationValidator.detect_overlaps(VisitCreate(**merged_data), pdf.visits, ignore_visit_id=visit_id)

    for key, value in update_data.items():
        setattr(annotation, key, value)

    annotation.version += 1
    annotation.updated_at = datetime.utcnow()
    
    AnnotationService.log_audit(db, "update_visit", "visit", annotation.id, old_snapshot)
    db.commit()
    db.refresh(annotation)

    return VisitCreateResponse(visit=VisitResponse.model_validate(annotation), warnings=overlaps if overlaps else None)

@router.delete("/pdf/{pdf_id}/visits/{visit_id}")
async def delete_visit(pdf_id: str, visit_id: str, db: Session = Depends(get_db)):
    annotation = db.query(VisitAnnotation).filter(VisitAnnotation.id == visit_id, VisitAnnotation.pdf_id == pdf_id).first()
    if not annotation:
        raise NotFoundError("Visit annotation not found")

    old_snapshot = VisitResponse.model_validate(annotation).model_dump(mode='json')
    AnnotationService.log_audit(db, "delete_visit", "visit", annotation.id, old_snapshot)
    
    db.delete(annotation)
    db.commit()
    return {"status": "deleted", "id": visit_id}

@router.get("/facilities", response_model=List[FacilitySuggestion])
async def get_facility_suggestions(db: Session = Depends(get_db)):
    patterns = db.query(FacilityPattern).order_by(FacilityPattern.sample_count.desc()).all()
    results = []
    for p in patterns:
        try:
            types = json.loads(p.common_document_types) if p.common_document_types else []
        except:
            types = []
        try:
            providers = json.loads(p.provider_names) if p.provider_names else []
        except:
            providers = []

        results.append(FacilitySuggestion(
            facility_name=p.facility_name,
            common_types=types,
            avg_pages=round(p.avg_page_count or 0, 1),
            providers=providers[:10],
            times_seen=p.sample_count,
        ))
    return results

@router.post("/pdf/{pdf_id}/quick-annotate", response_model=QuickAnnotateResponse)
async def quick_annotate(pdf_id: str, request: QuickAnnotateRequest, db: Session = Depends(get_db)):
    """
    Given a page range, extract ALL possible facility names, provider names,
    dates of service, and document types from those pages.
    Returns lists of suggestions — the user picks the correct one to autofill.
    """
    pdf = db.query(UploadedPDF).filter(UploadedPDF.id == pdf_id).first()
    if not pdf:
        raise NotFoundError("PDF not found")

    # Get existing extracted text, pad if necessary
    pages = []
    if pdf.extracted_text:
        try:
            pages = json.loads(pdf.extracted_text)
        except Exception:
            pass

    while len(pages) < pdf.page_count:
        pages.append("")

    start_idx = max(0, request.start_page - 1)
    end_idx = min(len(pages), request.end_page)
    
    combined_text = "\n".join(pages[start_idx:end_idx])

    # AUTO-OCR FALLBACK: If there's barely any text, run OCR on the fly!
    if len(combined_text.replace(" ", "").replace("\n", "")) < 20: # extremely low threshold
        try:
            extractor = TextExtractor(pdf.file_path)
            ocr_results = extractor.extract_specific_pages_ocr(request.start_page, request.end_page)
            
            pages_updated = False
            for idx, text in ocr_results.items():
                if len(text.strip()) > len(pages[idx].strip()):
                    pages[idx] = text
                    pages_updated = True
                    
            if pages_updated:
                pdf.extracted_text = json.dumps(pages)
                db.commit()
                combined_text = "\n".join(pages[start_idx:end_idx])
                
        except Exception as e:
            import logging
            logging.getLogger(__name__).warning(f"Auto-OCR failed during quick-annotate: {e}")

    # Extract ALL possible suggestions from the text using Regex
    extractor = SuggestionExtractor()
    suggestions = extractor.extract_all_suggestions(combined_text)

    # NEW: Phase 1 AI - Extract known entities from DB directly scanning text
    matcher = SmartMatcher(db)
    db_matches = matcher.scan_text_for_known_entities(combined_text)
    
    # Prepend DB matches to suggestions so they appear first!
    for f in db_matches["facilities"]:
        if f not in suggestions["facilities"]:
            suggestions["facilities"].insert(0, f)
            
    for p in db_matches["providers"]:
        if p not in suggestions["providers"]:
            suggestions["providers"].insert(0, p)

    # Also pull known facilities from the FacilityPattern DB
    # so user can pick from historically learned names too
    known_facilities = []

    # Fuzzy-match each extracted facility against known patterns
    for fac_name in suggestions["facilities"]:
        match = matcher.fuzzy_match_facility(fac_name)
        if match and match not in known_facilities:
            known_facilities.append(match)

    # Also include all known facility patterns as additional options
    all_patterns = db.query(FacilityPattern).order_by(FacilityPattern.sample_count.desc()).limit(20).all()
    for p in all_patterns:
        try:
            providers_list = json.loads(p.provider_names) if p.provider_names else []
        except Exception:
            providers_list = []
        try:
            doc_types_list = json.loads(p.common_document_types) if p.common_document_types else []
        except Exception:
            doc_types_list = []

        entry = {
            "facility_name": p.facility_name,
            "common_providers": providers_list,
            "common_doc_types": doc_types_list,
            "times_seen": p.sample_count,
        }
        if entry not in known_facilities:
            known_facilities.append(entry)

    return QuickAnnotateResponse(
        start_page=request.start_page,
        end_page=request.end_page,
        facilities=suggestions["facilities"],
        providers=suggestions["providers"],
        dates_of_service=suggestions["dates_of_service"],
        document_types=suggestions["document_types"],
        known_facilities=known_facilities,
    )

@router.post("/pdf/{pdf_id}/ai-annotate", response_model=QuickAnnotateResponse)
async def ai_annotate(pdf_id: str, request: AIExtractRequest, db: Session = Depends(get_db)):
    """
    Sends page text to a Cloud AI model to extract complex JSON structures flawlessly.
    Bypasses all regex patterns.
    """
    pdf = db.query(UploadedPDF).filter(UploadedPDF.id == pdf_id).first()
    if not pdf:
        raise NotFoundError("PDF not found")

    pages = []
    if pdf.extracted_text:
        try:
            pages = json.loads(pdf.extracted_text)
        except Exception:
            pass

    while len(pages) < pdf.page_count:
        pages.append("")

    start_idx = max(0, request.start_page - 1)
    end_idx = min(len(pages), request.end_page)
    combined_text = "\n".join(pages[start_idx:end_idx])

    # Ensure some text exists (AI can't read blanks obviously, so fallback OCR if missing)
    if len(combined_text.replace(" ", "").replace("\n", "")) < 20: 
        try:
            extractor = TextExtractor(pdf.file_path)
            ocr_results = extractor.extract_specific_pages_ocr(request.start_page, request.end_page)
            for idx, text in ocr_results.items():
                if len(text.strip()) > len(pages[idx].strip()):
                    pages[idx] = text
            combined_text = "\n".join(pages[start_idx:end_idx])
        except Exception:
            pass
            
    try:
        # Call the LLM
        ai_data = LLMExtractionService.extract_with_ai(combined_text, request.api_key)
        
        # Pull historically known facilities so user can still see them 
        known_facilities = []
        all_patterns = db.query(FacilityPattern).order_by(FacilityPattern.sample_count.desc()).limit(20).all()
        for p in all_patterns:
            known_facilities.append({
                "facility_name": p.facility_name,
                "common_providers": json.loads(p.provider_names) if p.provider_names else [],
                "common_doc_types": json.loads(p.common_document_types) if p.common_document_types else [],
                "times_seen": p.sample_count,
            })

        return QuickAnnotateResponse(
            start_page=request.start_page,
            end_page=request.end_page,
            facilities=ai_data["facilities"],
            providers=ai_data["providers"],
            dates_of_service=ai_data["dates_of_service"],
            document_types=ai_data["document_types"],
            known_facilities=known_facilities,
        )
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.post("/pdf/{pdf_id}/quick-ocr")
async def quick_ocr(pdf_id: str, request: QuickAnnotateRequest, db: Session = Depends(get_db)):
    """
    On-demand OCR for a specific page range. 
    Useful when a scanned PDF has missing text in the DB.
    """
    pdf = db.query(UploadedPDF).filter(UploadedPDF.id == pdf_id).first()
    if not pdf:
        raise NotFoundError("PDF not found")

    try:
        extractor = TextExtractor(pdf.file_path)
        ocr_results = extractor.extract_specific_pages_ocr(request.start_page, request.end_page)

        if not ocr_results:
            return {"status": "no_text_found", "message": "OCR ran but found no readable text."}

        # Merge new text into the existing extracted_text array
        if pdf.extracted_text:
            pages = json.loads(pdf.extracted_text)
        else:
            pages = [""] * pdf.page_count

        for idx, text in ocr_results.items():
            # Pad array if somehow it's shorter than the page index
            while len(pages) <= idx:
                pages.append("")
            # If the OCR text is more meaningful than what's there, replace it
            if len(text.strip()) > len(pages[idx].strip()):
                pages[idx] = text

        pdf.extracted_text = json.dumps(pages)
        db.commit()

        return {"status": "success", "pages_updated": len(ocr_results)}

    except Exception as e:
        raise ValidationError(str(e))