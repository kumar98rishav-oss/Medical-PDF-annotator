"""
Auto-detect routes — REMOVED.
Full auto-annotation has been replaced with a suggestion-based workflow.
Use POST /api/pdf/{pdf_id}/quick-annotate instead.
"""
from fastapi import APIRouter

router = APIRouter(prefix="/api", tags=["AutoDetect"])

# No endpoints — auto-detect has been replaced by quick-annotate suggestions.
# This file is kept as a stub so the router import in main.py doesn't break.
