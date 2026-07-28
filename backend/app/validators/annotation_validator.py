from typing import List
from ..models import VisitCreate, OverlapInfo
from ..db_models import VisitAnnotation

class AnnotationValidator:
    """Validator for visit annotations and overlaps."""

    @staticmethod
    def validate_page_range(visit: VisitCreate, total_pages: int):
        if visit.start_page < 1:
            raise ValueError("Start page must be >= 1")
        if visit.end_page > total_pages:
            raise ValueError(f"End page cannot exceed {total_pages}")
        if visit.start_page > visit.end_page:
            raise ValueError("Start page must be <= end page")

    @staticmethod
    def detect_overlaps(new_visit: VisitCreate, existing_visits: List[VisitAnnotation], ignore_visit_id: str = None) -> List[OverlapInfo]:
        """
        Returns list of OverlapInfo objects describing conflicts.
        """
        overlaps = []
        new_range = set(range(new_visit.start_page, new_visit.end_page + 1))
        
        for existing in existing_visits:
            if ignore_visit_id and existing.id == ignore_visit_id:
                continue
                
            existing_range = set(range(existing.start_page, existing.end_page + 1))
            common = new_range & existing_range
            if common:
                overlaps.append(OverlapInfo(
                    conflicting_visit_id=existing.id,
                    overlap_pages=sorted(list(common)),
                    severity="warning",
                ))
        return overlaps
