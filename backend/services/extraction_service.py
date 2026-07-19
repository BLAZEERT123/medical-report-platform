"""
Extraction Service — Uses LangChain + manual JSON parsing to convert raw OCR
text into a strictly-typed ReportData object.

Uses manual JSON parsing (not PydanticOutputParser directly in the chain) so
we can sanitize the LLM output before Pydantic validation — e.g. filter out
empty test objects like {} that the LLM sometimes returns.
"""
from __future__ import annotations

import json
import logging
import re

from langchain_core.prompts import ChatPromptTemplate

from backend.models.report import ReportData
from backend.services.llm_factory import get_llm

logger = logging.getLogger(__name__)


_SYSTEM_PROMPT = """\
You are a medical data extraction assistant. Read the raw OCR text from a medical
report and return a SINGLE valid JSON object with EXACTLY this structure:

{{
  "patient": "<patient full name or 'Unknown'>",
  "report_date": "<YYYY-MM-DD or today's date>",
  "report_type": "<one of: CBC, METABOLIC_PANEL, LIPID_PANEL, THYROID, LIVER_FUNCTION, KIDNEY_FUNCTION, DIABETES, PRESCRIPTION, DISCHARGE_SUMMARY, OTHER>",
  "lab_name": "<lab name or 'Unknown'>",
  "doctor": "<doctor name or 'Unknown'>",
  "tests": [
    {{
      "name": "<test parameter name as a string>",
      "value": <numeric float value — NOT a string, NOT null>,
      "unit": "<unit string or empty string>",
      "reference_range": "<reference range string or empty string>",
      "status": "UNKNOWN"
    }}
  ]
}}

STRICT RULES — FOLLOW EXACTLY:
1. "tests" MUST be a non-empty array. Extract EVERY numeric lab parameter.
2. EVERY test object MUST have all 5 keys: name, value, unit, reference_range, status.
3. "value" MUST be a plain number (e.g., 12.5) — never null, never a string.
4. "status" is always the literal string "UNKNOWN" — never anything else.
5. Do NOT include any test object that is missing name or value.
6. Do NOT output markdown, code fences, or any text outside the JSON.
7. Do NOT add comments inside the JSON.
"""

_HUMAN_PROMPT = """\
Extract ALL numeric lab test results from this medical report OCR text.

---BEGIN REPORT TEXT---
{ocr_text}
---END REPORT TEXT---

Return ONLY the JSON object. No markdown. No explanation.
"""

_RETRY_HUMAN_PROMPT = """\
Your previous response had empty test objects. Try again — extract every lab value.

For each row in the report that has a test name and a numeric result, produce one
test object with name, value (float), unit, reference_range, status="UNKNOWN".

---BEGIN REPORT TEXT---
{ocr_text}
---END REPORT TEXT---

Return ONLY the JSON object. No markdown. No explanation. No empty objects.
"""



def _sanitize_json_str(raw: str) -> str:
    """Strip markdown fences and leading/trailing whitespace from LLM output."""
    raw = raw.strip()
    # Remove ```json ... ``` or ``` ... ``` fences
    raw = re.sub(r"^```(?:json)?\s*", "", raw)
    raw = re.sub(r"\s*```$", "", raw)
    return raw.strip()


def _filter_tests(tests_raw: list) -> list:
    """Remove empty or incomplete test objects from the LLM output."""
    valid = []
    for t in tests_raw:
        if not isinstance(t, dict):
            continue
        # Skip if name or value is missing / empty
        name = t.get("name", "")
        value = t.get("value")
        if not name or value is None:
            logger.warning("Skipping incomplete test object: %s", t)
            continue
        # Coerce value to float if it's a string
        try:
            t["value"] = float(str(value).replace(",", ""))
        except (ValueError, TypeError):
            logger.warning("Cannot parse value '%s' for test '%s', skipping", value, name)
            continue
        # Ensure all required keys are present with defaults
        t.setdefault("unit", "")
        t.setdefault("reference_range", "")
        t.setdefault("status", "UNKNOWN")
        valid.append(t)
    return valid


def _repair_json(raw: str) -> dict:
    """
    Try multiple strategies to parse potentially truncated LLM JSON output.
    Strategy 1: direct parse (works for valid JSON)
    Strategy 2: find last complete '}' and close the array + object
    Strategy 3: regex-extract individual test objects
    """
    cleaned = _sanitize_json_str(raw)

    # Strategy 1 — direct parse
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass

    # Strategy 2 — truncate at last complete test object and close the JSON
    # Find last complete "}" that ends a test object
    try:
        last_brace = cleaned.rfind('"status"')
        if last_brace != -1:
            # Find the closing } after the last status field
            close_pos = cleaned.find("}", last_brace)
            if close_pos != -1:
                truncated = cleaned[:close_pos + 1] + "]\n}"
                # Make sure it starts from the outer {
                start = truncated.find("{")
                if start != -1:
                    truncated = truncated[start:]
                    return json.loads(truncated)
    except (json.JSONDecodeError, ValueError):
        pass

    # Strategy 3 — regex extract partial header + whatever test objects we can find
    try:
        patient = re.search(r'"patient"\s*:\s*"([^"]*)"', cleaned)
        report_date = re.search(r'"report_date"\s*:\s*"([^"]*)"', cleaned)
        report_type = re.search(r'"report_type"\s*:\s*"([^"]*)"', cleaned)
        lab_name = re.search(r'"lab_name"\s*:\s*"([^"]*)"', cleaned)
        doctor = re.search(r'"doctor"\s*:\s*"([^"]*)"', cleaned)

        # Extract complete test objects
        test_objects = re.findall(
            r'\{\s*"name"\s*:\s*"([^"]+)"\s*,\s*"value"\s*:\s*([\d.]+)\s*,\s*"unit"\s*:\s*"([^"]*)"\s*,\s*"reference_range"\s*:\s*"([^"]*)"\s*,\s*"status"\s*:\s*"([^"]*)"\s*\}',
            cleaned
        )
        tests = [
            {"name": t[0], "value": float(t[1]), "unit": t[2],
             "reference_range": t[3], "status": t[4]}
            for t in test_objects
        ]

        return {
            "patient": patient.group(1) if patient else "Unknown",
            "report_date": report_date.group(1) if report_date else "2000-01-01",
            "report_type": report_type.group(1) if report_type else "OTHER",
            "lab_name": lab_name.group(1) if lab_name else "Unknown",
            "doctor": doctor.group(1) if doctor else "Unknown",
            "tests": tests,
        }
    except Exception:
        pass

    raise json.JSONDecodeError("Could not repair truncated JSON", cleaned, 0)



def extract_structured_data(ocr_text: str) -> ReportData:
    """
    Main entry point.
    Sends OCR text to the LLM and returns a validated ReportData object.
    Uses _repair_json to handle truncated responses gracefully.
    Falls back to a retry prompt if the first attempt returns empty/invalid tests.
    Raises ValueError if parsing ultimately fails.
    """
    # Clear cached LLM instance so updated max_tokens setting is picked up
    get_llm.cache_clear()
    llm = get_llm()

    # Limit OCR to 6000 chars — keeps prompt+response well within 8192 token budget
    ocr_excerpt = ocr_text[:6000]

    # ── Attempt 1 ────────────────────────────────────────────────────────────
    prompt = ChatPromptTemplate.from_messages([
        ("system", _SYSTEM_PROMPT),
        ("human", _HUMAN_PROMPT),
    ])
    chain = prompt | llm
    logger.info("Sending %d chars of OCR text to LLM for extraction...", len(ocr_excerpt))

    try:
        response = chain.invoke({"ocr_text": ocr_excerpt})
        data = _repair_json(response.content)          # ← repair instead of plain parse
        data["tests"] = _filter_tests(data.get("tests", []))

        # ── Attempt 2 (retry) if no valid tests came back ────────────────────
        if not data["tests"]:
            logger.warning("Attempt 1 returned no valid tests — retrying with explicit prompt...")
            retry_prompt = ChatPromptTemplate.from_messages([
                ("system", _SYSTEM_PROMPT),
                ("human", _RETRY_HUMAN_PROMPT),
            ])
            retry_chain = retry_prompt | llm
            response2 = retry_chain.invoke({"ocr_text": ocr_excerpt})
            data2 = _repair_json(response2.content)    # ← repair here too
            data2["tests"] = _filter_tests(data2.get("tests", []))
            if data2["tests"]:
                data = data2
            else:
                logger.error("Retry also returned no valid tests. OCR text:\n%s", ocr_text[:2000])

        result = ReportData(**data)
        logger.info(
            "Extracted report for patient '%s' with %d test results.",
            result.patient,
            len(result.tests),
        )
        return result

    except json.JSONDecodeError as exc:
        logger.error("LLM output was not valid JSON even after repair: %s", exc)
        raise ValueError(f"Structured extraction failed: LLM did not return valid JSON — {exc}") from exc
    except Exception as exc:
        logger.error("Failed to parse LLM output into ReportData: %s", exc)
        raise ValueError(f"Structured extraction failed: {exc}") from exc


