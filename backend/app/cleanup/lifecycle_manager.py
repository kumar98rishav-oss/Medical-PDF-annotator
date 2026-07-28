import os
import shutil
from pathlib import Path
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from ..config import UPLOAD_DIR, PROCESSED_DIR, DATABASE_PATH, LOG_DIR, TEMP_DIR, MAX_PROCESSED_AGE_DAYS, MAX_LOG_AGE_DAYS
from ..db_models import UploadedPDF, ProcessedPDF, Base
from ..database import engine, backup_database
from ..errors import StorageError

class LifecycleManager:
    """Manages disk space, orphan files, and factory resets."""

    @staticmethod
    def _dir_size(directory: Path) -> int:
        if not directory.exists():
            return 0
        return sum(f.stat().st_size for f in directory.rglob('*') if f.is_file())

    @staticmethod
    def _dir_count(directory: Path) -> int:
        if not directory.exists():
            return 0
        return sum(1 for f in directory.rglob('*') if f.is_file())

    @staticmethod
    def get_storage_stats() -> dict:
        db_size = DATABASE_PATH.stat().st_size if DATABASE_PATH.exists() else 0
        return {
            "uploads_size": LifecycleManager._dir_size(UPLOAD_DIR),
            "uploads_count": LifecycleManager._dir_count(UPLOAD_DIR),
            "processed_size": LifecycleManager._dir_size(PROCESSED_DIR),
            "processed_count": LifecycleManager._dir_count(PROCESSED_DIR),
            "logs_size": LifecycleManager._dir_size(LOG_DIR),
            "logs_count": LifecycleManager._dir_count(LOG_DIR),
            "temp_size": LifecycleManager._dir_size(TEMP_DIR),
            "database_size": db_size,
        }

    @staticmethod
    def find_orphan_files(db: Session) -> list[Path]:
        """Find files in storage directories with no corresponding DB record."""
        orphans = []
        
        # Check uploads
        db_upload_paths = {Path(p[0]) for p in db.query(UploadedPDF.file_path).all()}
        for f in UPLOAD_DIR.glob('*.pdf'):
            if f not in db_upload_paths:
                orphans.append(f)

        # Check processed
        db_processed_paths = {Path(p[0]) for p in db.query(ProcessedPDF.file_path).all()}
        for f in PROCESSED_DIR.glob('*.pdf'):
            if f not in db_processed_paths:
                orphans.append(f)
                
        # Also zip files in temp etc
        for f in PROCESSED_DIR.glob('*.zip'):
            if f not in db_processed_paths:
                orphans.append(f)

        return orphans

    @staticmethod
    def cleanup_orphans(db: Session) -> int:
        orphans = LifecycleManager.find_orphan_files(db)
        count = 0
        for f in orphans:
            try:
                f.unlink(missing_ok=True)
                count += 1
            except Exception:
                pass
        return count

    @staticmethod
    def cleanup_processed(db: Session, older_than_days: int = MAX_PROCESSED_AGE_DAYS) -> int:
        cutoff = datetime.utcnow() - timedelta(days=older_than_days)
        old_records = db.query(ProcessedPDF).filter(ProcessedPDF.processed_at < cutoff).all()
        count = 0
        for record in old_records:
            try:
                Path(record.file_path).unlink(missing_ok=True)
                db.delete(record)
                count += 1
            except Exception:
                pass
        db.commit()
        return count

    @staticmethod
    def cleanup_temp() -> int:
        count = 0
        if TEMP_DIR.exists():
            for item in TEMP_DIR.iterdir():
                try:
                    if item.is_file():
                        item.unlink()
                    elif item.is_dir():
                        shutil.rmtree(item)
                    count += 1
                except Exception:
                    pass
        return count

    @staticmethod
    def factory_reset(db: Session) -> dict:
        """Atomic nuclear reset."""
        backup_dir = DATABASE_PATH.parent / "backups"
        backup_dir.mkdir(exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = backup_dir / f"annotator_backup_{timestamp}.db"
        
        try:
            # Drop connections and backup
            backup_database(backup_file)
            
            # Wipe DB
            Base.metadata.drop_all(bind=engine)
            Base.metadata.create_all(bind=engine)
            
            # Wipe files
            def wipe_dir(d: Path):
                deleted = 0
                for item in d.iterdir():
                    try:
                        if item.is_file():
                            item.unlink()
                        elif item.is_dir():
                            shutil.rmtree(item)
                        deleted += 1
                    except Exception:
                        pass
                return deleted

            up_del = wipe_dir(UPLOAD_DIR)
            proc_del = wipe_dir(PROCESSED_DIR)
            tmp_del = wipe_dir(TEMP_DIR)
            
            return {
                "status": "success",
                "backup_created": str(backup_file),
                "deleted_files_count": up_del + proc_del + tmp_del
            }
        except Exception as e:
            raise StorageError("Factory reset failed", internal_detail=str(e))
