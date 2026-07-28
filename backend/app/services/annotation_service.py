import uuid
import json
from datetime import datetime
from sqlalchemy.orm import Session
from ..db_models import VisitAnnotation, FacilityPattern, AuditLog
from ..models import VisitCreate, VisitResponse
from ..validators.annotation_validator import AnnotationValidator

class AnnotationService:
    """Handles visit annotations and facility learning."""

    @staticmethod
    def _normalize_facility(name: str) -> str:
        return " ".join(name.strip().lower().split())

    @staticmethod
    def learn_facility(db: Session, visit: VisitCreate):
        """Learn from a new visit annotation."""
        raw_name = (visit.facility_name or "").strip()
        if not raw_name:
            return

        normalized = AnnotationService._normalize_facility(raw_name)
        page_count = visit.end_page - visit.start_page + 1

        pattern = db.query(FacilityPattern).filter(FacilityPattern.normalized_name == normalized).first()

        if pattern:
            try:
                existing_types = json.loads(pattern.common_document_types)
            except:
                existing_types = []
            if visit.document_type not in existing_types:
                existing_types.append(visit.document_type)
            pattern.common_document_types = json.dumps(existing_types)

            n = pattern.sample_count
            pattern.avg_page_count = ((pattern.avg_page_count * n) + page_count) / (n + 1)

            try:
                existing_providers = json.loads(pattern.provider_names)
            except:
                existing_providers = []
            prov = (visit.provider_name or "").strip()
            if prov and prov not in existing_providers:
                existing_providers.append(prov)
            pattern.provider_names = json.dumps(existing_providers)

            pattern.sample_count += 1
            pattern.updated_at = datetime.utcnow()
        else:
            prov = (visit.provider_name or "").strip()
            pattern = FacilityPattern(
                id=str(uuid.uuid4()),
                facility_name=raw_name,
                normalized_name=normalized,
                common_document_types=json.dumps([visit.document_type]),
                avg_page_count=float(page_count),
                provider_names=json.dumps([prov] if prov else []),
                sample_count=1,
            )
            db.add(pattern)

    @staticmethod
    def log_audit(db: Session, action: str, entity_type: str, entity_id: str, details: dict):
        log = AuditLog(
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            details=json.dumps(details)
        )
        db.add(log)
