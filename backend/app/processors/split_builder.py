import fitz
import re
import zipfile
from pathlib import Path
from typing import List, Dict
from ..models import VisitResponse

# Section labels for folder/filename prefixes
SECTION_LABELS = {
    "injury_photo":    "Injury Photos",
    "vehicle_photo":   "Vehicle Photos",
    "medical_record":  "Medical Records",
    "medical_bill":    "Medical Billing",
    "other":           "Other Documents",
}

SIMPLE_SECTIONS = {"injury_photo", "vehicle_photo", "other"}

# Sections that carry facility metadata
MEDICAL_SECTIONS = {"medical_record", "medical_bill"}


class SplitBuilder:
    """Handles building individual PDFs and bundling them into a ZIP (Mode 2).

    ZIP layout: one folder per facility (or section label for non-medical
    visits), with each visit's PDF inside its folder.
    """

    def _safe_folder(self, visit: VisitResponse) -> str:
        """Folder name: facility for medical visits, section label otherwise."""
        section = getattr(visit, 'section_type', 'medical_record') or 'medical_record'
        if section in MEDICAL_SECTIONS:
            folder = (visit.facility_name or "Unknown Facility").strip()
        else:
            folder = SECTION_LABELS.get(section, "Other Documents")
        # Sanitize windows path chars (no slashes — keep it a single folder level)
        return re.sub(r'[\\/:*?"<>|]', '_', folder)[:120] or "Unknown Facility"

    def _safe_filename(self, visit: VisitResponse) -> str:
        section = getattr(visit, 'section_type', 'medical_record') or 'medical_record'
        section_label = SECTION_LABELS.get(section, section)

        if section in SIMPLE_SECTIONS:
            # Simple sections: just page range + notes
            parts = [
                f"[{section_label}]",
                f"Pg{visit.start_page}-{visit.end_page}",
            ]
            if visit.notes and visit.notes.strip():
                parts.append(visit.notes.strip()[:60])
        else:
            # Medical sections: full metadata
            parts = [
                f"[{section_label}]",
                visit.date_of_service.strip() if visit.date_of_service else "NoDate",
                visit.document_type.replace("_", " ").title() if visit.document_type else "Other",
                visit.facility_name.strip() if visit.facility_name else "UnknownFacility",
                visit.provider_name.strip() if visit.provider_name else "UnknownProvider",
            ]

        raw = " - ".join(parts) + ".pdf"
        # Sanitize windows filename chars
        safe = re.sub(r'[\\/:*?"<>|]', '_', raw)
        return safe[:200]

    def build(self, source_path: str, visits: List[VisitResponse], output_zip_path: str, progress_callback=None) -> Dict:
        """
        Build individual PDFs and ZIP them.
        """
        # Dictionary to track arcnames (folder/file) to handle duplicates
        used_names = {}
        # Each entry: (temp_path_on_disk, arcname_inside_zip)
        processed_files = []
        out_dir = Path(output_zip_path).parent / f"temp_{Path(output_zip_path).stem}"
        out_dir.mkdir(parents=True, exist_ok=True)

        total_pages_copied = 0
        facilities = set()
        temp_counter = 0

        try:
            with fitz.open(source_path) as source:
                processed_count = 0
                total_visits = len(visits)
                for visit in visits:
                    fac_name = (visit.facility_name or "Unknown Facility").strip()
                    facilities.add(fac_name)

                    folder = self._safe_folder(visit)
                    base_name = self._safe_filename(visit)

                    # Deduplicate by full folder/file path inside the zip
                    arc_key = f"{folder}/{base_name}"
                    if arc_key in used_names:
                        used_names[arc_key] += 1
                        stem = Path(base_name).stem
                        file_name = f"{stem}_{used_names[arc_key]}.pdf"
                    else:
                        used_names[arc_key] = 1
                        file_name = base_name

                    arcname = f"{folder}/{file_name}"

                    # Flat unique name on disk; nested path only inside the zip
                    temp_counter += 1
                    visit_pdf_path = out_dir / f"{temp_counter}.pdf"

                    # Stream single visit into a new document
                    with fitz.open() as single_pdf:
                        for src_page_idx in range(visit.start_page - 1, visit.end_page):
                            if 0 <= src_page_idx < source.page_count:
                                single_pdf.insert_pdf(
                                    source,
                                    from_page=src_page_idx,
                                    to_page=src_page_idx
                                )
                                total_pages_copied += 1
                        single_pdf.save(str(visit_pdf_path), deflate=False, incremental=False)
                    processed_files.append((visit_pdf_path, arcname))

                    processed_count += 1
                    if progress_callback:
                        progress_callback(processed_count, total_visits)

            # Zip all individual files using ZIP_STORED (faster, no recompress)
            with zipfile.ZipFile(output_zip_path, 'w', compression=zipfile.ZIP_STORED) as zipf:
                for fpath, arcname in processed_files:
                    zipf.write(fpath, arcname=arcname)
        finally:
            # Clean up the temp directory
            for fpath, _ in processed_files:
                fpath.unlink(missing_ok=True)
            if out_dir.exists():
                out_dir.rmdir()

        return {
            "page_count": total_pages_copied,
            "visit_count": len(visits),
            "facilities": sorted(list(facilities)),
        }
