"""
Safety Definitions for SAFE-Triage Benchmarking
================================================

This module contains the single, authoritative definition of critical
under-triage and related safety metrics. All benchmark scripts MUST
use these functions — do not redefine safety logic elsewhere.

Definitions:
  - Under-triage: predicted ESI > actual ESI (less urgent than reality)
  - Over-triage: predicted ESI < actual ESI (more urgent than reality)
  - Critical under-triage: actual ESI is 1 or 2, AND predicted ESI is
    strictly greater than actual ESI.

    This means: a truly high-acuity patient (resuscitation or emergent)
    was assigned a LESS urgent triage level than warranted.

    SAFETY RATIONALE: Under-triaging ESI 1/2 patients risks delayed
    life-saving intervention. Over-triaging (erring on the side of
    caution) is clinically preferable to under-triaging critical patients.

Assumptions documented:
  - ESI 1 = most urgent (resuscitation), ESI 5 = least urgent
  - A prediction of ESI 2 for an ESI 1 patient IS critical under-triage
    (even though both are "high acuity"), because ESI 1 requires
    IMMEDIATE resuscitation that ESI 2 does not guarantee
  - A prediction of ESI 3 for an ESI 2 patient IS critical under-triage
  - Under-triage of ESI 3+ patients is concerning but not "critical"
    in this definition
"""

from __future__ import annotations


def is_under_triage(actual_esi: int, predicted_esi: int) -> bool:
    """
    True if the predicted ESI is less urgent than the actual ESI.

    Under-triage means the system assigned a higher number (less urgent)
    than the true acuity level.

    Args:
        actual_esi: Ground-truth ESI level (1-5).
        predicted_esi: System-predicted ESI level (1-5).

    >>> is_under_triage(2, 3)
    True
    >>> is_under_triage(3, 2)
    False
    >>> is_under_triage(3, 3)
    False
    """
    _validate_esi(actual_esi, "actual_esi")
    _validate_esi(predicted_esi, "predicted_esi")
    return predicted_esi > actual_esi


def is_over_triage(actual_esi: int, predicted_esi: int) -> bool:
    """
    True if the predicted ESI is more urgent than the actual ESI.

    Over-triage means the system assigned a lower number (more urgent)
    than the true acuity level.

    >>> is_over_triage(3, 2)
    True
    >>> is_over_triage(2, 3)
    False
    """
    _validate_esi(actual_esi, "actual_esi")
    _validate_esi(predicted_esi, "predicted_esi")
    return predicted_esi < actual_esi


def is_critical_under_triage(actual_esi: int, predicted_esi: int) -> bool:
    """
    True if a high-acuity patient (ESI 1 or 2) was under-triaged.

    This is the most dangerous type of triage error: a patient needing
    immediate or emergent care is classified as less urgent.

    Critical under-triage cases:
      - Actual ESI 1, predicted ESI 2/3/4/5
      - Actual ESI 2, predicted ESI 3/4/5

    NOT critical under-triage:
      - Actual ESI 3, predicted ESI 4 (concerning, not critical)
      - Actual ESI 4, predicted ESI 5 (minor)
      - Any over-triage or exact match

    >>> is_critical_under_triage(1, 3)
    True
    >>> is_critical_under_triage(2, 4)
    True
    >>> is_critical_under_triage(1, 1)
    False
    >>> is_critical_under_triage(3, 5)
    False
    >>> is_critical_under_triage(4, 2)
    False
    """
    _validate_esi(actual_esi, "actual_esi")
    _validate_esi(predicted_esi, "predicted_esi")
    return actual_esi <= 2 and predicted_esi > actual_esi


def classify_triage_error(
    actual_esi: int, predicted_esi: int
) -> str:
    """
    Classify the triage outcome into one of four categories.

    Returns one of:
      - "exact_match"
      - "critical_under_triage"
      - "under_triage"
      - "over_triage"

    >>> classify_triage_error(2, 2)
    'exact_match'
    >>> classify_triage_error(1, 3)
    'critical_under_triage'
    >>> classify_triage_error(3, 5)
    'under_triage'
    >>> classify_triage_error(4, 2)
    'over_triage'
    """
    _validate_esi(actual_esi, "actual_esi")
    _validate_esi(predicted_esi, "predicted_esi")

    if predicted_esi == actual_esi:
        return "exact_match"
    if is_critical_under_triage(actual_esi, predicted_esi):
        return "critical_under_triage"
    if is_under_triage(actual_esi, predicted_esi):
        return "under_triage"
    return "over_triage"


def is_within_one_level(actual_esi: int, predicted_esi: int) -> bool:
    """
    True if the prediction is within one ESI level of the actual.

    >>> is_within_one_level(3, 4)
    True
    >>> is_within_one_level(1, 3)
    False
    """
    _validate_esi(actual_esi, "actual_esi")
    _validate_esi(predicted_esi, "predicted_esi")
    return abs(predicted_esi - actual_esi) <= 1


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

def _validate_esi(value: int, name: str) -> None:
    """Ensure ESI value is in valid range."""
    if not isinstance(value, int) or value < 1 or value > 5:
        raise ValueError(
            f"{name} must be an integer between 1 and 5, got {value!r}"
        )
