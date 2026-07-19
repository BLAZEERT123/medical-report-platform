"""
Upload Router — POST /upload
Handles the full pipeline:
  1. OCR extraction
  2. Structured extraction (LLM + Pydantic)
  3. Rule-based flagging
  4. Plain-language summary (LLM)
  5. SQLite persistence
  6. Chroma Store A indexing
"""
from __future__ import annotations

import logging
from typing import List

from fastapi import APIRouter, File, HTTPException, UploadFile

from backend.models.report import ParsedReportResponse, ReportData
from backend.services import (
    chroma_service,
    extraction_service,
    flagging_service,
    ocr_service,
    store_service,
    summary_service,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/reports", tags=["reports"])


@router.post("/upload", response_model=ParsedReportResponse)
async def upload_report(file: UploadFile = File(...)):
    """
    Upload a PDF or image medical report.
    Returns structured JSON, plain-language summary, and urgency flag.
    """
    filename = file.filename or "upload"
    content_type = file.content_type or ""

    allowed_types = {
        "application/pdf",
        "image/png",
        "image/jpeg",
        "image/jpg",
        "image/tiff",
        "image/bmp",
    }
    suffix = filename.lower().split(".")[-1]
    allowed_suffixes = {"pdf", "png", "jpg", "jpeg", "tiff", "bmp"}

    if content_type not in allowed_types and suffix not in allowed_suffixes:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: {content_type or suffix}. "
                   "Please upload a PDF or image file.",
        )

    file_bytes = await file.read()
    if len(file_bytes) == 0:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    # ── Step 1: OCR ───────────────────────────────────────────────────────────
    try:
        ocr_result = ocr_service.extract_text_from_file(file_bytes, filename)
    except Exception as exc:
        logger.error("OCR failed for '%s': %s", filename, exc)
        raise HTTPException(status_code=422, detail=f"OCR extraction failed: {exc}")

    if not ocr_result.text.strip():
        raise HTTPException(
            status_code=422,
            detail="No text could be extracted from this file. "
                   "Please ensure the image is clear and try again.",
        )

    # ── Step 2: Structured Extraction ─────────────────────────────────────────
    try:
        structured: ReportData = extraction_service.extract_structured_data(ocr_result.text)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    # ── Step 3: Rule-based Flagging ───────────────────────────────────────────
    flagged: ReportData = flagging_service.flag_report(structured)
    urgency: bool = flagging_service.has_critical_values(flagged)

    # ── Step 4: LLM Summary ───────────────────────────────────────────────────
    try:
        summary_text = summary_service.generate_summary(flagged)
    except Exception as exc:
        logger.warning("Summary generation failed: %s", exc)
        summary_text = "Summary unavailable — please review the structured findings below."

    # ── Step 5: Persist to SQLite ─────────────────────────────────────────────
    report_id = store_service.save_report(flagged)

    # ── Step 6: Index in Chroma Store A ──────────────────────────────────────
    try:
        chroma_service.index_report(flagged, report_id, ocr_result.text)
    except Exception as exc:
        logger.warning("Chroma indexing failed (non-fatal): %s", exc)

    return ParsedReportResponse(
        report_id=report_id,
        ocr=ocr_result,
        structured=flagged,
        summary=summary_text,
        urgency=urgency,
        ocr_warning=ocr_result.warning,
    )


@router.get("/", response_model=List[dict])
async def list_reports():
    """List all stored reports (metadata only)."""
    return store_service.list_reports()


@router.get("/{report_id}", response_model=ReportData)
async def get_report(report_id: int):
    """Retrieve a specific report by ID."""
    report = store_service.get_report_by_id(report_id)
    if report is None:
        raise HTTPException(status_code=404, detail=f"Report {report_id} not found.")
    return report
