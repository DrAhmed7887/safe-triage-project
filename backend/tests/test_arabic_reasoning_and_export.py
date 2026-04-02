"""Tests for Arabic reasoning derivation and export ownership."""

import inspect
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from backend.logic.arabic_reasoning import derive_safe_arabic_reasoning


# ---------------------------------------------------------------------------
# derive_safe_arabic_reasoning
# ---------------------------------------------------------------------------

class TestDeriveArabicReasoning:
    """Verify that Arabic reasoning is derived from trusted fields only."""

    def test_basic_esi_reasoning_translated(self):
        result = derive_safe_arabic_reasoning(
            esi_reasoning=["Vital signs abnormal — NEWS2 elevated"],
            resource_count=3,
        )
        assert any("العلامات الحيوية" in line for line in result)
        assert any("3" in line for line in result)

    def test_resource_count_always_present(self):
        result = derive_safe_arabic_reasoning(esi_reasoning=[], resource_count=5)
        assert any("5" in line and "موارد" in line for line in result)

    def test_silent_mi_flag(self):
        result = derive_safe_arabic_reasoning(
            esi_reasoning=["chest pain workup"],
            resource_count=2,
            silent_mi_forced=True,
        )
        assert any("الجلطة الصامتة" in line for line in result)

    def test_reasoning_floor_note(self):
        result = derive_safe_arabic_reasoning(
            esi_reasoning=[],
            resource_count=1,
            reasoning_floor_note="Safety floor applied for sepsis pattern",
        )
        assert any("تصعيد احتياطي" in line for line in result)

    def test_critical_floor_notes(self):
        result = derive_safe_arabic_reasoning(
            esi_reasoning=[],
            resource_count=1,
            critical_floor_notes=["pre-AI safety floor"],
        )
        assert any("قواعد أمان حرجة" in line for line in result)

    def test_no_free_form_arabic_passthrough(self):
        """Ensure the function does NOT return raw English reasoning."""
        result = derive_safe_arabic_reasoning(
            esi_reasoning=["High risk situation detected"],
            resource_count=2,
        )
        for line in result:
            assert "High risk situation detected" not in line

    def test_unmatched_reasoning_gets_generic_arabic(self):
        result = derive_safe_arabic_reasoning(
            esi_reasoning=["Some unusual reasoning pattern xyz"],
            resource_count=1,
        )
        assert any("المحرك الحتمي" in line for line in result)

    def test_empty_reasoning_still_has_resource_line(self):
        result = derive_safe_arabic_reasoning(esi_reasoning=[], resource_count=0)
        assert len(result) >= 1
        assert any("موارد" in line or "0" in line for line in result)

    def test_stroke_pattern_detected(self):
        result = derive_safe_arabic_reasoning(
            esi_reasoning=["Stroke symptoms detected — aphasia noted"],
            resource_count=2,
        )
        assert any("سكتة دماغية" in line for line in result)

    def test_sepsis_pattern_detected(self):
        result = derive_safe_arabic_reasoning(
            esi_reasoning=["Possible sepsis — fever with tachycardia"],
            resource_count=3,
        )
        assert any("تسمم دم" in line for line in result)

    def test_multiple_reasoning_lines(self):
        result = derive_safe_arabic_reasoning(
            esi_reasoning=[
                "High risk patient",
                "Chest pain protocol activated",
                "NEWS2 score elevated",
            ],
            resource_count=4,
        )
        # Should have at least one line per input reason + resource line
        assert len(result) >= 4

    def test_all_flags_together(self):
        result = derive_safe_arabic_reasoning(
            esi_reasoning=["Red flag detected"],
            resource_count=2,
            silent_mi_forced=True,
            reasoning_floor_note="floor note",
            critical_floor_notes=["critical"],
        )
        assert any("علامة حمراء" in line for line in result)
        assert any("الجلطة الصامتة" in line for line in result)
        assert any("تصعيد احتياطي" in line for line in result)
        assert any("قواعد أمان حرجة" in line for line in result)


# ---------------------------------------------------------------------------
# Export ownership: fetch_personal_export_cases query structure
# ---------------------------------------------------------------------------

class TestExportOwnershipQuery:
    """Verify that the export query includes triage-table clinician_id matching."""

    @pytest.fixture(autouse=True)
    def _load_source(self):
        report_path = os.path.join(
            os.path.dirname(__file__), "..", "report_service.py"
        )
        with open(report_path, "r") as f:
            self.source = f.read()

    def test_fetch_personal_uses_clinician_id_in_triage_table(self):
        """The SQL in fetch_personal_export_cases should match on t.clinician_id."""
        assert "t.clinician_id IN UNNEST(@clinician_ids)" in self.source

    def test_fetch_personal_also_checks_confirmation_table(self):
        """Export should also include cases confirmed by the clinician."""
        assert "c.clinician_id IN UNNEST(@clinician_ids)" in self.source

    def test_audit_log_accepts_clinician_id(self):
        """The audit log_triage call should accept clinician_id parameter."""
        audit_path = os.path.join(
            os.path.dirname(__file__), "..", "audit_service.py"
        )
        with open(audit_path, "r") as f:
            audit_source = f.read()
        assert "clinician_id" in audit_source
