import shutil
from pathlib import Path
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, declarative_base
from .config import DATABASE_URL, DATABASE_PATH

engine = create_engine(
    DATABASE_URL,
    connect_args={
        "check_same_thread": False,
        "timeout": 30,  # Busy timeout to prevent lock issues in concurrent accesses (even in single user, might happen)
    },
    echo=False,
    pool_pre_ping=True,
)

@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_conn, _):
    cursor = dbapi_conn.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA synchronous=NORMAL")
    cursor.execute("PRAGMA busy_timeout=30000")
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def backup_database(target_path: Path):
    """Create an atomic SQLite backup before destructive ops."""
    import sqlite3
    src = sqlite3.connect(str(DATABASE_PATH))
    dst = sqlite3.connect(str(target_path))
    with dst:
        src.backup(dst)
    dst.close()
    src.close()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()