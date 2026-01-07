"""Explainability endpoints (redundant with prediction/explain, but kept for clarity)."""
from fastapi import APIRouter

router = APIRouter(prefix="/v1", tags=["explainability"])

# This router is kept for future expansion
# Main explainability endpoint is in prediction.py as /explain




