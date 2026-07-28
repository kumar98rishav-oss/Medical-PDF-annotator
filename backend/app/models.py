from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from enum import Enum


class DocumentType(str, Enum):
    PROGRESS_NOTE = "progress_note"
    RADIOLOGY_REPORT = "radiology_report"
    PROCEDURE_NOTE = "procedure_note"
    DISCHARGE_SUMMARY = "discharge_summary"
    CONSULTATION_NOTE = "consultation_note"
    OPERATIVE_NOTE = "operative_note"
    LAB_REPORT = "lab_report"
    PATHOLOGY_REPORT = "pathology_report"
    EMERGENCY_NOTE = "emergency_note"
    NURSING_NOTE = "nursing_note"
    THERAPY_NOTE = "therapy_note"
    PRESCRIPTION = "prescription"
    IMAGING_REPORT = "imaging_report"
    INTAKE_FORM = "intake_form"
    INSURANCE_AUTH = "insurance_authorization"
    REFERRAL = "referral"
    OTHER = "other"


# ---------- Visit ----------

class VisitCreate(BaseModel):
    start_page: int = Field(..., ge=1)
    end_page: int = Field(..., ge=1)
    date_of_service: str = ""
    facility_name: str = ""
    provider_name: str = ""
    document_type: str = "other"
    section_type: str = "medical_record"
    notes: str = ""
    confidence: Optional[float] = None
    source: Optional[str] = "manual"
    allow_overlap: Optional[bool] = False


class VisitUpdate(BaseModel):
    start_page: Optional[int] = None
    end_page: Optional[int] = None
    date_of_service: Optional[str] = None
    facility_name: Optional[str] = None
    provider_name: Optional[str] = None
    document_type: Optional[str] = None
    section_type: Optional[str] = None
    notes: Optional[str] = None
    confidence: Optional[float] = None
    source: Optional[str] = None
    allow_overlap: Optional[bool] = None


class VisitResponse(BaseModel):
    id: str
    pdf_id: str
    start_page: int
    end_page: int
    date_of_service: str
    facility_name: str
    provider_name: str
    document_type: str
    section_type: str
    notes: str
    version: int
    created_at: datetime
    confidence: Optional[float]
    source: str
    allow_overlap: bool = False

    class Config:
        from_attributes = True


class OverlapInfo(BaseModel):
    conflicting_visit_id: str
    overlap_pages: List[int]
    severity: str


class VisitCreateResponse(BaseModel):
    visit: VisitResponse
    warnings: Optional[List[OverlapInfo]] = None


# ---------- PDF ----------

class PDFUploadResponse(BaseModel):
    id: str
    filename: str
    page_count: int
    file_size: int


class PDFInfoResponse(BaseModel):
    id: str
    filename: str
    page_count: int
    file_size: int
    uploaded_at: datetime
    visit_count: int
    marked_pages: int
    total_visit_pages: int
    
class PDFStatusResponse(BaseModel):
    preprocessing_status: str
    is_digital: bool
    text_extraction_method: Optional[str] = None
    suggestions_count: int = 0


class PDFListItem(BaseModel):
    id: str
    filename: str
    page_count: int
    file_size: int
    uploaded_at: datetime
    visit_count: int


# ---------- Process ----------

class ProcessResponse(BaseModel):
    id: str
    page_count: int
    visit_count: int
    facilities: List[str]
    download_url: str

class JobStatusResponse(BaseModel):
    job_id: str
    status: str
    progress: Optional[str] = None
    download_url: Optional[str] = None
    poll_url: Optional[str] = None
    error_message: Optional[str] = None



class QuickAnnotateRequest(BaseModel):
    start_page: int = Field(..., ge=1)
    end_page: int = Field(..., ge=1)

class AIExtractRequest(BaseModel):
    start_page: int = Field(..., ge=1)
    end_page: int = Field(..., ge=1)
    api_key: str

class QuickAnnotateResponse(BaseModel):
    start_page: int
    end_page: int
    facilities: List[str] = []
    providers: List[str] = []
    dates_of_service: List[str] = []
    document_types: List[str] = []
    known_facilities: List[dict] = []  # from FacilityPattern DB

class BatchUploadResponse(BaseModel):
    uploaded: int
    pdf_ids: List[str]



class BatchProcessResponse(BaseModel):
    jobs: List[dict]


# ---------- Facility ----------

class FacilitySuggestion(BaseModel):
    facility_name: str
    common_types: List[str]
    avg_pages: float
    providers: List[str]
    times_seen: int