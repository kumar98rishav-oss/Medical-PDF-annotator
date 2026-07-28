import difflib
import json
from sqlalchemy.orm import Session
from typing import List, Dict, Optional, Any
from .db_models import FacilityPattern

class SmartMatcher:
    """Uses FacilityPattern table to enrich auto-detection results."""

    def __init__(self, db: Session):
        self.db = db
        self.patterns = self.db.query(FacilityPattern).all()

    def fuzzy_match_facility(self, extracted_name: str, threshold: float = 0.65) -> Optional[Dict[str, Any]]:
        """Finds closest known facility name."""
        if not extracted_name:
            return None

        normalized_extracted = " ".join(extracted_name.strip().lower().split())

        best_match = None
        best_ratio = 0.0

        for pattern in self.patterns:
            ratio = difflib.SequenceMatcher(None, normalized_extracted, pattern.normalized_name).ratio()
            if ratio > best_ratio:
                best_ratio = ratio
                best_match = pattern

        if best_match and best_ratio >= threshold:
            try:
                common_doc_types = json.loads(best_match.common_document_types)
            except Exception:
                common_doc_types = []

            try:
                common_providers = json.loads(best_match.provider_names)
            except Exception:
                common_providers = []

            return {
                "facility_name": best_match.facility_name,
                "common_doc_types": common_doc_types,
                "common_providers": common_providers,
                "confidence": best_ratio
            }
        
        return None

    def enrich_visits(self, auto_visits: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Takes auto-detected visits and matches facility names against known patterns."""
        for visit in auto_visits:
            if visit.get("facility_name"):
                match = self.fuzzy_match_facility(visit["facility_name"])
                if match:
                    # Normalize facility name
                    visit["facility_name"] = match["facility_name"]
                    
                    # Fill missing provider
                    if not visit.get("provider_name") and match["common_providers"]:
                        # Just take the first common provider for now
                        visit["provider_name"] = match["common_providers"][0]
                        visit["confidence"] = min(1.0, visit.get("confidence", 0) + 0.1)

                    # Fill missing doc type
                    if (not visit.get("document_type") or visit["document_type"] == "Unknown") and match["common_doc_types"]:
                        visit["document_type"] = match["common_doc_types"][0]
                        visit["confidence"] = min(1.0, visit.get("confidence", 0) + 0.1)

            # Ensure expected dictionary format
            visit["confidence"] = visit.get("confidence", 0.0)
            
        return auto_visits

    def scan_text_for_known_entities(self, text: str) -> Dict[str, List[str]]:
        """
        Scans raw text against the entire FacilityPattern historical database.
        Returns a dictionary of matched facilities and providers.
        """
        if not text:
            return {"facilities": [], "providers": []}

        matched_facilities = set()
        matched_providers = set()
        
        normalized_text = " ".join(text.strip().lower().split())

        for pattern in self.patterns:
            # Check facility name
            if pattern.normalized_name and pattern.normalized_name in normalized_text:
                if len(pattern.normalized_name) > 5:  # Avoid matching very short trivial words
                    matched_facilities.add(pattern.facility_name)
                    
            # Check popular providers from this facility
            try:
                common_providers = json.loads(pattern.provider_names) if pattern.provider_names else []
                for prov in common_providers:
                    if not prov or len(prov) < 5:
                        continue
                    prov_norm = " ".join(prov.strip().lower().split())
                    # Strip 'Dr.' or 'MD' to find pure name matches if necessary, but exact match is safer first
                    if prov_norm in normalized_text:
                        matched_providers.add(prov)
            except Exception:
                pass

        return {
            "facilities": list(matched_facilities),
            "providers": list(matched_providers)
        }
