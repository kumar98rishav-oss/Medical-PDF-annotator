import fitz
from typing import List, Dict, Tuple
from datetime import datetime
from dateutil.parser import parse as parse_date
from ..models import VisitResponse

# Sections that carry facility/DOS/provider metadata
MEDICAL_SECTIONS = {"medical_record", "medical_bill"}

# Group labels for non-medical sections (used as the level-1 bookmark)
SECTION_LABELS = {
    "injury_photo":   "Injury Photos",
    "vehicle_photo":  "Vehicle Photos",
    "medical_record": "Medical Records",
    "medical_bill":   "Medical Billing",
    "other":          "Other Documents",
}


class CombinedBuilder:
    """Handles building a single combined PDF (Mode 1).

    Output structure (bookmarks):
      Facility name                       ← level 1, groups ordered by earliest DOS
        DOS / Provider (pg X-Y)           ← level 2, medical visits chronological by DOS
      Injury Photos                       ← non-medical sections grouped by label
        pg X-Y [- Notes]
    """

    @staticmethod
    def _parse_dos(dos_str: str) -> datetime:
        """Parse date of service string into datetime for sorting."""
        if not dos_str or not dos_str.strip():
            return datetime.max          # visits with no DOS sort last
        try:
            return parse_date(dos_str.strip(), fuzzy=True)
        except (ValueError, TypeError):
            return datetime.max

    @staticmethod
    def _group_key(visit: VisitResponse) -> str:
        """Group label: facility for medical visits, section label otherwise."""
        section = getattr(visit, "section_type", "medical_record") or "medical_record"
        if section in MEDICAL_SECTIONS:
            return (visit.facility_name or "Unknown Facility").strip()
        return SECTION_LABELS.get(section, "Other Documents")

    def build(self, source_path: str, visits: List[VisitResponse],
              output_path: str, progress_callback=None) -> Dict:
        """Build a single combined PDF grouped by facility, visits chronological."""

        # Bucket visits by group (facility / section label)
        groups: Dict[str, List[VisitResponse]] = {}
        for visit in visits:
            groups.setdefault(self._group_key(visit), []).append(visit)

        # Sort visits within each group chronologically (dateless last)
        for group_visits in groups.values():
            group_visits.sort(key=lambda v: self._parse_dos(v.date_of_service))

        # Order groups by their earliest DOS (groups with no DOS sort last)
        ordered_keys = sorted(
            groups.keys(),
            key=lambda k: self._parse_dos(groups[k][0].date_of_service)
        )

        toc: List[Tuple[int, str, int]] = []
        current_output_page = 0
        all_facilities: set = set()
        processed_count = 0
        total_visits = len(visits)

        with fitz.open(source_path) as source, fitz.open() as output:

            for group_key in ordered_keys:
                group_visits = groups[group_key]

                # Level 1: facility / group — points to the group's first page
                toc.append([1, group_key, current_output_page + 1])

                for visit in group_visits:
                    section = getattr(visit, "section_type", "medical_record") or "medical_record"
                    visit_start_out = current_output_page + 1

                    for src_idx in range(visit.start_page - 1, visit.end_page):
                        if 0 <= src_idx < source.page_count:
                            output.insert_pdf(source, from_page=src_idx, to_page=src_idx)
                            current_output_page += 1

                    visit_end_out = current_output_page

                    # Bookmark LABEL uses the ORIGINAL source page numbers that were
                    # marked in the tool (so it cross-references the source record),
                    # not the re-sequenced position in the combined output. The bookmark
                    # still NAVIGATES to the visit's page in the combined PDF via
                    # visit_start_out below.
                    if visit.start_page == visit.end_page:
                        pg_range = f"pg {visit.start_page}"
                    else:
                        pg_range = f"pg {visit.start_page}-{visit.end_page}"

                    if section in MEDICAL_SECTIONS:
                        all_facilities.add(group_key)
                        dos_label = visit.date_of_service or "No DOS"
                        provider_label = visit.provider_name or "Unknown Provider"
                        visit_title = f"{dos_label} / {provider_label} ({pg_range})"
                    else:
                        notes_label = (visit.notes or "").strip()
                        visit_title = pg_range
                        if notes_label:
                            visit_title += f" - {notes_label}"

                    # Level 2: visit under its facility / group
                    toc.append([2, visit_title, visit_start_out])

                    processed_count += 1
                    if progress_callback:
                        progress_callback(processed_count, total_visits)

            if toc:
                output.set_toc(toc)

            output.save(output_path, deflate=False, incremental=False)

        return {
            "page_count": current_output_page,
            "visit_count": len(visits),
            "facilities": sorted(list(all_facilities)),
        }
