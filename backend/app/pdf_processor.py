"""
PDF Processing Engine
- Renders pages as images for the viewer
- Creates processed PDFs with bookmarks, page filtering, chronological ordering
"""

import fitz  # PyMuPDF
from pathlib import Path
from typing import List, Dict, Tuple
from datetime import datetime
from dateutil.parser import parse as parse_date


class PDFProcessor:
    """Handles all PDF manipulation operations."""

    # ──────────────────────────────────────────────
    #  Inspection
    # ──────────────────────────────────────────────

    @staticmethod
    def get_page_count(pdf_path: str) -> int:
        with fitz.open(pdf_path) as doc:
            return doc.page_count

    @staticmethod
    def get_file_size(pdf_path: str) -> int:
        return Path(pdf_path).stat().st_size

    # ──────────────────────────────────────────────
    #  Page Rendering (for frontend viewer)
    # ──────────────────────────────────────────────

    @staticmethod
    def render_page_image(
        pdf_path: str,
        page_num: int,
        zoom: float = 1.5
    ) -> bytes:
        """
        Render a single page as PNG.
        page_num is 1-indexed (matches what users see).
        """
        with fitz.open(pdf_path) as doc:
            if page_num < 1 or page_num > doc.page_count:
                raise ValueError(
                    f"Page {page_num} out of range (1-{doc.page_count})"
                )
            page = doc[page_num - 1]
            mat = fitz.Matrix(zoom, zoom)
            pix = page.get_pixmap(matrix=mat, alpha=False)
            return pix.tobytes("png")

    # ──────────────────────────────────────────────
    #  Core Processing: Build annotated PDF
    # ──────────────────────────────────────────────

    @staticmethod
    def _parse_dos(dos_str: str) -> datetime:
        """Parse date of service string into datetime for sorting."""
        if not dos_str or not dos_str.strip():
            return datetime.min
        try:
            return parse_date(dos_str.strip(), fuzzy=True)
        except (ValueError, TypeError):
            return datetime.min

    @staticmethod
    def process_annotated_pdf(
        source_path: str,
        visits: list,
        output_path: str
    ) -> Dict:
        """
        Build a new PDF containing only annotated visit pages.

        Organization:
          Level 1 bookmark: Facility Name (alphabetical ascending)
            Level 2 bookmark: DOS | Document Type | Provider
              (DOS ascending — oldest first, newest last)
              Pages for that visit

        NO compression applied — preserves original quality
        for downstream MEDNEX pipeline processing.

        Returns dict with page_count, visit_count, facilities list.
        """
        source = fitz.open(source_path)
        output = fitz.Document()

        # ── Group visits by facility ──
        facility_map: Dict[str, list] = {}
        for v in visits:
            key = (v.facility_name or "Unknown Facility").strip()
            if key not in facility_map:
                facility_map[key] = []
            facility_map[key].append(v)

        # ── Sort: facilities alphabetically ──
        sorted_facilities = sorted(facility_map.keys(), key=str.lower)

        # ──────────────────────────────────────────
        # FIX 1: Sort by DOS ASCENDING (oldest → newest)
        #        reverse=False means oldest date first
        # ──────────────────────────────────────────
        for fac in sorted_facilities:
            facility_map[fac].sort(
                key=lambda v: PDFProcessor._parse_dos(v.date_of_service),
                reverse=False   # ← ASCENDING: oldest first, newest last
            )

        toc: List[Tuple[int, str, int]] = []   # [level, title, page_number]
        current_output_page = 0

        for facility in sorted_facilities:
            # Facility-level bookmark (1-indexed page number for fitz TOC)
            toc.append([1, f"📋 {facility}", current_output_page + 1])

            for visit in facility_map[facility]:
                # Visit-level bookmark
                doc_type_label = visit.document_type.replace("_", " ").title()
                dos_label = visit.date_of_service or "No DOS"
                provider_label = visit.provider_name or "Unknown Provider"
                visit_title = f"{dos_label}  ·  {doc_type_label}  ·  {provider_label}"

                toc.append([2, visit_title, current_output_page + 1])

                # Copy pages (start_page and end_page are 1-indexed)
                for src_page_idx in range(visit.start_page - 1, visit.end_page):
                    if 0 <= src_page_idx < source.page_count:
                        output.insert_pdf(
                            source,
                            from_page=src_page_idx,
                            to_page=src_page_idx
                        )
                        current_output_page += 1

        # ── Set TOC / Bookmarks ──
        if toc:
            output.set_toc(toc)

        # ──────────────────────────────────────────
        # FIX 2: Save WITHOUT compression
        #        No garbage collection, no deflate, no clean
        #        Preserves original quality for MEDNEX pipeline
        # ──────────────────────────────────────────
        output.save(output_path)

        total_pages = current_output_page

        output.close()
        source.close()

        return {
            "page_count": total_pages,
            "visit_count": len(visits),
            "facilities": sorted_facilities,
        }