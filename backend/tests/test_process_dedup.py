from datetime import datetime
from app.models import VisitResponse
from app.services.process_service import ProcessService

def test_deduplicate_visits():
    v1 = VisitResponse(
        id="1", pdf_id="p1", start_page=1, end_page=5,
        date_of_service="2024-01-01", facility_name="A", provider_name="B", document_type="other",
        section_type="medical_record", notes="",
        version=1, created_at=datetime(2024, 1, 1, 10, 0, 0), confidence=None, source="manual"
    )
    v2 = VisitResponse(
        id="2", pdf_id="p1", start_page=4, end_page=8,
        date_of_service="2024-01-02", facility_name="A", provider_name="B", document_type="other",
        section_type="medical_record", notes="",
        version=1, created_at=datetime(2024, 1, 1, 11, 0, 0), confidence=None, source="manual"  # Created later
    )

    visits = [v1, v2]
    deduped = ProcessService.deduplicate_visits(visits)

    assert len(deduped) == 2
    
    # Oldest visit (v1) should retain all its pages
    assert deduped[0].id == "1"
    assert deduped[0].start_page == 1
    assert deduped[0].end_page == 5
    
    # Newer visit (v2) should shrink to only the unique pages
    assert deduped[1].id == "2"
    assert deduped[1].start_page == 6
    assert deduped[1].end_page == 8
