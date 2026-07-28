from app.models import VisitCreate, OverlapInfo
from app.db_models import VisitAnnotation
from app.validators.annotation_validator import AnnotationValidator

def test_detect_overlaps():
    existing_visits = [
        VisitAnnotation(id="v1", start_page=1, end_page=4),
        VisitAnnotation(id="v2", start_page=8, end_page=10),
    ]

    # No overlap
    new_visit1 = VisitCreate(start_page=5, end_page=7, date_of_service="2024-01-01", facility_name="F1", provider_name="P1")
    overlaps1 = AnnotationValidator.detect_overlaps(new_visit1, existing_visits)
    assert len(overlaps1) == 0

    # Overlaps with v1
    new_visit2 = VisitCreate(start_page=3, end_page=6, date_of_service="2024-01-01", facility_name="F1", provider_name="P1")
    overlaps2 = AnnotationValidator.detect_overlaps(new_visit2, existing_visits)
    assert len(overlaps2) == 1
    assert overlaps2[0].conflicting_visit_id == "v1"
    assert overlaps2[0].overlap_pages == [3, 4]
    assert overlaps2[0].severity == "warning"

    # Overlaps with both
    new_visit3 = VisitCreate(start_page=4, end_page=8, date_of_service="2024-01-01", facility_name="F1", provider_name="P1")
    overlaps3 = AnnotationValidator.detect_overlaps(new_visit3, existing_visits)
    assert len(overlaps3) == 2
    ids = sorted([o.conflicting_visit_id for o in overlaps3])
    assert ids == ["v1", "v2"]
