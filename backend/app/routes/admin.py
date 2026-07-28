from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from ..database import get_db
from ..cleanup.lifecycle_manager import LifecycleManager
from ..services.session_service import SessionService
from ..db_models import AuditLog
from pydantic import BaseModel

router = APIRouter(prefix="/api/admin", tags=["Admin"])

class ResetConfirm(BaseModel):
    confirm: str

class SessionUpdate(BaseModel):
    key: str
    value: str

@router.get("/storage-stats")
async def get_storage_stats():
    return LifecycleManager.get_storage_stats()

@router.post("/cleanup-orphans")
async def cleanup_orphans(db: Session = Depends(get_db)):
    count = LifecycleManager.cleanup_orphans(db)
    return {"status": "success", "deleted_files": count}

@router.delete("/factory-reset")
async def factory_reset(request: ResetConfirm, db: Session = Depends(get_db)):
    if request.confirm != "RESET_ALL_DATA":
        return {"error": "Invalid confirmation string"}
    result = LifecycleManager.factory_reset(db)
    return result

@router.put("/session")
async def update_session(data: SessionUpdate, db: Session = Depends(get_db)):
    SessionService.save(db, data.key, data.value)
    return {"status": "success"}

@router.get("/session")
async def get_session(db: Session = Depends(get_db)):
    return SessionService.restore(db)

@router.get("/audit-log")
async def get_audit_log(limit: int = 50, entity_id: str = None, db: Session = Depends(get_db)):
    query = db.query(AuditLog).order_by(AuditLog.timestamp.desc())
    if entity_id:
        query = query.filter(AuditLog.entity_id == entity_id)
    return query.limit(limit).all()
