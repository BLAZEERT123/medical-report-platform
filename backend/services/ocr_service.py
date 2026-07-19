"""
OCR Service — Extracts text from PDFs and images using Tesseract.
Returns raw text along with a confidence score so the caller can
warn the user if the quality is too low.
"""
from __future__ import annotations

import io
import logging
from pathlib import Path
from typing import Union

import pytesseract
from PIL import Image

from backend.config import get_settings
from backend.models.report import OCRResult

logger = logging.getLogger(__name__)

# Set explicit path so pytesseract works even if Tesseract is not in PATH
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

# ── Try to import pdf2image; gracefully degrade if poppler is not installed ──
try:
    from pdf2image import convert_from_bytes, convert_from_path

    PDF2IMAGE_AVAILABLE = True
except ImportError:
    PDF2IMAGE_AVAILABLE = False
    logger.warning("pdf2image not available — PDF uploads will not be supported.")


def _extract_confidence(tsv_data: str) -> float:
    """Parse Tesseract TSV output and compute average word-level confidence."""
    lines = tsv_data.strip().split("\n")
    confidences = []
    for line in lines[1:]:  # skip header
        parts = line.split("\t")
        if len(parts) >= 11:
            try:
                conf = float(parts[10])
                if conf >= 0:  # -1 means not a word token
                    confidences.append(conf)
            except ValueError:
                continue
    if not confidences:
        return 0.0
    return round(sum(confidences) / len(confidences), 2)


def _ocr_image(img: Image.Image) -> tuple[str, float]:
    """Run Tesseract on a single PIL image; return (text, confidence)."""
    # Get text
    text = pytesseract.image_to_string(img, config="--psm 6")
    # Get confidence via TSV output
    tsv = pytesseract.image_to_data(img, config="--psm 6", output_type=pytesseract.Output.STRING)
    confidence = _extract_confidence(tsv)
    return text.strip(), confidence


def extract_text_from_file(
    file_bytes: bytes,
    filename: str,
) -> OCRResult:
    """
    Main entry point.  Accepts raw file bytes + filename.
    Supports: PDF, PNG, JPG, JPEG, TIFF, BMP.
    Returns an OCRResult with text, confidence, page_count, and warning flag.
    """
    settings = get_settings()
    suffix = Path(filename).suffix.lower()

    texts: list[str] = []
    confidences: list[float] = []

    if suffix == ".pdf":
        # First, try to extract embedded text using pypdf (native, fast, 100% accurate)
        try:
            import pypdf
            reader = pypdf.PdfReader(io.BytesIO(file_bytes))
            pdf_text = []
            for page in reader.pages:
                text = page.extract_text()
                if text:
                    pdf_text.append(text)
            
            if pdf_text and len("".join(pdf_text).strip()) > 50:
                full_text = "\n\n--- PAGE BREAK ---\n\n".join(pdf_text)
                return OCRResult(
                    text=full_text,
                    confidence=100.0,
                    page_count=len(reader.pages),
                    warning=False,
                )
        except Exception as e:
            logger.warning("pypdf extraction failed, falling back to OCR: %s", e)

        # Fallback to OCR if pypdf extracts no text (scanned PDF)
        if not PDF2IMAGE_AVAILABLE:
            raise RuntimeError(
                "pdf2image is not installed or poppler is missing. "
                "Please install poppler and retry."
            )
        # Find Poppler — check the bundled location first, then fall back to PATH
        import shutil
        _POPPLER_BUNDLED = r"C:\Users\aksha\.gemini\antigravity\scratch\poppler\poppler-26.02.0\Library\bin"
        poppler_path = _POPPLER_BUNDLED if Path(_POPPLER_BUNDLED).exists() else None

        pages = convert_from_bytes(file_bytes, dpi=300, poppler_path=poppler_path)
        for page_img in pages:
            t, c = _ocr_image(page_img)
            texts.append(t)
            confidences.append(c)
    elif suffix in {".png", ".jpg", ".jpeg", ".tiff", ".bmp", ".gif"}:
        img = Image.open(io.BytesIO(file_bytes)).convert("RGB")
        t, c = _ocr_image(img)
        texts.append(t)
        confidences.append(c)
    else:
        raise ValueError(f"Unsupported file type: {suffix}")

    full_text = "\n\n--- PAGE BREAK ---\n\n".join(texts)
    avg_confidence = round(sum(confidences) / len(confidences), 2) if confidences else 0.0
    below_threshold = avg_confidence < settings.ocr_confidence_threshold

    if below_threshold:
        logger.warning(
            "OCR confidence %.1f%% is below threshold %.1f%% for file '%s'",
            avg_confidence,
            settings.ocr_confidence_threshold,
            filename,
        )

    return OCRResult(
        text=full_text,
        confidence=avg_confidence,
        page_count=len(texts),
        warning=below_threshold,
    )
