from sqlalchemy import (
    Column, String, Integer, Text, DateTime, Float, ForeignKey, Boolean
)
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

from .database import Base


def generate_uuid():
    return str(uuid.uuid4())


class UploadedPDF(Base):
    __tablename__ = "uploaded_pdfs"

    id = Column(String, primary_key=True, default=generate_uuid)
    original_filename = Column(String, nullable=False)
    file_path = Column(String, nullable=False)
    page_count = Column(Integer, nullable=False)
    file_size = Column(Integer, nullable=False)
    uploaded_at = Column(DateTime, default=datetime.utcnow)

    preprocessing_status = Column(String, default="pending")
    extracted_text = Column(Text, nullable=True)
    auto_suggestions = Column(Text, nullable=True)
    is_digital = Column(Boolean, default=True)
    text_extraction_method = Column(String, nullable=True)

    visits = relationship(
        "VisitAnnotation",
        back_populates="pdf",
        cascade="all, delete-orphan",
        order_by="VisitAnnotation.start_page"
    )
    processed_versions = relationship(
        "ProcessedPDF",
        back_populates="source_pdf",
        cascade="all, delete-orphan"
    )


class VisitAnnotation(Base):
    __tablename__ = "visit_annotations"

    id = Column(String, primary_key=True, default=generate_uuid)
    pdf_id = Column(String, ForeignKey("uploaded_pdfs.id"), nullable=False)
    start_page = Column(Integer, nullable=False)
    end_page = Column(Integer, nullable=False)
    date_of_service = Column(String, default="")
    facility_name = Column(String, default="")
    provider_name = Column(String, default="")
    document_type = Column(String, nullable=False, default="other")
    section_type = Column(String, nullable=False, default="medical_record")
    notes = Column(Text, default="")
    version = Column(Integer, default=1, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    confidence = Column(Float, nullable=True)
    source = Column(String, default="manual")
    allow_overlap = Column(Boolean, default=False, nullable=False)

    pdf = relationship("UploadedPDF", back_populates="visits")


class SessionState(Base):
    __tablename__ = "session_state"

    key = Column(String, primary_key=True)
    value = Column(Text, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class AuditLog(Base):
    __tablename__ = "audit_log"

    id = Column(String, primary_key=True, default=generate_uuid)
    timestamp = Column(DateTime, default=datetime.utcnow)
    action = Column(String, nullable=False)
    entity_type = Column(String)
    entity_id = Column(String)
    details = Column(Text, default="{}")


class FacilityPattern(Base):
    __tablename__ = "facility_patterns"

    id = Column(String, primary_key=True, default=generate_uuid)
    facility_name = Column(String, nullable=False, index=True)
    normalized_name = Column(String, nullable=False, index=True)
    common_document_types = Column(Text, default="[]")  # JSON list
    avg_page_count = Column(Float, default=0)
    provider_names = Column(Text, default="[]")  # JSON list
    dos_formats_seen = Column(Text, default="[]")  # JSON list
    sample_count = Column(Integer, default=1)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class ProcessedPDF(Base):
    __tablename__ = "processed_pdfs"

    id = Column(String, primary_key=True, default=generate_uuid)
    source_pdf_id = Column(String, ForeignKey("uploaded_pdfs.id"), nullable=False)
    file_path = Column(String, nullable=False)
    page_count = Column(Integer, nullable=False)
    visit_count = Column(Integer, nullable=False)
    facilities_json = Column(Text, default="[]")
    processed_at = Column(DateTime, default=datetime.utcnow)

    status = Column(String, default="queued")
    progress = Column(String, nullable=True)
    download_url = Column(String, nullable=True)
    error_message = Column(String, nullable=True)
    total_visits = Column(Integer, nullable=True)
    total_pages_extracted = Column(Integer, nullable=True)

    source_pdf = relationship("UploadedPDF", back_populates="processed_versions")

def upgrade_tables(engine):
    """Add new columns to existing tables without losing data."""
    import sqlite3
    conn = sqlite3.connect(engine.url.database)
    cursor = conn.cursor()
    
    # For each new column, try to add it (ignore if already exists)
    alterations = [
        "ALTER TABLE uploaded_pdfs ADD COLUMN preprocessing_status TEXT DEFAULT 'pending'",
        "ALTER TABLE uploaded_pdfs ADD COLUMN extracted_text TEXT",
        "ALTER TABLE uploaded_pdfs ADD COLUMN auto_suggestions TEXT",
        "ALTER TABLE uploaded_pdfs ADD COLUMN is_digital BOOLEAN DEFAULT 1",
        "ALTER TABLE uploaded_pdfs ADD COLUMN text_extraction_method TEXT",
        "ALTER TABLE visit_annotations ADD COLUMN confidence REAL",
        "ALTER TABLE visit_annotations ADD COLUMN source TEXT DEFAULT 'manual'",
        "ALTER TABLE visit_annotations ADD COLUMN version INTEGER DEFAULT 1",
        "ALTER TABLE visit_annotations ADD COLUMN section_type TEXT DEFAULT 'medical_record'",
        "ALTER TABLE visit_annotations ADD COLUMN allow_overlap BOOLEAN DEFAULT 0",
        "ALTER TABLE processed_pdfs ADD COLUMN status TEXT DEFAULT 'queued'",
        "ALTER TABLE processed_pdfs ADD COLUMN progress TEXT",
        "ALTER TABLE processed_pdfs ADD COLUMN download_url TEXT",
        "ALTER TABLE processed_pdfs ADD COLUMN error_message TEXT",
        "ALTER TABLE processed_pdfs ADD COLUMN total_visits INTEGER",
        "ALTER TABLE processed_pdfs ADD COLUMN total_pages_extracted INTEGER",
    ]
    for alt in alterations:
        try:
            cursor.execute(alt)
        except sqlite3.OperationalError:
            pass  # Column already exists
    conn.commit()
    conn.close()