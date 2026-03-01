from pathlib import Path
import sys


BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

import main  # noqa: E402


def test_normalize_ai_category_runny_nose_mild_cough():
    ai_result = {
        "category": "respiratory_distress",
        "extracted_symptoms": ["runny nose", "mild cough"],
        "reasoning": "Likely uncomplicated URI symptoms.",
    }
    category = main._normalize_ai_category_for_esi(ai_result, "Runny nose and mild cough for two days")
    assert category == "uri_symptoms"


def test_normalize_ai_category_simple_non_urgent_consultation():
    ai_result = {
        "category": "other",
        "extracted_symptoms": ["simple consultation"],
        "reasoning": "Routine non-urgent visit.",
    }
    category = main._normalize_ai_category_for_esi(ai_result, "Simple non-urgent consultation")
    assert category == "minor_complaint"


def test_normalize_ai_category_mild_sore_throat():
    ai_result = {
        "category": "respiratory",
        "extracted_symptoms": ["mild sore throat"],
        "reasoning": "Mild upper respiratory complaint without dyspnea.",
    }
    category = main._normalize_ai_category_for_esi(
        ai_result,
        "Mild sore throat without respiratory distress",
    )
    assert category == "sore_throat"


def test_normalize_ai_category_stroke_fast_case():
    ai_result = {
        "category": "other",
        "extracted_symptoms": ["facial droop", "unilateral arm weakness", "slurred speech"],
    }
    category = main._normalize_ai_category_for_esi(
        ai_result,
        "Facial droop, unilateral arm weakness, and slurred speech",
    )
    assert category == "stroke_symptoms"


def test_normalize_ai_category_severe_chest_pain_case():
    ai_result = {
        "category": "other",
        "extracted_symptoms": ["severe chest pain", "radiating to left arm"],
    }
    category = main._normalize_ai_category_for_esi(
        ai_result,
        "Severe chest pain radiating to left arm",
    )
    assert category == "chest_pain_cardiac"


def test_sanitize_ai_red_flags_drops_non_objective_noise():
    flags = main._sanitize_ai_red_flags(
        ["acute onset", "pain", "respiratory_distress"],
        complaint_text="Runny nose and mild cough for two days",
        normalized_category="uri_symptoms",
    )
    assert flags == []


def test_sanitize_ai_red_flags_keeps_objective_supported_flags():
    flags = main._sanitize_ai_red_flags(
        ["acute onset", "chest_pain", "radiation_to_arm"],
        complaint_text="Severe chest pain radiating to left arm",
        normalized_category="chest_pain_cardiac",
    )
    assert "chest_pain" in flags
    assert "radiation_to_arm" in flags
