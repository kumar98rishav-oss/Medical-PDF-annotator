from datetime import datetime
from sqlalchemy.orm import Session
from ..db_models import SessionState

class SessionService:
    """Manages crash-safe UI session state."""

    @staticmethod
    def save(db: Session, key: str, value: str):
        existing = db.query(SessionState).filter_by(key=key).first()
        if existing:
            existing.value = value
            existing.updated_at = datetime.utcnow()
        else:
            db.add(SessionState(key=key, value=value))
        db.commit()

    @staticmethod
    def restore(db: Session) -> dict:
        rows = db.query(SessionState).all()
        return {r.key: r.value for r in rows}
