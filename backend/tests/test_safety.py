"""Tests for benchmarks.safety — critical under-triage definitions."""

import pytest

from benchmarks.safety import (
    classify_triage_error,
    is_critical_under_triage,
    is_over_triage,
    is_under_triage,
    is_within_one_level,
)


# ---------------------------------------------------------------------------
# is_under_triage
# ---------------------------------------------------------------------------

class TestIsUnderTriage:
    def test_under_triage_true(self):
        assert is_under_triage(2, 3) is True
        assert is_under_triage(1, 5) is True
        assert is_under_triage(3, 4) is True

    def test_under_triage_false_exact_match(self):
        for esi in range(1, 6):
            assert is_under_triage(esi, esi) is False

    def test_under_triage_false_over_triage(self):
        assert is_under_triage(3, 2) is False
        assert is_under_triage(5, 1) is False

    def test_invalid_esi_raises(self):
        with pytest.raises(ValueError):
            is_under_triage(0, 3)
        with pytest.raises(ValueError):
            is_under_triage(3, 6)


# ---------------------------------------------------------------------------
# is_over_triage
# ---------------------------------------------------------------------------

class TestIsOverTriage:
    def test_over_triage_true(self):
        assert is_over_triage(3, 2) is True
        assert is_over_triage(5, 1) is True

    def test_over_triage_false(self):
        assert is_over_triage(2, 3) is False
        assert is_over_triage(3, 3) is False


# ---------------------------------------------------------------------------
# is_critical_under_triage — THE CORE SAFETY TEST
# ---------------------------------------------------------------------------

class TestIsCriticalUnderTriage:
    """
    Critical under-triage: actual ESI 1 or 2, predicted > actual.
    This is the single most important safety metric.
    """

    def test_esi1_predicted_higher_is_critical(self):
        """ESI 1 patient assigned ESI 2/3/4/5 = critical."""
        assert is_critical_under_triage(1, 2) is True
        assert is_critical_under_triage(1, 3) is True
        assert is_critical_under_triage(1, 4) is True
        assert is_critical_under_triage(1, 5) is True

    def test_esi2_predicted_higher_is_critical(self):
        """ESI 2 patient assigned ESI 3/4/5 = critical."""
        assert is_critical_under_triage(2, 3) is True
        assert is_critical_under_triage(2, 4) is True
        assert is_critical_under_triage(2, 5) is True

    def test_exact_match_not_critical(self):
        """Correct predictions are never critical under-triage."""
        assert is_critical_under_triage(1, 1) is False
        assert is_critical_under_triage(2, 2) is False

    def test_esi3_under_triage_not_critical(self):
        """ESI 3+ under-triage is concerning but NOT 'critical'."""
        assert is_critical_under_triage(3, 4) is False
        assert is_critical_under_triage(3, 5) is False
        assert is_critical_under_triage(4, 5) is False

    def test_over_triage_never_critical(self):
        """Over-triage (predicting MORE urgent) is never critical under-triage."""
        assert is_critical_under_triage(3, 1) is False
        assert is_critical_under_triage(5, 1) is False
        assert is_critical_under_triage(2, 1) is False

    def test_all_esi_pairs_exhaustive(self):
        """Exhaustively verify all 25 ESI pairs."""
        expected_critical = {(1, 2), (1, 3), (1, 4), (1, 5),
                             (2, 3), (2, 4), (2, 5)}
        for actual in range(1, 6):
            for pred in range(1, 6):
                result = is_critical_under_triage(actual, pred)
                if (actual, pred) in expected_critical:
                    assert result is True, f"({actual}, {pred}) should be critical"
                else:
                    assert result is False, f"({actual}, {pred}) should NOT be critical"


# ---------------------------------------------------------------------------
# classify_triage_error
# ---------------------------------------------------------------------------

class TestClassifyTriageError:
    def test_exact_match(self):
        for esi in range(1, 6):
            assert classify_triage_error(esi, esi) == "exact_match"

    def test_critical_under_triage(self):
        assert classify_triage_error(1, 3) == "critical_under_triage"
        assert classify_triage_error(2, 4) == "critical_under_triage"

    def test_non_critical_under_triage(self):
        assert classify_triage_error(3, 5) == "under_triage"
        assert classify_triage_error(4, 5) == "under_triage"

    def test_over_triage(self):
        assert classify_triage_error(4, 2) == "over_triage"
        assert classify_triage_error(3, 1) == "over_triage"


# ---------------------------------------------------------------------------
# is_within_one_level
# ---------------------------------------------------------------------------

class TestIsWithinOneLevel:
    def test_exact_match(self):
        for esi in range(1, 6):
            assert is_within_one_level(esi, esi) is True

    def test_one_off(self):
        assert is_within_one_level(2, 3) is True
        assert is_within_one_level(3, 2) is True
        assert is_within_one_level(1, 2) is True

    def test_two_off_is_not_within_one(self):
        assert is_within_one_level(1, 3) is False
        assert is_within_one_level(5, 3) is False
