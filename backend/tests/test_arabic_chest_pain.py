"""
Regression tests for Arabic chest-pain classification in the canonical
deterministic engine.

History: the cross-engine parity harness
(`tests/parity/run_python_engine.py` + `tests/parity/run_js_engine.mjs
--compare`) found that the Python engine was returning `severe_pain` /
ESI 4 for `ألم شديد في الصدر منذ ساعة` because every Arabic chest-pain
token assumed the pain-word and the chest-word were adjacent.  When a
modifier (شديد / حاد / خفيف) sat between them, the chest pathway never
fired and the complaint fell through to the generic severe-pain match.

This test pins the fixed behaviour:

  • Each common Arabic / Egyptian-dialect chest-pain phrasing must
    classify to `chest_pain_cardiac` in `_fallback_keyword_match` (the
    no-AI path used by Hospital Lite mode).
  • The end-to-end deterministic triage of an adult patient with normal
    vitals must return ESI level ≤ 2 (Emergent) for those phrasings —
    matching the English chest-pain behaviour.

Run with:  python -m pytest backend/tests/test_arabic_chest_pain.py -v
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

# Make `backend/` importable without installing the package.
REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND_DIR = REPO_ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

os.environ.setdefault("SAFE_TRIAGE_MODE", "hospital_lite")

import pytest

from logic.deterministic_triage import DeterministicTriageEngine


ARABIC_CHEST_PAIN_PHRASINGS = [
    # Plain forms (definite article).
    "ألم في الصدر",
    "ألم شديد في الصدر",
    "ألم شديد في الصدر منذ ساعة",
    "ألم حاد في الصدر",
    "وجع في الصدر",
    "وجع في الصدر بقاله ساعتين",
    "ضغط في الصدر",
    "ضغط على الصدر",
    "ضيق في الصدر",
    "ضيقة في الصدر",
    # Possessive variants — صدري / صدره / صدرها.
    "ألم في صدري",
    "وجع في صدره",
    "ضيق في صدرها",
    "حاسس بألم في صدري",
    # Word-order variants where the pain-word and chest-word are not
    # adjacent — modifiers or extra context sit between them.
    "ألم شديد ومتقطع في الصدر منذ ساعتين",
    "بحس بضغط شديد في الصدر مع ضيق نفس",
    "نغزة قوية في صدري بعد المجهود",
]

# Chest burning (حرقان) is intentionally tracked separately: clinically
# it overlaps the silent-MI / atypical ACS pathway because "حرقان" is
# Arabic colloquial for "burning" and is used for both heartburn (GI)
# and chest burning (cardiac).  The canonical engine routes it to
# `silent_mi` — a category now protected from severity-ceiling
# demotion in `_ESI2_MANDATORY_CATEGORIES`.  Both `silent_mi` and
# `chest_pain_cardiac` are clinically acceptable L2 cardiac pathways
# for these phrasings; the full-triage assertion (ESI ≤ 2) still
# applies.
ARABIC_CHEST_BURNING_PHRASINGS = [
    "حرقان في الصدر",
    "حرقان في صدري",
]
CARDIAC_L2_CATEGORIES = {"chest_pain_cardiac", "silent_mi"}

# Cases that look superficially similar (pain word present, or chest word
# present, but not BOTH).  These must NOT route to chest_pain_cardiac —
# the pair-check would over-trigger otherwise and the safety claim that
# "the rule does not catch unrelated severe pain without chest context"
# would be false.
ARABIC_NON_CHEST_PAIN_PHRASINGS = [
    "ألم في الركبة",        # knee pain
    "ألم شديد في الظهر",    # severe back pain
    "ألم في البطن",         # abdominal pain
    "وجع في الرأس",         # headache
    "ألم في الذراع",        # arm pain
]

ADULT_NORMAL_VITALS = {
    "hr": 92,
    "rr": 18,
    "spo2": 97,
    "sbp": 138,
    "dbp": 86,
    "temp": 37.0,
}


@pytest.fixture(scope="module")
def engine():
    return DeterministicTriageEngine(use_ai=False)


@pytest.mark.parametrize("complaint", ARABIC_CHEST_PAIN_PHRASINGS)
def test_classifier_routes_to_chest_pain_cardiac(engine, complaint):
    """`_fallback_keyword_match` must classify each phrasing as
    cardiac chest pain so the downstream ESI ceiling-bypass applies."""
    category = engine.ai_classifier._fallback_keyword_match(complaint)
    assert category == "chest_pain_cardiac", (
        f"Arabic chest-pain complaint {complaint!r} classified as "
        f"{category!r}; expected 'chest_pain_cardiac'. This is a "
        "regression of the parity-harness-discovered Arabic "
        "chest-pain under-triage bug."
    )


@pytest.mark.parametrize("complaint", ARABIC_CHEST_BURNING_PHRASINGS)
def test_chest_burning_routes_to_cardiac_l2_pathway(engine, complaint):
    """Chest burning (حرقان في الصدر) is clinically ambiguous between
    typical cardiac chest pain and atypical ACS (silent MI).  Either
    L2 pathway is acceptable; under-triage to L3+ is not."""
    category = engine.ai_classifier._fallback_keyword_match(complaint)
    assert category in CARDIAC_L2_CATEGORIES, (
        f"Chest-burning complaint {complaint!r} classified as "
        f"{category!r}; expected one of {CARDIAC_L2_CATEGORIES}."
    )


@pytest.mark.parametrize(
    "complaint", ARABIC_CHEST_PAIN_PHRASINGS + ARABIC_CHEST_BURNING_PHRASINGS,
)
def test_full_triage_returns_at_most_emergent(engine, complaint):
    """Adult with normal vitals + Arabic chest pain → ESI ≤ 2.

    We allow the canonical engine to escalate further (e.g. to ESI 1 if
    additional context triggers a safety floor), but we never accept
    ESI 3+ for chest pain in a connected Hospital Lite session.
    """
    payload = {
        "patient_id": "REGRESSION-CHEST",
        "age": 58.0,
        "gender": "male",
        "chief_complaint_text": complaint,
        "vitals": ADULT_NORMAL_VITALS,
        "consciousness": "A",
        "is_immunocompromised": False,
        "immuno_compromised": False,
        "on_supplemental_o2": False,
        "is_copd": False,
        "is_pregnant": False,
    }
    result = engine.triage(payload)
    level = getattr(result, "final_level", None) or getattr(result, "level", None)
    assert level is not None, f"Engine returned no level for {complaint!r}"
    assert level <= 2, (
        f"Arabic chest-pain {complaint!r} produced ESI {level}; "
        "must be ≤ 2 (Emergent or Resuscitation)."
    )


@pytest.mark.parametrize("complaint", ARABIC_NON_CHEST_PAIN_PHRASINGS)
def test_non_chest_pain_not_routed_to_chest_pain_cardiac(engine, complaint):
    """Pair-check safety: a pain-word with a NON-chest location must
    not be classified as cardiac chest pain.  Prevents the over-broad
    failure mode where any "ألم" anywhere becomes ESI 2 cardiac."""
    category = engine.ai_classifier._fallback_keyword_match(complaint)
    assert category != "chest_pain_cardiac", (
        f"Non-chest complaint {complaint!r} misclassified as "
        f"chest_pain_cardiac. The pair-check is too broad."
    )


def test_silent_mi_still_wins_when_gi_signals_present(engine):
    """Silent-MI safety pathway must run BEFORE the chest-pain
    pair-check.  When GI discomfort tokens (حرقان / heartburn) appear
    together with diaphoresis / fatigue tokens (عرق / تعب) AND chest
    signs, the engine must route to `silent_mi`, not `chest_pain_cardiac`.

    This is the explicit guardrail for atypical ACS presentation —
    losing it would be a clinical regression introduced by the new
    pair-check."""
    complaint = "حرقان في الصدر مع عرق وتعب شديد"
    category = engine.ai_classifier._fallback_keyword_match(complaint)
    assert category == "silent_mi", (
        f"Silent-MI pattern misclassified as {category!r}. The new "
        "Arabic chest-pain pair-check must not displace the silent-MI "
        "branch which has precedence in `_fallback_keyword_match`."
    )


def test_silent_mi_without_chest_signs_does_not_become_chest_pain(engine):
    """Sanity: a GI-only silent-MI-shaped complaint with no chest words
    must NOT be silently upgraded to chest_pain_cardiac by the new
    pair-check (since the pair requires a chest-word)."""
    complaint = "حرقان في المعدة مع تعب وعرق"
    category = engine.ai_classifier._fallback_keyword_match(complaint)
    assert category != "chest_pain_cardiac", (
        f"GI-only complaint {complaint!r} should not route to "
        f"chest_pain_cardiac; got {category!r}."
    )
