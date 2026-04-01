"""
Deterministic ESI v5 two-stage engine with confidence-aware escalation.

Safety principle:
- AI extracts features
- Rules assign ESI
- Human confirms
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional, Tuple

try:
    from logic.resource_estimator import estimate_resources, resources_to_esi
except ImportError:  # pragma: no cover - package import fallback
    from backend.logic.resource_estimator import estimate_resources, resources_to_esi


class ESILevel(Enum):
    RESUSCITATION = 1
    EMERGENT = 2
    URGENT = 3
    LESS_URGENT = 4
    NON_URGENT = 5


@dataclass
class PatientFeatures:
    chief_complaint: str
    snomed_codes: List[str]
    body_system: str
    severity: str
    onset: str
    red_flags: List[str]
    age: int
    gender: str
    comorbidities: List[str]
    mental_status: str
    pain_score: Optional[int]
    ai_confidence: float
    is_offline: bool = False


@dataclass
class VitalSigns:
    heart_rate: Optional[int]
    systolic_bp: Optional[int]
    diastolic_bp: Optional[int]
    respiratory_rate: Optional[int]
    spo2: Optional[float]
    temperature: Optional[float]
    gcs: Optional[int]


@dataclass
class NEWS2Result:
    total_score: int
    risk_level: str
    parameter_scores: Dict[str, int]
    single_param_3: bool


@dataclass
class TriageResult:
    esi_level: int
    reasoning: List[str]
    stage_reached: str
    resources_estimated: int
    safety_floors_applied: List[str]
    confidence_action: str
    news2_override: bool
    final_esi: int
    context_rules_triggered: List[str]
    requires_review: bool


LIFE_THREATENING_CONDITIONS = {
    "airway_obstruction",
    "anaphylaxis",
    "angioedema_airway",
    "severe_respiratory_distress",
    "apnea",
    "intubated",
    "respiratory_arrest",
    "severe_asthma_attack",
    "tension_pneumothorax",
    "cardiac_arrest",
    "pulseless",
    "active_massive_hemorrhage",
    "hemodynamic_instability",
    "shock",
    "unresponsive",
    "gcs_3_to_8",
    "status_epilepticus",
    "actively_seizing",
    "major_trauma",
    "penetrating_chest_wound",
    "severe_burns_over_30pct",
}

LIFE_THREATENING_SNOMED = {
    "410429000",
    "230690007",
    "39579001",
    "233604007",
    "91302008",
}

HIGH_RISK_SNOMED = {
    "29857009",
    "230690007",
    "22298006",
    "267036007",
    "3006004",
}

UNKNOWN_CATEGORIES = {
    "",
    "unclear",
    "unclear_needs_evaluation",
    "insufficient_information",
    "unknown",
    "other",
    "general",
}

GI_SIGNALS = {
    "heartburn",
    "indigestion",
    "dyspepsia",
    "epigastric",
    "abdominal_pain",
    "حرقان",
    "حموضة",
    "عسر هضم",
    "فم المعدة",
    "المعدة",
}

ATYPICAL_ACS_SIGNALS = {
    "fatigue",
    "nausea",
    "jaw_pain",
    "back_pain",
    "weakness",
    "sweating",
    "diaphoresis",
    "عرق",
}

URINARY_NONCARDIAC_SIGNALS = {
    "urinary",
    "urine",
    "dysuria",
    "uti",
    "التهاب بول",
    "حرقان بول",
    "حرقان عند التبول",
    "بول",
}

CHEST_PAIN_SIGNALS = {
    "chest_pain",
    "chest pain",
    "angina",
    "discomfort, chest",
    "discomfort chest",
    "chest discomfort",
    "chest palpitation",
    "pain, chest",
    "pain chest",
    "صدري",
    "الم صدر",
    "ألم صدر",
    "وجع في الصدر",
    "وجع في صدرها",
    "وجع في صدره",
    "وجع في صدري",
    "وجع صدر",
}

STROKE_FAST_SNOMED = {"230690007", "87486003", "29040004", "50582007", "95820000"}

STROKE_EXPLICIT_SIGNALS = {
    "stroke",
    "cva",
    "face droop",
    "facial droop",
    "facial asymmetry",
    "arm weakness",
    "arm drift",
    "unilateral weakness",
    "one-sided weakness",
    "left-sided weakness",
    "right-sided weakness",
    "aphasia",
    "dysarthria",
    "speech loss",
    "sudden speech loss",
    "slurred speech",
    "speech difficulty",
    "difficulty speaking",
    "inability to speak",
    "unable to speak",
    "cannot speak",
    "can't speak",
    "sudden inability to speak",
    # Lateralized motor weakness patterns (Korean/international ED phrasing)
    "motor weakness",
    "left side weakness",
    "right side weakness",
    "left side motor weakness",
    "right side motor weakness",
    "lt. side weakness",
    "rt. side weakness",
    "lt. motor weakness",
    "rt. motor weakness",
    "lt side weakness",
    "rt side weakness",
    "left motor weakness",
    "right motor weakness",
    "lower extremity paraparesis",
    "paraparesis",
    "side motor weakness",
    "جلطة",
    "جلطة في المخ",
    "سكتة",
    "سكتة دماغية",
    "مش قادر اتكلم",
    "مش قادر أتكلم",
    "مبقتش قادر اتكلم",
    "كلامي اتلخبط",
    "كلامه اتلخبط",
    "لساني اتلت",
    "لسانه اتلت",
    "لساني تقيل",
    "لسانه تقيل",
    "كلامي مش واضح",
    "وشه مايل",
    "وشي مايل",
    "ايده ضعيفة",
    "رجله ضعيفة",
    "نص جسمه مش شغال",
    "مش قادر يرفع ايده",
    "سوء وعي مفاجئ",
    "تشوش مفاجئ",
    "لخبطه مفاجئه",
}

STROKE_SPEECH_HIGH_RISK_SIGNALS = {
    "slurred speech",
    "speech difficulty",
    "difficulty speaking",
    "inability to speak",
    "unable to speak",
    "cannot speak",
    "can't speak",
    "loss of speech",
    "sudden speech loss",
    "sudden inability to speak",
    "aphasia",
    "dysarthria",
    "مش قادر اتكلم",
    "مش قادر أتكلم",
    "مبقتش قادر اتكلم",
    "مش قادر يتكلم",
    "كلامي اتلخبط",
    "كلامه اتلخبط",
    "لساني اتلت",
    "لسانه اتلت",
    "لساني تقيل",
    "لسانه تقيل",
    "كلامي مش واضح",
    "فقدان النطق",
    "فقدان الكلام",
    "عدم القدرة على الكلام",
    "عدم القدرة على التكلم",
}

STROKE_SINGLE_FAST_SIGNALS = {
    "facial droop",
    "face droop",
    "face drooping",
    "facial asymmetry",
    "وشي مايل",
    "وشه مايل",
    "وشي اتعوج",
    "وشه اتعوج",
    "نص وشي وقع",
    "نص وشه وقع",
    "arm weakness",
    "one side weakness",
    "one sided weakness",
    "one-sided weakness",
    "unilateral weakness",
    "left-sided weakness",
    "right-sided weakness",
    "arm drift",
    "hemiplegia",
    "hemiparesis",
    # Lateralized motor weakness patterns (Korean/international ED phrasing)
    "motor weakness",
    "left side weakness",
    "right side weakness",
    "left side motor weakness",
    "right side motor weakness",
    "lt. side weakness",
    "rt. side weakness",
    "lt. motor weakness",
    "rt. motor weakness",
    "lt side weakness",
    "rt side weakness",
    "left motor weakness",
    "right motor weakness",
    "paraparesis",
    "side motor weakness",
    "نص جسمي مش بيتحرك",
    "نص جسمه مش بيتحرك",
    "نص جسمه مش شغال",
    "ايدي مش بتتحرك",
    "ايده مش بتتحرك",
    "رجلي مش بتتحرك",
    "انحراف بالفم",
    "انحراف في الفم",
    "انحراف الفم",
    "ضعف في الطرف الايسر",
    "ضعف بالطرف الايسر",
    "ضعف مفاجئ في الطرف الايسر",
    "ضعف في الطرف الايمن",
    "ضعف بالطرف الايمن",
    "ضعف مفاجئ في الطرف الايمن",
    "ايده ضعيفة",
    "رجله ضعيفة",
    "مش قادر يرفع ايده",
    "لسانه تقيل",
    "ايده وقعت",
    "ايدي وقعت",
}

STROKE_SPEECH_SIGNALS = {
    "speech",
    "slurred",
    "slurred speech",
    "speech difficulty",
    "difficulty speaking",
    "inability to speak",
    "unable to speak",
    "cannot speak",
    "can't speak",
    "aphasia",
    "dysarthria",
    "كلام",
    "اتكلم",
    "يتكلم",
    "نطق",
    "لسان",
    "لساني",
    "لسانه",
    "مش قادر يتكلم",
    "مش عارف يتكلم",
    "مش عارف اتكلم",
    "كلامه متلخبط",
}

STROKE_FACE_SIGNALS = {
    "facial droop",
    "face droop",
    "face drooping",
    "facial asymmetry",
    "وش",
    "وشي",
    "وشه",
    "مايل",
    "اتعوج",
    "انحراف بالفم",
    "انحراف في الفم",
    "انحراف الفم",
    "نص وشي وقع",
    "نص وشه وقع",
    "وقع",
}

STROKE_WEAKNESS_SIGNALS = {
    "arm weakness",
    "arm drift",
    "one side weakness",
    "one sided weakness",
    "one-sided weakness",
    "unilateral weakness",
    "left-sided weakness",
    "right-sided weakness",
    "hemiplegia",
    "hemiparesis",
    "weakness one side",
    # Lateralized motor weakness patterns (Korean/international ED phrasing)
    "motor weakness",
    "left side weakness",
    "right side weakness",
    "left side motor weakness",
    "right side motor weakness",
    "lt. side weakness",
    "rt. side weakness",
    "lt. motor weakness",
    "rt. motor weakness",
    "lt side weakness",
    "rt side weakness",
    "left motor weakness",
    "right motor weakness",
    "paraparesis",
    "side motor weakness",
    "نص جسمي",
    "نص جسمه",
    "نص جسمه مش شغال",
    "مش بيتحرك",
    "ايدي مش بتتحرك",
    "ايده مش بتتحرك",
    "رجلي مش بتتحرك",
    "ايده ضعيفة",
    "رجله ضعيفة",
    "ضعف في الطرف الايسر",
    "ضعف بالطرف الايسر",
    "ضعف مفاجئ في الطرف الايسر",
    "ضعف في الطرف الايمن",
    "ضعف بالطرف الايمن",
    "ضعف مفاجئ في الطرف الايمن",
    "مش قادر يرفع ايده",
    "ايده وقعت",
}

STROKE_CONFUSION_SIGNALS = {
    "sudden confusion",
    "acute confusion",
    "confused suddenly",
    "abrupt confusion",
    "altered speech",
    "altered mental status",
    "altered mentality",
    "mental change",
    "altered mental change",
    "confuse mentality",
    "confused mentality",
    "change in mental",
    "loss of consciousness",
    "confusion and inability to speak",
    "تشوش مفاجئ",
    "ارتباك مفاجئ",
    "لخبطه مفاجئه",
    "تلخبط مفاجئ",
    "يتلخبط",
    "بدأ فجاة يتلخبط",
}

STROKE_SUDDEN_SIGNALS = {
    "sudden",
    "abrupt",
    "acute",
    "started suddenly",
    "فجاه",
    "فجاة",
    "فجأة",
    "من شوية",
    "لسه",
    "النهارده",
    "الان",
    "دلوقتي",
}

FAST_FACE_RAW_SIGNALS = {
    "facial asymmetry",
    "facial droop",
    "face droop",
    "face drooping",
    "وشه مايل",
    "وشه اتلوى",
    "وشه اتلوي",
    "وشي مايل",
    "وشي اتلوى",
    "وشي اتلوي",
    "انحراف بالفم",
    "انحراف في الفم",
    "انحراف الفم",
    "نص وشه",
}

FAST_ARM_RAW_SIGNALS = {
    "arm weakness",
    "arm drift",
    "left-sided weakness",
    "right-sided weakness",
    "unilateral weakness",
    "hemiparesis",
    "hemiplegia",
    "motor weakness",
    "left side weakness",
    "right side weakness",
    "left side motor weakness",
    "right side motor weakness",
    "lt. side weakness",
    "rt. side weakness",
    "lt. motor weakness",
    "rt. motor weakness",
    "lt side weakness",
    "rt side weakness",
    "left motor weakness",
    "right motor weakness",
    "paraparesis",
    "side motor weakness",
    "ايده ضعيفة",
    "رجله ضعيفة",
    "نص جسمه",
    "ضعف في الطرف الايسر",
    "ضعف بالطرف الايسر",
    "ضعف مفاجئ في الطرف الايسر",
    "ضعف في الطرف الايمن",
    "ضعف بالطرف الايمن",
    "ضعف مفاجئ في الطرف الايمن",
}

FAST_SPEECH_RAW_SIGNALS = {
    "slurred speech",
    "inability to speak",
    "unable to speak",
    "speech difficulty",
    "cannot speak",
    "aphasia",
    "dysarthria",
    "مش قادر يتكلم",
    "مش عارف يتكلم",
    "مش عارف اتكلم",
    "بيتكلم غريب",
    "لسانه تقيل",
}

FAST_CONFUSION_RAW_SIGNALS = {
    "sudden confusion",
    "acute confusion",
    "altered mental status",
    "altered mentality",
    "mental change",
    "altered mental change",
    "confuse mentality",
    "confused mentality",
    "change in mental",
    "loss of consciousness",
    "loc",
    "syncope",
    "confusion and inability to speak",
    "ارتباك مفاجئ",
    "بدأ فجاة يتلخبط",
    "بدأ فجاه يتلخبط",
    "يتلخبط ومش عارف يتكلم",
}

ABDOMINAL_SIGNALS = {
    "abdominal",
    "abdomen",
    "stomach",
    "belly",
    "abdominal_pain",
    "abdominal pain",
    "بطني",
    "بطن",
    "المعدة",
    "معده",
}

BACK_PAIN_SIGNALS = {
    "back pain",
    "lower back pain",
    "lumbar pain",
    "flank pain",
    "ظهر",
    "الم ظهر",
    "ألم ظهر",
    "وجع ضهر",
    "الخاصرة",
}

ACUTE_ONSET_SIGNALS = {
    "acute",
    "sudden",
    "abrupt",
    "suddenly",
    "new onset",
    "فجاه",
    "فجاة",
    "فجأة",
    "حاد",
}

ECTOPIC_RISK_SIGNALS = {
    "ectopic",
    "pregnancy",
    "early pregnancy",
    "first trimester",
    "حمل",
    "حامل",
    "حمل خارج الرحم",
    "نزيف مهبلي",
    "ectopic_pregnancy_risk",
}

LOW_ACUITY_UNKNOWN_HINTS = {
    "chronic back pain",
    "stable chronic",
    "follow-up",
    "follow up",
    "non urgent",
    "non-urgent",
    "consultation",
    "medication refill",
    "routine check",
    "استشارة",
    "غير عاجل",
    "غير طارئ",
    "غير طارئة",
    "اجدد علاج",
    "تجديد علاج",
    "متابعة",
    "الم ظهر مزمن",
    "الام ظهر مزمنة",
}

FEVER_SIGNALS = {
    "fever",
    "pyrexia",
    "febrile",
    "حمى",
    "سخونية",
    "سخونه",
    "حرارة",
}

NEGATED_FEVER_PHRASES = {
    "no fever",
    "no fevers",
    "denies fever",
    "denies fevers",
    "without fever",
    "afebrile",
    "بدون حرارة",
    "لا يوجد حرارة",
    "لا توجد حرارة",
    "ينفي الحمى",
    "دون حمى",
}

FEVER_SNOMED_CODES = {"386661006"}

VOMITING_SIGNALS = {
    "vomit",
    "vomiting",
    "nausea",
    "emesis",
    "retching",
    "ترجيع",
    "استفراغ",
    "قيء",
    "قئ",
    "بستفرغ",
    "غثيان",
}

NEGATED_VOMITING_PHRASES = {
    "no vomiting",
    "denies vomiting",
    "without vomiting",
    "no nausea",
    "denies nausea",
    "without nausea",
    "no nausea or vomiting",
    "denies nausea or vomiting",
    "denies n/v",
    "no n/v",
    "لا يوجد قيء",
    "لا توجد قيء",
    "بدون قيء",
    "ينفي القيء",
    "لا يوجد غثيان",
    "لا توجد غثيان",
    "بدون غثيان",
    "ينفي الغثيان",
}


def _clean_text(value: str) -> str:
    return (
        (value or "")
        .strip()
        .lower()
        .replace("أ", "ا")
        .replace("إ", "ا")
        .replace("آ", "ا")
        .replace("ى", "ي")
    )


def _normalize_list(values: List[str]) -> List[str]:
    return [_clean_text(str(item)) for item in (values or []) if str(item).strip()]


def _has_chest_pain_signal(features: PatientFeatures) -> bool:
    category = _clean_text(features.body_system)
    complaint = _clean_text(features.chief_complaint)
    red_flags = set(_normalize_list(features.red_flags))
    if "chest_pain" in category or "cardiac" in category:
        return True
    if any(flag in red_flags for flag in {"chest_pain", "radiation_to_arm", "radiation_to_jaw"}):
        return True
    return any(token in complaint for token in CHEST_PAIN_SIGNALS)


def _stroke_fast_raw_components(complaint_text: str) -> Tuple[bool, bool, bool, bool, int]:
    raw = _clean_text(complaint_text)
    has_face = any(token in raw for token in FAST_FACE_RAW_SIGNALS)
    has_arm = any(token in raw for token in FAST_ARM_RAW_SIGNALS)
    has_speech = any(token in raw for token in FAST_SPEECH_RAW_SIGNALS)
    has_confusion = any(token in raw for token in FAST_CONFUSION_RAW_SIGNALS)
    fast_count = int(has_face) + int(has_arm) + int(has_speech)
    return has_face, has_arm, has_speech, has_confusion, fast_count


def _combined_clinical_text(features: PatientFeatures) -> str:
    body = _clean_text(features.body_system)
    complaint = _clean_text(features.chief_complaint)
    red_flags = " ".join(_normalize_list(features.red_flags))
    return f"{body} {complaint} {red_flags}"


def _has_abdominal_pain_signal(features: PatientFeatures) -> bool:
    combined = _combined_clinical_text(features)
    if any(token in combined for token in ABDOMINAL_SIGNALS):
        return True
    snomed_codes = {str(code) for code in (features.snomed_codes or [])}
    return "21522001" in snomed_codes


def _has_fever_signal(features: PatientFeatures, vitals: VitalSigns) -> bool:
    if vitals.temperature is not None and vitals.temperature >= 38.0:
        return True
    combined = _combined_clinical_text(features)
    if any(phrase in combined for phrase in NEGATED_FEVER_PHRASES):
        return False
    if any(token in combined for token in FEVER_SIGNALS):
        return True
    snomed_codes = {str(code) for code in (features.snomed_codes or [])}
    return bool(snomed_codes.intersection(FEVER_SNOMED_CODES))


def _has_vomiting_signal(features: PatientFeatures) -> bool:
    combined = _combined_clinical_text(features)
    if any(phrase in combined for phrase in NEGATED_VOMITING_PHRASES):
        return False
    return any(token in combined for token in VOMITING_SIGNALS)


def _has_back_pain_signal(features: PatientFeatures) -> bool:
    combined = _combined_clinical_text(features)
    return any(token in combined for token in BACK_PAIN_SIGNALS)


def _has_ectopic_risk_signal(features: PatientFeatures) -> bool:
    combined = _combined_clinical_text(features)
    return any(token in combined for token in ECTOPIC_RISK_SIGNALS)


def _has_abnormal_vitals_for_ectopic(vitals: VitalSigns) -> bool:
    return bool(
        (vitals.heart_rate is not None and vitals.heart_rate >= 100)
        or (vitals.systolic_bp is not None and vitals.systolic_bp < 100)
        or (vitals.respiratory_rate is not None and vitals.respiratory_rate >= 22)
        or (vitals.spo2 is not None and vitals.spo2 < 94)
    )


def _has_ectopic_high_risk_pattern(features: PatientFeatures, vitals: VitalSigns) -> bool:
    gender = _clean_text(features.gender)
    if gender not in {"female", "f", "انثى", "أنثى"}:
        return False
    if features.age < 15 or features.age > 50:
        return False

    combined = _combined_clinical_text(features)
    has_acute_pain = (
        (_has_abdominal_pain_signal(features) or _has_back_pain_signal(features))
        and (
            any(token in combined for token in ACUTE_ONSET_SIGNALS)
            or _clean_text(features.onset) in ACUTE_ONSET_SIGNALS
        )
    )
    if not has_acute_pain:
        return False

    red_flags = set(_normalize_list(features.red_flags))
    red_flag_signal = bool(
        red_flags.intersection(
            {
                "ectopic_pregnancy_risk",
                "occult_shock",
                "high_risk_abdominal_pain",
                "abnormal_vitals",
            }
        )
    ) or any("ectopic" in flag or "pregnan" in flag or "حمل" in flag for flag in red_flags)

    return red_flag_signal or _has_abnormal_vitals_for_ectopic(vitals) or _has_ectopic_risk_signal(features)


def _has_urinary_noncardiac_signal(features: PatientFeatures) -> bool:
    combined = _combined_clinical_text(features)
    return any(token in combined for token in URINARY_NONCARDIAC_SIGNALS)


def _has_silent_mi_gi_signal(features: PatientFeatures) -> bool:
    combined = _combined_clinical_text(features)
    return any(signal in combined for signal in GI_SIGNALS)


def _has_silent_mi_symptom_cluster(features: PatientFeatures) -> bool:
    body = _clean_text(features.body_system)
    complaint = _clean_text(features.chief_complaint)
    red_flags = set(_normalize_list(features.red_flags))
    all_text = f"{body} {complaint} {' '.join(red_flags)}"
    has_gi_signal = any(signal in all_text for signal in GI_SIGNALS)
    has_atypical_signal = any(signal in all_text for signal in ATYPICAL_ACS_SIGNALS)
    has_chest_discomfort = any(
        token in all_text
        for token in {"chest discomfort", "burning chest", "chest burning", "حرقان في الصدر", "ضيق في الصدر"}
    )
    return bool(has_gi_signal and (has_atypical_signal or has_chest_discomfort))


def _has_diabetic_emergency_red_flag(features: PatientFeatures) -> bool:
    red_flags = _normalize_list(features.red_flags)
    return any(
        ("hypogly" in flag)
        or ("hypergly" in flag)
        or ("dka" in flag)
        or ("سكري" in flag and "حرج" in flag)
        for flag in red_flags
    )


def _stroke_fast_components(features: PatientFeatures) -> Tuple[str, bool, bool, bool, bool, int]:
    combined = _combined_clinical_text(features)
    has_face = any(token in combined for token in STROKE_FACE_SIGNALS)
    has_weakness = any(token in combined for token in STROKE_WEAKNESS_SIGNALS)
    has_speech = any(token in combined for token in STROKE_SPEECH_SIGNALS)
    has_confusion = any(token in combined for token in STROKE_CONFUSION_SIGNALS)
    fast_count = int(has_face) + int(has_weakness) + int(has_speech)
    return combined, has_face, has_weakness, has_speech, has_confusion, fast_count


def _has_stroke_fast_signal(features: PatientFeatures) -> bool:
    combined, has_face, has_weakness, has_speech, has_confusion, fast_count = _stroke_fast_components(features)
    snomed_codes = {str(code) for code in (features.snomed_codes or [])}

    if snomed_codes.intersection(STROKE_FAST_SNOMED):
        return True

    if any(token in combined for token in STROKE_EXPLICIT_SIGNALS):
        return True

    if any(token in combined for token in STROKE_SPEECH_HIGH_RISK_SIGNALS):
        return True

    if any(token in combined for token in STROKE_SINGLE_FAST_SIGNALS):
        return True

    has_sudden = any(token in combined for token in STROKE_SUDDEN_SIGNALS)
    raw_face, raw_arm, raw_speech, raw_confusion, raw_fast_count = _stroke_fast_raw_components(
        features.chief_complaint
    )
    if raw_fast_count >= 2 or raw_confusion:
        return True

    # FAST protocol: 2/3 face-arm-speech, with speech+acute confusion as equivalent high-risk neurologic emergency.
    if fast_count >= 2:
        return True
    if has_speech and has_confusion:
        return True
    if has_speech and has_sudden and (has_face or has_weakness):
        return True
    if raw_speech and raw_confusion:
        return True

    return False


def _silent_mi_pattern(features: PatientFeatures, vitals: Optional[VitalSigns] = None) -> bool:
    comorb = set(_normalize_list(features.comorbidities))
    body = _clean_text(features.body_system)
    complaint = _clean_text(features.chief_complaint)
    red_flags = set(_normalize_list(features.red_flags))
    all_text = f"{body} {complaint} {' '.join(red_flags)}"

    has_gi_signal = any(signal in all_text for signal in GI_SIGNALS)
    has_atypical_signal = any(signal in all_text for signal in ATYPICAL_ACS_SIGNALS)
    has_chest_discomfort = any(
        token in all_text
        for token in {"chest discomfort", "burning chest", "chest burning", "حرقان في الصدر", "ضيق في الصدر"}
    )

    is_diabetic = "diabetes" in comorb or "سكري" in comorb
    gender = _clean_text(features.gender)
    age = int(features.age or 0)
    demographic_high_risk = (gender == "male" and age >= 50) or age >= 65
    if not (is_diabetic and demographic_high_risk and has_gi_signal):
        return False

    has_supporting_vitals = False
    if vitals is not None:
        has_supporting_vitals = bool(
            (vitals.heart_rate is not None and vitals.heart_rate >= 95)
            or (vitals.systolic_bp is not None and vitals.systolic_bp < 110)
            or (vitals.respiratory_rate is not None and vitals.respiratory_rate >= 20)
            or (vitals.spo2 is not None and vitals.spo2 < 95)
            or (vitals.temperature is not None and vitals.temperature >= 37.8)
        )

    # Smoker with chest discomfort or epigastric symptoms
    smoker_flags = {"smoker", "smoking", "heavy smoker", "مدخن", "تدخين"}
    is_smoker = bool(comorb.intersection(smoker_flags)) or any(s in all_text for s in smoker_flags)
    cardiac_supporting_risk = is_smoker or bool(
        comorb.intersection({"hypertension", "hyperlipidemia", "ضغط", "كوليسترول"})
    )
    has_supporting_red_flags = bool(
        red_flags.intersection({"chest_pain", "cardiac_risk", "radiation_to_arm", "radiation_to_jaw"})
    )
    has_supporting_symptoms = has_atypical_signal or has_chest_discomfort
    return bool((has_supporting_vitals or has_supporting_red_flags) and (has_supporting_symptoms or cardiac_supporting_risk))


def vitals_in_danger_zone(vitals: VitalSigns) -> bool:
    if vitals.heart_rate is not None and (vitals.heart_rate > 130 or vitals.heart_rate < 40):
        return True
    if vitals.systolic_bp is not None and (vitals.systolic_bp < 90 or vitals.systolic_bp >= 220):
        return True
    if vitals.spo2 is not None and vitals.spo2 < 90:
        return True
    if vitals.respiratory_rate is not None and (vitals.respiratory_rate < 8 or vitals.respiratory_rate > 30):
        return True
    return False


def _vitals_objectively_stable(vitals: VitalSigns) -> bool:
    """
    Objective stability gate used before escalating severe + high-risk-body-system to ESI 2.
    """
    hr = vitals.heart_rate
    sbp = vitals.systolic_bp
    spo2 = vitals.spo2
    rr = vitals.respiratory_rate
    temp = vitals.temperature
    gcs = vitals.gcs

    if hr is None or sbp is None or spo2 is None or rr is None or temp is None:
        return False

    if not (50 <= int(hr) <= 109):
        return False
    if not (101 <= int(sbp) <= 199):
        return False
    if not (float(spo2) > 94):
        return False
    if not (9 <= int(rr) <= 24):
        return False
    if not (36.0 <= float(temp) <= 38.4):
        return False
    if gcs is not None and int(gcs) != 15:
        return False

    # Explicitly preserve stability checks requested for severe/high-risk-body-system logic.
    if int(hr) >= 110:
        return False
    if int(sbp) <= 100:
        return False
    if float(spo2) <= 94:
        return False
    return True


def stage1_life_threatening(
    features: PatientFeatures, vitals: VitalSigns, news2: NEWS2Result
) -> Optional[Tuple[int, List[str]]]:
    reasons: List[str] = []

    raw_face, raw_arm, raw_speech, raw_confusion, raw_fast_count = _stroke_fast_raw_components(
        features.chief_complaint
    )
    if raw_fast_count >= 2 or raw_confusion:
        reasons.append(
            "Raw complaint FAST-positive stroke signal -> ESI 1 "
            f"(face={raw_face}, arm={raw_arm}, speech={raw_speech}, confusion={raw_confusion}, fast_count={raw_fast_count})"
        )
        return 1, reasons

    if news2.total_score >= 7:
        reasons.append(f"NEWS2 {news2.total_score} >= 7: immediate resuscitation")
        return 1, reasons

    if features.mental_status in {"unresponsive", "pain_only"}:
        reasons.append(f"Mental status is {features.mental_status}: life-threatening")
        return 1, reasons

    if vitals.gcs is not None and vitals.gcs <= 8:
        reasons.append(f"GCS {vitals.gcs} <= 8: life-threatening")
        return 1, reasons

    for flag in _normalize_list(features.red_flags):
        if flag in LIFE_THREATENING_CONDITIONS:
            reasons.append(f"Life-threatening red flag: {flag}")
            return 1, reasons

    for code in [str(code) for code in (features.snomed_codes or [])]:
        if code in LIFE_THREATENING_SNOMED:
            reasons.append(f"Life-threatening SNOMED match: {code}")
            return 1, reasons

    # FAST-positive stroke -> ESI 1 (time-critical intervention).
    if _has_stroke_fast_signal(features):
        _, has_face, has_weakness, has_speech, has_confusion, fast_count = _stroke_fast_components(features)
        if fast_count >= 2 or (has_speech and has_confusion):
            reasons.append(
                f"FAST stroke protocol override -> ESI 1 (face={has_face}, arm={has_weakness}, "
                f"speech={has_speech}, confusion={has_confusion}, fast_count={fast_count})"
            )
            return 1, reasons

    if vitals.spo2 is not None and vitals.spo2 < 85:
        reasons.append(f"SpO2 {vitals.spo2} < 85%: critical hypoxia")
        return 1, reasons
    if vitals.systolic_bp is not None and vitals.systolic_bp < 70:
        reasons.append(f"SBP {vitals.systolic_bp} < 70: critical hypotension")
        return 1, reasons
    if vitals.heart_rate is not None and vitals.heart_rate < 30:
        reasons.append(f"HR {vitals.heart_rate} < 30: critical bradycardia")
        return 1, reasons

    return None


def evaluate_context_rule(rule: Dict[str, object], features: PatientFeatures, vitals: VitalSigns) -> bool:
    conditions = rule.get("conditions", {})
    if not isinstance(conditions, dict):
        return False

    comorb = set(_normalize_list(features.comorbidities))
    body = _clean_text(features.body_system)
    red_flags = set(_normalize_list(features.red_flags))
    snomed_codes = {str(code) for code in (features.snomed_codes or [])}

    age_over = conditions.get("age_over")
    if isinstance(age_over, (int, float)) and features.age <= age_over:
        return False

    gender = conditions.get("gender")
    if isinstance(gender, str) and _clean_text(features.gender) != _clean_text(gender):
        return False

    include_one = conditions.get("comorbidities_include")
    if isinstance(include_one, str) and _clean_text(include_one) not in comorb:
        return False

    include_any = conditions.get("comorbidities_include_any")
    if isinstance(include_any, list):
        normalized = {_clean_text(item) for item in include_any}
        if not comorb.intersection(normalized):
            return False

    body_systems = conditions.get("body_systems")
    if isinstance(body_systems, list):
        expected = {_clean_text(item) for item in body_systems}
        if not any(token in body for token in expected):
            return False

    snomed_triggers = rule.get("snomed_triggers")
    if isinstance(snomed_triggers, list):
        if not snomed_codes.intersection({str(item) for item in snomed_triggers}):
            return False

    red_flag_triggers = rule.get("red_flag_triggers")
    if isinstance(red_flag_triggers, list):
        if not red_flags.intersection({_clean_text(item) for item in red_flag_triggers}):
            return False

    vital_triggers = rule.get("vital_triggers")
    if isinstance(vital_triggers, dict):
        triggered = 0
        if "temperature_over" in vital_triggers and vitals.temperature is not None:
            if vitals.temperature > float(vital_triggers["temperature_over"]):
                triggered += 1
        if "heart_rate_over" in vital_triggers and vitals.heart_rate is not None:
            if vitals.heart_rate > float(vital_triggers["heart_rate_over"]):
                triggered += 1
        if "respiratory_rate_over" in vital_triggers and vitals.respiratory_rate is not None:
            if vitals.respiratory_rate > float(vital_triggers["respiratory_rate_over"]):
                triggered += 1
        min_vitals = int(rule.get("min_vital_triggers", 1))
        if triggered < min_vitals:
            return False

    return True


def evaluate_context_rules(features: PatientFeatures, vitals: VitalSigns) -> List[str]:
    triggered: List[str] = []
    for rule in CONTEXT_HIGH_RISK_RULES:
        if not evaluate_context_rule(rule, features, vitals):
            continue
        name = str(rule.get("name", "Unnamed context rule")).strip()
        alert = str(rule.get("alert", "")).strip()
        triggered.append(f"{name} ({alert})" if alert else name)
    return triggered


CONTEXT_HIGH_RISK_RULES: List[Dict[str, object]] = [
    {
        "name": "Silent MI in diabetics",
        "conditions": {
            "comorbidities_include": "diabetes",
            "age_over": 50,
            "gender": "male",
            "body_systems": ["gi", "cardiac", "heartburn"],
        },
        "snomed_triggers": ["16331000", "162031009"],
        "vital_triggers": {
            "heart_rate_over": 95,
            "respiratory_rate_over": 20,
        },
        "min_vital_triggers": 1,
        "alert": "Silent MI risk profile",
    },
    {
        "name": "Atypical ACS in women",
        "conditions": {
            "age_over": 45,
            "gender": "female",
            "body_systems": ["gi", "cardiac", "musculoskeletal"],
        },
        "red_flag_triggers": list(ATYPICAL_ACS_SIGNALS),
        "alert": "Atypical ACS profile",
    },
    {
        "name": "Sepsis screening",
        "conditions": {
            "comorbidities_include_any": [
                "diabetes",
                "immunocompromised",
                "cancer",
                "elderly",
            ],
            "body_systems": [
                "sepsis",
                "sepsis_concern",
                "infection",
                "pneumonia",
                "cellulitis",
                "pyelo",
                "uti",
            ],
        },
        "vital_triggers": {
            "temperature_over": 38.5,
            "heart_rate_over": 100,
            "respiratory_rate_over": 22,
        },
        "min_vital_triggers": 2,
        "alert": "Sepsis screening positive",
    },
]


def stage2_high_risk(
    features: PatientFeatures, vitals: VitalSigns, news2: NEWS2Result
) -> Optional[Tuple[int, List[str], List[str]]]:
    reasons: List[str] = []
    context_rules_triggered: List[str] = []

    if news2.total_score >= 5:
        reasons.append(f"NEWS2 {news2.total_score} >= 5: high risk")
        return 2, reasons, context_rules_triggered

    if features.mental_status in {"confused", "voice_only", "verbal"}:
        reasons.append(f"Altered mental status: {features.mental_status}")
        return 2, reasons, context_rules_triggered

    if _has_diabetic_emergency_red_flag(features):
        reasons.append("Critical diabetic red-flag text detected (hypoglycemia/DKA risk)")
        return 2, reasons, context_rules_triggered

    if _has_abdominal_pain_signal(features) and _has_fever_signal(features, vitals):
        has_objective_fever = vitals.temperature is not None and vitals.temperature >= 38.5
        if has_objective_fever or news2.total_score >= 5:
            reasons.append("Fever + abdominal pain with objective risk indicators")
            return 2, reasons, context_rules_triggered
        reasons.append(
            "Fever + abdominal pain reported without objective instability; continue to resource estimation"
        )

    red_flags = set(_normalize_list(features.red_flags))
    body_system = _clean_text(features.body_system)
    severe_signal = _clean_text(features.severity)
    objective_red_flags = {
        "chest_pain",
        "radiation_to_arm",
        "radiation_to_jaw",
        "respiratory_distress",
        "severe_bleeding",
        "stroke_symptoms",
        "sepsis",
        "shock",
    }
    high_risk_body_system = body_system in {
        "stroke",
        "chest_pain_cardiac",
        "stroke_symptoms",
        "neurological",
        "respiratory_distress",
        "sepsis_concern",
    }

    if _has_ectopic_high_risk_pattern(features, vitals):
        reasons.append("Reproductive-age female with acute abdominal/back pain + risk marker (ectopic concern)")
        return 2, reasons, context_rules_triggered

    if features.pain_score is not None and features.pain_score >= 7:
        has_abdominal_systemic_flag = any(
            ("abdominal_pain" in flag) or ("abdominal" in flag) or ("بطن" in flag)
            for flag in red_flags
        )
        has_noncritical_vital_strain = bool(
            (vitals.heart_rate is not None and vitals.heart_rate >= 110)
            or (vitals.respiratory_rate is not None and vitals.respiratory_rate >= 21)
        )
        objective_pain_risk = bool(
            features.pain_score >= 9
            or high_risk_body_system
            or red_flags.intersection(objective_red_flags)
            or has_abdominal_systemic_flag
            or has_noncritical_vital_strain
            or _has_chest_pain_signal(features)
            or _has_stroke_fast_signal(features)
            or vitals_in_danger_zone(vitals)
        )
        if objective_pain_risk:
            reasons.append(f"Pain score {features.pain_score}/10 with objective high-risk signals")
            return 2, reasons, context_rules_triggered
        reasons.append(
            f"Pain score {features.pain_score}/10 without objective instability/high-risk pattern; defer to resource stage"
        )

    if severe_signal in {"severe", "critical"}:
        has_red_flag_match = bool(red_flags.intersection(objective_red_flags))
        has_danger_vitals = vitals_in_danger_zone(vitals)

        if has_red_flag_match or has_danger_vitals:
            reasons.append(f"Severity is {severe_signal} with objective high-risk evidence")
            return 2, reasons, context_rules_triggered

        if high_risk_body_system:
            vitals_truly_stable = _vitals_objectively_stable(vitals)
            parameter_scores = news2.parameter_scores or {}
            news2_params_within_safe_band = True
            for score in parameter_scores.values():
                try:
                    parsed_score = int(score)
                except (TypeError, ValueError):
                    news2_params_within_safe_band = False
                    break
                if parsed_score >= 2:
                    news2_params_within_safe_band = False
                    break
            news2_stable = bool(news2.total_score < 5 and news2_params_within_safe_band)

            if not (vitals_truly_stable and news2_stable):
                reasons.append(
                    f"Severity is {severe_signal} with high-risk body system and borderline vitals"
                )
                return 2, reasons, context_rules_triggered

            reasons.append(
                f"Severity '{severe_signal}' with high-risk body system but objectively stable vitals; "
                "defer to resource stage"
            )
        else:
            reasons.append(
                f"Severity '{severe_signal}' without objective high-risk evidence; defer to resource stage"
            )

    for code in [str(code) for code in (features.snomed_codes or [])]:
        if code in HIGH_RISK_SNOMED:
            reasons.append(f"High-risk SNOMED match: {code}")
            return 2, reasons, context_rules_triggered

    if _has_stroke_fast_signal(features):
        reasons.append("Stroke FAST signal detected (speech/face/limb neurologic deficit)")
        return 2, reasons, context_rules_triggered

    if "chest_pain" in red_flags or _has_chest_pain_signal(features):
        reasons.append("Chest pain safety floor path")
        return 2, reasons, context_rules_triggered
    if {"radiation_to_arm", "radiation_to_jaw"}.intersection(red_flags):
        reasons.append("Radiation pattern concerning for ACS")
        return 2, reasons, context_rules_triggered

    context_rules_triggered = evaluate_context_rules(features, vitals)
    if context_rules_triggered:
        for matched_rule in context_rules_triggered:
            reasons.append(f"Context rule triggered: {matched_rule}")
        return 2, reasons, context_rules_triggered

    if _silent_mi_pattern(features, vitals):
        reasons.append("Silent MI pattern detected (comorbidity + demographics)")
        return 2, reasons, context_rules_triggered

    # If keyword extractor pre-classified silent_mi, require corroborating profile.
    body = _clean_text(features.body_system)
    if "silent_mi" in body or "silent mi" in body:
        if _silent_mi_pattern(features, vitals):
            reasons.append("Category pre-classified as Silent MI and profile corroborated")
            return 2, reasons, context_rules_triggered
        if _has_silent_mi_gi_signal(features) and not _has_urinary_noncardiac_signal(features):
            reasons.append("Silent MI category with GI atypical profile (non-urinary) -> ESI 2")
            return 2, reasons, context_rules_triggered
        if _has_silent_mi_symptom_cluster(features) and not _has_urinary_noncardiac_signal(features):
            reasons.append("Silent MI category with atypical ACS symptom cluster (non-urinary) -> ESI 2")
            return 2, reasons, context_rules_triggered
        reasons.append("Silent MI category not corroborated by demographic/vital profile; defer to resource stage")

    if vitals_in_danger_zone(vitals):
        reasons.append("Vital signs in danger zone")
        return 2, reasons, context_rules_triggered

    return None


def stage3_resource_estimation(
    features: PatientFeatures,
    vitals: VitalSigns,
    news2_total: Optional[int] = None,
) -> Tuple[int, List[str]]:
    has_fever = _has_fever_signal(features, vitals)
    has_vomiting = _has_vomiting_signal(features)
    vitals_payload = {
        "hr": vitals.heart_rate,
        "sbp": vitals.systolic_bp,
        "spo2": vitals.spo2,
        "temp": vitals.temperature,
    }
    result = estimate_resources(
        category=features.body_system,
        severity=features.severity,
        has_fever=has_fever,
        has_vomiting=has_vomiting,
        age=features.age,
        comorbidities=features.comorbidities,
        news2_score=news2_total,
        vitals=vitals_payload,
        red_flags=features.red_flags,
        ai_confidence=features.ai_confidence,
        chief_complaint=features.chief_complaint,
        is_offline=features.is_offline,
    )
    reasons = [f"Resource estimate category '{result['category']}' -> {result['count']} resources"]
    reasons.append(
        f"Modifiers: fever={str(has_fever).lower()}, vomiting={str(has_vomiting).lower()}, severity={_clean_text(features.severity)}"
    )
    reasons.extend([str(note) for note in result.get("notes", [])])
    return int(result["count"]), reasons


def stage3_assign_esi(resources: int, vitals: VitalSigns) -> Tuple[int, List[str]]:
    reasons: List[str] = []
    esi_from_resources = resources_to_esi(int(resources))
    if esi_from_resources == 5:
        reasons.append("0 resources: ESI 5")
    elif esi_from_resources == 4:
        reasons.append("1 resource: ESI 4")
    else:
        reasons.append(f"{resources} resources: ESI 3")

    # Decision Point D should already have been handled in stage 2.
    if vitals_in_danger_zone(vitals) and esi_from_resources > 2:
        reasons.append("Danger-zone vitals fallback: upgraded to ESI 2")
        return 2, reasons

    return int(esi_from_resources), reasons


def apply_confidence_gate(
    base_esi: int, confidence: float, features: PatientFeatures
) -> Tuple[int, str, List[str]]:
    reasons: List[str] = []
    score = max(0.0, min(1.0, float(confidence)))

    if features.is_offline:
        conservative_esi = int(base_esi)
        if conservative_esi > 4:
            conservative_esi = 4
            reasons.append(
                f"Offline mode floor applied: deterministic ESI {base_esi} -> {conservative_esi}"
            )
            return conservative_esi, "offline_conservative_floor", reasons
        reasons.append(
            f"Offline mode active (confidence {score:.2f}): deterministic ESI retained"
        )
        return conservative_esi, "offline_conservative", reasons

    if score > 0.85:
        reasons.append(f"AI confidence {score:.2f} > 0.85: trusted")
        return int(base_esi), "trusted", reasons

    if score >= 0.70:
        reasons.append(
            f"AI confidence {score:.2f} in [0.70, 0.85]: deterministic result retained"
        )
        return int(base_esi), "deterministic_online", reasons

    reasons.append(
        f"AI confidence {score:.2f} < 0.70: keeping deterministic ESI (review required)"
    )
    return int(base_esi), "deterministic_low_confidence", reasons


def apply_safety_floors(
    esi: int,
    features: PatientFeatures,
    vitals: VitalSigns,
    news2: NEWS2Result,
    *,
    context_rules_triggered: Optional[List[str]] = None,
) -> Tuple[int, List[str]]:
    final_esi = int(esi)
    floors: List[str] = []
    category = _clean_text(features.body_system)
    red_flags = set(_normalize_list(features.red_flags))

    if news2.total_score >= 7 and final_esi > 1:
        final_esi = 1
        floors.append(f"NEWS2 floor applied: {news2.total_score} >= 7 forces ESI 1")
    elif news2.total_score >= 5 and final_esi > 2:
        final_esi = 2
        floors.append(f"NEWS2 upgrade applied: {news2.total_score} >= 5 forces ESI 2")
    elif news2.total_score >= 3 and final_esi > 3:
        final_esi = 3
        floors.append(f"NEWS2 upgrade applied: {news2.total_score} >= 3 forces minimum ESI 3")

    if _has_chest_pain_signal(features) and final_esi > 2:
        final_esi = 2
        floors.append("Chest pain floor applied: maximum ESI 2")

    if _has_stroke_fast_signal(features):
        _, has_face, has_weakness, has_speech, has_confusion, fast_count = _stroke_fast_components(features)
        if (fast_count >= 2 or (has_speech and has_confusion)) and final_esi > 1:
            final_esi = 1
            floors.append("FAST stroke protocol override applied: ESI 1")
        elif final_esi > 2:
            final_esi = 2
            floors.append("Stroke FAST floor applied: maximum ESI 2")

    # High-risk categories safety floor
    high_risk_categories = {
        "altered_mental_status", "ectopic_pregnancy", "high_risk_abdominal_pain",
        "severe_hypoglycemia", "dka_concern", "diabetic_emergency",
    }
    if category in high_risk_categories and final_esi > 2:
        final_esi = 2
        floors.append(f"High-risk category '{category}' floor applied: maximum ESI 2")

    # High-risk red flags safety floor
    high_risk_red_flags = {
        "altered_mental_status", "high_risk_neuro", "ectopic_pregnancy_risk",
        "occult_shock", "severe_hypoglycemia", "dka_concern",
        "high_risk_abdominal_pain",
    }
    if red_flags.intersection(high_risk_red_flags) and final_esi > 2:
        final_esi = 2
        floors.append(f"High-risk red flag floor applied: maximum ESI 2")

    if _has_ectopic_high_risk_pattern(features, vitals) and final_esi > 2:
        final_esi = 2
        floors.append("Ectopic-risk floor applied: reproductive-age female with acute abd/back pain + objective risk")

    if (
        category == "silent_mi"
        and final_esi > 2
        and (_has_silent_mi_gi_signal(features) or _has_silent_mi_symptom_cluster(features))
        and not _has_urinary_noncardiac_signal(features)
    ):
        final_esi = 2
        floors.append("Silent MI category floor applied: atypical ACS symptom cluster")

    if _silent_mi_pattern(features, vitals) and final_esi > 2:
        final_esi = 2
        floors.append("Silent MI floor applied: diabetic atypical ACS profile")

    has_high_risk_comorbidity = bool(
        set(_normalize_list(features.comorbidities)).intersection(
            {"cancer", "immunocompromised", "elderly", "diabetes"}
        )
    )
    has_objective_fever = vitals.temperature is not None and vitals.temperature >= 38.5
    if (
        _has_abdominal_pain_signal(features)
        and _has_fever_signal(features, vitals)
        and final_esi > 2
        and (has_objective_fever or has_high_risk_comorbidity or news2.total_score >= 5)
    ):
        final_esi = 2
        floors.append("High-risk fever + abdominal pain floor applied: maximum ESI 2")

    if category in UNKNOWN_CATEGORIES and final_esi > 3:
        complaint = _clean_text(features.chief_complaint)
        looks_low_acuity_unknown = any(token in complaint for token in LOW_ACUITY_UNKNOWN_HINTS)
        if (
            looks_low_acuity_unknown
            and news2.total_score < 3
            and not red_flags
            and not vitals_in_danger_zone(vitals)
        ):
            floors.append("Unknown-category low-acuity complaint detected: ESI 3 floor skipped")
        else:
            final_esi = 3
            floors.append("Unknown presentation default applied: minimum ESI 3")

    context_rule_hits = list(context_rules_triggered or [])
    high_risk_body_system = category in {
        "stroke",
        "chest_pain_cardiac",
        "stroke_symptoms",
        "neurological",
        "neurological_emergency",
        "respiratory_distress",
        "sepsis_concern",
        "silent_mi",
        "altered_mental_status",
        "ectopic_pregnancy",
        "high_risk_abdominal_pain",
        "severe_hypoglycemia",
        "dka_concern",
        "diabetic_emergency",
    }
    has_objective_high_risk = bool(
        red_flags
        or context_rule_hits
        or vitals_in_danger_zone(vitals)
        or news2.total_score >= 5
        or _has_chest_pain_signal(features)
        or _has_stroke_fast_signal(features)
        or _silent_mi_pattern(features, vitals)
        or high_risk_body_system
        or features.mental_status in {"confused", "voice_only", "verbal", "pain_only", "unresponsive"}
        or (features.pain_score is not None and features.pain_score >= 7)
    )
    if not has_objective_high_risk and final_esi < 3:
        final_esi = 3
        floors.append(
            "Low-risk safeguard applied: no red flags/vital instability/context match -> max acuity ESI 3"
        )

    return final_esi, floors


def triage_patient(features: PatientFeatures, vitals: VitalSigns, news2: NEWS2Result) -> TriageResult:
    all_reasons: List[str] = []
    stage_reached = "stage3_resources"
    resources = 0
    context_rules_triggered: List[str] = []
    raw_face, raw_arm, raw_speech, raw_confusion, raw_fast_count = _stroke_fast_raw_components(
        features.chief_complaint
    )
    if raw_fast_count >= 2 or raw_confusion:
        base_esi = 1
        all_reasons.append(
            "FAST raw-complaint precheck -> ESI 1 "
            f"(face={raw_face}, arm={raw_arm}, speech={raw_speech}, confusion={raw_confusion}, fast_count={raw_fast_count})"
        )
        stage_reached = "stage0_fast_raw_complaint"
    else:
        stage1_result = stage1_life_threatening(features, vitals, news2)
        if stage1_result is not None:
            base_esi, reasons = stage1_result
            all_reasons.extend(reasons)
            stage_reached = "stage1_life_threatening"
        else:
            stage2_result = stage2_high_risk(features, vitals, news2)
            if stage2_result is not None:
                base_esi, reasons, context_rules_triggered = stage2_result
                all_reasons.extend(reasons)
                stage_reached = "stage2_high_risk"
            else:
                resources, resource_reasons = stage3_resource_estimation(
                    features,
                    vitals,
                    news2_total=news2.total_score,
                )
                all_reasons.extend(resource_reasons)
                base_esi, stage3_reasons = stage3_assign_esi(resources, vitals)
                all_reasons.extend(stage3_reasons)
                stage_reached = "stage3_resource_estimation"

    gated_esi, confidence_action, confidence_reasons = apply_confidence_gate(
        base_esi, features.ai_confidence, features
    )
    all_reasons.extend(confidence_reasons)

    final_esi, floors_applied = apply_safety_floors(
        gated_esi,
        features,
        vitals,
        news2,
        context_rules_triggered=context_rules_triggered,
    )
    if floors_applied:
        all_reasons.extend(floors_applied)

    requires_review = (
        features.ai_confidence < 0.70
        or features.is_offline
        or bool(floors_applied)
        or _clean_text(features.body_system) in UNKNOWN_CATEGORIES
    )

    return TriageResult(
        esi_level=int(base_esi),
        reasoning=all_reasons,
        stage_reached=stage_reached,
        resources_estimated=int(resources),
        safety_floors_applied=floors_applied,
        confidence_action=confidence_action,
        news2_override=news2.total_score >= 3,
        final_esi=int(final_esi),
        context_rules_triggered=context_rules_triggered,
        requires_review=requires_review,
    )


__all__ = [
    "ESILevel",
    "PatientFeatures",
    "VitalSigns",
    "NEWS2Result",
    "TriageResult",
    "triage_patient",
    "stage1_life_threatening",
    "stage2_high_risk",
    "stage3_resource_estimation",
    "evaluate_context_rule",
    "evaluate_context_rules",
]
