from typing import List
from ..models import VisitResponse

class ProcessService:
    """Orchestrates PDF processing with deduplication."""

    @staticmethod
    def deduplicate_visits(visits: List[VisitResponse]) -> List[VisitResponse]:
        """
        Ensures no source page appears in output more than once,
        UNLESS a visit has allow_overlap=True — those pages are included
        even if another visit already claimed them.

        Priority for non-overlap visits: earliest created_at wins.
        """
        claimed_pages = set()
        sorted_visits = sorted(visits, key=lambda v: v.created_at)

        deduped = []
        for visit in sorted_visits:
            pages = set(range(visit.start_page, visit.end_page + 1))

            if getattr(visit, "allow_overlap", False):
                # User explicitly chose to keep this overlap — include all pages
                visit_dict = visit.model_dump()
                deduped.append(VisitResponse(**visit_dict))
                # Don't add these pages to claimed_pages so other visits can also claim them
                continue

            unique_pages = pages - claimed_pages
            if not unique_pages:
                continue

            # Split into contiguous runs (avoids including gap pages)
            sorted_unique = sorted(unique_pages)
            runs = []
            run_start = sorted_unique[0]
            run_end = sorted_unique[0]
            for p in sorted_unique[1:]:
                if p == run_end + 1:
                    run_end = p
                else:
                    runs.append((run_start, run_end))
                    run_start = p
                    run_end = p
            runs.append((run_start, run_end))

            for r_start, r_end in runs:
                visit_dict = visit.model_dump()
                visit_dict["start_page"] = r_start
                visit_dict["end_page"] = r_end
                deduped.append(VisitResponse(**visit_dict))

            claimed_pages |= unique_pages

        return deduped
