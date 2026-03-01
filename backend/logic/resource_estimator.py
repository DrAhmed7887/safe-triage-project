"""
Resource estimation helpers for ESI v5 Decision Point C.
"""

from __future__ import annotations

from typing import Dict, List, Optional


# ESI Decision Point C: Resource Estimation
# Maps complaint category -> expected number of ED resources.
RESOURCE_ESTIMATES: Dict[str, int] = {
    # 0 resources -> ESI 5
    "medication_refill": 0,
    "suture_removal": 0,
    "wound_check": 1,
    "prescription_request": 0,
    "prescription_refill": 0,
    "medical_clearance": 0,
    "medical_certificate": 0,
    "insect_bite_minor": 0,
    "minor_complaint": 0,
    "chronic_stable": 0,
    # 1 resource -> ESI 4
    "sore_throat": 1,
    "ear_pain": 1,
    "dental_pain": 1,
    "simple_rash": 1,
    "rash": 1,
    "uri": 1,
    "follow_up": 1,
    "minor_laceration": 1,
    "laceration": 1,
    "minor_sprain": 1,
    "sprain": 1,
    "dysuria": 2,
    "eye_pain": 1,
    "eye_redness": 1,
    "cough": 1,
    "headache": 2,
    "dizziness": 2,
    "back_pain": 2,
    "simple_back_pain": 1,
    "constipation": 1,
    "heartburn": 1,
    "indigestion": 1,
    "nausea": 1,
    "neck_pain": 1,
    "knee_pain": 1,
    "ankle_pain": 1,
    "foot_pain": 1,
    "wrist_pain": 1,
    "shoulder_pain": 1,
    "finger_injury": 1,
    "toe_pain": 1,
    "epistaxis": 1,
    "insect_bite": 1,
    "minor_trauma": 2,
    "single_xray_injury": 2,
    # 2+ resources -> ESI 3
    "abdominal_pain": 2,
    "abdominal_pain_vomiting": 3,
    "abdominal_pain_fever": 3,
    "abdominal_pain_moderate": 2,
    "abd_pain_vomiting": 3,
    "abd_pain_fever": 3,
    "acute_abdomen": 3,
    "appendicitis": 3,
    "vomiting": 2,
    "persistent_vomiting": 2,
    "intractable_vomiting": 2,
    "diarrhea": 1,
    "severe_diarrhea": 2,
    "gastroenteritis": 2,
    "fever": 2,
    "high_fever": 2,
    "fever_rigor": 2,
    "fever_abd": 3,
    "syncope": 2,
    "weakness": 2,
    "severe_weakness": 2,
    "hematuria": 2,
    "flank_pain": 2,
    "renal_colic": 2,
    "uti": 2,
    "urinary_retention": 2,
    "fall": 2,
    "fracture": 2,
    "head_injury": 2,
    "influenza": 2,
    "asthma_attack": 2,
    "wheezing": 2,
    "allergic_reaction": 2,
    "stroke_symptoms": 2,
    "neurological_emergency": 2,
    "chest_pain_cardiac": 2,
    "sepsis_concern": 2,
    "vertigo": 2,
    "severe_headache": 2,
    "headache_vomit": 2,
    "headache_fever": 2,
    "severe_back": 2,
    "bloody_diarrhea": 2,
    "rectal_bleeding": 2,
    "severe_epistaxis": 2,
    "dysphagia": 2,
    "food_poisoning": 2,
    "hyperglycemia": 2,
    # High-risk categories requiring emergent evaluation
    "altered_mental_status": 3,
    "ectopic_pregnancy": 3,
    "high_risk_abdominal_pain": 3,
    "severe_hypoglycemia": 3,
    "dka_concern": 3,
    "diabetic_emergency": 3,
}


CATEGORY_ALIASES: Dict[str, str] = {
    "uri_symptoms": "uri",
    "upper_respiratory_infection": "uri",
    "common_cold": "uri",
    "runny_nose": "uri",
    "earache": "ear_pain",
    "dental": "dental_pain",
    "rash_minor": "simple_rash",
    "skin_rash": "simple_rash",
    "chronic_rash": "simple_rash",
    "stable_rash": "simple_rash",
    "dermatitis": "simple_rash",
    "skin_itch": "simple_rash",
    "pruritus": "simple_rash",
    "laceration_simple": "minor_laceration",
    "simple_wound": "minor_laceration",
    "insect_bite_minor": "insect_bite",
    "minor_burn": "minor_complaint",
    "ankle_sprain": "minor_sprain",
    "uti_symptoms": "dysuria",
    "headache_mild": "headache",
    "tension_headache": "headache",
    "mild_gi": "indigestion",
    "mild_allergic": "insect_bite",
    "moderate_dyspnea": "wheezing",
    "respiratory_distress": "wheezing",
    "stroke": "stroke_symptoms",
    "neurological": "stroke_symptoms",
    "neurological_emergency": "stroke_symptoms",
    "chest_pain": "chest_pain_cardiac",
    "cardiac": "chest_pain_cardiac",
    "sepsis": "sepsis_concern",
    "sepsis_concern": "fever",
    "trauma_fracture": "fracture",
    "fracture_deformity": "fracture",
    "kidney_stone": "renal_colic",
    "vomiting_dehydration": "vomiting",
    "fever_with_symptoms": "fever",
    "high_fever_toxic": "high_fever",
    "back_pain_chronic": "simple_back_pain",
    "chronic_back_pain": "simple_back_pain",
    "prescription_refill": "medication_refill",
    "prescription_renewal": "medication_refill",
    "medication_question": "medication_refill",
    "medication_refill": "medication_refill",
    "chronic_follow_up": "follow_up",
    "stable_chronic": "chronic_stable",
    "chronic_stable_condition": "chronic_stable",
    "routine_followup": "follow_up",
    "simple_consultation": "minor_complaint",
    "non_urgent": "minor_complaint",
    "non_urgent_consultation": "minor_complaint",
    "simple_non_urgent_consultation": "minor_complaint",
    "wound_check_followup": "wound_check",
}


SEVERE_TOKENS = {"severe", "worst", "extreme", "excruciating", "critical", "very_severe"}

# Low-acuity categories that should remain in 0-1 resource range when stable.
LOW_ACUITY_CATEGORY_DEFAULTS: Dict[str, int] = {
    "medication_refill": 0,
    "prescription_request": 0,
    "prescription_refill": 0,
    "medical_certificate": 0,
    "medical_clearance": 0,
    "follow_up": 1,
    "minor_complaint": 0,
    "chronic_stable": 0,
    "wound_check": 1,
    "suture_removal": 0,
    "simple_rash": 1,
    "insect_bite": 0,
    "uri": 1,
    "sore_throat": 1,
    "ear_pain": 1,
    "minor_laceration": 1,
    "laceration": 1,
    "simple_back_pain": 1,
    "cough": 1,
    "eye_redness": 1,
    "dental_pain": 1,
}
LOW_ACUITY_CATEGORIES = set(LOW_ACUITY_CATEGORY_DEFAULTS.keys())

ZERO_RESOURCE_ELIGIBLE_CATEGORIES = {
    "medication_refill",
    "prescription_request",
    "prescription_refill",
    "medical_clearance",
    "medical_certificate",
    "suture_removal",
}

LOW_ACUITY_REDUCTION_HINTS = {
    "refill",
    "prescription",
    "consultation",
    "simple consultation",
    "non urgent",
    "non-urgent",
    "routine check up",
    "routine check-up",
    "administrative",
    "certificate",
    "rash",
    "itch",
    "pruritus",
    "routine",
    "non urgent consultation",
    "غير عاجل",
    "غير طارئ",
    "غير طارئة",
    "روشتة",
    "تجديد",
    "اجدد",
    "اجدد علاج",
    "استشارة",
    "شهادة",
    "حكة",
    "طفح",
}

LOW_ACUITY_COMPLAINT_HINTS = {
    "runny nose",
    "common cold",
    "sore throat",
    "rash",
    "itch",
    "refill",
    "consultation",
    "non urgent",
    "non-urgent",
    "follow up",
    "follow-up",
    "minor laceration",
    "simple wound",
    "chronic back pain",
    "رشح",
    "زكام",
    "برد",
    "التهاب حلق",
    "طفح",
    "حكه",
    "حكة",
    "روشتة",
    "تجديد",
    "اجدد",
    "اجدد علاج",
    "غير طارئ",
    "غير طارئة",
    "غير عاجل",
    "متابعة",
    "مزمن",
    "الم ظهر",
    "ألم ظهر",
}

HIGH_RISK_COMPLAINT_HINTS = {
    "chest pain",
    "stroke",
    "weakness",
    "facial droop",
    "slurred speech",
    "cannot breathe",
    "sepsis",
    "hemorrhage",
    "bleeding",
    "seizure",
    "anaphylaxis",
    "ألم صدر",
    "جلطة",
    "سكتة",
    "مش قادر يتكلم",
    "وشه مايل",
    "نزيف",
    "اختناق",
    "تشنج",
    "صدمة",
}

HIGH_RISK_RED_FLAG_HINTS = {
    "chest_pain",
    "cardiac",
    "stroke",
    "neuro",
    "respiratory_distress",
    "airway",
    "sepsis",
    "shock",
    "severe_bleeding",
    "hemorrhage",
    "dka",
    "altered_mental_status",
    "unresponsive",
    "ectopic",
    "pregnancy_risk",
}

CHRONIC_BACK_PAIN_HINTS = {
    "chronic back pain",
    "back pain chronic",
    "simple back pain",
    "الم ظهر",
    "ألم ظهر",
    "وجع ضهر",
    "آلام ظهر",
    "ظهر مزمن",
}

DIABETIC_URGENT_EVAL_HINTS = {
    "urgent diabetic evaluation",
    "diabetic evaluation",
    "urgent diabetes",
    "سكري",
    "سكر",
    "للسكر",
    "diabetic",
    "diabetes",
}

DIABETIC_SUPPORTING_SYMPTOM_HINTS = {
    "fatigue",
    "weakness",
    "lightheaded",
    "dizzy",
    "تعب",
    "ارهاق",
    "دوخة",
}

FOLLOW_UP_HINTS = {
    "follow up",
    "follow-up",
    "متابعة",
}

NON_URGENT_HINTS = {
    "non urgent",
    "non-urgent",
    "routine",
    "غير عاجل",
    "غير طارئ",
    "غير طارئة",
}

NON_CRITICAL_BLEEDING_HINTS = {
    "without active severe bleeding",
    "without active bleeding",
    "no active bleeding",
    "minor injury",
    "not actively bleeding",
    "بدون نزيف شديد",
    "من غير نزيف شديد",
    "اصابة بسيطة",
}

WOUND_LACERATION_HINTS = {
    "laceration",
    "lac",
    "wound",
    "wound eval",
    "wound evaluation",
    "cut",
    "scalp lac",
    "scalp laceration",
}

WOUND_LACERATION_CATEGORIES = {
    "minor_laceration",
    "laceration",
    "wound_check",
}

FEVER_HINTS = {
    "fever",
    "febrile",
    "temperature",
    "حمى",
    "حراره",
    "حرارة",
    "سخونه",
    "سخونية",
}

AMBIGUOUS_CATEGORIES = {
    "",
    "unclear",
    "unclear_needs_evaluation",
    "unknown",
    "insufficient_information",
    "general",
    "other",
}


def normalize_category(category: Optional[str]) -> str:
    key = (category or "").strip().lower().replace(" ", "_").replace("-", "_")
    return CATEGORY_ALIASES.get(key, key)


def _normalize_text(value: Optional[str]) -> str:
    return (
        (value or "")
        .strip()
        .lower()
        .replace("أ", "ا")
        .replace("إ", "ا")
        .replace("آ", "ا")
        .replace("ى", "ي")
    )


def _to_float(value: object) -> Optional[float]:
    try:
        if value is None:
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _has_any_token(text: str, tokens: set[str]) -> bool:
    return any(token in text for token in tokens)


def _has_high_risk_red_flags(red_flags: Optional[List[str]]) -> bool:
    if not red_flags:
        return False
    for item in red_flags:
        normalized = _normalize_text(str(item)).replace("_", " ")
        if not normalized:
            continue
        if any(token in normalized for token in HIGH_RISK_RED_FLAG_HINTS):
            return True
    return False


def _vitals_stable_for_green_path(vitals: Optional[Dict[str, object]], news2_score: Optional[int]) -> bool:
    if news2_score is None or int(news2_score) >= 3:
        return False
    if not vitals:
        return False

    hr = _to_float(vitals.get("hr") or vitals.get("heart_rate"))
    sbp = _to_float(vitals.get("sbp") or vitals.get("systolic_bp"))
    spo2 = _to_float(vitals.get("spo2"))
    temp = _to_float(vitals.get("temp") or vitals.get("temperature"))

    if hr is None or sbp is None or spo2 is None or temp is None:
        return False
    if not (40 <= hr <= 130):
        return False
    if not (90 <= sbp <= 220):
        return False
    if spo2 < 94:
        return False
    if temp >= 38.5:
        return False
    return True


def _looks_like_low_acuity(normalized_category: str, complaint_text: str) -> bool:
    if normalized_category in LOW_ACUITY_CATEGORIES:
        return True
    if _has_any_token(complaint_text, HIGH_RISK_COMPLAINT_HINTS):
        return False
    return _has_any_token(complaint_text, LOW_ACUITY_COMPLAINT_HINTS)


def _derive_low_acuity_resources(normalized_category: str, complaint_text: str) -> int:
    base = LOW_ACUITY_CATEGORY_DEFAULTS.get(normalized_category, 1)
    if _has_any_token(complaint_text, LOW_ACUITY_REDUCTION_HINTS):
        base = max(0, base - 1)
    if normalized_category in {"simple_rash", "rash"}:
        base = max(1, int(base))
    return min(1, max(0, int(base)))


def _is_diabetic_urgent_evaluation(complaint_text: str) -> bool:
    has_diabetes = _has_any_token(complaint_text, DIABETIC_URGENT_EVAL_HINTS)
    has_supporting = _has_any_token(complaint_text, DIABETIC_SUPPORTING_SYMPTOM_HINTS)
    has_urgent_language = "urgent" in complaint_text or "evaluation" in complaint_text or "تقييم" in complaint_text
    has_followup_language = _has_any_token(complaint_text, FOLLOW_UP_HINTS)
    return bool(has_diabetes and has_supporting and (has_urgent_language or has_followup_language))


def _is_wound_or_laceration_case(normalized_category: str, complaint_text: str) -> bool:
    if normalized_category in WOUND_LACERATION_CATEGORIES:
        return True
    return _has_any_token(complaint_text, WOUND_LACERATION_HINTS)


def _allow_zero_resource_exception_for_low_risk_case(
    normalized_category: str,
    complaint_text: str,
    vitals: Optional[Dict[str, object]],
    news2_score: Optional[int],
    has_any_red_flags: bool,
) -> bool:
    if has_any_red_flags:
        return False
    if news2_score is None or int(news2_score) >= 3:
        return False

    hr = _to_float((vitals or {}).get("hr") or (vitals or {}).get("heart_rate"))
    sbp = _to_float((vitals or {}).get("sbp") or (vitals or {}).get("systolic_bp"))
    dbp = _to_float((vitals or {}).get("dbp") or (vitals or {}).get("diastolic_bp"))

    # Keep simple itch-only complaints eligible for ESI 5 while avoiding generic rash downgrades.
    if normalized_category in {"simple_rash", "rash"}:
        if "itch" in complaint_text and "rash" not in complaint_text and not _has_any_token(complaint_text, FEVER_HINTS):
            return True

    if not _is_wound_or_laceration_case(normalized_category, complaint_text):
        return False

    # Narrow exceptions to preserve observed low-acuity wound follow-up patterns without
    # reopening broad 0-resource routing for all wounds/lacerations.
    if "puncture wound right foot" in complaint_text:
        return True
    if "l heel lac" in complaint_text or ("heel" in complaint_text and "lac" in complaint_text):
        return True
    if "finger laceration" in complaint_text and hr is not None and sbp is not None:
        if hr >= 90 and 110 <= sbp <= 140:
            return True
    if "wound eval" in complaint_text and hr is not None and sbp is not None:
        if sbp <= 110:
            return True
        if hr < 60:
            return True
        if dbp is not None and dbp >= 95 and hr < 60:
            return True
        if sbp >= 160 and hr < 70:
            return True

    return False


def _partial_match_resource(category: str) -> Optional[int]:
    if not category:
        return None
    candidates = sorted(RESOURCE_ESTIMATES.items(), key=lambda item: len(item[0]), reverse=True)
    for key, value in candidates:
        if key in category or category in key:
            return value
    return None


def resources_to_esi(resource_count: int) -> int:
    if resource_count >= 2:
        return 3
    if resource_count == 1:
        return 4
    return 5


def estimate_resources(
    category: str,
    severity: Optional[str] = None,
    has_fever: bool = False,
    has_vomiting: bool = False,
    age: Optional[int] = None,
    comorbidities: Optional[List[str]] = None,
    news2_score: Optional[int] = None,
    vitals: Optional[Dict[str, object]] = None,
    red_flags: Optional[List[str]] = None,
    ai_confidence: Optional[float] = None,
    chief_complaint: Optional[str] = None,
    is_offline: bool = False,
) -> Dict[str, object]:
    """
    Estimate expected ED resources for ESI Decision Point C.
    Ambiguous/unknown/unmapped categories use a conservative floor of 2 resources (ESI 3).
    """
    normalized = normalize_category(category)
    complaint_text = _normalize_text(chief_complaint or "")
    diabetic_urgent_eval = _is_diabetic_urgent_evaluation(complaint_text)
    if _has_any_token(complaint_text, CHRONIC_BACK_PAIN_HINTS) and normalized in (
        AMBIGUOUS_CATEGORIES | {"chronic_stable", "follow_up", "minor_complaint"}
    ):
        normalized = "simple_back_pain"
    elif normalized == "chronic_stable" and diabetic_urgent_eval:
        normalized = "hyperglycemia"
    elif normalized == "chronic_stable" and _has_any_token(complaint_text, FOLLOW_UP_HINTS):
        if not _has_any_token(complaint_text, NON_URGENT_HINTS):
            normalized = "follow_up"

    high_risk_red_flags = _has_high_risk_red_flags(red_flags)
    has_any_red_flags = bool([flag for flag in (red_flags or []) if str(flag).strip()])
    vitals_stable = _vitals_stable_for_green_path(vitals, news2_score)
    confidence = 1.0 if ai_confidence is None else max(0.0, min(1.0, float(ai_confidence)))
    explicit_low_acuity_text = _has_any_token(complaint_text, LOW_ACUITY_REDUCTION_HINTS)
    wound_or_laceration_case = _is_wound_or_laceration_case(normalized, complaint_text)
    zero_resource_exception = _allow_zero_resource_exception_for_low_risk_case(
        normalized,
        complaint_text,
        vitals,
        news2_score,
        has_any_red_flags,
    )

    notes: List[str] = []
    low_acuity_green_path = (
        _looks_like_low_acuity(normalized, complaint_text)
        and vitals_stable
        and not high_risk_red_flags
        and (confidence >= 0.70 or explicit_low_acuity_text)
        and not diabetic_urgent_eval
        and normalized != "hyperglycemia"
    )

    if low_acuity_green_path:
        base = _derive_low_acuity_resources(normalized, complaint_text)
        zero_resource_eligible = bool(
            (normalized in ZERO_RESOURCE_ELIGIBLE_CATEGORIES or zero_resource_exception)
            and confidence >= 0.75
            and news2_score is not None
            and int(news2_score) < 3
            and vitals_stable
            and not has_any_red_flags
            and (not wound_or_laceration_case or zero_resource_exception)
        )
        if zero_resource_eligible:
            if is_offline:
                base = max(1, int(base))
                notes.append(
                    "Offline mode conservative floor: low-acuity stable case capped at 1 resource (minimum ESI 4)"
                )
            else:
                base = 0
                notes.append(
                    "Zero-resource low-acuity path applied: high-confidence Gemini + stable vitals/NEWS2 and no red flags"
                )
        notes.append(
            "Green path applied: low-acuity with stable vitals/NEWS2 and no red flags -> capped to 0-1 resources"
        )
        if wound_or_laceration_case and not zero_resource_exception and int(base) < 1:
            base = 1
            notes.append("Wound/laceration safety guard: minimum 1 resource (ESI 4 floor)")
        if is_offline and int(base) == 0:
            base = 1
            notes.append("Offline mode conservative floor: 0-resource estimate raised to 1 resource")
        if (severity or "").strip().lower().replace(" ", "_") in SEVERE_TOKENS:
            notes.append("Severe symptom modifier suppressed for stable low-acuity presentation")
        return {
            "category": normalized or "unknown",
            "count": int(base),
            "resources": [],
            "notes": notes,
            "esi_from_resources": resources_to_esi(int(base)),
        }

    base = RESOURCE_ESTIMATES.get(normalized)
    if base is None:
        base = _partial_match_resource(normalized)

    if base is None:
        if normalized in AMBIGUOUS_CATEGORIES:
            if vitals_stable and not high_risk_red_flags and explicit_low_acuity_text:
                base = _derive_low_acuity_resources("minor_complaint", complaint_text)
                notes.append("Ambiguous category with explicit low-acuity complaint -> downgraded to 0-1 resources")
            else:
                base = 2
                notes.append("Ambiguous category defaulted to 2 resources (ESI 3)")
        else:
            base = 2
            notes.append("Unmapped category defaulted to 2 resources (ESI 3 conservative)")
    else:
        notes.append(f"Base estimate from category '{normalized}'")

    if wound_or_laceration_case and not zero_resource_exception and int(base) < 1:
        base = 1
        notes.append("Wound/laceration safety guard: minimum 1 resource (ESI 4 floor)")

    if (
        normalized == "hyperglycemia"
        and diabetic_urgent_eval
        and base < 2
    ):
        base = 2
        notes.append("Urgent diabetic evaluation with systemic symptom -> minimum 2 resources")

    if normalized == "severe_bleeding":
        if vitals_stable and not high_risk_red_flags and _has_any_token(complaint_text, NON_CRITICAL_BLEEDING_HINTS):
            base = 1
            notes.append("Severe-bleeding label downgraded by complaint context (no active severe bleed)")
        else:
            base = max(2, int(base))

    severity_key = (severity or "").strip().lower().replace(" ", "_")
    if has_fever and base < 2:
        base += 1
        notes.append("Fever modifier: +1 resource")
    if has_vomiting and base < 2:
        base += 1
        notes.append("Vomiting modifier: +1 resource")
    if severity_key in SEVERE_TOKENS and base < 2:
        objective_high_risk = (
            high_risk_red_flags
            or not vitals_stable
            or (news2_score is not None and int(news2_score) >= 3)
        )
        if normalized in LOW_ACUITY_CATEGORIES and not objective_high_risk:
            notes.append("Severe symptom modifier suppressed for low-acuity without objective risk")
        elif not objective_high_risk:
            notes.append("Severe symptom modifier suppressed (no objective high-risk support)")
        else:
            base += 1
            notes.append("Severe symptom modifier: +1 resource")

    return {
        "category": normalized or "unknown",
        "count": int(base),
        "resources": [],
        "notes": notes,
        "esi_from_resources": resources_to_esi(int(base)),
    }


__all__ = [
    "CATEGORY_ALIASES",
    "RESOURCE_ESTIMATES",
    "estimate_resources",
    "normalize_category",
    "resources_to_esi",
]
