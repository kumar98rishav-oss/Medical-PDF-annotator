"""
Suggestion Extractor — scans text and returns ALL possible matches
for facility names, provider names, dates of service, and document types.

This is NOT an auto-annotator. It extracts candidates that a user reviews
and clicks to autofill into the annotation form.
"""
import re
from typing import List, Dict, Any, Optional
import logging

try:
    from dateutil.parser import parse as parse_date
    DATEUTIL_AVAILABLE = True
except ImportError:
    DATEUTIL_AVAILABLE = False
    logging.warning("python-dateutil not installed. Date parsing will be limited.")

logger = logging.getLogger(__name__)

DOS_PATTERNS = [
    r'(?:Date\s*of\s*Service|DOS|Service\s*Date|Visit\s*Date|Encounter\s*Date|Visit|Appt|Appointment)\s*[:\-]?\s*(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4})',
    r'(?:Admission|Admit|Discharge)\s*Date\s*[:\-]?\s*(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4})',
    # Bill-specific date labels
    r'(?:Statement\s*Date|Bill\s*Date|Invoice\s*Date|Due\s*Date|Billing\s*Date)\s*[:\-]?\s*(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4})',
    r'(?:Date|Dt)\s*[:\-]\s*(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4})',
    # Fallback: catch ANY loose date in MM/DD/YYYY or MM-DD-YYYY format on the page
    r'\b(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4})\b'
]

FACILITY_PATTERNS = [
    # 1. Labeled fields: "Facility: ...", "Hospital: ...", "Office: ..."
    r'(?:Facility|Hospital|Clinic|Practice|Office|Location)\s*(?:Name)?\s*[:\-]\s*([A-Za-z .\&\|\,\'\-]{3,80})',
    # 2. Full name ending with a medical-org suffix, PLUS trailing "of ..." location
    r'^([A-Z][A-Za-z\s\.\-\&\']{3,50}(?:Hospital|Medical\s*Center|Health\s*System|Health\s*Center|Clinic|Center|Associates|Group|Institute|Pain\s*Institute)(?:\s+(?:of|at|in|for)\s+[A-Za-z\s\.\-\&\']{2,40})?)',
    # 3. ALL-CAPS header lines (likely letterhead / facility banners)
    r'(?:^|\n)([A-Z][A-Z\s\.\-\&\']{8,70})(?:\n|$)',
]

# ── Section headings & common phrases that are NOT facility names ──
# These appear frequently in medical records and must be filtered out.
FACILITY_BLACKLIST = {
    # Document section headers
    'medical history', 'past medical history', 'past medical',
    'medical history past medical', 'history of present illness',
    'history of present', 'present illness', 'social history',
    'family history', 'surgical history', 'past surgical history',
    'review of systems', 'physical examination', 'physical exam',
    'chief complaint', 'chief complaints', 'assessment and plan',
    'assessment plan', 'plan of care', 'plan of treatment',
    'medications', 'medication list', 'current medications',
    'allergies', 'medications allergies', 'medications and allergies',
    'vital signs', 'vitals', 'laboratory results', 'lab results',
    'imaging results', 'radiology results', 'test results',
    'diagnosis', 'diagnoses', 'impression', 'impressions',
    'recommendations', 'follow up', 'follow up instructions',
    'discharge instructions', 'discharge summary',
    'operative report', 'procedure note', 'progress note',
    'consultation note', 'clinic note', 'office note',
    'visit summary', 'encounter summary', 'patient information',
    'patient demographics', 'insurance information',
    'emergency contact', 'next of kin',
    # Common boilerplate
    'confidential', 'confidentiality notice', 'page of',
    'continued', 'see next page', 'end of report',
    'history and physical', 'history physical',
    'past history', 'interval history',
    'objective', 'subjective', 'assessment',
    'ros', 'hpi', 'pmh', 'psh', 'fh',
}

PROVIDER_PATTERNS = [
    r'(?:Provider|Physician|Doctor|Attending|Referring|Treating|Seen\s*by)\s*[:\-]?\s*(?:Dr\.?\s*)?([A-Z][A-Za-z\-]+[\s,]+[A-Z][A-Za-z\-]+(?:[\s,]+[A-Z][A-Za-z\-]+)?(?:\s*,?\s*(?:MD|DO|NP|PA|PhD|APRN|FNP))?)',
    r'Dr\.?\s+([A-Z][A-Za-z\-]+\s+[A-Z][A-Za-z\-]+(?:[\s,]+[A-Z][A-Za-z\-]+)?)',
    r'([A-Z][A-Za-z\-]+[\s,]+[A-Z][A-Za-z\-]+(?:[\s,]+[A-Z][A-Za-z\-]+)?)\s*,?\s*(?:MD|DO|NP|PA|PhD|APRN|FNP)',
]

DOC_TYPE_KEYWORDS = {
    'Progress Note': ['progress note', 'follow up', 'follow-up', 'office visit', 'clinic note', 'office note', 'soap note'],
    'Discharge Summary': ['discharge summary', 'discharge instructions', 'discharge note'],
    'H&P': ['history and physical', 'h&p', 'h & p', 'admission note', 'initial evaluation'],
    'Operative Report': ['operative report', 'surgical report', 'op note', 'procedure note', 'operation'],
    'Lab Results': ['lab results', 'laboratory', 'blood work', 'cbc', 'bmp', 'cmp', 'lipid panel', 'a1c', 'hemoglobin'],
    'Radiology Report': ['radiology', 'x-ray', 'xray', 'ct scan', 'mri', 'imaging', 'ultrasound', 'mammogram'],
    'Consultation': ['consultation', 'consult note', 'referral note'],
    'Emergency Report': ['emergency', 'er visit', 'ed visit', 'emergency department', 'emergency room'],
    'Prescription/Medications': ['prescription', 'rx', 'medication list', 'med list', 'medication reconciliation'],
    'Physical Therapy': ['physical therapy', 'pt note', 'rehabilitation', 'therapy note'],
    'Mental Health': ['psychiatric', 'psychology', 'mental health', 'behavioral health', 'therapy session'],
    'Pathology Report': ['pathology', 'biopsy', 'cytology', 'histology'],
    'Cardiology': ['cardiology', 'echocardiogram', 'ekg', 'ecg', 'stress test', 'cardiac'],
    'Nursing Note': ['nursing note', 'nurse note', 'rn note', 'nursing assessment'],
    'Medical Bill': [
        'invoice', 'statement', 'bill', 'balance due', 'amount due',
        'amount owed', 'charges', 'total charges', 'payment due',
        'insurance claim', 'itemized', 'billing summary', 'account summary',
        'patient responsibility', 'amount billed'
    ],
}


class SuggestionExtractor:
    """
    Scans text from selected pages and returns ALL possible matches
    for each field. The user picks the correct one from the list.
    """

    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def _normalize_date(self, date_str: str) -> str:
        """Normalize a date string to MM/DD/YYYY format."""
        if not date_str or not DATEUTIL_AVAILABLE:
            return date_str
        try:
            dt = parse_date(date_str, fuzzy=True)
            return dt.strftime("%m/%d/%Y")
        except Exception:
            return date_str

    def extract_all_suggestions(self, text: str) -> Dict[str, Any]:
        """
        Extract ALL possible facility names, provider names, dates of service,
        and document types from the given text.

        Returns:
            {
                "facilities": ["St. Mary's Hospital", "Regional Medical Center", ...],
                "providers": ["Dr. John Smith, MD", "Jane Doe, NP", ...],
                "dates_of_service": ["03/15/2024", "04/01/2024", ...],
                "document_types": ["Progress Note", "Lab Results", ...]
            }
        """
        facilities = []
        providers = []
        dates = []
        doc_types = []

        # ── Collect ALL date matches ──
        for pattern in DOS_PATTERNS:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                raw = match.group(1).strip()
                normalized = self._normalize_date(raw)
                if normalized and normalized not in dates:
                    dates.append(normalized)

        # ── Collect ALL facility matches with scoring ──
        facility_candidates = []  # list of (name, score)
        text_length = max(len(text), 1)
        
        # Keywords that strongly indicate a real facility name
        facility_keywords = {
            'hospital', 'medical', 'health', 'clinic', 'center', 'institute',
            'associates', 'group', 'pain', 'surgery', 'surgical', 'ortho',
            'orthopedic', 'cardiology', 'oncology', 'rehab', 'rehabilitation',
            'urgent', 'care', 'wellness', 'diagnostic', 'imaging', 'labs',
            'laboratory', 'pharmacy', 'physicians', 'specialists', 'foundation',
        }

        for pattern in FACILITY_PATTERNS:
            for match in re.finditer(pattern, text, re.MULTILINE):
                name = match.group(1).strip()
                # Clean up trailing punctuation / whitespace
                name = re.sub(r'[\s,.:;]+$', '', name).strip()
                
                if not name or len(name) < 4:
                    continue
                
                # ── Blacklist check ──
                normalized_lower = ' '.join(name.lower().split())
                if normalized_lower in FACILITY_BLACKLIST:
                    continue
                
                # Check if ANY blacklist phrase is a substring of the candidate
                # (catches "Past Medical History Review" etc.)
                is_blacklisted = False
                for bl in FACILITY_BLACKLIST:
                    if bl in normalized_lower and len(bl) > 4:
                        is_blacklisted = True
                        break
                if is_blacklisted:
                    continue

                # ── Reject single common words ──
                words = name.split()
                if len(words) <= 1:
                    continue  # Single words are almost never facility names

                # ── Score the candidate ──
                score = 0.0

                # Position bonus: earlier in text → more likely to be a header/facility
                position = match.start() / text_length
                if position < 0.05:
                    score += 40  # Very top of text — strong signal
                elif position < 0.15:
                    score += 25
                elif position < 0.30:
                    score += 10

                # Keyword bonus: contains medical-facility-related words
                name_words_lower = set(w.lower() for w in words)
                keyword_hits = name_words_lower & facility_keywords
                score += len(keyword_hits) * 15

                # Multi-word bonus
                score += min(len(words), 6) * 3

                # ALL-CAPS bonus (letterhead style)
                if name == name.upper() and len(name) > 10:
                    score += 20

                # Penalty for very long matches (probably grabbed a whole paragraph)
                if len(name) > 60:
                    score -= 15
                
                # Avoid duplicates (keep higher score)
                existing = next((i for i, (n, _) in enumerate(facility_candidates)
                                 if n.lower() == name.lower()), None)
                if existing is not None:
                    if score > facility_candidates[existing][1]:
                        facility_candidates[existing] = (name, score)
                else:
                    facility_candidates.append((name, score))

        # Sort by score descending, then take the names
        facility_candidates.sort(key=lambda x: -x[1])
        facilities = [name for name, _ in facility_candidates]

        # ── Collect ALL provider matches ──
        for pattern in PROVIDER_PATTERNS:
            for match in re.finditer(pattern, text, re.MULTILINE):
                name = match.group(1).strip()
                name = re.sub(r'[\s,.:]+$', '', name).strip()
                if name and len(name) > 3 and name not in providers:
                    providers.append(name)

        # ── Collect ALL matching document types ──
        text_lower = text.lower()
        for doc_type, keywords in DOC_TYPE_KEYWORDS.items():
            if any(kw in text_lower for kw in keywords):
                if doc_type not in doc_types:
                    doc_types.append(doc_type)

        return {
            "facilities": facilities,
            "providers": providers,
            "dates_of_service": dates,
            "document_types": doc_types,
        }
