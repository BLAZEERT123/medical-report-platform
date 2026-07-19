"""
Pydantic models for structured report data.
These are the strict schemas that the LLM must populate via PydanticOutputParser.
"""
from __future__ import annotations

from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field, field_validator
import re


class TestStatus(str, Enum):
    NORMAL = "NORMAL"
    BORDERLINE = "BORDERLINE"
    ABNORMAL = "ABNORMAL"
    CRITICAL = "CRITICAL"
    UNKNOWN = "UNKNOWN"


class ReportType(str, Enum):
    CBC = "CBC"                          # Complete Blood Count
    METABOLIC_PANEL = "METABOLIC_PANEL"  # BMP / CMP
    LIPID_PANEL = "LIPID_PANEL"
    THYROID = "THYROID"
    LIVER_FUNCTION = "LIVER_FUNCTION"
    KIDNEY_FUNCTION = "KIDNEY_FUNCTION"
    DIABETES = "DIABETES"
    PRESCRIPTION = "PRESCRIPTION"
    DISCHARGE_SUMMARY = "DISCHARGE_SUMMARY"
    OTHER = "OTHER"


class TestResult(BaseModel):
    """A single lab test result extracted from the report."""

    name: str = Field(description="Name of the test (e.g., Hemoglobin, Glucose)")
    value: float = Field(description="Numeric measured value")
    unit: str = Field(description="Unit of measurement (e.g., g/dL, mg/dL, %)")
    reference_range: str = Field(
        description="Reference/normal range as string (e.g., '13-17', '<100', '>40')"
    )
    # Status is intentionally left as UNKNOWN — will be overwritten by rule-based flagging
    status: TestStatus = Field(
        default=TestStatus.UNKNOWN,
        description="Flagging status — do NOT set this; it is determined by rule-based logic",
    )


class ReportData(BaseModel):
    """Top-level structured representation of an uploaded medical report."""

    patient: str = Field(description="Patient full name as it appears on the report")
    report_date: str = Field(description="Report date in YYYY-MM-DD format")
    report_type: ReportType = Field(
        description="Type of medical report (CBC, METABOLIC_PANEL, etc.)"
    )
    lab_name: Optional[str] = Field(
        default=None, description="Name of the laboratory or hospital"
    )
    doctor: Optional[str] = Field(
        default=None, description="Referring doctor's name if present"
    )
    tests: List[TestResult] = Field(description="List of all test results found in the report")

    @field_validator("report_date")
    @classmethod
    def validate_date_format(cls, v: str) -> str:
        if not re.match(r"^\d{4}-\d{2}-\d{2}$", v):
            # Attempt to coerce common formats
            import datetime
            for fmt in ("%d/%m/%Y", "%m/%d/%Y", "%d-%m-%Y", "%B %d, %Y", "%b %d, %Y"):
                try:
                    return datetime.datetime.strptime(v, fmt).strftime("%Y-%m-%d")
                except ValueError:
                    continue
            # If all else fails, return as-is (LLM already gave us something)
        return v


# ──────────────────────────────────────────────
# API Response models
# ──────────────────────────────────────────────

class OCRResult(BaseModel):
    text: str
    confidence: float   # 0–100
    page_count: int
    warning: bool       # True if confidence < threshold


class ParsedReportResponse(BaseModel):
    report_id: int
    ocr: OCRResult
    structured: ReportData
    summary: str           # LLM-generated plain-language summary
    urgency: bool          # True if any CRITICAL values found
    ocr_warning: bool      # Surfaces the OCR warning at response level


class RetrievedChunk(BaseModel):
    source_type: str       # "report" | "reference"
    source_name: str       # e.g., "Your CBC report (2024-01-15)" or "MedlinePlus: Anemia"
    source_url: Optional[str] = None
    snippet: str
    score: float           # similarity score (0–1)
    metadata: dict = {}


class SourceCitation(BaseModel):
    """A structured source citation included with the answer."""
    title: str
    url: Optional[str] = None
    snippet: str
    score: float
    source_type: str       # "report" | "reference"


class QAResponse(BaseModel):
    question: str
    rewritten_query: Optional[str] = None  # set when query was rewritten for retrieval
    report_chunks: List[RetrievedChunk]    # from Store A
    reference_chunks: List[RetrievedChunk] # from Store B
    answer: str
    refused: bool = False   # True if no relevant context found
    # ── New fields (inspired by Ratnesh-181998/Medical-RAG-Chatbot) ──
    source_citations: List[SourceCitation] = []  # structured citations for UI display
    confidence: str = "Medium"                   # "High" | "Medium" | "Low"
    latency_ms: Optional[int] = None             # end-to-end answer latency in ms
