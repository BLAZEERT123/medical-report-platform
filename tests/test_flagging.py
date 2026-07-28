"""
Tests for the rule-based flagging service.
These tests verify that the LLM-free logic correctly assigns statuses.
"""
import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.models.report import ReportData, ReportType, TestResult, TestStatus
from backend.services.flagging_service import flag_test, flag_report, has_critical_values


def make_test(name: str, value: float, ref_range: str) -> TestResult:
    return TestResult(name=name, value=value, unit="g/dL", reference_range=ref_range)


class TestFlagTest:
    def test_normal_value_in_range(self):
        t = make_test("Hemoglobin", 14.0, "13-17")
        result = flag_test(t)
        assert result.status == TestStatus.NORMAL

    def test_abnormal_value_below_range(self):
        t = make_test("Hemoglobin", 9.0, "13-17")
        result = flag_test(t)
        assert result.status == TestStatus.ABNORMAL

    def test_borderline_value_just_below_range(self):
        # 13 * 0.9 = 11.7, so 12.5 should be borderline (within 10% of 13)
        t = make_test("Hemoglobin", 12.5, "13-17")
        result = flag_test(t)
        assert result.status == TestStatus.BORDERLINE

    def test_abnormal_value_above_range(self):
        t = make_test("Glucose", 200.0, "70-100")
        result = flag_test(t)
        assert result.status == TestStatus.ABNORMAL

    def test_critical_hemoglobin(self):
        """Hemoglobin < 7.0 should always be CRITICAL regardless of reference range."""
        t = make_test("Hemoglobin", 6.5, "12-16")
        result = flag_test(t)
        assert result.status == TestStatus.CRITICAL

    def test_critical_hba1c(self):
        """HbA1c > 10.0 should be CRITICAL."""
        t = TestResult(name="HbA1c", value=11.2, unit="%", reference_range="< 5.7")
        result = flag_test(t)
        assert result.status == TestStatus.CRITICAL

    def test_upper_bound_only(self):
        """Reference range like '< 100' — value below is NORMAL."""
        t = TestResult(name="LDL", value=95.0, unit="mg/dL", reference_range="< 100")
        result = flag_test(t)
        assert result.status == TestStatus.NORMAL

    def test_upper_bound_exceeded(self):
        t = TestResult(name="LDL", value=165.0, unit="mg/dL", reference_range="< 100")
        result = flag_test(t)
        assert result.status == TestStatus.ABNORMAL

    def test_lower_bound_only(self):
        """Reference range like '> 60' — value above is NORMAL."""
        t = TestResult(name="HDL", value=65.0, unit="mg/dL", reference_range="> 60")
        result = flag_test(t)
        assert result.status == TestStatus.NORMAL

    def test_lower_bound_below(self):
        t = TestResult(name="HDL", value=35.0, unit="mg/dL", reference_range="> 60")
        result = flag_test(t)
        assert result.status == TestStatus.ABNORMAL

    def test_unparseable_range_returns_unknown(self):
        t = make_test("Custom", 50.0, "see notes")
        result = flag_test(t)
        assert result.status == TestStatus.UNKNOWN


class TestFlagReport:
    def test_flag_report_all_normal(self):
        report = ReportData(
            patient="Test Patient",
            report_date="2024-01-01",
            report_type=ReportType.CBC,
            tests=[
                TestResult(name="Hemoglobin", value=14.0, unit="g/dL", reference_range="13-17"),
                TestResult(name="WBC", value=7.0, unit="K/uL", reference_range="4-11"),
            ],
        )
        flagged = flag_report(report)
        assert all(t.status == TestStatus.NORMAL for t in flagged.tests)

    def test_has_critical_values_true(self):
        report = ReportData(
            patient="Test",
            report_date="2024-01-01",
            report_type=ReportType.CBC,
            tests=[
                TestResult(name="Hemoglobin", value=5.5, unit="g/dL", reference_range="13-17"),
            ],
        )
        flagged = flag_report(report)
        assert has_critical_values(flagged) is True

    def test_has_critical_values_false(self):
        report = ReportData(
            patient="Test",
            report_date="2024-01-01",
            report_type=ReportType.CBC,
            tests=[
                TestResult(name="Hemoglobin", value=14.0, unit="g/dL", reference_range="13-17"),
            ],
        )
        flagged = flag_report(report)
        assert has_critical_values(flagged) is False


class TestFalseCriticalRegressions:
    """
    Regression tests for the false-critical bug:
    A value within the lab's own stated reference range must NEVER be CRITICAL,
    even if it crosses an absolute threshold designed for standard ranges.
    """

    def test_hb_within_lab_range_not_critical(self):
        """Hb = 6.8 in range 6.0–9.0 (e.g. paediatric/anaemia scale) → NORMAL, not CRITICAL."""
        t = TestResult(name="Hb", value=6.8, unit="g/dL", reference_range="6.0-9.0")
        result = flag_test(t)
        assert result.status == TestStatus.NORMAL

    def test_glucose_within_lab_range_not_critical(self):
        """Glucose = 45 in range 40–110 (lab with wider low cutoff) → NORMAL, not CRITICAL."""
        t = TestResult(name="Glucose", value=45.0, unit="mg/dL", reference_range="40.0-110.0")
        result = flag_test(t)
        assert result.status == TestStatus.NORMAL

    def test_hemoglobin_within_lab_range_not_critical(self):
        """Hemoglobin = 6.9 in range 6.5–9.0 → NORMAL, not CRITICAL."""
        t = TestResult(name="Hemoglobin", value=6.9, unit="g/dL", reference_range="6.5-9.0")
        result = flag_test(t)
        assert result.status == TestStatus.NORMAL

    def test_potassium_within_lab_range_not_critical(self):
        """Potassium = 2.4 in lab range 2.0–5.5 → NORMAL, not CRITICAL."""
        t = TestResult(name="Potassium", value=2.4, unit="mEq/L", reference_range="2.0-5.5")
        result = flag_test(t)
        assert result.status == TestStatus.NORMAL

    def test_sodium_within_lab_range_not_critical(self):
        """Sodium = 118 in lab range 115–145 → NORMAL, not CRITICAL."""
        t = TestResult(name="Sodium", value=118.0, unit="mEq/L", reference_range="115-145")
        result = flag_test(t)
        assert result.status == TestStatus.NORMAL

    def test_hb_below_lab_range_and_critical_threshold_is_critical(self):
        """Hb = 5.5 below range 7.0–10.0 AND below critical threshold 7.0 → still CRITICAL."""
        t = TestResult(name="Hemoglobin", value=5.5, unit="g/dL", reference_range="7.0-10.0")
        result = flag_test(t)
        assert result.status == TestStatus.CRITICAL

    def test_glucose_below_lab_range_and_critical_threshold_is_critical(self):
        """Glucose = 40 below range 70–100 AND below critical threshold 50 → CRITICAL."""
        t = TestResult(name="Glucose", value=40.0, unit="mg/dL", reference_range="70-100")
        result = flag_test(t)
        assert result.status == TestStatus.CRITICAL
