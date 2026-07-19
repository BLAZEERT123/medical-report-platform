"""
Generate synthetic lab report PDFs for demo/testing.
Uses ReportLab to create realistic-looking CBC and metabolic panel reports.

Run from project root:
    python scripts/generate_sample_reports.py
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    HRFlowable,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

OUTPUT_DIR = Path(__file__).parent.parent / "backend" / "data" / "synthetic_reports"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

STYLES = getSampleStyleSheet()

# Custom styles
TITLE_STYLE = ParagraphStyle(
    "title",
    parent=STYLES["Title"],
    fontSize=16,
    textColor=colors.HexColor("#1a3a5c"),
    spaceAfter=4,
)
HEADER_STYLE = ParagraphStyle(
    "header",
    parent=STYLES["Normal"],
    fontSize=10,
    textColor=colors.HexColor("#444444"),
    spaceAfter=2,
)
SECTION_STYLE = ParagraphStyle(
    "section",
    parent=STYLES["Normal"],
    fontSize=11,
    textColor=colors.HexColor("#1a3a5c"),
    fontName="Helvetica-Bold",
    spaceBefore=8,
    spaceAfter=4,
)


def _header_block(patient: str, dob: str, date: str, lab: str, doctor: str) -> list:
    return [
        Paragraph("PathCare Diagnostics Laboratory", TITLE_STYLE),
        Paragraph("123 Medical Center Drive, New Delhi 110001", HEADER_STYLE),
        Paragraph("Tel: +91-11-4000-1234 | NABL Accredited", HEADER_STYLE),
        HRFlowable(width="100%", thickness=2, color=colors.HexColor("#1a3a5c")),
        Spacer(1, 4 * mm),
        Paragraph(f"Patient Name: <b>{patient}</b>", HEADER_STYLE),
        Paragraph(f"Date of Birth: {dob} | Ref. Doctor: Dr. {doctor}", HEADER_STYLE),
        Paragraph(f"Report Date: {date} | Lab ID: {hash(patient + date) % 100000:05d}", HEADER_STYLE),
        HRFlowable(width="100%", thickness=0.5, color=colors.grey),
        Spacer(1, 4 * mm),
    ]


def _make_table(headers: list, rows: list) -> Table:
    data = [headers] + rows
    t = Table(data, colWidths=[60 * mm, 30 * mm, 30 * mm, 40 * mm, 30 * mm])
    t.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1a3a5c")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f0f4f8")]),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("ALIGN", (1, 1), (-1, -1), "CENTER"),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ])
    )
    return t


# ─────────────────────────────────────────────────────────────────────────────
# Report 1: CBC with Low Hemoglobin + Borderline Platelets
# ─────────────────────────────────────────────────────────────────────────────
def generate_cbc_report_1():
    path = OUTPUT_DIR / "cbc_anemia_report.pdf"
    doc = SimpleDocTemplate(str(path), pagesize=A4, topMargin=15 * mm, bottomMargin=15 * mm)
    content = _header_block(
        patient="Priya Sharma",
        dob="1990-03-15",
        date="2024-11-20",
        lab="PathCare Diagnostics",
        doctor="Rajesh Kumar",
    )
    content.append(Paragraph("COMPLETE BLOOD COUNT (CBC)", SECTION_STYLE))
    headers = ["Test", "Result", "Unit", "Reference Range", "Flag"]
    rows = [
        ["Hemoglobin (Hb)", "9.2", "g/dL", "12.0 – 16.0", "LOW ↓"],
        ["Hematocrit (PCV)", "28.5", "%", "36.0 – 46.0", "LOW ↓"],
        ["RBC Count", "3.2", "million/µL", "3.8 – 5.2", "LOW ↓"],
        ["WBC Count", "7.8", "thousand/µL", "4.0 – 11.0", "NORMAL"],
        ["Platelets", "148", "thousand/µL", "150 – 400", "LOW ↓"],
        ["MCV", "72.0", "fL", "80.0 – 100.0", "LOW ↓"],
        ["MCH", "24.5", "pg", "27.0 – 33.0", "LOW ↓"],
        ["MCHC", "32.3", "g/dL", "31.5 – 36.0", "NORMAL"],
        ["Neutrophils", "62", "%", "40 – 70", "NORMAL"],
        ["Lymphocytes", "28", "%", "20 – 45", "NORMAL"],
        ["Eosinophils", "4", "%", "1 – 6", "NORMAL"],
    ]
    content.append(_make_table(headers, rows))
    content.append(Spacer(1, 6 * mm))
    content.append(Paragraph("CLINICAL INTERPRETATION", SECTION_STYLE))
    content.append(Paragraph(
        "The results suggest microcytic hypochromic anemia, likely due to iron deficiency. "
        "The low hemoglobin, hematocrit, MCV, and MCH are consistent with iron deficiency anemia. "
        "A serum ferritin and iron profile is recommended for confirmation.",
        HEADER_STYLE,
    ))
    doc.build(content)
    print(f"Generated: {path}")


# ─────────────────────────────────────────────────────────────────────────────
# Report 2: Metabolic Panel with High Glucose + Borderline Creatinine
# ─────────────────────────────────────────────────────────────────────────────
def generate_metabolic_report():
    path = OUTPUT_DIR / "metabolic_panel_diabetes.pdf"
    doc = SimpleDocTemplate(str(path), pagesize=A4, topMargin=15 * mm, bottomMargin=15 * mm)
    content = _header_block(
        patient="Arjun Mehta",
        dob="1978-07-22",
        date="2024-12-05",
        lab="PathCare Diagnostics",
        doctor="Sunita Patel",
    )
    content.append(Paragraph("COMPREHENSIVE METABOLIC PANEL + HbA1c", SECTION_STYLE))
    headers = ["Test", "Result", "Unit", "Reference Range", "Flag"]
    rows = [
        ["Fasting Glucose", "186", "mg/dL", "70 – 100", "HIGH ↑"],
        ["HbA1c", "8.4", "%", "< 5.7", "HIGH ↑"],
        ["Creatinine", "1.28", "mg/dL", "0.6 – 1.2", "HIGH ↑"],
        ["eGFR", "68", "mL/min/1.73m²", "> 60", "NORMAL"],
        ["BUN", "22", "mg/dL", "7 – 25", "NORMAL"],
        ["Sodium", "138", "mEq/L", "136 – 145", "NORMAL"],
        ["Potassium", "4.1", "mEq/L", "3.5 – 5.1", "NORMAL"],
        ["Chloride", "101", "mEq/L", "98 – 107", "NORMAL"],
        ["Bicarbonate", "24", "mEq/L", "22 – 29", "NORMAL"],
        ["Calcium", "9.4", "mg/dL", "8.5 – 10.5", "NORMAL"],
        ["Total Protein", "7.2", "g/dL", "6.0 – 8.0", "NORMAL"],
        ["Albumin", "4.1", "g/dL", "3.5 – 5.0", "NORMAL"],
        ["ALT (SGPT)", "32", "U/L", "7 – 56", "NORMAL"],
        ["AST (SGOT)", "28", "U/L", "10 – 40", "NORMAL"],
    ]
    content.append(_make_table(headers, rows))
    content.append(Spacer(1, 6 * mm))
    content.append(Paragraph("CLINICAL INTERPRETATION", SECTION_STYLE))
    content.append(Paragraph(
        "HbA1c of 8.4% indicates poor glycemic control (target < 7.0% for diabetics). "
        "Fasting glucose of 186 mg/dL is significantly elevated. "
        "Mild elevation in creatinine; eGFR of 68 suggests early-stage kidney involvement. "
        "Recommend dietary modification, medication review, and repeat testing in 3 months.",
        HEADER_STYLE,
    ))
    doc.build(content)
    print(f"Generated: {path}")


# ─────────────────────────────────────────────────────────────────────────────
# Report 3: Lipid Panel with High LDL
# ─────────────────────────────────────────────────────────────────────────────
def generate_lipid_report():
    path = OUTPUT_DIR / "lipid_panel_high_ldl.pdf"
    doc = SimpleDocTemplate(str(path), pagesize=A4, topMargin=15 * mm, bottomMargin=15 * mm)
    content = _header_block(
        patient="Neha Singh",
        dob="1985-11-08",
        date="2025-01-10",
        lab="PathCare Diagnostics",
        doctor="Vikram Bose",
    )
    content.append(Paragraph("LIPID PROFILE", SECTION_STYLE))
    headers = ["Test", "Result", "Unit", "Reference Range", "Flag"]
    rows = [
        ["Total Cholesterol", "248", "mg/dL", "< 200", "HIGH ↑"],
        ["LDL Cholesterol", "165", "mg/dL", "< 100", "HIGH ↑"],
        ["HDL Cholesterol", "38", "mg/dL", "> 60", "LOW ↓"],
        ["Triglycerides", "210", "mg/dL", "< 150", "HIGH ↑"],
        ["VLDL Cholesterol", "42", "mg/dL", "< 30", "HIGH ↑"],
        ["Non-HDL Cholesterol", "210", "mg/dL", "< 130", "HIGH ↑"],
        ["LDL/HDL Ratio", "4.3", "", "< 3.5", "HIGH ↑"],
        ["Total/HDL Ratio", "6.5", "", "< 5.0", "HIGH ↑"],
    ]
    content.append(_make_table(headers, rows))
    content.append(Spacer(1, 6 * mm))
    content.append(Paragraph("CLINICAL INTERPRETATION", SECTION_STYLE))
    content.append(Paragraph(
        "Significant dyslipidemia with elevated LDL and low HDL, indicating elevated "
        "cardiovascular risk. Recommend lifestyle modifications (diet, exercise) and "
        "consider statin therapy after physician consultation.",
        HEADER_STYLE,
    ))
    doc.build(content)
    print(f"Generated: {path}")


if __name__ == "__main__":
    generate_cbc_report_1()
    generate_metabolic_report()
    generate_lipid_report()
    print(f"\n✅ All synthetic reports generated in: {OUTPUT_DIR}")
