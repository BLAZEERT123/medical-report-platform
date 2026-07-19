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
    "hemoglobin": (7.0, 20.0),
    "hgb": (7.0, 20.0),
    "hb": (7.0, 20.0),
    "glucose": (50.0, 500.0),
    "blood glucose": (50.0, 500.0),
    "fasting glucose": (50.0, 400.0),
    "hba1c": (None, 10.0),
    "glycated hemoglobin": (None, 10.0),
    "potassium": (2.5, 6.5),
    "sodium": (120.0, 160.0),
    "creatinine": (None, 10.0),
    "platelet": (20.0, None),
    "platelets": (20.0, None),
    "plt": (20.0, None),
    "wbc": (1.0, 30.0),
    "white blood cell": (1.0, 30.0),
    "white blood cells": (1.0, 30.0),
    "inr": (None, 5.0),
}

# Within what fraction of the boundary do we call something BORDERLINE?
BORDERLINE_MARGIN = 0.10  # 10% of the range width


def _parse_range(ref_range: str) -> Tuple[Optional[float], Optional[float]]:
    """
    Parse a reference range string into (low, high).
    Handles formats:
      "13-17"        → (13.0, 17.0)
      "13.0 - 17.0"  → (13.0, 17.0)
      "< 100"        → (None, 100.0)
      "<100"         → (None, 100.0)
      "> 40"         → (40.0, None)
      ">=3.5"        → (3.5, None)
      "0.5-1.5"      → (0.5, 1.5)
    Returns (None, None) if parsing fails.
    """
    ref = ref_range.strip()

    # Bounded range: e.g., "13 - 17" or "13-17"
    m = re.match(r"^([\d.]+)\s*[-–]\s*([\d.]+)$", ref)
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


def _is_critical(name: str, value: float) -> bool:
    """Check if a test value crosses an absolute critical threshold.

    Uses whole-word boundary matching so that e.g. "hemoglobin" does NOT
    match "glycated hemoglobin" (which has a different critical threshold).
    """
    key = name.lower().strip()
    for k, (low_crit, high_crit) in CRITICAL_THRESHOLDS.items():
        # Whole-word match: pad both strings with spaces so every token is
        # surrounded by spaces, then check for exact substring containment.
        # This ensures "hemoglobin" matches "hemoglobin" and "hb" but NOT
        # "glycated hemoglobin" when k == "hemoglobin".
        padded_key = f" {key} "
        padded_k = f" {k} "
        if padded_k in padded_key or padded_key == padded_k:
            if low_crit is not None and value < low_crit:
                return True
            if high_crit is not None and value > high_crit:
                return True
    return False


def flag_test(test: TestResult) -> TestResult:
    """
    Assign a TestStatus to a single TestResult based on its reference_range.
    Returns a new TestResult (immutable).

    Borderline logic: a value is BORDERLINE if it is outside the reference range
    but within BORDERLINE_MARGIN (10%) of the nearest boundary value.
    For example, range 13-17 → low=13. Margin = 13 * 10% = 1.3.
    Values in [11.7, 13) are BORDERLINE; values < 11.7 are ABNORMAL.
    """
    # First check absolute critical thresholds
    if _is_critical(test.name, test.value):
        return test.model_copy(update={"status": TestStatus.CRITICAL})

    low, high = _parse_range(test.reference_range)

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
