"""
Boundary Clarification Mode
============================

Adaptive follow-up questions (0-3) triggered only at ESI boundary zones
to improve hidden-risk detection and ESI 2/3 / 3/4 discrimination.

Architecture:
    - Questions are PRE-COMPUTED by the AI extraction layer in a single call.
    - The deterministic engine decides which questions to surface based on
      boundary zone detection.
    - Answers can only ADD features (upgrade acuity), never downgrade.
    - "I don't know" / irrelevant → abort, keep safer ESI.
    - Safety floors are NEVER weakened.

References:
    Wong & Wong, JMIR Med Inform 2026. DOI: 10.2196/82026
    Fatai et al., Int Emerg Nurs 2025. DOI: 10.1016/j.ienj.2025.101680
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
from copy import deepcopy
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

try:
    from logic.esi_v5_engine import PatientFeatures, VitalSigns, NEWS2Result
except ImportError:
    from backend.logic.esi_v5_engine import PatientFeatures, VitalSigns, NEWS2Result


# =============================================================================
# CONSTANTS
# =============================================================================

VALID_QUESTION_TYPES = frozenset({"danger", "hidden_risk", "resource"})
VALID_ACTIONS = frozenset({"add_red_flag", "add_comorbidity", "adjust_resources"})
VALID_RESPONSES = frozenset({"yes", "no", "unknown"})

# Diagnosis terms that MUST NOT appear in questions (anti-leading guardrail)
DIAGNOSIS_BLOCKLIST_EN = frozenset({
    "heart attack", "myocardial infarction", "mi ", "stroke", "cva",
    "ectopic", "pulmonary embolism", "pe ", "sepsis", "meningitis",
    "appendicitis", "aortic dissection", "aneurysm",
})
DIAGNOSIS_BLOCKLIST_AR = frozenset({
    "جلطة", "ذبحة", "حمل خارج الرحم", "انسداد رئوي", "تسمم دم",
    "التهاب سحايا", "التهاب الزائدة", "تمدد الشريان",
})

# Hard safety floors that lock ESI — no questions needed when active
HARD_FLOOR_KEYWORDS = frozenset({
    "chest pain floor", "stroke fast", "news2 floor", "news2 upgrade",
    "fast stroke protocol",
})

# High-risk body systems for near-miss detection
HIGH_RISK_BODY_SYSTEMS = frozenset({
    "chest_pain_cardiac", "stroke_symptoms", "neurological",
    "respiratory_distress", "sepsis_concern", "abdominal_pain",
    "cardiac", "respiratory",
})

# =============================================================================
# COMPLAINT-AWARE QUESTION BANK (MIMIC-IV evidence-driven)
# =============================================================================
#
# Source: mimic_complaint_full_statistics.csv — 418K labeled triage cases.
# Each complaint cluster has specific clinical discriminators that separate
# ESI 2 from ESI 3 in real ED data. Questions target those exact signals.
#
# MIMIC-IV under-triage risk data (mode=ESI 3, HAF = fraction actually ESI 1-2):
#   dizziness:       HAF=50.7%  — posterior stroke, vertebrobasilar insufficiency
#   presyncope:      HAF=50.0%  — arrhythmia, PE, aortic stenosis
#   fever:           HAF=45.8%  — sepsis, meningitis, neutropenic fever
#   abdominal dist:  HAF=44.3%  — bowel obstruction, peritonitis
#   headache:        HAF=35.1%  — SAH, meningitis, hypertensive emergency
#   vomiting:        HAF=31.7%  — DKA, bowel obstruction, intracranial pressure
#   vaginal bleeding:HAF=31.7%  — ectopic pregnancy, placental abruption
#   epigastric pain: HAF=28.8%  — silent MI, pancreatitis
#   abdominal pain:  HAF=23.2%  — appendicitis, AAA, ectopic, mesenteric ischemia
#   back pain:       HAF=23.7%  — aortic dissection, ectopic, cauda equina

# Complaint category → specialized questions per type
# These replace the generic fallbacks when the complaint matches a known pattern.
COMPLAINT_QUESTION_BANK: Dict[str, Dict[str, Dict[str, Any]]] = {
    # --- ABDOMINAL PAIN (35,936 cases, HAF=23.2%) ---
    # Key discriminator: fever+rigidity → peritonitis/appendicitis; female+missed period → ectopic
    "abdominal_pain": {
        "danger": {
            "type": "danger",
            "question_en": "Is the pain constant and getting worse, not coming and going?",
            "question_ar": "الألم ثابت وبيزيد، مش بييجي ويروح؟",
            "upgrade_signal": {"action": "add_red_flag", "value": "acute_abdomen_worsening", "severity_override": "severe", "category_hint": None},
            "clinical_rationale": "Constant worsening abdominal pain → peritonitis, appendicitis, mesenteric ischemia (MIMIC HAF=23.2%)",
        },
        "hidden_risk": {
            "type": "hidden_risk",
            "question_en": "Do you have a fever or chills with this pain?",
            "question_ar": "عندك سخونية أو رعشة مع الألم ده؟",
            "upgrade_signal": {"action": "add_red_flag", "value": "fever_with_abdominal_pain", "severity_override": "severe", "category_hint": "sepsis_concern"},
            "clinical_rationale": "Fever + abdominal pain → sepsis/peritonitis screening (45.8% of fever cases are ESI 1-2)",
        },
        "resource": {
            "type": "resource",
            "question_en": "Have you vomited or had bloody stool today?",
            "question_ar": "استفرغت أو نزل دم مع البراز النهارده؟",
            "upgrade_signal": {"action": "add_red_flag", "value": "gi_bleed_vomiting", "severity_override": None, "category_hint": None},
            "clinical_rationale": "Vomiting/GI bleeding with abdominal pain adds imaging + labs + monitoring resources",
        },
    },

    # --- HEADACHE (14,327 cases, HAF=35.1%) ---
    # Key discriminator: sudden onset "thunderclap" → SAH; fever+stiff neck → meningitis
    "headache": {
        "danger": {
            "type": "danger",
            "question_en": "Did this headache start suddenly and severely, like a hit?",
            "question_ar": "الصداع جه فجأة وشديد، زي ما حد ضربك؟",
            "upgrade_signal": {"action": "add_red_flag", "value": "thunderclap_headache", "severity_override": "severe", "category_hint": "neurological"},
            "clinical_rationale": "Thunderclap headache → SAH until proven otherwise (MIMIC: 35.1% of headaches are ESI 1-2)",
        },
        "hidden_risk": {
            "type": "hidden_risk",
            "question_en": "Is it hard to bend your neck forward?",
            "question_ar": "صعب تحني رقبتك لقدام؟",
            "upgrade_signal": {"action": "add_red_flag", "value": "neck_stiffness_meningeal", "severity_override": "severe", "category_hint": "neurological"},
            "clinical_rationale": "Neck stiffness + headache → meningeal signs (meningitis/SAH) requiring urgent LP/CT",
        },
        "resource": {
            "type": "resource",
            "question_en": "Is this the worst headache you've ever had?",
            "question_ar": "ده أسوأ صداع جالك في حياتك؟",
            "upgrade_signal": {"action": "add_red_flag", "value": "worst_headache_ever", "severity_override": "severe", "category_hint": "neurological"},
            "clinical_rationale": "'Worst headache of life' is classic SAH presentation requiring CT + LP",
        },
    },

    # --- DIZZINESS/PRESYNCOPE (9,470 + 1,841 cases, HAF=50.7%/50.0%) ---
    # Key discriminator: continuous vs positional; associated neuro symptoms → posterior stroke
    "dizziness": {
        "danger": {
            "type": "danger",
            "question_en": "Did you lose consciousness or nearly black out?",
            "question_ar": "فقدت وعيك أو حسيت إنك هتقع؟",
            "upgrade_signal": {"action": "add_red_flag", "value": "syncope_presyncope", "severity_override": "severe", "category_hint": None},
            "clinical_rationale": "Syncope/near-syncope → arrhythmia, PE, aortic stenosis (MIMIC: 50% of dizziness is ESI 1-2)",
        },
        "hidden_risk": {
            "type": "hidden_risk",
            "question_en": "Do you have any numbness, weakness, or trouble speaking?",
            "question_ar": "عندك تنميل، ضعف، أو صعوبة في الكلام؟",
            "upgrade_signal": {"action": "add_red_flag", "value": "neuro_deficit_with_dizziness", "severity_override": "severe", "category_hint": "stroke_symptoms"},
            "clinical_rationale": "Dizziness + focal neuro deficit → posterior circulation stroke",
        },
        "resource": {
            "type": "resource",
            "question_en": "Do you take blood pressure or heart medication?",
            "question_ar": "بتاخد أدوية ضغط أو قلب؟",
            "upgrade_signal": {"action": "add_comorbidity", "value": "cardiac_medication", "severity_override": None, "category_hint": None},
            "clinical_rationale": "Cardiac medications + dizziness → ECG + monitoring + labs needed",
        },
    },

    # --- FEVER (12,901 cases, HAF=45.8%) ---
    # Key discriminator: immunocompromised + fever = emergency; rigors → bacteremia
    "fever": {
        "danger": {
            "type": "danger",
            "question_en": "Are you shaking or having chills that won't stop?",
            "question_ar": "جسمك بيرجف أو عندك رعشة مش بتوقف؟",
            "upgrade_signal": {"action": "add_red_flag", "value": "rigors_bacteremia", "severity_override": "severe", "category_hint": "sepsis_concern"},
            "clinical_rationale": "Rigors → bacteremia/sepsis (MIMIC: 45.8% of fever cases are ESI 1-2)",
        },
        "hidden_risk": {
            "type": "hidden_risk",
            "question_en": "Do you have diabetes, cancer, or take immune medications?",
            "question_ar": "عندك سكر، سرطان، أو بتاخد أدوية مناعة؟",
            "upgrade_signal": {"action": "add_comorbidity", "value": "immunocompromised", "severity_override": None, "category_hint": "sepsis_concern"},
            "clinical_rationale": "Immunocompromised + fever → neutropenic fever / opportunistic sepsis",
        },
        "resource": {
            "type": "resource",
            "question_en": "Do you have pain when passing urine or coughing up phlegm?",
            "question_ar": "عندك ألم وانت بتتبول أو بتكح بلغم؟",
            "upgrade_signal": {"action": "add_red_flag", "value": "fever_localizing_source", "severity_override": None, "category_hint": None},
            "clinical_rationale": "Localizing source + fever → targeted workup (urine + CXR + blood cultures)",
        },
    },

    # --- EPIGASTRIC/GI PAIN (2,323 cases, HAF=28.8%) → Silent MI pathway ---
    "epigastric_pain": {
        "danger": {
            "type": "danger",
            "question_en": "Does the pain spread to your jaw, arm, or back?",
            "question_ar": "الألم بيروح للفك، الدراع، أو الضهر؟",
            "upgrade_signal": {"action": "add_red_flag", "value": "radiation_pattern_acs", "severity_override": "severe", "category_hint": "chest_pain_cardiac"},
            "clinical_rationale": "Epigastric + radiation → atypical ACS / silent MI (MIMIC: 28.8% HAF)",
        },
        "hidden_risk": {
            "type": "hidden_risk",
            "question_en": "Do you have diabetes or heart problems?",
            "question_ar": "عندك سكر أو مشاكل في القلب؟",
            "upgrade_signal": {"action": "add_comorbidity", "value": "diabetes", "severity_override": None, "category_hint": "silent_mi"},
            "clinical_rationale": "Diabetic + epigastric pain → silent MI risk profile",
        },
        "resource": {
            "type": "resource",
            "question_en": "Are you sweating or feeling nauseous with this pain?",
            "question_ar": "بتعرق أو حاسس بغثيان مع الألم ده؟",
            "upgrade_signal": {"action": "add_red_flag", "value": "diaphoresis_nausea_acs", "severity_override": "severe", "category_hint": "chest_pain_cardiac"},
            "clinical_rationale": "Diaphoresis + nausea + epigastric pain = ACS symptom cluster",
        },
    },

    # --- VAGINAL BLEEDING (2,511 cases, HAF=31.7%) → Ectopic pathway ---
    "vaginal_bleeding": {
        "danger": {
            "type": "danger",
            "question_en": "Are you soaking more than one pad per hour?",
            "question_ar": "بتملي أكتر من فوطة في الساعة؟",
            "upgrade_signal": {"action": "add_red_flag", "value": "severe_hemorrhage", "severity_override": "severe", "category_hint": None},
            "clinical_rationale": "Soaking >1 pad/hour = hemodynamically significant hemorrhage",
        },
        "hidden_risk": {
            "type": "hidden_risk",
            "question_en": "Could you be pregnant or have you missed a period?",
            "question_ar": "ممكن تكوني حامل أو الدورة اتأخرت؟",
            "upgrade_signal": {"action": "add_red_flag", "value": "ectopic_pregnancy_risk", "severity_override": "severe", "category_hint": "obstetric_emergency"},
            "clinical_rationale": "Vaginal bleeding + possible pregnancy → ectopic until proven otherwise (MIMIC: 31.7% HAF)",
        },
        "resource": {
            "type": "resource",
            "question_en": "Do you feel dizzy or lightheaded when you stand up?",
            "question_ar": "بتحسي بدوخة لما بتقومي؟",
            "upgrade_signal": {"action": "add_red_flag", "value": "orthostatic_hypotension", "severity_override": "severe", "category_hint": None},
            "clinical_rationale": "Orthostatic symptoms + bleeding → hemodynamic compromise requiring IV + monitoring",
        },
    },

    # --- BACK PAIN (10,126 cases, HAF=23.7%) → AAA, dissection, cauda equina ---
    "back_pain": {
        "danger": {
            "type": "danger",
            "question_en": "Did the pain start very suddenly, like something tearing?",
            "question_ar": "الألم بدأ فجأة، زي ما حاجة بتتقطع؟",
            "upgrade_signal": {"action": "add_red_flag", "value": "acute_tearing_pain", "severity_override": "severe", "category_hint": None},
            "clinical_rationale": "Sudden tearing back pain → aortic dissection/AAA (MIMIC: 23.7% of back pain is ESI 1-2)",
        },
        "hidden_risk": {
            "type": "hidden_risk",
            "question_en": "Have you lost control of your bladder or bowel?",
            "question_ar": "فقدت التحكم في البول أو البراز؟",
            "upgrade_signal": {"action": "add_red_flag", "value": "cauda_equina_signs", "severity_override": "severe", "category_hint": "neurological"},
            "clinical_rationale": "Bladder/bowel incontinence + back pain → cauda equina syndrome (surgical emergency)",
        },
        "resource": {
            "type": "resource",
            "question_en": "Do you have numbness or weakness in your legs?",
            "question_ar": "عندك تنميل أو ضعف في رجليك؟",
            "upgrade_signal": {"action": "add_red_flag", "value": "lower_extremity_neuro_deficit", "severity_override": None, "category_hint": "neurological"},
            "clinical_rationale": "Neuro deficit + back pain → MRI + neuro consult + monitoring needed",
        },
    },

    # --- VOMITING (4,127 cases, HAF=31.7%) ---
    "vomiting": {
        "danger": {
            "type": "danger",
            "question_en": "Is there blood in what you're vomiting?",
            "question_ar": "في دم في القيء بتاعك؟",
            "upgrade_signal": {"action": "add_red_flag", "value": "hematemesis", "severity_override": "severe", "category_hint": "gi_bleed"},
            "clinical_rationale": "Hematemesis → upper GI bleed requiring urgent endoscopy (MIMIC: 31.7% HAF)",
        },
        "hidden_risk": {
            "type": "hidden_risk",
            "question_en": "Do you have diabetes?",
            "question_ar": "عندك مرض السكر؟",
            "upgrade_signal": {"action": "add_comorbidity", "value": "diabetes", "severity_override": None, "category_hint": "diabetic_emergency"},
            "clinical_rationale": "Vomiting + diabetes → DKA screening required",
        },
        "resource": {
            "type": "resource",
            "question_en": "How many times have you vomited today?",
            "question_ar": "استفرغت كام مرة النهارده؟",
            "upgrade_signal": {"action": "add_red_flag", "value": "intractable_vomiting", "severity_override": None, "category_hint": None},
            "clinical_rationale": "Intractable vomiting → IV fluids + labs + antiemetics (multiple resources)",
        },
    },

    # --- LEG SWELLING (1,487 cases, HAF=44.6%) → DVT/PE ---
    "leg_swelling": {
        "danger": {
            "type": "danger",
            "question_en": "Do you have any trouble breathing or chest pain?",
            "question_ar": "عندك صعوبة في التنفس أو ألم في الصدر؟",
            "upgrade_signal": {"action": "add_red_flag", "value": "respiratory_distress_pe", "severity_override": "severe", "category_hint": "respiratory_distress"},
            "clinical_rationale": "Leg swelling + dyspnea/chest pain → PE (MIMIC: 44.6% of leg swelling is ESI 1-2)",
        },
        "hidden_risk": {
            "type": "hidden_risk",
            "question_en": "Is it only in one leg, and is it red or warm?",
            "question_ar": "في رجل واحدة بس، وهي حمرا أو سخنة؟",
            "upgrade_signal": {"action": "add_red_flag", "value": "unilateral_dvt_signs", "severity_override": None, "category_hint": None},
            "clinical_rationale": "Unilateral + warm/red → DVT requiring ultrasound + anticoagulation workup",
        },
        "resource": {
            "type": "resource",
            "question_en": "Have you had surgery or been on bed rest recently?",
            "question_ar": "عملت عملية أو كنت نايم فترة طويلة مؤخراً؟",
            "upgrade_signal": {"action": "add_comorbidity", "value": "vte_risk_factor", "severity_override": None, "category_hint": None},
            "clinical_rationale": "Immobility/surgery + leg swelling → elevated Wells score (DVT/PE pathway)",
        },
    },
}

# Complaint keyword → question bank key mapping
# Maps body_system values and keyword fragments to the right question set
_COMPLAINT_TO_BANK_KEY: Dict[str, str] = {
    # Abdominal
    "abdominal_pain": "abdominal_pain", "abdominal_pain_moderate": "abdominal_pain",
    "abdominal": "abdominal_pain", "بطن": "abdominal_pain", "بطني": "abdominal_pain",
    "مغص": "abdominal_pain",
    # Headache
    "headache": "headache", "headache_severe": "headache", "severe_headache": "headache",
    "صداع": "headache",
    # Dizziness
    "dizziness": "dizziness", "presyncope": "dizziness", "syncope": "dizziness",
    "lightheaded": "dizziness", "دوخة": "dizziness", "دوخه": "dizziness",
    # Fever
    "fever": "fever", "fever_with_symptoms": "fever", "fever_simple": "fever",
    "سخونية": "fever", "حمى": "fever", "سخونه": "fever",
    # Epigastric / GI
    "epigastric": "epigastric_pain", "heartburn": "epigastric_pain",
    "indigestion": "epigastric_pain", "gi": "epigastric_pain",
    "حموضة": "epigastric_pain", "حرقان": "epigastric_pain", "فم المعدة": "epigastric_pain",
    "silent_mi": "epigastric_pain",
    # Vaginal bleeding
    "vaginal_bleeding": "vaginal_bleeding", "obstetric_emergency": "vaginal_bleeding",
    "نزيف مهبلي": "vaginal_bleeding",
    # Back pain
    "back_pain": "back_pain", "back_pain_chronic": "back_pain",
    "flank_pain": "back_pain", "ضهر": "back_pain", "ظهر": "back_pain",
    # Vomiting
    "vomiting": "vomiting", "vomiting_diarrhea_dehydration": "vomiting",
    "nausea": "vomiting", "قيء": "vomiting", "ترجيع": "vomiting", "استفراغ": "vomiting",
    # Leg swelling
    "leg_swelling": "leg_swelling", "dvt_pe": "leg_swelling",
    "تورم": "leg_swelling",
}


def _resolve_complaint_bank_key(body_system: str, chief_complaint: str) -> Optional[str]:
    """Match body system or complaint text to a question bank key."""
    body = _clean(body_system)

    # Direct match on body_system
    if body in _COMPLAINT_TO_BANK_KEY:
        return _COMPLAINT_TO_BANK_KEY[body]

    # Substring match on body_system
    for keyword, bank_key in _COMPLAINT_TO_BANK_KEY.items():
        if keyword in body:
            return bank_key

    # Fallback: search chief complaint text
    complaint_lower = _clean(chief_complaint)
    for keyword, bank_key in _COMPLAINT_TO_BANK_KEY.items():
        if keyword in complaint_lower:
            return bank_key

    return None


# Generic fallback questions (used when complaint doesn't match any bank)
FALLBACK_QUESTIONS: Dict[str, Dict[str, Any]] = {
    "danger": {
        "type": "danger",
        "question_en": "Is your condition getting worse right now?",
        "question_ar": "حالتك بتسوء دلوقتي؟",
        "upgrade_signal": {
            "action": "add_red_flag",
            "value": "acute_deterioration",
            "severity_override": "severe",
            "category_hint": None,
        },
        "clinical_rationale": "Acute deterioration suggests unstable condition requiring upgrade",
    },
    "hidden_risk": {
        "type": "hidden_risk",
        "question_en": "Do you have diabetes, heart problems, or take immune medications?",
        "question_ar": "عندك سكر، مشاكل قلب، أو بتاخد أدوية مناعة؟",
        "upgrade_signal": {
            "action": "add_comorbidity",
            "value": "chronic_disease_unspecified",
            "severity_override": None,
            "category_hint": None,
        },
        "clinical_rationale": "Undetected comorbidities change risk profile",
    },
    "resource": {
        "type": "resource",
        "question_en": "Have you seen a doctor for this problem before?",
        "question_ar": "رحت لدكتور عشان المشكلة دي قبل كده؟",
        "upgrade_signal": {
            "action": "adjust_resources",
            "value": "prior_workup_available",
            "severity_override": None,
            "category_hint": None,
        },
        "clinical_rationale": "Prior workup may reduce or increase ED resource needs",
    },
}


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass(frozen=True)
class BoundaryZone:
    """Describes which ESI boundary the patient sits on."""
    zone: str           # "none", "esi_2_3", "esi_3_hidden", "esi_3_4"
    questions: int      # 0, 1, 2, or 3
    selected_types: Tuple[str, ...] = ()


@dataclass
class ClarificationResult:
    """Result of applying clarification answers."""
    features: PatientFeatures
    aborted: bool = False
    modifications: List[str] = field(default_factory=list)


# =============================================================================
# BOUNDARY ZONE DETECTION
# =============================================================================

def _clean(value: str) -> str:
    return (value or "").strip().lower()


def _has_hard_floor_active(safety_floors: List[str]) -> bool:
    """Check if any hard safety floor is locking the ESI."""
    for floor in (safety_floors or []):
        floor_lower = floor.lower()
        if any(kw in floor_lower for kw in HARD_FLOOR_KEYWORDS):
            return True
    return False


def _is_near_miss_stage2(
    body_system: str,
    severity: str,
    stage_reached: str,
) -> bool:
    """Check if stage2 was close to triggering (high-risk category, stable vitals)."""
    if stage_reached != "stage3_resource_estimation":
        return False
    body = _clean(body_system)
    sev = _clean(severity)
    return body in HIGH_RISK_BODY_SYSTEMS or sev in ("moderate", "severe")


def _hidden_risk_plausible(
    body_system: str,
    age: int,
    gender: str,
) -> bool:
    """Check if a hidden high-risk syndrome is epidemiologically plausible."""
    body = _clean(body_system)
    gen = _clean(gender)

    # Silent MI plausible: GI-like symptoms + age >= 40
    gi_systems = {"gi", "abdominal_pain", "heartburn", "indigestion", "nausea",
                  "abdominal_pain_moderate", "vomiting_diarrhea_dehydration"}
    if body in gi_systems and age >= 40:
        return True

    # Ectopic plausible: female 15-50 with abdominal/pelvic pain
    if gen in ("female", "f", "انثى", "أنثى") and 15 <= age <= 50:
        if "abdominal" in body or "pelvic" in body or "back" in body:
            return True

    # Sepsis plausible: age extremes or fever-related complaints
    if age >= 65 or age <= 2:
        return True

    return False


def detect_boundary_zone(
    esi_level: int,
    stage_reached: str,
    ai_confidence: float,
    body_system: str,
    severity: str,
    age: int,
    gender: str,
    news2_total: int,
    resources_estimated: int,
    safety_floors_applied: List[str],
) -> BoundaryZone:
    """
    Determine if this case sits on an ESI boundary that questions could resolve.

    Returns BoundaryZone with zone name and number of questions (0-3).
    """
    # RULE: ESI 1 (always immediate) and ESI 5 (always non-urgent) → 0 questions
    if esi_level == 1 or esi_level == 5:
        return BoundaryZone(zone="none", questions=0)

    # RULE: Hard safety floor active → ESI is locked, no questions needed
    if _has_hard_floor_active(safety_floors_applied):
        return BoundaryZone(zone="none", questions=0)

    # RULE: High confidence + no floors + low NEWS2 → clear case, 0 questions
    if ai_confidence >= 0.85 and not safety_floors_applied and news2_total < 3:
        return BoundaryZone(zone="none", questions=0)

    # ESI 2 from borderline path with moderate confidence → 1 danger question
    if esi_level == 2 and 0.60 <= ai_confidence < 0.85:
        return BoundaryZone(
            zone="esi_2_3",
            questions=1,
            selected_types=("danger",),
        )

    # ESI 3: check if near-miss from stage2
    if esi_level == 3 and _is_near_miss_stage2(body_system, severity, stage_reached):
        if _hidden_risk_plausible(body_system, age, gender):
            return BoundaryZone(
                zone="esi_3_hidden",
                questions=2,
                selected_types=("danger", "hidden_risk"),
            )
        return BoundaryZone(
            zone="esi_2_3",
            questions=1,
            selected_types=("danger",),
        )

    # ESI 3/4 boundary: resource estimation is uncertain (1-2 resources)
    if esi_level in (3, 4) and resources_estimated in (1, 2):
        if _hidden_risk_plausible(body_system, age, gender):
            return BoundaryZone(
                zone="esi_3_4",
                questions=3,
                selected_types=("danger", "hidden_risk", "resource"),
            )
        return BoundaryZone(
            zone="esi_3_4",
            questions=1,
            selected_types=("resource",),
        )

    return BoundaryZone(zone="none", questions=0)


# =============================================================================
# QUESTION SELECTION
# =============================================================================

def select_questions(
    boundary_zone: BoundaryZone,
    candidate_questions: List[Dict[str, Any]],
    body_system: str = "",
    chief_complaint: str = "",
) -> List[Dict[str, Any]]:
    """
    Select which questions to present, using 3-tier priority:

    1. **Complaint-aware bank** (MIMIC-IV evidence-driven): If the complaint
       matches a known high-risk category, use clinically specific questions
       grounded in real under-triage data.
    2. **AI-generated candidates**: If the AI produced valid questions for
       this specific patient, use those.
    3. **Generic fallback**: Last resort if neither above matches.

    This ensures questions are always complaint-relevant (e.g., abdominal pain
    gets "Do you have fever/chills?" not "Is your condition getting worse?").
    """
    if boundary_zone.questions == 0:
        return []

    # Tier 1: Resolve complaint-aware question bank
    bank_key = _resolve_complaint_bank_key(body_system, chief_complaint)
    complaint_bank = COMPLAINT_QUESTION_BANK.get(bank_key, {}) if bank_key else {}

    # Tier 2: AI-generated candidates indexed by type
    candidates_by_type: Dict[str, Dict[str, Any]] = {}
    for q in (candidate_questions or []):
        qtype = q.get("type")
        if qtype and qtype not in candidates_by_type:
            candidates_by_type[qtype] = q

    selected: List[Dict[str, Any]] = []
    for qtype in boundary_zone.selected_types:
        # Priority: complaint bank > AI candidate > generic fallback
        if qtype in complaint_bank:
            selected.append(deepcopy(complaint_bank[qtype]))
        elif qtype in candidates_by_type:
            selected.append(candidates_by_type[qtype])
        elif qtype in FALLBACK_QUESTIONS:
            selected.append(deepcopy(FALLBACK_QUESTIONS[qtype]))

    return selected


# =============================================================================
# ANSWER APPLICATION
# =============================================================================

def apply_answers(
    answers: List[Dict[str, Any]],
    selected_questions: List[Dict[str, Any]],
    features: PatientFeatures,
) -> ClarificationResult:
    """
    Modify PatientFeatures based on patient answers.

    Only upgrades (adds features), never removes. If any answer is "unknown"
    or invalid, sets aborted=True and returns unmodified features (caller
    should default to the safer ESI tier).
    """
    modified = PatientFeatures(
        chief_complaint=features.chief_complaint,
        snomed_codes=list(features.snomed_codes or []),
        body_system=features.body_system,
        severity=features.severity,
        onset=features.onset,
        red_flags=list(features.red_flags or []),
        age=features.age,
        gender=features.gender,
        comorbidities=list(features.comorbidities or []),
        mental_status=features.mental_status,
        pain_score=features.pain_score,
        ai_confidence=features.ai_confidence,
        is_offline=features.is_offline,
    )
    modifications: List[str] = []

    # Build question lookup by id
    question_by_id: Dict[str, Dict[str, Any]] = {}
    for i, q in enumerate(selected_questions):
        question_by_id[f"q{i}"] = q

    for answer in (answers or []):
        qid = str(answer.get("question_id", ""))
        response = _clean(answer.get("response", ""))

        question = question_by_id.get(qid)
        if not question:
            continue

        # ABORT: unknown / irrelevant / invalid response → keep safer tier
        if response not in VALID_RESPONSES or response == "unknown":
            return ClarificationResult(features=features, aborted=True)

        if response == "no":
            # Negative answer: no upgrade signal applied
            continue

        if response == "yes":
            signal = question.get("upgrade_signal", {})
            action = signal.get("action", "")

            if action == "add_red_flag":
                value = str(signal.get("value", ""))
                if value and value not in modified.red_flags:
                    modified.red_flags.append(value)
                    modifications.append(f"Added red flag: {value}")
                sev_override = signal.get("severity_override")
                if sev_override:
                    modified.severity = str(sev_override)
                    modifications.append(f"Severity upgraded to: {sev_override}")

            elif action == "add_comorbidity":
                value = str(signal.get("value", ""))
                if value and value not in modified.comorbidities:
                    modified.comorbidities.append(value)
                    modifications.append(f"Added comorbidity: {value}")
                cat_hint = signal.get("category_hint")
                if cat_hint:
                    modified.body_system = str(cat_hint)
                    modifications.append(f"Body system reclassified to: {cat_hint}")

            elif action == "adjust_resources":
                # Informational only; stage3 will re-estimate resources
                modifications.append("Resource adjustment signaled")

    return ClarificationResult(
        features=modified,
        aborted=False,
        modifications=modifications,
    )


# =============================================================================
# CLARIFICATION TOKEN (stateless, HMAC-signed)
# =============================================================================

_TOKEN_SECRET = os.getenv("CLARIFICATION_TOKEN_SECRET", "safe-triage-dev-secret-change-in-prod")


def _sign(payload_bytes: bytes) -> str:
    return hmac.new(
        _TOKEN_SECRET.encode("utf-8"),
        payload_bytes,
        hashlib.sha256,
    ).hexdigest()


def build_clarification_token(
    initial_esi: int,
    stage_reached: str,
    news2_total: int,
    resources_estimated: int,
    selected_questions: List[Dict[str, Any]],
    patient_features: Dict[str, Any],
    patient_vitals: Dict[str, Any],
    initial_result_snapshot: Dict[str, Any],
) -> str:
    """Encode clarification state into a compact, HMAC-signed base64 token."""
    payload = {
        "esi": initial_esi,
        "stage": stage_reached,
        "n2": news2_total,
        "res": resources_estimated,
        "qs": selected_questions,
        "feat": patient_features,
        "vit": patient_vitals,
        "snap": initial_result_snapshot,
    }
    payload_bytes = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    sig = _sign(payload_bytes)
    token_data = {"p": base64.b64encode(payload_bytes).decode("ascii"), "s": sig}
    return base64.b64encode(
        json.dumps(token_data, separators=(",", ":")).encode("utf-8")
    ).decode("ascii")


def decode_clarification_token(token: str) -> Optional[Dict[str, Any]]:
    """Decode and verify a clarification token. Returns None if invalid."""
    try:
        token_data = json.loads(base64.b64decode(token.encode("ascii")))
        payload_bytes = base64.b64decode(token_data["p"].encode("ascii"))
        expected_sig = _sign(payload_bytes)
        if not hmac.compare_digest(token_data["s"], expected_sig):
            return None
        payload = json.loads(payload_bytes)
        return {
            "initial_esi": payload["esi"],
            "stage_reached": payload["stage"],
            "news2_total": payload["n2"],
            "resources_estimated": payload["res"],
            "selected_questions": payload["qs"],
            "patient_features": payload["feat"],
            "patient_vitals": payload["vit"],
            "initial_result_snapshot": payload["snap"],
        }
    except Exception:
        return None


# =============================================================================
# QUESTION VALIDATION (for AI-generated candidates)
# =============================================================================

def _contains_diagnosis_term(text: str) -> bool:
    """Check if text contains a blocked diagnosis term (anti-leading guardrail)."""
    text_lower = text.lower()
    for term in DIAGNOSIS_BLOCKLIST_EN:
        if term in text_lower:
            return True
    for term in DIAGNOSIS_BLOCKLIST_AR:
        if term in text:
            return True
    return False


def validate_boundary_questions(raw: Any) -> List[Dict[str, Any]]:
    """Sanitize AI-generated boundary questions. Reject malformed entries."""
    if not isinstance(raw, list):
        return []

    validated: List[Dict[str, Any]] = []
    seen_types: set = set()

    for q in raw[:3]:  # Hard cap at 3
        if not isinstance(q, dict):
            continue

        qtype = q.get("type")
        if qtype not in VALID_QUESTION_TYPES or qtype in seen_types:
            continue

        question_en = str(q.get("question_en", "")).strip()
        question_ar = str(q.get("question_ar", "")).strip()
        if not question_en or not question_ar:
            continue

        # Anti-leading guardrail: reject questions mentioning diagnoses
        if _contains_diagnosis_term(question_en) or _contains_diagnosis_term(question_ar):
            continue

        signal = q.get("upgrade_signal", {})
        if not isinstance(signal, dict):
            continue
        if signal.get("action") not in VALID_ACTIONS:
            continue

        seen_types.add(qtype)
        validated.append({
            "type": qtype,
            "question_en": question_en[:200],
            "question_ar": question_ar[:200],
            "upgrade_signal": {
                "action": signal["action"],
                "value": str(signal.get("value", ""))[:100],
                "severity_override": signal.get("severity_override"),
                "category_hint": signal.get("category_hint"),
            },
            "clinical_rationale": str(q.get("clinical_rationale", ""))[:300],
        })

    return validated
