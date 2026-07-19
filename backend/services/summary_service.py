"""
Summary Service — LLM generates a rich, scientifically-informed plain-language
explanation for each flagged lab result.

Passes ALL test values to the LLM (not just flagged ones), so it can describe
the overall clinical picture and contextualise each abnormal finding.
"""
from __future__ import annotations

import logging
from typing import List

from langchain_core.prompts import ChatPromptTemplate

from backend.models.report import ReportData, TestResult, TestStatus
from backend.services.llm_factory import get_llm

logger = logging.getLogger(__name__)


def _format_all_tests(tests: List[TestResult]) -> str:
    """Build a structured table of ALL test results with status labels."""
    lines = ["Test Name | Value | Unit | Reference Range | Status"]
    lines.append("-" * 70)
    for t in tests:
        status_label = t.status.value if hasattr(t.status, "value") else str(t.status)
        lines.append(
            f"{t.name} | {t.value} {t.unit} | ref: {t.reference_range} | {status_label}"
        )
    return "\n".join(lines)


_SYSTEM_PROMPT = """\
You are a knowledgeable medical assistant producing a detailed, scientifically-informed
report explanation for a patient. Your response must:

STYLE:
- Start by greeting the patient by name and briefly summarising the overall picture
- For EVERY abnormal/critical/borderline finding, write a dedicated paragraph that:
    a) States the parameter name and the actual measured value
    b) States the normal reference range and how far off it is
    c) Explains in plain English what this parameter measures in the body
    d) Explains the clinical significance of this specific deviation
       (e.g., what organs/systems are affected, what conditions are associated)
    e) Names 2–3 common causes of this type of result in plain language
    f) Mentions what a doctor might investigate or recommend next
- End with a brief note on normal findings and a closing reminder to consult the doctor

FORMAT:
- Plain text paragraphs only — NO HTML, NO markdown, NO bullet points, NO headers
- Each abnormal finding as its own paragraph separated by a blank line
- Closing: "Please discuss these results with your doctor before making any health decisions."

IMPORTANT:
- Include real medical context and science — be specific about values and what they mean
- Do NOT be vague (e.g. do NOT say just "your cholesterol is high" — explain what
  LDL/HDL cholesterol does, what a value of 165 vs. the 100 reference range means clinically)
- You are NOT diagnosing — you are educating the patient about their own numbers
"""

_HUMAN_PROMPT = """\
Patient: {patient}
Report date: {report_date}
Report type: {report_type}

Complete test results:
{all_tests}

Write a thorough, medically informative yet patient-friendly explanation of these results.
"""


def generate_summary(report: ReportData) -> str:
    """Generate a detailed scientific + plain-language summary for the full report."""
    all_tests_text = _format_all_tests(report.tests)
    llm = get_llm()

    prompt = ChatPromptTemplate.from_messages([
        ("system", _SYSTEM_PROMPT),
        ("human", _HUMAN_PROMPT),
    ])

    chain = prompt | llm

    logger.info("Generating detailed summary for patient '%s'", report.patient)

    response = chain.invoke({
        "patient": report.patient,
        "report_date": report.report_date,
        "report_type": report.report_type.value if hasattr(report.report_type, "value") else str(report.report_type),
        "all_tests": all_tests_text,
    })
    return response.content.strip()
