"""
Rule-based flagging service.
The LLM never decides what is NORMAL/BORDERLINE/ABNORMAL/CRITICAL.
All decisions are made here using pure Python comparisons against reference ranges.
"""
from __future__ import annotations

import logging
import re
from typing import Optional, Tuple

from backend.models.report import ReportData, TestResult, TestStatus

logger = logging.getLogger(__name__)

# ── Critical threshold overrides ─────────────────────────────────────────────
# If a value crosses these absolute thresholds, it is always CRITICAL
# regardless of the reference range on the report.
# Format: {normalized_test_name: (low_critical, high_critical)}
CRITICAL_THRESHOLDS: dict[str, Tuple[Optional[float], Optional[float]]] = {
    # ── Specific / longer names FIRST so they win over generic shorter keys ──
    # Corpuscular indices (MCH, MCHC, MCV) — no life-threatening absolute thresholds;
    # listed explicitly so they are NOT matched by the generic "hemoglobin" / "hb" entries.
    "mean corpuscular hemoglobin concentration": (None, None),
    "mean corpuscular hb concentration": (None, None),
    "mean corpuscular hemoglobin": (None, None),
    "mean corpuscular volume": (None, None),
    "corpuscular hemoglobin": (None, None),
    "corpuscular hb": (None, None),
    "glycated hemoglobin": (None, 10.0),
    "white blood cells": (1.0, 30.0),
    "white blood cell": (1.0, 30.0),
    "blood glucose": (50.0, 500.0),
    "fasting glucose": (50.0, 400.0),
    # ── Short / generic keys AFTER specific ones ──
    "mchc": (None, None),
    "mch": (None, None),
    "mcv": (None, None),
    "hemoglobin": (7.0, 20.0),
    "hgb": (7.0, 20.0),
    "hb": (7.0, 20.0),
    "glucose": (50.0, 500.0),
    "hba1c": (None, 10.0),
    "potassium": (2.5, 6.5),
    "sodium": (120.0, 160.0),
    "creatinine": (None, 10.0),
    "platelet": (20.0, None),
    "platelets": (20.0, None),
    "plt": (20.0, None),
    "wbc": (1.0, 30.0),
    "inr": (None, 5.0),
}

# Within what fraction of the boundary do we call something BORDERLINE?
BORDERLINE_MARGIN = 0.10  # 10% of the range width


def _parse_range(ref_range: str) -> Tuple[Optional[float], Optional[float]]:
    """
    Parse a reference range string into (low, high).
    Handles formats:
      "13-17"            → (13.0, 17.0)
      "13.0 - 17.0"      → (13.0, 17.0)
      "13.0 - 17.0 g/dL" → (13.0, 17.0)  ← units stripped
      "70 to 110"        → (70.0, 110.0)  ← word separator
      "< 100"            → (None, 100.0)
      "<100 mg/dL"       → (None, 100.0)  ← units stripped
      "> 40"             → (40.0, None)
      ">=3.5"            → (3.5, None)
      "0.5-1.5"          → (0.5, 1.5)
    Returns (None, None) if parsing fails.
    """
    if not ref_range:
        return None, None

    # Normalise: strip leading/trailing whitespace, collapse internal spaces
    ref = ref_range.strip()

    # Strip any trailing unit text (e.g. "g/dL", "mg/dL", "mEq/L", "mmol/L", "%", "IU/L")
    # Keep only the leading numeric / operator portion.
    ref = re.sub(r"\s*[A-Za-z%/][A-Za-z%/\d.]*$", "", ref).strip()

    # Normalise all dash variants (en‑dash, em‑dash, figure‑dash, minus sign) → ASCII hyphen
    ref = re.sub(r"[\u2012\u2013\u2014\u2015\u2212]", "-", ref)

    # Bounded range: "13 - 17", "13-17", "70 to 110", "70 TO 110"
    m = re.match(r"^([\d.]+)\s*(?:-|to)\s*([\d.]+)$", ref, re.IGNORECASE)
    if m:
        return float(m.group(1)), float(m.group(2))

    # Upper bound: < or <=
    m = re.match(r"^[<≤]=?\s*([\d.]+)$", ref)
    if m:
        return None, float(m.group(1))

    # Lower bound: > or >=
    m = re.match(r"^[>≥]=?\s*([\d.]+)$", ref)
    if m:
        return float(m.group(1)), None

    logger.debug("Could not parse reference range: '%s'", ref_range)
    return None, None


def _is_critical(name: str, value: float, ref_low: Optional[float] = None, ref_high: Optional[float] = None) -> bool:
    """Check if a test value crosses an absolute critical threshold.

    Uses whole-word boundary matching so that e.g. "hemoglobin" does NOT
    match "glycated hemoglobin" (which has a different critical threshold).

    Keys are evaluated longest-first (most specific first). The first key
    that matches the test name wins and no further keys are checked. This
    prevents generic short keys like "hemoglobin" or "hb" from falsely
    matching longer test names such as "Mean Corpuscular Hemoglobin (MCH)"
    or "Mean Corpuscular Hb Concentration (MCHC)".

    IMPORTANT: If ref_low / ref_high are provided and the value is within
    the report's own stated reference range, critical thresholds are NOT
    applied. A value that the lab itself considers normal cannot be CRITICAL.
    """
    # Guard: if the value is within the report's own stated normal range,
    # it cannot be flagged CRITICAL — the lab's own range takes precedence.
    in_report_range = True
    if ref_low is not None and value < ref_low:
        in_report_range = False
    if ref_high is not None and value > ref_high:
        in_report_range = False
    if in_report_range and (ref_low is not None or ref_high is not None):
        # Value is within the report's own range → cannot be CRITICAL.
        return False

    key = name.lower().strip()
    # Sort by key length descending so the most specific (longest) match wins.
    sorted_thresholds = sorted(CRITICAL_THRESHOLDS.items(), key=lambda x: len(x[0]), reverse=True)
    for k, (low_crit, high_crit) in sorted_thresholds:
        # Whole-word match: pad both strings with spaces so every token is
        # surrounded by spaces, then check for exact substring containment.
        padded_key = f" {key} "
        padded_k = f" {k} "
        if padded_k in padded_key or padded_key == padded_k:
            # This key matched — check its thresholds and stop searching.
            # This prevents a shorter generic key (e.g. "hemoglobin") from
            # overriding the result of a longer specific key that already matched.
            if low_crit is not None and value < low_crit:
                return True
            if high_crit is not None and value > high_crit:
                return True
            return False  # Matched this key but value is within its critical range.
    return False


def flag_test(test: TestResult) -> TestResult:
    """
    Assign a TestStatus to a single TestResult based on its reference_range.
    Returns a new TestResult (immutable).

    Borderline logic: a value is BORDERLINE if it is outside the reference range
    but within BORDERLINE_MARGIN (10%) of the nearest boundary value.
    For example, range 13-17 → low=13. Margin = 13 * 10% = 1.3.
    Values in [11.7, 13) are BORDERLINE; values < 11.7 are ABNORMAL.

    Critical logic: absolute critical thresholds only fire when the value is
    ALREADY outside the report's own stated reference range. A value that the
    lab itself considers normal is never flagged as CRITICAL.
    """
    low, high = _parse_range(test.reference_range)

    # Check absolute critical thresholds, passing the report's own range so that
    # values within the lab's stated normal range are never marked CRITICAL.
    if _is_critical(test.name, test.value, ref_low=low, ref_high=high):
        return test.model_copy(update={"status": TestStatus.CRITICAL})

    if low is None and high is None:
        # Cannot determine — leave as UNKNOWN
        return test.model_copy(update={"status": TestStatus.UNKNOWN})

    # Determine status: compute margin from the *boundary value* (not range width)
    if low is not None and test.value < low:
        # Below the lower bound — BORDERLINE if within 10% of the low boundary
        margin = low * BORDERLINE_MARGIN
        status = TestStatus.BORDERLINE if test.value >= (low - margin) else TestStatus.ABNORMAL
    elif high is not None and test.value > high:
        # Above the upper bound — BORDERLINE if within 10% of the high boundary
        margin = high * BORDERLINE_MARGIN
        status = TestStatus.BORDERLINE if test.value <= (high + margin) else TestStatus.ABNORMAL
    else:
        status = TestStatus.NORMAL

    return test.model_copy(update={"status": status})


def flag_report(report: ReportData) -> ReportData:
    """Flag all tests in a report. Returns a new ReportData with statuses set."""
    flagged_tests = [flag_test(t) for t in report.tests]
    return report.model_copy(update={"tests": flagged_tests})


def has_critical_values(report: ReportData) -> bool:
    """Return True if any test in the report is flagged CRITICAL."""
    return any(t.status == TestStatus.CRITICAL for t in report.tests)
