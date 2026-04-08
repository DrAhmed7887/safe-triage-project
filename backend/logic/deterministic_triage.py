"""
SAFE-Triage AI - Deterministic Hybrid Triage Engine
====================================================

A clinically-validated triage system combining NEWS2 vital sign scoring
with ESI-based complaint classification, using AI only for Arabic NLP
classification (not decision-making).

ACADEMIC REFERENCES
===================

1. NEWS2 (National Early Warning Score 2):
   - Royal College of Physicians. "National Early Warning Score (NEWS) 2:
     Standardising the assessment of acute-illness severity in the NHS."
     London: RCP, 2017.
   - URL: https://www.rcplondon.ac.uk/projects/outputs/national-early-warning-score-news-2
   - Validation: Smith GB, et al. "The ability of the National Early Warning
     Score (NEWS) to discriminate patients at risk of early cardiac arrest,
     unanticipated intensive care unit admission, and death."
     Resuscitation. 2013;84(4):465-470.

2. ESI (Emergency Severity Index) v4:
   - Gilboy N, Tanabe T, Travers D, Rosenau AM. "Emergency Severity Index (ESI):
     A Triage Tool for Emergency Department Care, Version 4."
     AHRQ Publication No. 12-0014. Rockville, MD: AHRQ, 2011.
   - URL: https://www.ahrq.gov/patient-safety/settings/emergency-dept/esi.html
   - Validation: Wuerz RC, et al. "Reliability and validity of a new five-level
     triage instrument." Academic Emergency Medicine. 2000;7(3):236-242.

3. Hybrid AI + Deterministic CDSS Architecture:
   - Shortliffe EH, Sepúlveda MJ. "Clinical Decision Support in the Era of
     Artificial Intelligence." JAMA. 2018;320(21):2199-2200.
   - Sutton RT, et al. "An overview of clinical decision support systems:
     benefits, risks, and strategies for success." NPJ Digital Medicine. 2020;3:17.
   - Topol EJ. "High-performance medicine: the convergence of human and
     artificial intelligence." Nature Medicine. 2019;25(1):44-56.

4. Constrained AI Classification Approach:
   - Rajkomar A, Dean J, Kohane I. "Machine Learning in Medicine."
     New England Journal of Medicine. 2019;380(14):1347-1358.
   - WHO. "Ethics and Governance of Artificial Intelligence for Health."
     Geneva: World Health Organization, 2021. (Chapter 6: Constrained outputs)

5. Arabic Clinical NLP:
   - Alshammari N, et al. "Arabic Natural Language Processing for Clinical Text:
     A Systematic Review." Journal of Biomedical Informatics. 2021;118:103810.

ARCHITECTURE PRINCIPLE
======================
"AI should augment, not replace, clinical decision-making. The most effective
systems combine machine learning for pattern recognition with rule-based
systems for final decisions." — Shortliffe & Sepúlveda, JAMA 2018

Author: Ahmed Zayed
Project: SAFE-Triage AI (Egyptian Emergency Department Triage System)
"""

from typing import Optional, List, Tuple, Dict, Any
from dataclasses import dataclass
from enum import Enum
import os
import json
import re
import time
from dotenv import load_dotenv

# ICD-10 coding for GAHAR compliance (Egyptian hospitals)
from logic.icd10_mapping import ICD10_MAPPING

try:
    from logic.esi_v5_compliance import evaluate_esi_v5
except ImportError:
    from logic.esi_v5_compliance import evaluate_esi_v5

if os.getenv("DISABLE_RAG", "").lower() in {"1", "true", "yes"}:
    rag_retrieve = None
else:
    try:
        from rag.retriever import retrieve as rag_retrieve
    except ImportError:
        try:
            from rag.retriever import retrieve as rag_retrieve
        except ImportError:
            rag_retrieve = None

load_dotenv()

# ===== MODULE-LEVEL REGEX CONSTANTS =====
# Pre-compiled at import time — used in hot-path _fallback_keyword_match.
_DENIED_TERMS = (
    r"(?:fever|cough|chills|nausea|vomiting|diarrhea|headache|"
    r"rash|bleeding|bloody stools|chest pain|abdominal pain|"
    r"shortness of breath|drainage|weight loss|weight changes|"
    r"dysuria|hematuria|pain|swelling)"
)
_NEGATION_RE = re.compile(
    r'\b(?:denies?|negative for)\s+'
    + _DENIED_TERMS
    + r'(?:\s*,\s*' + _DENIED_TERMS + r')*'
    + r'(?:\s*,?\s*(?:and|or)\s+' + _DENIED_TERMS + r')?',
    re.IGNORECASE,
)
_NO_BENIGN_RE = re.compile(
    r'\b(?:reported no|no)\s+(?:pain|fever|cough|bleeding|vomiting|nausea|headache|diarrhea|rash|swelling)\b'
)
_AR_LETTER = r'[\u0621-\u063A\u0641-\u064A\u0660-\u0669\u0670-\u06D3]'
_AR_WORD = _AR_LETTER + r'+'
_AR_NEGATION_RE = re.compile(
    r'(?:بينفي|بتنفي|مفيش|من غير|بدون|مش عنده|مش عندها)'
    r'(?:\s+(?:أي|اي))?'
    r'\s+' + _AR_WORD
    + r'(?:[،,]\s*' + _AR_WORD + r')*'
    + r'(?:[،,]?\s*(?:أو|او)\s+' + _AR_WORD + r'(?:\s+' + _AR_WORD + r')*)?'
)
_AR_MED_ALLERGY_RE = re.compile(
    r'(?:حساسية من|وحساسية من|حساسيه من)\s+' + _AR_WORD
    + r'(?:\s+' + _AR_WORD + r')*'
)
_AR_NORMAL_TEMP_RE = re.compile(
    r'حرارة\s*[:=]?\s*(?:3[5-7](?:\.\d+)?)\s*(?:مئوية|درجة)?'
)

# Legacy google.generativeai removed — all AI extraction now goes through
# ai_service.py (Vertex AI: Gemma 4 primary, Gemini 2.5-flash fallback).
# The AISymptomClassifier below runs keyword-only in deterministic mode.


_NEGATION_SENTENCE_RE = re.compile(
    r'(?:there were |were )?'
    r'(?:no|denies?|denied|negative for|without)\s+'
    r'(?:symptoms?\s+of\s+|evidence\s+of\s+|signs?\s+of\s+|history\s+of\s+)?'
    r'[^.]*?\.',
    re.IGNORECASE,
)


def _normalize_guardrail_text(complaint_text: str) -> str:
    """Normalize complaint text for narrow, text-only safety guardrails.

    Strips English and Arabic negation clauses so that denied symptoms
    (e.g. "denies melena, hematochezia") do not false-positive as signals.
    """
    normalized = (complaint_text or "").strip().lower()
    normalized = normalized.replace("أ", "ا").replace("إ", "ا").replace("آ", "ا")
    normalized = normalized.replace("ى", "ي")
    # Strip complete negation sentences (e.g. "There were no symptoms of X, Y, Z.")
    normalized = _NEGATION_SENTENCE_RE.sub("", normalized)
    # Strip inline negation clauses (e.g. "denies fever, cough")
    normalized = _NEGATION_RE.sub("", normalized)
    normalized = _NO_BENIGN_RE.sub("", normalized)
    normalized = _AR_NEGATION_RE.sub("", normalized)
    return " ".join(normalized.split())


def _contains_any(text: str, phrases: List[str]) -> bool:
    return any(phrase in text for phrase in phrases)


def _first_int_match(text: str, patterns: List[str]) -> Optional[int]:
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            try:
                return int(match.group(1))
            except (TypeError, ValueError):
                continue
    return None


def _text_has_tachycardia_signal(text: str) -> bool:
    if _contains_any(
        text,
        [
            "tachycardia",
            "rapid pulse",
            "rapid heart rate",
            "heart racing",
            "fast pulse",
            "fast heart rate",
            "نبض سريع",
            "تسرع قلب",
        ],
    ):
        return True
    hr_value = _first_int_match(
        text,
        [
            r"\bhr\s*[:=]?\s*(\d{2,3})\b",
            r"\bheart rate\s*[:=]?\s*(\d{2,3})\b",
        ],
    )
    return bool(hr_value is not None and hr_value > 100)


def _text_has_hypotension_signal(text: str) -> bool:
    if _contains_any(
        text,
        [
            "hypotensive",
            "low bp",
            "low blood pressure",
            "sbp < 90",
            "ضغط واطي",
            "ضغط منخفض",
            "هبوط ضغط",
        ],
    ):
        return True
    systolic_value = _first_int_match(
        text,
        [
            r"\bsbp\s*[:=]?\s*(\d{2,3})\b",
            r"\bbp\s*[:=]?\s*(\d{2,3})/\d{2,3}\b",
            r"\bblood pressure\s*[:=]?\s*(\d{2,3})/\d{2,3}\b",
        ],
    )
    return bool(systolic_value is not None and systolic_value < 90)


def _text_has_altered_mental_status_signal(text: str) -> bool:
    return _contains_any(
        text,
        [
            "confused",
            "altered",
            "unresponsive",
            "drowsy",
            "lethargic",
            "disoriented",
            "not acting right",
            "مشوش",
            "ملخبط",
            "مش واعي",
            "مش بيرد",
            "خامل",
        ],
    )


def _text_has_sepsis_signal(text: str) -> bool:
    return _contains_any(text, ["sepsis", "urosepsis", "septic", "sirs", "تعفن", "انتان"])


def _text_has_hypoxia_signal(text: str) -> bool:
    if _contains_any(
        text,
        [
            "low oxygen",
            "can't breathe",
            "cannot breathe",
            "hypoxic",
            "مش قادر يتنفس",
            "مش عارف ياخد نفسه",
            "نقص اكسجين",
        ],
    ):
        return True
    spo2_value = _first_int_match(
        text,
        [
            r"\bspo2\s*[:=]?\s*(\d{2,3})\b",
            r"\bo2 sat(?:uration)?\s*[:=]?\s*(\d{2,3})\b",
            r"\boxygen saturation\s*[:=]?\s*(\d{2,3})\b",
        ],
    )
    return bool(spo2_value is not None and spo2_value < 94)


def _text_has_tachypnea_signal(text: str) -> bool:
    if _contains_any(
        text,
        [
            "fast breathing",
            "tachypneic",
            "tachypnea",
            "respiratory distress",
            "breathing fast",
            "تنفس سريع",
            "ضيق تنفس شديد",
        ],
    ):
        return True
    rr_value = _first_int_match(
        text,
        [
            r"\brr\s*[:=]?\s*(\d{1,2})\b",
            r"\bresp(?:iratory)? rate\s*[:=]?\s*(\d{1,2})\b",
        ],
    )
    return bool(rr_value is not None and rr_value > 22)


def _text_has_fever_signal(text: str) -> bool:
    # Arabic negated fever: "بينفي سخونية" (denies fever) → no fever signal.
    _NEGATED_FEVER_AR = ("بينفي أي سخونية", "بينفي سخونية", "مفيش سخونية",
                          "من غير سخونية", "بدون سخونية", "بينفي السخونية")
    if any(nf in text for nf in _NEGATED_FEVER_AR):
        # Fever explicitly denied. Only trigger if English fever keyword present.
        if _contains_any(text, ["fever", "febrile"]):
            return True
        return False
    # Arabic normal-temperature reporting patterns that should NOT trigger fever.
    # e.g. "وحرارة 37.4 مئوية" or "حرارة 36.8" are vitals reports, not complaints.
    if _AR_NORMAL_TEMP_RE.search(text):
        # "حرارة" appeared only as a normal temperature reading — skip it.
        # But still check for explicit fever complaint words.
        if _contains_any(text, ["fever", "febrile", "حمى", "سخونية"]):
            return True
        return False
    if _contains_any(text, ["fever", "febrile", "حمى", "سخونية", "حرارة"]):
        return True
    temp_value = _first_int_match(
        text,
        [
            r"\btemp(?:erature)?\s*[:=]?\s*(\d{2})(?:\.\d+)?\b",
        ],
    )
    return bool(temp_value is not None and temp_value >= 38)


def _text_has_syncope_signal(text: str) -> bool:
    return _contains_any(
        text,
        [
            "syncope",
            "near syncope",
            "passed out",
            "fainted",
            "blacked out",
            "fell out",
            "اغمى عليه",
            "اغمي عليه",
            "فقد الوعي",
            "قرب يغمى عليه",
        ],
    )


UTI_CATEGORY_FAMILIES = [
    "uti",
    "urinary tract",
    "pyelonephritis",
    "urosepsis",
    "dysuria",
    "urinary infection",
    "kidney infection",
]

PNEUMONIA_CATEGORY_FAMILIES = [
    "pneumonia",
    "lower respiratory",
    "lung infection",
    "community acquired pneumonia",
    "cap ",
    "respiratory infection",
]

DEHYDRATION_CATEGORY_FAMILIES = [
    "dehydration",
    "vomiting and diarrhea",
    "gastroenteritis",
    "fluid loss",
    "poor oral intake",
    "nausea vomiting diarrhea",
]

CELLULITIS_CATEGORY_FAMILIES = [
    "cellulitis",
    "skin infection",
    "soft tissue infection",
    "wound infection",
    "erysipelas",
]

LACERATION_CATEGORY_FAMILIES = [
    "laceration",
    "wound",
    "cut",
    "laceration needs sutures",
    "facial laceration",
    "hand laceration",
]

# Signals shared between INSTABILITY_SIGNALS and LIFE_THREAT_SIGNALS.
# Defined once to prevent drift — changes here propagate to both lists.
_SHARED_CRITICAL_SIGNALS = (
    "somnolent", "listless", "mottled", "floppy",
    "not acting right", "obtunded", "drooling",
)

INSTABILITY_SIGNALS = [
    # Hemodynamic
    "hypotension", "hypotensive", "low blood pressure", "sbp",
    "bp 8", "bp 7", "bp 6", "systolic",
    # Tachycardia
    "tachycardia", "heart rate over 100", "hr over 100",
    "hr 1", "rapid pulse", "racing heart",
    # Respiratory compromise
    "respiratory distress", "can't breathe", "cannot breathe",
    "shortness of breath at rest", "low spo2", "spo2 drop", "oxygen desaturation",
    "hypoxia", "hypoxic", "tachypnea", "breathing fast",
    "dyspnea", "acute dyspnea",
    # Trauma
    "trauma", "injury", "blunt trauma", "penetrating trauma",
    # Neurological
    "altered", "unresponsive", "unconscious", "not responding",
    "confused", "disoriented", "loss of consciousness", "syncope",
    "passed out", "fainted",
    "mental change", "altered mentality", "confuse mentality",
    "loc",
    # Hemorrhage
    "uncontrolled bleeding", "spurting", "massive blood loss",
    "hematemesis", "melena", "bright red blood", "won't stop bleeding",
    # Explicit severity
    "sepsis", "septic", "shock", "in shock",
    "cardiac arrest", "not breathing", "no pulse",
    "acute stroke", "facial droop", "arm weakness", "slurred speech",
    "dissection", "aortic dissection", "ectopic", "ruptured",
    "anaphylaxis", "anaphylactic",
    "suicide attempt", "overdose", "ingested",
    "dka", "diabetic ketoacidosis",
    # Neurological / meningeal
    "worst headache", "thunderclap", "meningitis", "nuchal rigidity",
    "stiff neck", "photophobia", "light sensitivity",
    # Neurological — stroke / TIA / focal deficit
    "wake up deficit", "wake-up deficit", "focal deficit", "focal neurological",
    "aphasia", "hemiplegia", "hemiparesis", "tia", "transient ischemic",
    "sudden weakness", "sudden numbness", "sudden vision loss",
    "visual acuity", "visual abnormality", "vision abnormality",
    "amnesia", "transient global amnesia",
    "neurological symptoms", "resolved neurological",
    # Stroke — motor/speech deficit language
    "unable to move", "can't move", "cannot move",
    "can't speak", "cannot speak", "unable to speak",
    "can't speak clearly", "can't talk", "cannot talk",
    "one sided weakness", "one-sided weakness",
    "right side weakness", "left side weakness",
    "left sided weakness", "right sided weakness",
    "left-sided weakness", "right-sided weakness",
    "arm weakness", "leg weakness", "facial weakness",
    "motor weakness", "side motor weakness", "paraparesis",
    "ضعف في الناحية الشمال", "ضعف في الناحية اليمين",
    "الناحية الشمال مرتخية", "الناحية اليمين مرتخية",
    # Egyptian stroke descriptions (Gemini-expanded)
    "بقه اتلوح", "كلامه تقل", "إيده خذلت",
    "وشه اتعوج", "لسانه تقل", "ريقه بيجري",
    "بيجر رجله", "نص جسمه نمل", "بيتهته",
    "زغللة",  # sudden blurred vision — stroke/TIA sign
    # Arabic fever/infection instability
    "سخونية تروح وتيجي", "عرق بالليل", "سخونية",
    # Arabic chest pain (expanded with Egyptian colloquial)
    "وجع في الصدر", "وجع في صدرها", "وجع في صدره",
    "عصرة في صدري", "نغزة في قلبي", "صدري مكلبش",
    "قلبي بيدق بسرعة", "قلبي بيفرفر",
    "سكاكين في صدري", "حاسس بطوبة على صدري",
    "woke up unable", "woke up and couldn't",
    "flaccid", "gaze deviation", "gaze preference",
    "hemibody", "dense hemiplegia",
    # Cardiac
    "chest pain", "pain, chest", "pain chest",
    "discomfort, chest", "discomfort chest", "chest discomfort",
    "chest palpitation",
    "crushing", "pressure in chest", "diaphoresis",
    "sweating with pain", "jaw pain", "radiation to arm",
    # Metabolic emergency — DKA / hyperglycemia
    "fruity breath", "blood sugar over", "blood sugar 5", "blood sugar 6",
    "blood sugar 7", "blood sugar 8", "glucose over", "glucose 5", "glucose 6",
    "ketoacidosis", "diabetic emergency", "diabetic crisis",
    # Obstetric / surgical emergency
    "ectopic", "ruptured", "peritonitis", "rigid abdomen",
    # Obstetric emergency — vaginal bleeding in pregnancy
    "vaginal bleeding", "bleeding in pregnancy", "pregnant and bleeding",
    "bleeding while pregnant", "obstetric bleeding", "antepartum bleeding",
    "placenta", "miscarriage", "ectopic bleeding",
    # Psychiatric / toxicology emergency
    "suicide attempt", "overdose", "self harm", "ingested pills",
    # Psychiatric emergency — suicidal ideation with plan
    "suicidal ideation", "suicidal with plan", "plan to harm",
    "wants to die", "active suicidal", "thinking about suicide",
    "intent to", "plan to kill", "means to harm",
    # Suicidal ideation with plan — intent language
    "wants to kill", "kill himself", "kill herself",
    "kill themselves", "has a plan", "suicidal plan",
    "method to harm", "means and plan", "plan to end",
    "going to kill",
    # Urological emergency — testicular torsion
    "testicular torsion", "torsion", "testicle pain sudden",
    "scrotal pain sudden", "testicular pain",
    # Orthopedic emergency — open fractures require ESI 2
    "open fracture", "compound fracture", "bone exposed",
    "open tibia", "open femur", "open humerus",
    "open left tibia", "open right tibia",
    "open left femur", "open right femur",
    # Transfer patients (inter-facility) often have instability
    "transferred to", "transferred from", "transfer from",
    "was transferred",
    # ── ESI Handbook-derived signals (batch fix) ─────────────────────
    # NOTE: Signals also in LIFE_THREAT_SIGNALS are sourced from _SHARED_CRITICAL_SIGNALS
    # to avoid drift. Signals unique to instability (ESI 2) are listed here directly.
    # Altered mental status / appearance
    "lethargic", "lethargy", "limp",
    # Psychiatric/violence — ESI 2 regardless of vitals
    "threatening to kill", "threatening to harm", "out of control",
    "sexually assaulted", "sexual assault",
    "suicidal", "kill myself",
    # Severe pain / dislocation
    "10/10", "obvious dislocation", "obvious deformity",
    # C-spine / high-energy mechanism
    "c-collar", "backboard", "back board", "immobilized on",
    "high-speed", "hit by a car", "struck by car", "multicar",
    # High-risk devices / signs
    "vp shunt", "shunt malfunction",
    "petechiae", "petechial", "purpuric", "purpura",
    # Compartment syndrome
    "cast is cutting", "cutting off circulation", "swollen and the cast",
    # Dysphagia with airway concern
    "barely swallow", "peritonsillar",
    "voice is different", "muffled voice",
    # Neonatal / infant alarm
    "sunken fontanel",
    # Psychotic / dangerous behaviour
    "screaming about", "end of the world",
    "standing in traffic",
    # ── Arabic / Egyptian dialect instability signals ───────────────────
    # Cardiac arrest / pulselessness
    "توقف في عضلة القلب",
    "قلبه وقف", "قلبها وقف",
    "مفيش نبض",
    "العلامات الحيوية كلها كانت أصفار",
    "العلامات الحيوية مكنتش محسوسة",
    "مكنتش محسوسة",
    # Unresponsive / unconscious
    "فاقد الوعي", "فاقدة الوعي",
    "مش بترد", "مش بيرد",
    # Resuscitation / intubation / ventilation
    "إنعاش فوري", "انعاش فوري",
    "أنبوبة حنجرية", "انبوبة حنجرية",
    "جهاز تنفس صناعي",
    # NOTE: Sepsis ("تسمم في الدم"), standalone overdose ("جرعة زيادة"),
    # and hypotension ("ضغط واطي") → moved to INSTABILITY_SIGNALS (ESI 2).
    # Only keep signals that unambiguously require ESI 1 (resuscitation) here.
    # Seizures (active)
    "تشنجات",
    # Confirmed suicide attempt
    "محاولة انتحار",
    # Chest tube (implies pneumothorax/hemothorax — surgical emergency)
    "أنبوبة الصدر", "انبوبة الصدر",
    # MVC / high-energy collision
    "حادثة عربية", "حادث عربية",
    # Open fracture — ESI 2 path (matches English "open fracture" in INSTABILITY)
    "كسر مفتوح",
] + list(_SHARED_CRITICAL_SIGNALS)

NON_URGENT_SIGNALS = [
    "routine", "physical exam", "sports physical", "work note",
    "medication refill", "prescription", "referral",
    "dandruff", "shampoo", "cosmetic", "elective",
    "chronic", "years", "months", "follow up", "follow-up",
    "check up", "checkup", "blood pressure check", "bp check",
    "insomnia", "can't sleep", "cannot sleep", "trouble sleeping",
    "sleep problem", "sleep difficulty",
    "flu-like", "flu like", "influenza", "runny nose",
    "body aches", "mild body", "feels like flu",
]

LIFE_THREAT_SIGNALS = [
    # Cardiac arrest / pulselessness / post-resuscitation
    "cardiac arrest",
    "arrest",           # bare keyword — catches "arrest" without "cardiac" prefix
    "not breathing",
    "no pulse",
    "pulseless",
    "vital signs were absent",
    "vitals absent",
    "found down",
    "found unresponsive",
    # Post-CPR / ROSC — definitionally ESI 1 (resuscitation)
    "post-cpr",
    "post cpr",
    "after cpr",
    "rosc",
    "return of spontaneous circulation",
    "post-resuscitation",
    "post resuscitation",
    "post-arrest",
    "post arrest",
    # Airway / breathing failure
    "respiratory distress",
    "respiratory failure",
    "acute respiratory failure",
    "can't breathe",
    "cannot breathe",
    "airway obstruction",
    "complete airway obstruction",
    "apneic",
    "intubated",
    "on ventilator",
    "mechanical ventilation",
    "requires intubation",
    "bipap",
    # Consciousness
    "unresponsive",
    "unconscious",
    "not responding",
    "obtunded",
    "comatose",
    "gcs 3",
    "gcs 4",
    "gcs 5",
    "gcs 6",
    "gcs 7",
    "gcs 8",
    "no response to pain",
    # Shock / hemodynamic collapse
    "shock",
    "in shock",
    "hemodynamically unstable",
    "hemodynamic instability",
    "severe hypotension",
    "decompensated",
    # Hemorrhage
    "uncontrolled bleeding",
    "spurting",
    "massive blood loss",
    "hematemesis",
    "bright red blood",
    "won't stop bleeding",
    "exsanguinating",
    # Anaphylaxis
    "anaphylaxis",
    "anaphylactic",
    # Trauma
    "major trauma",
    "ejected from vehicle",
    "multiple injuries",
    "motor vehicle collision",
    "motor vehicle accident",
    "mvc",
    "high speed",
    "pedestrian struck",
    "rollover",
    "gunshot wound",
    "stab wound",
    "evisceration",
    "pulsatile abdominal mass",
    "ruptured aaa",
    "aaa",
    # Ingestion / toxicology
    "caustic",
    "drain cleaner",
    "drooling",
    "intentional overdose",
    "toxic ingestion",
    # Seizure — any seizure is ESI 1 until proven otherwise
    "seizure",
    "status epilepticus",
    "continuous seizure",
    "seizure not stopping",
    "tonic-clonic seizure",
    "tonic clonic seizure",
    "seizure activity",
    "active seizure",
    "convulsion",
    "convulsing",
    # Transfer patients with critical conditions
    "transfer",  # patients transferred between facilities are often ESI 1-2
    # Altered mental status (when in combination with other signals)
    "altered mental status",
    # Pulmonary / vascular emergencies
    "pulmonary embolism",
    "saddle embolus",
    "acute worsening dyspnea",
    "acute worsening shortness",
    "acute decompensation",
    # ── ESI Handbook life-threat signals (batch fix) ─────────────────
    # Shared signals sourced from _SHARED_CRITICAL_SIGNALS (defined above INSTABILITY_SIGNALS)
    # Pediatric hit by car / pedestrian struck (high-energy mechanism)
    "hit by a car", "hit by car", "struck by a car",
    "ped struck", "pedestrian hit", "pedestrian struck",
    # ── Arabic / Egyptian dialect life-threat signals ───────────────────
    # Cardiac arrest / pulselessness
    "توقف في عضلة القلب",        # cardiac arrest (lit. "heart muscle stopped")
    "قلبه وقف",                  # his heart stopped
    "قلبها وقف",                  # her heart stopped
    "مفيش نبض",                  # no pulse
    "العلامات الحيوية كلها كانت أصفار",  # all vitals were zeros
    "العلامات الحيوية مكنتش محسوسة",     # vitals not palpable
    "مكنتش محسوسة",              # not palpable (vitals)
    # Unresponsive / unconscious
    "فاقد الوعي",                # unconscious (masculine)
    "فاقدة الوعي",               # unconscious (feminine)
    "مش بترد",                   # not responding (feminine)
    "مش بيرد",                   # not responding (masculine)
    # Egyptian AMS — Gemini-expanded (unambiguous life-threat patterns only)
    "مبلّم وباصص للسقف",         # staring blankly at ceiling
    "مش دريان باللي حواليه",      # unaware of surroundings
    "نايم على نفسه ومش راضي يصحى", # drowsy and won't wake up
    "همدان ومش فايق",            # lethargic and not alert (ESI handbook)
    "مهدود خالص",                # completely exhausted/listless (pediatric)
    # Pediatric life-threat — sunken fontanel
    "يافوخ هابط", "يافوخه هابط", "يافوخه هبطان", "يافوخه نزل",
    # Resuscitation / intubation
    "إنعاش فوري",               # immediate resuscitation
    "انعاش فوري",               # immediate resuscitation (no hamza)
    "إنعاش قلبي",               # cardiac resuscitation
    "انعاش قلبي",               # cardiac resuscitation (no hamza)
    "بعد إنعاش",                # post-resuscitation (Arabic)
    "أنبوبة حنجرية",            # laryngeal tube / intubated
    "انبوبة حنجرية",            # laryngeal tube (no hamza)
    "جهاز تنفس صناعي",          # mechanical ventilator
    # NOTE: "تسمم في الدم" (sepsis), "جرعة زيادة" (overdose) moved to
    # INSTABILITY_SIGNALS (ESI 2). Only unambiguous ESI 1 signals here.
    # Seizures (active) — Gemini-expanded
    "تشنجات",                   # seizures
    "اتخشب وعينيه قلبت",        # went stiff, eyes rolled back
    "بيتنفض",                   # convulsing/shaking
    "طلع رغاوي من بقه",         # foaming at the mouth
    "عض لسانه",                 # bit his tongue
    # Confirmed suicide attempt with severe signs
    "محاولة انتحار",             # suicide attempt
    # MVC / high-energy collision (life-threatening trauma)
    "حادثة عربية",              # car accident (Egyptian)
    "حادث عربية",               # car accident
    # Chest tube (pneumothorax/hemothorax)
    "أنبوبة الصدر",             # chest tube (with hamza)
    "انبوبة الصدر",             # chest tube (without hamza)
    # NOTE: "كسر مفتوح" (open fracture) → DEFINITIVE_ESI2_SIGNALS only (ESI 2),
    # matching English "open fracture" behavior.
] + list(_SHARED_CRITICAL_SIGNALS)

CLEAR_NON_URGENT_SIGNALS = [
    "routine",
    "physical exam",
    "sports physical",
    "work note",
    "medication refill",
    "prescription",
    "referral",
    "dandruff",
    "elective",
    "follow up",
    "follow-up",
    "check up",
    "checkup",
    "blood pressure check",
    "bp check",
]


def guardrail_uti_pyelonephritis(complaint_text: str, ai_category: str, proposed_esi: int) -> Tuple[int, str]:
    """Cap AI-only UTI/pyelo escalation to ESI 3 unless sepsis criteria are explicit."""
    category_lower = str(ai_category or "").lower()
    if not any(family in category_lower for family in UTI_CATEGORY_FAMILIES):
        return proposed_esi, "PASS"
    if proposed_esi >= 3:
        return proposed_esi, "PASS"
    text = _normalize_guardrail_text(complaint_text)
    if not _contains_any(
        text,
        [
            "uti",
            "urinary",
            "urination",
            "pee",
            "dysuria",
            "pyelonephritis",
            "burning with urination",
            "burning when i pee",
            "back pain",
            "بول",
        ],
    ):
        return proposed_esi, "PASS"

    has_sepsis_criteria = any(
        [
            _text_has_tachycardia_signal(text),
            _text_has_hypotension_signal(text),
            _text_has_altered_mental_status_signal(text),
            _text_has_sepsis_signal(text),
        ]
    )
    if not has_sepsis_criteria:
        return 3, "GUARDRAIL_UTI: No sepsis criteria detected - capped at ESI 3"
    return proposed_esi, "PASS"


def guardrail_pneumonia_stable(complaint_text: str, ai_category: str, proposed_esi: int) -> Tuple[int, str]:
    """Cap stable pneumonia-like complaints to ESI 3 unless hypoxia/tachypnea/AMS is explicit."""
    category_lower = str(ai_category or "").lower()
    if not any(family in category_lower for family in PNEUMONIA_CATEGORY_FAMILIES):
        return proposed_esi, "PASS"
    if proposed_esi >= 3:
        return proposed_esi, "PASS"
    text = _normalize_guardrail_text(complaint_text)
    if not (
        "pneumonia" in text
        or ("cough" in text and "sputum" in text)
        or ("productive cough" in text)
        or ("سعال" in text and "بلغم" in text)
    ):
        return proposed_esi, "PASS"

    severe_respiratory_signal = any(
        [
            _text_has_hypoxia_signal(text),
            _text_has_tachypnea_signal(text),
            _text_has_altered_mental_status_signal(text),
        ]
    )
    if not severe_respiratory_signal:
        return 3, "GUARDRAIL_PNEUMONIA: No hypoxia, tachypnea, or AMS detected - capped at ESI 3"
    return proposed_esi, "PASS"


def guardrail_dehydration_moderate(complaint_text: str, ai_category: str, proposed_esi: int) -> Tuple[int, str]:
    """Cap moderate dehydration to ESI 3 unless instability or syncope is explicit."""
    category_lower = str(ai_category or "").lower()
    if not any(family in category_lower for family in DEHYDRATION_CATEGORY_FAMILIES):
        return proposed_esi, "PASS"
    if proposed_esi >= 3:
        return proposed_esi, "PASS"
    text = _normalize_guardrail_text(complaint_text)
    if not _contains_any(
        text,
        [
            "dehydration",
            "vomiting and diarrhea",
            "vomiting",
            "diarrhea",
            "not urinating much",
            "dry",
            "جفاف",
            "اسهال",
            "قيء",
            "ترجيع",
        ],
    ):
        return proposed_esi, "PASS"

    instability_signal = any(
        [
            _text_has_syncope_signal(text),
            _text_has_tachycardia_signal(text),
            _text_has_hypotension_signal(text),
            _text_has_altered_mental_status_signal(text),
        ]
    )
    if not instability_signal:
        return 3, "GUARDRAIL_DEHYDRATION: No syncope, instability, or AMS detected - capped at ESI 3"
    return proposed_esi, "PASS"


def guardrail_cellulitis_spreading(complaint_text: str, ai_category: str, proposed_esi: int) -> Tuple[int, str]:
    """Cap spreading cellulitis to ESI 3 unless systemic signs are explicitly present."""
    category_lower = str(ai_category or "").lower()
    if not any(family in category_lower for family in CELLULITIS_CATEGORY_FAMILIES):
        return proposed_esi, "PASS"
    if proposed_esi >= 3:
        return proposed_esi, "PASS"
    text = _normalize_guardrail_text(complaint_text)
    spreading_signal = _contains_any(
        text,
        [
            "spreading",
            "getting bigger",
            "red streaks",
            "worsening redness",
            "يمتد",
            "بينتشر",
            "بيكبر",
        ],
    )
    cellulitis_signal = _contains_any(
        text,
        [
            "cellulitis",
            "red swollen",
            "infected skin",
            "leg infection",
            "التهاب نسيج خلوي",
            "احمرار وتورم",
        ],
    )
    if not (spreading_signal and cellulitis_signal):
        return proposed_esi, "PASS"

    has_systemic_sign = any(
        [
            _text_has_fever_signal(text),
            _text_has_tachycardia_signal(text),
            _text_has_sepsis_signal(text),
        ]
    )
    if not has_systemic_sign:
        return 3, "GUARDRAIL_CELLULITIS: Spreading without systemic signs - capped at ESI 3"
    return proposed_esi, "PASS"


def guardrail_laceration_needs_sutures(complaint_text: str, ai_category: str, proposed_esi: int) -> Tuple[int, str]:
    """Cap lacerations needing repair to ESI 3 unless active hemorrhage is explicit."""
    category_lower = str(ai_category or "").lower()
    if not any(family in category_lower for family in LACERATION_CATEGORY_FAMILIES):
        return proposed_esi, "PASS"
    if proposed_esi >= 3:
        return proposed_esi, "PASS"
    text = _normalize_guardrail_text(complaint_text)
    if not _contains_any(
        text,
        [
            "laceration",
            "cut",
            "stitches",
            "sutures",
            "wound repair",
            "جرح",
            "غرز",
            "خياطة",
        ],
    ):
        return proposed_esi, "PASS"

    active_hemorrhage_signal = _contains_any(
        text,
        [
            "uncontrolled bleeding",
            "spurting",
            "won't stop bleeding",
            "arterial",
            "massive blood loss",
            "active hemorrhage",
            "bleeding heavily",
            "نزيف شديد",
            "النزيف مش بيوقف",
            "دم نافور",
        ],
    ) or _text_has_tachycardia_signal(text) or _text_has_hypotension_signal(text)
    if not active_hemorrhage_signal:
        return 3, "GUARDRAIL_LACERATION: Repair-only laceration without hemorrhage - capped at ESI 3"
    return proposed_esi, "PASS"


def apply_safety_guardrails(complaint_text: str, ai_category: str, proposed_esi: int) -> Tuple[int, List[str]]:
    """Apply narrow AI over-triage guardrails before NEWS2 and downstream deterministic floors."""
    final_esi = proposed_esi
    fired_reasons: List[str] = []
    guardrail_functions = [
        guardrail_uti_pyelonephritis,
        guardrail_pneumonia_stable,
        guardrail_dehydration_moderate,
        guardrail_cellulitis_spreading,
        guardrail_laceration_needs_sutures,
    ]
    for guardrail in guardrail_functions:
        final_esi, reason = guardrail(complaint_text, ai_category, final_esi)
        if reason != "PASS":
            fired_reasons.append(reason)
    return final_esi, fired_reasons


# Categories where ESI v5 protocol mandates ESI 2 regardless of vitals/text signals.
# The ceiling must never override these — they were placed at ESI 2 for clinical
# reasons that the text signals cannot capture (e.g. psychiatric emergency = "si",
# stroke abbrev = "cva", confirmed GI bleed = "brbpr").
_ESI2_MANDATORY_CATEGORIES: set = {
    "suicidal_homicidal",     # ESI v5: psych emergency always ESI 2
    "stroke_symptoms",        # ESI v5: stroke signs always ESI 2
    "altered_mental_status",  # ESI v5: AMS always ESI 2
    "gi_bleed",               # Active GI bleed → always ESI 2
    "hemoptysis",             # Bleeding from airway → always ESI 2
    "respiratory_distress",   # Acute respiratory distress → always ESI 2
    "chest_pain_cardiac",     # Cardiac chest pain → always ESI 2
    "diabetic_emergency",     # DKA/hypoglycemia → always ESI 2
    "obstetric_emergency",    # Obstetric emergency → always ESI 2
}


def apply_severity_ceiling(complaint_text: str, proposed_esi: int, ai_category: str = "") -> Tuple[int, str]:
    """
    Universal post-guardrail ceiling for AI-derived severity.

    This applies only to the AI classification path before NEWS2 and the
    downstream deterministic ESI floors. It never suppresses high NEWS2 or
    deterministic overrides that run after this step.
    """
    text = _normalize_guardrail_text(complaint_text)
    has_instability_signal = _contains_any(text, INSTABILITY_SIGNALS)

    non_urgent_matches = [signal for signal in NON_URGENT_SIGNALS if signal in text]
    clearly_non_urgent = _contains_any(text, CLEAR_NON_URGENT_SIGNALS) or len(non_urgent_matches) >= 2

    if proposed_esi <= 3 and clearly_non_urgent and not has_instability_signal:
        return 4, "CEILING_NON_URGENT: No acute signals - capped at ESI 4"

    if proposed_esi == 1 and not _contains_any(text, LIFE_THREAT_SIGNALS):
        return 2, "CEILING_ESI1: No life-threat signals - capped at ESI 2"

    # Do NOT cap ESI 2 categories that the protocol mandates at ESI 2 regardless of vitals.
    # These were assigned ESI 2 by a clinical guardrail (e.g. "si" → suicidal_homicidal,
    # "cva" → stroke_symptoms) — the absence of instability signals in the 2-word triage
    # text is expected, not a reason to downgrade.
    if proposed_esi == 2 and ai_category in _ESI2_MANDATORY_CATEGORIES:
        return proposed_esi, "PASS"

    if proposed_esi == 2 and not has_instability_signal:
        return 3, "CEILING_ESI2: No instability signals - capped at ESI 3"

    return proposed_esi, "PASS"

# Try to import dynamic keyword database
try:
    from logic.keyword_database import get_keyword_database, KeywordDatabase
    USE_DYNAMIC_KEYWORDS = True
except ImportError:
    USE_DYNAMIC_KEYWORDS = False


# =============================================================================
# SYMPTOM CATEGORIES (ESI-Based)
# =============================================================================
# Reference: ESI v4 Handbook, AHRQ 2011, Chapter 3: ESI Triage Algorithm
#
# Categories map to ESI levels based on:
# - Level 1: Immediate life-saving intervention required
# - Level 2: High-risk situation, confused/lethargic/disoriented, severe pain
# - Level 3: Two or more resources needed
# - Level 4: One resource needed
# - Level 5: No resources needed

@dataclass
class SymptomCategory:
    """Represents a clinical symptom category with its ESI level mapping"""
    esi_level: int
    name_ar: str
    name_en: str
    requires_immediate_intervention: bool = False


SYMPTOM_CATEGORIES: Dict[str, SymptomCategory] = {
    # =========== LEVEL 1: Resuscitation ===========
    "unconscious": SymptomCategory(1, "فقدان وعي", "Unconscious/Unresponsive", True),
    "cardiac_arrest": SymptomCategory(1, "توقف القلب", "Cardiac Arrest", True),
    "respiratory_arrest": SymptomCategory(1, "توقف التنفس", "Respiratory Arrest", True),
    "active_seizure": SymptomCategory(1, "تشنجات نشطة", "Active Seizure", True),
    "severe_trauma": SymptomCategory(1, "إصابة شديدة", "Severe Trauma (GSW/Stab/MVA)", True),
    "choking": SymptomCategory(1, "اختناق/شرقة", "Choking/Airway Obstruction", True),
    "anaphylaxis": SymptomCategory(1, "صدمة تحسسية", "Anaphylaxis", True),
    "poisoning_overdose": SymptomCategory(1, "تسمم/جرعة زائدة", "Poisoning/Overdose", True),
    "drowning": SymptomCategory(1, "غرق", "Drowning/Near-drowning", True),
    "severe_bleeding": SymptomCategory(1, "نزيف شديد", "Severe/Uncontrolled Bleeding", True),
    
    # ========== PHASE 2: NEW LEVEL 1 CATEGORIES (AUDIT FIX) ==========
    "ectopic_pregnancy": SymptomCategory(1, "حمل خارج الرحم", "Ectopic Pregnancy", True),
    "aortic_dissection": SymptomCategory(1, "تسلخ الأبهر", "Aortic Dissection", True),
    "sepsis": SymptomCategory(1, "تعفن دم", "Sepsis/Septic Shock", True),
    "severe_hypothermia": SymptomCategory(1, "انخفاض حرارة شديد", "Severe Hypothermia", True),
    # ========== BATCH 2 FIX: NEW LEVEL 1 CATEGORIES ==========
    "pediatric_critical": SymptomCategory(1, "طفل في حالة حرجة", "Pediatric Critical (Floppy/Unresponsive)", True),
    
    # =========== LEVEL 2: Emergent ===========
    "chest_pain_cardiac": SymptomCategory(2, "ألم صدر قلبي", "Cardiac Chest Pain"),
    "stroke_symptoms": SymptomCategory(2, "أعراض جلطة دماغية", "Stroke Symptoms (FAST+)"),
    "respiratory_distress": SymptomCategory(2, "ضيق تنفس شديد", "Severe Respiratory Distress"),
    "altered_mental_status": SymptomCategory(2, "تغير مستوى الوعي", "Altered Mental Status"),
    "suicidal_homicidal": SymptomCategory(2, "أفكار انتحارية/عدوانية", "Suicidal/Homicidal Ideation"),
    "severe_pain": SymptomCategory(2, "ألم شديد جداً", "Severe Pain (8-10/10)"),
    "obstetric_emergency": SymptomCategory(2, "طوارئ حمل/ولادة", "Obstetric Emergency"),
    "diabetic_emergency": SymptomCategory(2, "طوارئ سكر", "Diabetic Emergency (Hypo/DKA)"),
    "testicular_pain": SymptomCategory(2, "ألم خصية حاد", "Acute Testicular Pain"),
    "severe_headache": SymptomCategory(2, "صداع شديد مفاجئ", "Sudden Severe Headache"),
    "high_fever_toxic": SymptomCategory(2, "سخونية عالية مع إعياء شديد", "High Fever + Toxic Appearance"),
    "dvt_pe": SymptomCategory(2, "جلطة وريدية/رئوية", "DVT/Pulmonary Embolism"),
    "hemoptysis": SymptomCategory(2, "كحة بدم", "Hemoptysis"),
    # PHASE 2: New Level 2 category
    "mesenteric_ischemia": SymptomCategory(2, "نقص تروية الأمعاء", "Mesenteric Ischemia"),
    # ========== BATCH 2 FIX: NEW LEVEL 2 CATEGORIES ==========
    # Allergic reaction without airway signs → ESI 2 (anaphylaxis ruled out above)
    "allergic_reaction_moderate": SymptomCategory(2, "حساسية متوسطة-شديدة", "Moderate/Severe Allergic Reaction"),
    "silent_mi": SymptomCategory(2, "ذبحة صامتة", "Silent MI (Atypical Cardiac)"),
    "gi_bleed": SymptomCategory(2, "نزيف معوي", "GI Bleeding (Hematemesis/Melena)"),
    "hip_fracture": SymptomCategory(2, "كسر ورك", "Hip Fracture (Elderly Fall)"),
    "intussusception": SymptomCategory(2, "انغلاف أمعاء", "Intussusception"),
    "pediatric_meningitis": SymptomCategory(2, "التهاب سحايا أطفال", "Pediatric Meningitis Signs"),
    "pediatric_dehydration": SymptomCategory(2, "جفاف شديد أطفال", "Severe Pediatric Dehydration"),
    "pediatric_respiratory": SymptomCategory(2, "ضيق تنفس أطفال", "Pediatric Respiratory Distress"),
    "febrile_seizure": SymptomCategory(2, "تشنج حراري", "Febrile Seizure"),
    "pediatric_sepsis": SymptomCategory(2, "تعفن دم أطفال", "Pediatric Sepsis Risk"),
    "pediatric_emergency": SymptomCategory(2, "طوارئ أطفال", "Pediatric Emergency"),
    
    # =========== LEVEL 3: Urgent ===========
    "abdominal_pain_moderate": SymptomCategory(3, "ألم بطن متوسط", "Moderate Abdominal Pain"),
    "chest_pain_noncardiac": SymptomCategory(3, "ألم صدر غير قلبي", "Non-cardiac Chest Pain"),
    "moderate_dyspnea": SymptomCategory(3, "ضيق تنفس متوسط", "Moderate Dyspnea"),
    "fracture_deformity": SymptomCategory(3, "كسر/تشوه", "Fracture with Deformity"),
    "moderate_bleeding": SymptomCategory(3, "نزيف متوسط", "Moderate Bleeding"),
    "fever_with_symptoms": SymptomCategory(3, "سخونية مع أعراض", "Fever + Associated Symptoms"),
    "vomiting_dehydration": SymptomCategory(3, "قيء مع جفاف", "Vomiting with Dehydration"),
    "psychiatric_agitated": SymptomCategory(3, "حالة نفسية هائجة", "Psychiatric - Agitated"),
    "pediatric_distress": SymptomCategory(3, "طفل في ضائقة", "Pediatric Distress"),
    # PHASE 2: New Level 3 categories
    "asthma_exacerbation": SymptomCategory(3, "نوبة ربو", "Asthma Exacerbation"),
    "kidney_stone": SymptomCategory(3, "حصوة كلى", "Kidney Stone/Renal Colic"),
    
    # =========== LEVEL 4: Less Urgent ===========
    "minor_trauma": SymptomCategory(4, "إصابة بسيطة", "Minor Trauma"),
    "laceration_simple": SymptomCategory(4, "جرح بسيط يحتاج خياطة", "Simple Laceration"),
    "mild_pain": SymptomCategory(4, "ألم خفيف-متوسط", "Mild-Moderate Pain (4-6/10)"),
    "uri_symptoms": SymptomCategory(4, "أعراض برد/إنفلونزا", "URI/Flu Symptoms"),
    "uti_symptoms": SymptomCategory(4, "أعراض التهاب بولي", "UTI Symptoms"),
    "mild_allergic": SymptomCategory(4, "حساسية خفيفة", "Mild Allergic Reaction"),
    "earache": SymptomCategory(4, "ألم أذن", "Earache"),
    "sore_throat": SymptomCategory(4, "التهاب حلق", "Sore Throat"),
    "mild_gi": SymptomCategory(4, "أعراض معوية خفيفة", "Mild GI Symptoms"),
    "back_pain_chronic": SymptomCategory(4, "ألم ظهر مزمن", "Chronic Back Pain"),
    "headache_mild": SymptomCategory(4, "صداع خفيف", "Mild Headache"),
    "eye_complaint": SymptomCategory(4, "شكوى عين", "Eye Complaint"),
    "dental": SymptomCategory(4, "مشكلة أسنان", "Dental Problem"),
    "skin_fungal": SymptomCategory(4, "فطريات جلدية", "Skin Fungal Infection"),
    "hiccups": SymptomCategory(4, "زغطة", "Hiccups"),
    # PHASE 2: New Level 4 categories
    "ankle_sprain": SymptomCategory(4, "التواء كاحل", "Ankle Sprain"),
    "insect_bite": SymptomCategory(4, "قرصة حشرة", "Insect Bite"),
    # Gemini-expanded Egyptian categories
    "dental_pain": SymptomCategory(4, "ألم أسنان", "Dental Pain"),
    "burn_minor": SymptomCategory(4, "حرق بسيط", "Minor Burn"),
    "musculoskeletal": SymptomCategory(4, "عضلات ومفاصل", "Musculoskeletal Pain"),
    "skin_wound": SymptomCategory(4, "خراج أو جرح ملوث", "Abscess / Wound Infection"),
    "panic_anxiety": SymptomCategory(3, "نوبة هلع", "Panic / Anxiety Attack"),
    
    # =========== LEVEL 5: Non-Urgent ===========
    "prescription_refill": SymptomCategory(5, "تجديد روشتة", "Prescription Refill"),
    "minor_complaint": SymptomCategory(5, "شكوى بسيطة", "Minor Complaint"),
    "chronic_stable": SymptomCategory(5, "حالة مزمنة مستقرة", "Stable Chronic Condition"),
    "suture_removal": SymptomCategory(5, "فك غرز", "Suture Removal"),
    "medical_certificate": SymptomCategory(5, "شهادة طبية", "Medical Certificate Request"),
    # PHASE 2: New Level 5 categories
    "wound_check": SymptomCategory(5, "متابعة جرح", "Wound Check"),
    "rash_minor": SymptomCategory(5, "طفح بسيط", "Minor Rash"),
    
    # =========== DEFAULT: Requires Assessment ===========
    "unclear": SymptomCategory(3, "يحتاج تقييم", "Requires Clinical Assessment"),
}


# =============================================================================
# NEWS2 SCORING TABLES
# =============================================================================
# Reference: Royal College of Physicians, NEWS2 2017
# https://www.rcplondon.ac.uk/projects/outputs/national-early-warning-score-news-2
#
# NEWS2 Score Interpretation:
# - 0: No risk → Triage Level 5
# - 1-4: Low risk → Triage Level 4
# - 5-6: Medium risk → Triage Level 3
# - 7+ or 3 in single parameter: High risk → Triage Level 2
#
# AUDIT FIX: Added SpO2 Scale 2, Supplemental O2, New Confusion, Pediatric Vitals

@dataclass
class NEWS2Result:
    """Result of NEWS2 scoring calculation"""
    total_score: int
    has_extreme_value: bool  # Any parameter scored 3
    component_scores: Dict[str, int]
    missing_vitals: List[str]
    alerts_ar: List[str]
    alerts_en: List[str]
    triage_level: int  # Derived from NEWS2 score


class VitalSignsValidator:
    """Validate required vital signs and detect out-of-range entries."""

    REQUIRED_VITALS = ["hr", "sbp", "dbp", "rr", "spo2", "temp", "consciousness"]

    RANGES = {
        "hr": (20, 250),
        "sbp": (50, 250),
        "dbp": (20, 150),
        "rr": (4, 60),
        "spo2": (50, 100),
        "temp": (30.0, 45.0),
        "blood_glucose": (20, 1000),
    }

    BYPASS_ALLOWED = {
        "cardiac_arrest",
        "severe_trauma",
        "active_seizure",
        "severe_bleeding",
        "respiratory_arrest",
        "anaphylaxis",
        "drowning",
    }

    BYPASS_KEYWORDS = [
        "cardiac arrest",
        "not breathing",
        "respiratory arrest",
        "unconscious",
        "active seizure",
        "massive hemorrhage",
        "توقف القلب",
        "توقف التنفس",
        "مش بيتنفس",
        "فاقد الوعي",
        "تشنج",
        "نزيف شديد",
    ]

    @staticmethod
    def normalize_vitals(vitals: Dict[str, Any]) -> Dict[str, Any]:
        data = dict(vitals or {})
        if "bp_systolic" in data and "sbp" not in data:
            data["sbp"] = data.get("bp_systolic")
        if "bp_diastolic" in data and "dbp" not in data:
            data["dbp"] = data.get("bp_diastolic")
        if "temperature" in data and "temp" not in data:
            data["temp"] = data.get("temperature")
        # Accept Fahrenheit temperature payloads and normalize to Celsius.
        raw_temp = data.get("temp")
        try:
            if raw_temp is not None:
                temp_value = float(raw_temp)
                if 80.0 <= temp_value <= 120.0:
                    data["temp"] = round((temp_value - 32.0) * 5.0 / 9.0, 1)
        except (TypeError, ValueError):
            pass
        return data

    @staticmethod
    def validate(
        vitals: Dict[str, Any],
        complaint_text: str = "",
        extracted_features: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        normalized = VitalSignsValidator.normalize_vitals(vitals)
        category = (extracted_features or {}).get("category", "")
        category = str(category or "").strip().lower()
        complaint_l = str(complaint_text or "").lower()

        bypass = category in VitalSignsValidator.BYPASS_ALLOWED or any(
            token in complaint_l for token in VitalSignsValidator.BYPASS_KEYWORDS
        )
        if bypass:
            return {
                "valid": True,
                "bypass_allowed": True,
                "temporary_esi": 1,
                "message": "Life-threatening presentation - vitals can be completed during resuscitation",
                "normalized_vitals": normalized,
            }

        missing = []
        for field in VitalSignsValidator.REQUIRED_VITALS:
            value = normalized.get(field)
            if value is None or (isinstance(value, str) and value.strip() == ""):
                missing.append(field)

        if missing:
            return {
                "valid": False,
                "bypass_allowed": False,
                "errors": [
                    {
                        "type": "missing_vitals",
                        "fields": missing,
                        "message": f"Missing required vital signs: {', '.join(missing)}",
                    }
                ],
                "warnings": [],
                "normalized_vitals": normalized,
            }

        errors: List[Dict[str, Any]] = []
        warnings: List[Dict[str, Any]] = []
        for field, (min_v, max_v) in VitalSignsValidator.RANGES.items():
            if field not in normalized or normalized.get(field) in (None, ""):
                continue
            try:
                value = float(normalized[field])
            except (TypeError, ValueError):
                errors.append(
                    {
                        "type": "invalid_value",
                        "field": field,
                        "message": f"Invalid {field} value",
                    }
                )
                continue
            if value < min_v or value > max_v:
                warnings.append(
                    {
                        "type": "out_of_range",
                        "field": field,
                        "value": value,
                        "range": [min_v, max_v],
                        "message": f"{field} ({value}) outside valid range ({min_v}-{max_v})",
                    }
                )

        hr = normalized.get("hr")
        sbp = normalized.get("sbp")
        try:
            if hr is not None and sbp is not None and float(hr) > 120 and float(sbp) < 90:
                warnings.append(
                    {
                        "type": "shock_indicators",
                        "message": "High HR + Low BP may indicate shock",
                        "severity": "critical",
                    }
                )
        except Exception:
            pass

        return {
            "valid": len(errors) == 0,
            "bypass_allowed": False,
            "errors": errors,
            "warnings": warnings,
            "normalized_vitals": normalized,
        }


def calculate_news2_plus(news2_result: NEWS2Result, vitals: Any) -> Dict[str, Any]:
    """
    Extended NEWS2 scoring with optional blood glucose contribution.
    Blood glucose input is expected in mg/dL.
    """
    bg_mgdl = getattr(vitals, "blood_glucose", None)
    glucose_score = 0
    glucose_category = "not_measured"

    if bg_mgdl is not None:
        try:
            bg_mgdl = float(bg_mgdl)
            bg_mmol = bg_mgdl / 18.0
            if bg_mmol < 3.0:
                glucose_score = 3
                glucose_category = "severe_hypoglycemia"
            elif bg_mmol < 4.0:
                glucose_score = 2
                glucose_category = "hypoglycemia"
            elif bg_mmol < 6.0:
                glucose_score = 1
                glucose_category = "abnormal_low"
            elif bg_mmol > 15.0:
                glucose_score = 1
                glucose_category = "hyperglycemia"
            else:
                glucose_score = 0
                glucose_category = "normal"
        except (TypeError, ValueError):
            glucose_score = 0
            glucose_category = "invalid"

    total = int(news2_result.total_score) + int(glucose_score)
    triage_level = news2_result.triage_level
    if total >= 10:
        triage_level = 1
    elif total >= 7 or news2_result.has_extreme_value:
        triage_level = 2
    elif total >= 5:
        triage_level = 3
    elif total >= 1:
        triage_level = 4
    else:
        triage_level = 5

    return {
        "news2_base": int(news2_result.total_score),
        "glucose_score": int(glucose_score),
        "news2_plus_total": int(total),
        "glucose_measured": bg_mgdl is not None,
        "glucose_value_mgdl": bg_mgdl,
        "glucose_value_mmol": round(bg_mgdl / 18.0, 2) if bg_mgdl is not None else None,
        "glucose_category": glucose_category,
        "triage_level": triage_level,
    }


def check_glucose_red_flags(vitals: Any, patient_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Check glucose-specific red flags."""
    flags: List[Dict[str, Any]] = []
    bg = getattr(vitals, "blood_glucose", None)

    if bg is None:
        # If glucose is not measured, suggest it for presentations where bedside glucose
        # is clinically important and can change urgency.
        symptoms = [str(item).lower() for item in (patient_data.get("extracted_symptoms") or [])]
        complaint_text = str(
            patient_data.get("chief_complaint_text")
            or patient_data.get("chief_complaint")
            or patient_data.get("complaint")
            or ""
        ).lower()
        joined = " ".join(symptoms + [complaint_text])
        recommend_tokens = [
            "altered mental",
            "confusion",
            "seizure",
            "weakness",
            "fatigue",
            "syncope",
            "sepsis",
            "تغير الوعي",
            "تشوش",
            "تشنج",
            "ضعف",
            "إغماء",
            "تعفن",
        ]
        if any(token in joined for token in recommend_tokens):
            flags.append(
                {
                    "type": "glucose_recommended",
                    "min_esi": 3,
                    "alert": "Blood glucose measurement recommended for this presentation",
                    "action": "Check bedside glucose now",
                    "icd10": "",
                }
            )
        return flags

    try:
        bg = float(bg)
    except (TypeError, ValueError):
        return flags

    comorbidities = [str(item).lower() for item in (patient_data.get("comorbidities") or [])]
    has_diabetes = any("diabet" in item or "سكري" in item for item in comorbidities)

    if bg < 54:
        flags.append(
            {
                "type": "severe_hypoglycemia",
                "min_esi": 2,
                "alert": "Critical hypoglycemia - immediate intervention required",
                "action": "IV dextrose + neuro assessment",
                "icd10": "E16.2",
            }
        )
    if bg > 250 and has_diabetes:
        flags.append(
            {
                "type": "dka_concern",
                "min_esi": 2,
                "alert": "Severe hyperglycemia in diabetic - possible DKA",
                "action": "Obtain ABG, BMP, urinalysis, ketones",
                "icd10": "E10.10",
            }
        )
    if bg > 600:
        flags.append(
            {
                "type": "hhs_concern",
                "min_esi": 2,
                "alert": "Extreme hyperglycemia - possible HHS",
                "action": "Aggressive fluid resuscitation, electrolyte monitoring",
                "icd10": "E11.01",
            }
        )

    return flags


class ESI5Criteria:
    """Strict eligibility criteria for ESI 5 assignments."""

    APPROVED_CATEGORIES = {
        "medication_refill",
        "prescription_refill",
        "prescription_renewal",
        "routine_followup",
        "minor_uri",
        "stable_rash",
        "minor_sprain_48h",
        "cast_check",
        "chronic_stable_pain",
        "administrative_issue",
        "minor_complaint",
        "chronic_stable",
        "suture_removal",
        "wound_check",
        "rash_minor",
    }

    HIGH_RISK_COMORBIDITY_TOKENS = {
        "active_cancer",
        "immunocomprom",
        "dialysis",
        "unstable_angina",
        "recent_surgery",
    }

    CONCERNING_MODIFIERS = ("severe", "acute", "sudden", "worsening", "شديد", "حاد")

    @staticmethod
    def is_eligible(patient_data: Dict[str, Any], news2_plus_total: int, category: str) -> Dict[str, Any]:
        age = float(patient_data.get("age") or 0)
        complaint = str(
            patient_data.get("chief_complaint_text")
            or patient_data.get("chief_complaint")
            or patient_data.get("complaint")
            or ""
        ).lower()
        comorbidities = [str(item).lower() for item in (patient_data.get("comorbidities") or [])]
        pain_score = patient_data.get("pain_scale")
        if pain_score is None:
            pain_score = (patient_data.get("vitals") or {}).get("pain_score")
        try:
            pain_score = float(pain_score) if pain_score is not None else 0.0
        except (TypeError, ValueError):
            pain_score = 0.0

        if age < 18 or age > 65:
            return {"eligible": False, "reason": "age_out_of_range", "recommended_esi": 4}
        # NEWS2 ≤ 1 is acceptable for ESI 5 — a single point from a borderline
        # vital (e.g., temp 37.6°C) is not clinically significant for non-acute
        # presentations like medication refills or suture removals.
        if news2_plus_total > 1:
            return {"eligible": False, "reason": "abnormal_vitals", "recommended_esi": 4}
        if pain_score > 2:
            return {"eligible": False, "reason": "significant_pain", "recommended_esi": 4}
        if any(any(token in item for token in ESI5Criteria.HIGH_RISK_COMORBIDITY_TOKENS) for item in comorbidities):
            return {"eligible": False, "reason": "high_risk_comorbidities", "recommended_esi": 4}
        if category not in ESI5Criteria.APPROVED_CATEGORIES:
            return {"eligible": False, "reason": "complaint_requires_evaluation", "recommended_esi": 4}
        if any(token in complaint for token in ESI5Criteria.CONCERNING_MODIFIERS):
            return {"eligible": False, "reason": "concerning_severity_modifiers", "recommended_esi": 4}

        return {"eligible": True, "reason": "meets_all_esi5_criteria", "confidence": "high"}


# =============================================================================
# PEDIATRIC VITAL SIGN THRESHOLDS (AUDIT FIX - CRITICAL)
# =============================================================================
# Reference: PALS Guidelines, Pediatric Advanced Life Support
# Using adult thresholds for children is clinically dangerous!
#
# Format: (min_age_years, max_age_years): (normal_hr_low, normal_hr_high)

PEDIATRIC_HR_THRESHOLDS = {
    (0, 0.08): (100, 205),      # 0-1 month (neonate)
    (0.08, 0.25): (100, 180),   # 1-3 months
    (0.25, 1): (100, 160),      # 3-12 months (infant)
    (1, 3): (90, 150),          # 1-3 years (toddler)
    (3, 6): (80, 140),          # 3-6 years (preschool)
    (6, 12): (70, 120),         # 6-12 years (school age)
    (12, 18): (60, 100),        # 12-18 years (adolescent)
}

PEDIATRIC_RR_THRESHOLDS = {
    (0, 1): (30, 60),           # 0-12 months
    (1, 3): (24, 40),           # 1-3 years
    (3, 6): (22, 34),           # 3-6 years
    (6, 12): (18, 30),          # 6-12 years
    (12, 18): (12, 20),         # 12-18 years (near adult)
}

# Pediatric fever thresholds by age (ESI v4, Chapter 5)
# Fever in young infants is ALWAYS high-risk
PEDIATRIC_FEVER_RISK = {
    (0, 0.08): 2,    # <28 days + fever = Level 2 (sepsis risk)
    (0.08, 0.25): 2, # 28-90 days + fever ≥38°C = Level 2-3
    (0.25, 3): 3,    # 3mo-3yr + fever = Level 3 (febrile illness)
}


def get_pediatric_hr_range(age_years: float) -> Tuple[int, int]:
    """
    Get normal heart rate range for a pediatric patient.
    Returns (low, high) or None if adult thresholds should be used.
    """
    for (min_age, max_age), (hr_low, hr_high) in PEDIATRIC_HR_THRESHOLDS.items():
        if min_age <= age_years < max_age:
            return (hr_low, hr_high)
    return None  # Use adult thresholds


def get_pediatric_rr_range(age_years: float) -> Tuple[int, int]:
    """
    Get normal respiratory rate range for a pediatric patient.
    Returns (low, high) or None if adult thresholds should be used.
    """
    for (min_age, max_age), (rr_low, rr_high) in PEDIATRIC_RR_THRESHOLDS.items():
        if min_age <= age_years < max_age:
            return (rr_low, rr_high)
    return None  # Use adult thresholds


def score_pediatric_hr(hr: int, age_years: float) -> Tuple[int, bool]:
    """
    Score heart rate using pediatric thresholds.
    Returns (score, is_extreme).
    
    Scoring logic:
    - Within normal range: 0
    - Mildly abnormal (10-20% outside): 1
    - Moderately abnormal (20-30% outside): 2
    - Severely abnormal (>30% outside or critical): 3
    """
    normal_range = get_pediatric_hr_range(age_years)
    if normal_range is None:
        return None  # Signal to use adult thresholds
    
    low, high = normal_range
    
    if low <= hr <= high:
        return 0, False
    
    # Calculate deviation percentage
    if hr < low:
        deviation = (low - hr) / low
    else:
        deviation = (hr - high) / high
    
    # Critical bradycardia in pediatrics
    if hr < 60 and age_years < 1:
        return 3, True  # Bradycardia in infant is emergency
    if hr < 50 and age_years < 6:
        return 3, True  # Bradycardia in young child
    
    # Score based on deviation
    if deviation > 0.30:
        return 3, True
    elif deviation > 0.20:
        return 2, False
    elif deviation > 0.10:
        return 1, False
    else:
        return 1, False  # Just outside normal


def score_pediatric_rr(rr: int, age_years: float) -> Tuple[int, bool]:
    """
    Score respiratory rate using pediatric thresholds.
    Returns (score, is_extreme).
    """
    normal_range = get_pediatric_rr_range(age_years)
    if normal_range is None:
        return None  # Signal to use adult thresholds
    
    low, high = normal_range
    
    if low <= rr <= high:
        return 0, False
    
    # Critical values
    if rr < 10:
        return 3, True  # Respiratory depression
    if rr > high * 1.5:
        return 3, True  # Severe tachypnea
    
    # Calculate deviation
    if rr < low:
        deviation = (low - rr) / low
    else:
        deviation = (rr - high) / high
    
    if deviation > 0.30:
        return 3, True
    elif deviation > 0.20:
        return 2, False
    else:
        return 1, False


class NEWS2Calculator:
    """
    NEWS2 (National Early Warning Score 2) Calculator
    
    Reference: Royal College of Physicians, 2017
    
    AUDIT FIXES IMPLEMENTED:
    1. SpO2 Scale 2 for COPD/hypercapnic patients (target 88-92%)
    2. +2 points for supplemental oxygen
    3. ACVPU consciousness scoring (A=0, C/V/P/U=3)
    4. Pediatric vital sign thresholds
    
    Parameters scored:
    - Respiratory rate (RR) - with pediatric thresholds
    - Oxygen saturation (SpO2) - Scale 1 or Scale 2
    - Systolic blood pressure (SBP)
    - Heart rate (HR) - with pediatric thresholds
    - Level of consciousness (ACVPU)
    - Temperature
    - Supplemental oxygen (+2 if on O2)
    """
    
    # NEWS2 Scoring thresholds - ADULT (Scale 1 for SpO2)
    # Format: list of (min_value, max_value, score)
    
    RR_THRESHOLDS = [
        (None, 8, 3),      # ≤8
        (9, 11, 1),        # 9-11
        (12, 20, 0),       # 12-20 (Normal)
        (21, 24, 2),       # 21-24
        (25, None, 3),     # ≥25
    ]
    
    # SpO2 Scale 1 - Most patients (target ≥96%)
    SPO2_SCALE1_THRESHOLDS = [
        (None, 91, 3),     # ≤91
        (92, 93, 2),       # 92-93
        (94, 95, 1),       # 94-95
        (96, None, 0),     # ≥96 (Normal)
    ]
    
    # SpO2 Scale 2 - COPD/Hypercapnic patients (target 88-92%)
    # AUDIT FIX: This was missing entirely
    SPO2_SCALE2_THRESHOLDS = [
        (None, 83, 3),     # ≤83 - Critical hypoxia
        (84, 85, 2),       # 84-85
        (86, 87, 1),       # 86-87
        (88, 92, 0),       # 88-92 (Target range for COPD)
        (93, 94, 1),       # 93-94 on O2 (above target)
        (95, 96, 2),       # 95-96 on O2 (significantly above)
        (97, None, 3),     # ≥97 on O2 (dangerous hyperoxia for COPD)
    ]
    
    SBP_THRESHOLDS = [
        (None, 90, 3),     # ≤90
        (91, 100, 2),      # 91-100
        (101, 110, 1),     # 101-110
        (111, 219, 0),     # 111-219 (Normal)
        (220, None, 3),    # ≥220
    ]
    
    HR_THRESHOLDS = [
        (None, 40, 3),     # ≤40
        (41, 50, 1),       # 41-50
        (51, 90, 0),       # 51-90 (Normal)
        (91, 110, 1),      # 91-110
        (111, 130, 2),     # 111-130
        (131, None, 3),    # ≥131
    ]
    
    TEMP_THRESHOLDS = [
        (None, 35.0, 3),   # ≤35.0
        (35.1, 36.0, 1),   # 35.1-36.0
        (36.1, 38.0, 0),   # 36.1-38.0 (Normal)
        (38.1, 39.0, 1),   # 38.1-39.0
        (39.1, None, 2),   # ≥39.1
    ]
    
    @staticmethod
    def _score_value(value: Optional[float], thresholds: list) -> Tuple[int, bool]:
        """
        Score a single vital sign value against thresholds.
        Returns (score, is_extreme) where is_extreme = True if score is 3
        """
        if value is None:
            return 0, False  # Missing values don't contribute to score
        
        for min_val, max_val, score in thresholds:
            in_range = True
            if min_val is not None and value < min_val:
                in_range = False
            if max_val is not None and value > max_val:
                in_range = False
            if in_range:
                return score, (score == 3)
        
        return 0, False  # Default if no range matched
    
    @staticmethod
    def calculate_news2_consciousness(consciousness: str) -> int:
        """
        NEWS2 consciousness scoring using ACVPU scale.
        Reference: NEWS2 Guidelines, Royal College of Physicians

        A (Alert) = 0 points
        C, V, P, U = 3 points each
        """
        if consciousness == "A":
            return 0
        return 3
    
    def calculate(
        self,
        vitals,
        age: float = 30,
        is_copd: bool = False,
        on_supplemental_o2: bool = False,
        consciousness: str = "A",
    ) -> NEWS2Result:
        """
        Calculate NEWS2 score from vital signs.
        
        AUDIT FIXES:
        - Uses pediatric thresholds for patients <18 years
        - Uses SpO2 Scale 2 for COPD patients
        - Adds +2 for supplemental oxygen
        - Scores ACVPU consciousness (A=0, C/V/P/U=3)
        
        Args:
            vitals: Vitals object with hr, rr, spo2, sbp, temp
            age: Patient age in years (for pediatric thresholds)
            is_copd: Use SpO2 Scale 2 (target 88-92%)
            on_supplemental_o2: Add +2 points
            consciousness: ACVPU level (A, C, V, P, U)
            
        Returns:
            NEWS2Result with scores, alerts, and derived triage level
        """
        scores = {}
        alerts_ar = []
        alerts_en = []
        missing = []
        has_extreme = False
        is_pediatric = age < 18
        
        # ===== Respiratory Rate (with pediatric thresholds) =====
        if vitals.rr is not None:
            # Try pediatric scoring first
            if is_pediatric:
                peds_result = score_pediatric_rr(vitals.rr, age)
                if peds_result is not None:
                    score, extreme = peds_result
                    scores['rr'] = score
                    has_extreme = has_extreme or extreme
                    if score >= 2:
                        normal_range = get_pediatric_rr_range(age)
                        alerts_ar.append(f"معدل التنفس غير طبيعي للطفل: {vitals.rr}/دقيقة (الطبيعي: {normal_range[0]}-{normal_range[1]})")
                        alerts_en.append(f"Abnormal pediatric RR: {vitals.rr}/min (normal: {normal_range[0]}-{normal_range[1]})")
                else:
                    # Use adult thresholds
                    score, extreme = self._score_value(vitals.rr, self.RR_THRESHOLDS)
                    scores['rr'] = score
                    has_extreme = has_extreme or extreme
                    if score >= 2:
                        alerts_ar.append(f"معدل التنفس غير طبيعي: {vitals.rr}/دقيقة")
                        alerts_en.append(f"Abnormal RR: {vitals.rr}/min")
            else:
                score, extreme = self._score_value(vitals.rr, self.RR_THRESHOLDS)
                scores['rr'] = score
                has_extreme = has_extreme or extreme
                if score >= 2:
                    alerts_ar.append(f"معدل التنفس غير طبيعي: {vitals.rr}/دقيقة")
                    alerts_en.append(f"Abnormal RR: {vitals.rr}/min")
        else:
            scores['rr'] = 0
            missing.append("RR (معدل التنفس)")
        
        # ===== Oxygen Saturation (Scale 1 or Scale 2) =====
        # AUDIT FIX: Added Scale 2 for COPD patients
        if vitals.spo2 is not None:
            if is_copd:
                # Use Scale 2 for COPD (target 88-92%)
                score, extreme = self._score_value(vitals.spo2, self.SPO2_SCALE2_THRESHOLDS)
                scores['spo2'] = score
                has_extreme = has_extreme or extreme
                if score >= 2:
                    alerts_ar.append(f"⚠️ نسبة الأكسجين (مقياس COPD): {vitals.spo2}% (الهدف: 88-92%)")
                    alerts_en.append(f"⚠️ SpO2 (COPD Scale 2): {vitals.spo2}% (target: 88-92%)")
            else:
                # Use Scale 1 (standard)
                score, extreme = self._score_value(vitals.spo2, self.SPO2_SCALE1_THRESHOLDS)
                scores['spo2'] = score
                has_extreme = has_extreme or extreme
                if score >= 2:
                    alerts_ar.append(f"نسبة الأكسجين منخفضة: {vitals.spo2}%")
                    alerts_en.append(f"Low SpO2: {vitals.spo2}%")
        else:
            scores['spo2'] = 0
            missing.append("SpO2 (نسبة الأكسجين)")
        
        # ===== Supplemental Oxygen (AUDIT FIX: +2 points) =====
        if on_supplemental_o2:
            scores['supplemental_o2'] = 2
            alerts_ar.append("⚠️ المريض على أكسجين إضافي (+2 نقاط)")
            alerts_en.append("⚠️ Patient on supplemental O2 (+2 points)")
        else:
            scores['supplemental_o2'] = 0
        
        # ===== Systolic Blood Pressure =====
        if vitals.sbp is not None:
            score, extreme = self._score_value(vitals.sbp, self.SBP_THRESHOLDS)
            scores['sbp'] = score
            has_extreme = has_extreme or extreme
            if score >= 2:
                alerts_ar.append(f"ضغط الدم غير طبيعي: {vitals.sbp} mmHg")
                alerts_en.append(f"Abnormal BP: {vitals.sbp} mmHg")
        else:
            scores['sbp'] = 0
            missing.append("SBP (ضغط الدم)")
        
        # ===== Heart Rate (with pediatric thresholds) =====
        if vitals.hr is not None:
            # Try pediatric scoring first
            if is_pediatric:
                peds_result = score_pediatric_hr(vitals.hr, age)
                if peds_result is not None:
                    score, extreme = peds_result
                    scores['hr'] = score
                    has_extreme = has_extreme or extreme
                    if score >= 2:
                        normal_range = get_pediatric_hr_range(age)
                        alerts_ar.append(f"النبض غير طبيعي للطفل: {vitals.hr}/دقيقة (الطبيعي: {normal_range[0]}-{normal_range[1]})")
                        alerts_en.append(f"Abnormal pediatric HR: {vitals.hr}/min (normal: {normal_range[0]}-{normal_range[1]})")
                else:
                    score, extreme = self._score_value(vitals.hr, self.HR_THRESHOLDS)
                    scores['hr'] = score
                    has_extreme = has_extreme or extreme
                    if score >= 2:
                        alerts_ar.append(f"النبض غير طبيعي: {vitals.hr}/دقيقة")
                        alerts_en.append(f"Abnormal HR: {vitals.hr}/min")
            else:
                score, extreme = self._score_value(vitals.hr, self.HR_THRESHOLDS)
                scores['hr'] = score
                has_extreme = has_extreme or extreme
                if score >= 2:
                    alerts_ar.append(f"النبض غير طبيعي: {vitals.hr}/دقيقة")
                    alerts_en.append(f"Abnormal HR: {vitals.hr}/min")
        else:
            scores['hr'] = 0
            missing.append("HR (النبض)")
        
        # ===== Temperature =====
        if vitals.temp is not None:
            score, extreme = self._score_value(vitals.temp, self.TEMP_THRESHOLDS)
            scores['temp'] = score
            has_extreme = has_extreme or extreme
            if score >= 2:
                alerts_ar.append(f"درجة الحرارة غير طبيعية: {vitals.temp}°C")
                alerts_en.append(f"Abnormal Temp: {vitals.temp}°C")
            
            # PEDIATRIC FEVER ALERT (ESI v4 Chapter 5)
            if is_pediatric and vitals.temp >= 38.0:
                for (min_age, max_age), risk_level in PEDIATRIC_FEVER_RISK.items():
                    if min_age <= age < max_age:
                        if risk_level == 2:
                            has_extreme = True
                            alerts_ar.append(f"🚨 سخونية في طفل صغير جداً - خطر عدوى خطيرة!")
                            alerts_en.append(f"🚨 Fever in young infant - HIGH sepsis risk!")
                        break
        else:
            scores['temp'] = 0
            missing.append("Temp (الحرارة)")
        
        # ===== Consciousness (ACVPU) =====
        acvpu = str(consciousness or "A").upper()
        if acvpu not in ["A", "C", "V", "P", "U"]:
            acvpu = "A"
        score = self.calculate_news2_consciousness(acvpu)
        scores['consciousness'] = score
        if score == 3:
            has_extreme = True
            alerts_ar.append(f"مستوى الوعي منخفض: ACVPU {acvpu}")
            alerts_en.append(f"Reduced consciousness: ACVPU {acvpu}")
        
        # ===== Calculate Total Score =====
        total_score = sum(scores.values())
        
        # Add warning for missing vitals
        if len(missing) >= 3:
            alerts_ar.append(f"⚠️ تحذير: {len(missing)} علامات حيوية غير مسجلة")
            alerts_en.append(f"⚠️ Warning: {len(missing)} vital signs not recorded")
        
        # ===== Derive Triage Level from NEWS2 Score =====
        # Reference: NEWS2 Clinical Response Thresholds (RCP 2017)
        # AUDIT FIX: "3 in single parameter" also triggers Level 3 minimum
        if total_score >= 10:
            triage_level = 1  # Moderate-high score for L1 Resuscitation (user preference)
        elif total_score >= 7 or has_extreme:
            triage_level = 2  # High clinical risk - Emergent
        elif total_score >= 5:
            triage_level = 3  # Medium clinical risk - Urgent
        elif total_score >= 1:
            triage_level = 4  # Low clinical risk - Less Urgent
        else:
            triage_level = 5  # Minimal risk - Non-Urgent
        
        return NEWS2Result(
            total_score=total_score,
            has_extreme_value=has_extreme,
            component_scores=scores,
            missing_vitals=missing,
            alerts_ar=alerts_ar,
            alerts_en=alerts_en,
            triage_level=triage_level
        )



# =============================================================================
# AI SYMPTOM CLASSIFIER (Constrained Output)
# =============================================================================
# Reference: Rajkomar A, Dean J, Kohane I. "Machine Learning in Medicine."
# NEJM 2019;380(14):1347-1358.
#
# "Classification tasks with defined output categories are more reliable
# and auditable than open-ended generation tasks in clinical settings."

class AISymptomClassifier:
    """
    Constrained AI classifier for Arabic/English symptom categorization.
    
    CRITICAL DESIGN PRINCIPLE:
    - AI ONLY classifies text into predefined categories
    - AI NEVER decides triage level
    - AI NEVER generates free-text clinical reasoning
    - Output is constrained to one of ~40 category IDs
    
    This follows WHO 2021 AI Ethics Guidelines (Chapter 6) for
    constrained outputs in healthcare AI systems.
    """
    
    @staticmethod
    def _offline_mode_enabled() -> bool:
        return str(os.getenv("TRIAGE_OFFLINE_MODE", "false")).strip().lower() in {"1", "true", "yes"}

    def __init__(self):
        # AI extraction is handled by ai_service.py (Vertex AI).
        # This classifier runs keyword-only in the deterministic engine.
        self.model = None
        self._genai_loaded = False

        # Build category list for prompt
        self.category_list = list(SYMPTOM_CATEGORIES.keys())
        self.category_descriptions = {
            k: f"{v.name_ar} / {v.name_en}"
            for k, v in SYMPTOM_CATEGORIES.items()
        }

        self._failure_count = 0
        self._failure_threshold = 3
        self._circuit_open_until = 0
        self._cooldown_seconds = 60
        self.last_extraction_method = "keyword_offline"

        # Lazy semantic matcher (EgyBERT offline). Instantiate only when needed.
        self._egybert_matcher = None
        self._egybert_unavailable = False

    def _get_egybert_matcher(self):
        # Performance/safety guard: never touch EgyBERT outside explicit offline mode.
        if not self._offline_mode_enabled():
            return None
        if self._egybert_unavailable:
            return None
        if self._egybert_matcher is not None:
            return self._egybert_matcher

        import_started = time.perf_counter()
        try:
            from egybert_matcher import EgyBertOfflineMatcher
        except Exception:
            try:
                from backend.egybert_matcher import EgyBertOfflineMatcher
            except Exception as import_exc:
                print(f"[EgyBERT] Matcher import unavailable: {import_exc}")
                self._egybert_unavailable = True
                return None

        print(
            f"[Timing] EgyBERT import prepared in {(time.perf_counter() - import_started):.3f}s",
            flush=True,
        )
        init_started = time.perf_counter()
        try:
            self._egybert_matcher = EgyBertOfflineMatcher()
            print(
                f"[Timing] EgyBERT model loaded in {(time.perf_counter() - init_started):.3f}s",
                flush=True,
            )
            return self._egybert_matcher
        except Exception as init_exc:
            print(f"[EgyBERT] Matcher init failed: {init_exc}")
            self._egybert_unavailable = True
            return None

    def _semantic_offline_match(self, text: str) -> Optional[str]:
        matcher = self._get_egybert_matcher()
        if matcher is None:
            return None

        match_started = time.perf_counter()
        try:
            result = matcher.match(text)
        except Exception as match_exc:
            print(f"[EgyBERT] Semantic match failed: {match_exc}")
            return None
        print(
            f"[Timing] EgyBERT semantic match in {(time.perf_counter() - match_started):.3f}s",
            flush=True,
        )

        candidate_category = str(result.get("category", "")).strip()
        if candidate_category and candidate_category != "unknown" and candidate_category in SYMPTOM_CATEGORIES:
            self.last_extraction_method = "egybert_offline"
            return candidate_category
        return None
    
    def _ensure_model_loaded(self):
        """No-op. AI extraction is handled by ai_service.py (Vertex AI)."""
        pass
    
    def _is_circuit_open(self) -> bool:
        """Check if circuit breaker is open (AI calls disabled temporarily)."""
        import time
        if self._failure_count >= self._failure_threshold:
            if time.time() < self._circuit_open_until:
                return True
            # Cooldown expired, allow one retry (half-open state)
            self._failure_count = self._failure_threshold - 1
        return False
    
    def _record_failure(self):
        """Record an AI failure and potentially open the circuit."""
        import time
        self._failure_count += 1
        if self._failure_count >= self._failure_threshold:
            self._circuit_open_until = time.time() + self._cooldown_seconds
            print(f"[Circuit Breaker] AI disabled for {self._cooldown_seconds}s after {self._failure_count} failures")
    
    def _record_success(self):
        """Record a successful AI call and reset the failure counter."""
        self._failure_count = 0
    
    def classify(self, complaint_text: str, age: float = 30, gender: str = "male") -> str:
        """
        Classify a chief complaint into one of the predefined categories.
        
        Args:
            complaint_text: Free-text complaint in Arabic or English
            age: Patient age (for context)
            gender: Patient gender (for context)
            
        Returns:
            Category ID string (e.g., "chest_pain_cardiac", "minor_trauma")
            Returns "unclear" if classification fails or is uncertain
        """
        # ===== PERFORMANCE FIX: Lazy load model on first use =====
        self._ensure_model_loaded()
        
        if not self.model or self.model == "deferred":
            return self._fallback_keyword_match(complaint_text)
        
        # ===== PERFORMANCE FIX: Check circuit breaker =====
        if self._is_circuit_open():
            return self._fallback_keyword_match(complaint_text)
        
        # Build the classification prompt
        categories_formatted = "\n".join([
            f"- {cat_id}: {desc}" 
            for cat_id, desc in self.category_descriptions.items()
        ])
        
        prompt = f"""أنت نظام تصنيف طبي. مهمتك تصنيف شكوى المريض إلى واحدة فقط من الفئات المحددة.

المريض:
- العمر: {age} سنة
- الجنس: {gender}
- الشكوى: {complaint_text}

الفئات المتاحة:
{categories_formatted}

التعليمات:
1. اختر الفئة الأكثر مطابقة للشكوى
2. إذا الشكوى خطيرة أو غير واضحة، اختر فئة أعلى خطورة
3. أجب باسم الفئة فقط (category ID) بدون أي شرح

الإجابة:"""

        try:
            response = self.model.generate_content(prompt)
            category = response.text.strip().lower().replace(" ", "_")
            
            # Remove any markdown or extra characters
            category = category.replace("`", "").replace("*", "").strip()
            
            # Validate against known categories
            if category in self.category_list:
                self.last_extraction_method = "gemini_online"
                self._record_success()  # Reset circuit breaker on success
                return category
            
            # Try fuzzy matching for close matches
            for known_cat in self.category_list:
                if known_cat in category or category in known_cat:
                    self.last_extraction_method = "gemini_online"
                    self._record_success()  # Reset circuit breaker on success
                    return known_cat
            
            # Default to unclear if no match
            print(f"AI returned unknown category: '{category}'. Defaulting to 'unclear'")
            self.last_extraction_method = "gemini_online"
            return "unclear"
            
        except Exception as e:
            print(f"AI Classification Error: {e}")
            self._record_failure()  # Record failure for circuit breaker
            return self._fallback_keyword_match(complaint_text)
    
    def _fallback_keyword_match(self, text: str) -> str:
        """
        Fallback keyword matching when AI is unavailable.
        Uses dynamic keyword database if available, otherwise static keywords.
        """
        self.last_extraction_method = "keyword_offline"
        text_lower = text.lower()
        normalized_text = text_lower.replace("أ", "ا")

        # Strip negated phrases to prevent false keyword matches.
        # Clinical vignettes contain "denies X, Y, Z" where X/Y/Z should
        # not trigger keyword classification.
        #
        # IMPORTANT: We only strip known benign denial terms, NOT
        # everything to the sentence boundary.  A greedy sentence-level
        # strip would delete true-positive symptoms that follow a comma
        # (e.g., "denies fever, sudden testicular pain" must keep the
        # high-risk phrase).
        normalized_text = _NEGATION_RE.sub('', normalized_text)
        normalized_text = _NO_BENIGN_RE.sub('', normalized_text)
        text_lower = _NEGATION_RE.sub('', text_lower)
        text_lower = _NO_BENIGN_RE.sub('', text_lower)
        # Arabic negation stripping — remove denied symptom phrases so that
        # downstream keyword matching does not false-positive on negated terms.
        # E.g. "بينفي أي سخونية، رعشة، إسهال" → strip the whole denied list.
        normalized_text = _AR_NEGATION_RE.sub('', normalized_text)
        text_lower = _AR_NEGATION_RE.sub('', text_lower)
        # Strip medication allergy history — "حساسية من X" (allergy to drug)
        # is medical history, NOT an allergic reaction complaint.
        normalized_text = _AR_MED_ALLERGY_RE.sub('', normalized_text)
        text_lower = _AR_MED_ALLERGY_RE.sub('', text_lower)

        # Guardrail: abdominal pain + fever is a high-risk combination (ESI 2 pathway).
        # NOTE: "temp" removed — it false-positives on "temperature 98.3" in
        # clinical vignettes.  Use explicit fever terms only.
        # NOTE: "حرارة" must be checked against normal-temp negation to avoid
        # false-positives on "وحرارة 37.4 مئوية" (vitals reporting).
        fever_tokens = ["سخونية", "حمى", "fever", "febrile", "high fever"]
        _has_ar_harara = "حرارة" in normalized_text and not _AR_NORMAL_TEMP_RE.search(normalized_text)
        abdominal_tokens = ["بطني", "وجع بطن", "الم بطن", "ألم بطن", "stomach pain", "abdominal pain", "مغص"]
        if (any(token in normalized_text for token in fever_tokens) or _has_ar_harara) and any(
            token in normalized_text for token in abdominal_tokens
        ):
            return "high_fever_toxic"

        # Guardrail: fever + constitutional symptoms (night sweats, weight loss,
        # rigors) = infection / malignancy pathway → ESI 2 (high_fever_toxic).
        # This catches Arabic "سخونية تروح وتيجي وعرق بالليل" (episodic fevers
        # + night sweats) which indicates serious systemic illness.
        _constitutional_tokens = [
            "night sweat", "عرق بالليل", "عرق ليلي",
            "rigors", "رعشة", "بيترعش",
            "weight loss", "نقص وزن", "خس", "وزنه قل",
        ]
        _has_fever_signal_for_const = (
            any(token in normalized_text for token in fever_tokens) or _has_ar_harara
        )
        if _has_fever_signal_for_const and any(
            token in normalized_text for token in _constitutional_tokens
        ):
            return "high_fever_toxic"

        # Guardrail: atypical ACS / silent MI often presents as GI discomfort + sweating/fatigue.
        silent_mi_gi_tokens = [
            "indigestion",
            "epigastr",
            "heartburn",
            "dyspepsia",
            "عسر هضم",
            "سوء هضم",
            "حرقان",
            "فم المعدة",
            "فم المعده",
            "المعده",
        ]
        silent_mi_signal_tokens = [
            "عرقان",
            "عرق",
            "sweat",
            "diaphores",
            "fatigue",
            "تعب",
            "ارهاق",
            "إرهاق",
            "هبطان",
            "ضعف",
            "weak",
        ]
        chest_discomfort_tokens = [
            "chest pain",
            "chest discomfort",
            "burning chest",
            "chest burning",
            "angina",
            "ألم صدر",
            "الم صدر",
            "وجع صدر",
            "وجع في الصدر",
            "وجع في صدرها",
            "وجع في صدره",
            "وجع في صدري",
            "حرقان صدر",
            "حارق بالصدر",
            "ضغط على الصدر",
            "ضيقة في الصدر",
        ]
        has_silent_mi_gi = any(token in normalized_text for token in silent_mi_gi_tokens)
        has_silent_mi_signal = any(token in normalized_text for token in silent_mi_signal_tokens)
        has_chest_discomfort = any(token in normalized_text for token in chest_discomfort_tokens)
        if has_silent_mi_gi and (has_silent_mi_signal or has_chest_discomfort):
            return "silent_mi"
        if has_chest_discomfort:
            return "chest_pain_cardiac"

        # ══════════════════════════════════════════════════════════════════════
        # PRE-KEYWORD GUARDRAILS  (run before any keyword/DB lookup)
        # These catch high-acuity patterns that need whole-word matching or
        # multi-signal logic that the simple substring keyword lists can't do.
        # ══════════════════════════════════════════════════════════════════════

        # ── ICH / intracranial hemorrhage → ESI 1 ────────────────────────────
        # "ICH" is a 3-letter clinical abbreviation — substring "ich" is unsafe
        # (matches "rich", "which").  Use whole-word detection.
        _complaint_stripped = text_lower.strip().rstrip(".,;/?")
        _ich_exact = _complaint_stripped in {"ich", "?ich", "ich/", "ich transfer"}
        _ich_prefix = (
            text_lower.lstrip("? ").startswith("ich,")
            or text_lower.lstrip("? ").startswith("ich ")
            or text_lower.lstrip("? ").startswith("ich/")
        )
        _ich_inline = " ich," in text_lower or " ich " in text_lower
        _ich_longform = any(t in text_lower for t in (
            "intracranial hemorrhage", "intracranial haemorrhage",
            "intracerebral hemorrhage", "intracerebral haemorrhage",
            "brain bleed", "brain hemorrhage", "brain haemorrhage",
            "subdural hematoma", "subdural haematoma",
            "subdural hemorrhage", "subdural haemorrhage",
            "نزيف في المخ", "نزيف دماغي", "نزيف داخل الجمجمة",
        ))
        # ── SDH abbreviation (standalone) — same ESI 1 path as ICH ─────────────
        # "sdh, transfer", "sdh" etc. — word-boundary safe (no benign substring risk)
        _sdh_exact = _complaint_stripped in {"sdh", "?sdh"}
        _sdh_prefix = (
            text_lower.lstrip("? ").startswith("sdh,")
            or text_lower.lstrip("? ").startswith("sdh ")
        )
        _sdh_inline = " sdh," in text_lower or " sdh " in text_lower
        if _ich_exact or _ich_prefix or _ich_inline or _ich_longform or _sdh_exact or _sdh_prefix or _sdh_inline:
            return "unconscious"  # → ESI 1 (intracranial/subdural hemorrhage = immediate)

        # ── CVA abbreviation → stroke_symptoms (ESI 2) ───────────────────────
        # "cva" alone or leading is a safe whole-word match (no benign substrings).
        _cva_stripped = text_lower.strip().rstrip(".,;/?")
        _cva_exact = _cva_stripped in {"cva", "?cva"}
        _cva_prefix = (
            text_lower.lstrip("? ").startswith("cva,")
            or text_lower.lstrip("? ").startswith("cva ")
        )
        if _cva_exact or _cva_prefix:
            return "stroke_symptoms"  # → ESI 2 (ceiling bypass applies)

        # ── Arabic homicidal/kill threat → suicidal_homicidal (ESI 2) ─────
        _ar_homicidal = ("بيهدد يقتل", "هيقتل", "عايز يقتل",
                         "بيهدد بالقتل", "هيأذي حد")
        if any(t in text_lower for t in _ar_homicidal):
            return "suicidal_homicidal"  # → ESI 2

        # ── BRBPR (Bright Red Blood Per Rectum) → gi_bleed (ESI 2) ──────────
        if "brbpr" in text_lower or "bright red blood per rectum" in text_lower:
            return "gi_bleed"  # → ESI 2 (ceiling bypass applies)

        # ── LOC abbreviation → altered_mental_status (ESI 2) ──────────────────
        # "LOC" = Loss of Consciousness. Use anchored match like SI/CVA.
        _loc_stripped = text_lower.strip().rstrip(".,;/?")
        _loc_is_abbrev = (
            _loc_stripped in {"loc", "?loc"}
            or text_lower.lstrip("? ").startswith("loc,")
            or text_lower.lstrip("? ").startswith("loc ")
        )
        if _loc_is_abbrev:
            return "altered_mental_status"  # → ESI 2

        # ── Syncope → altered_mental_status (ESI 2) ──────────────────────────
        _syncope_tokens = (
            "syncope",
            "اغمى عليا", "اغمى عليه", "اغمي عليا", "اغمي عليه",
            "أغمى عليا", "أغمى عليه", "أغمي عليا", "أغمي عليه",
        )
        if any(t in normalized_text for t in _syncope_tokens):
            return "altered_mental_status"  # → ESI 2

        # ── Arabic AMS patterns → altered_mental_status (ESI 2) ──────────────
        # Must run BEFORE dynamic keyword DB to prevent OD/sepsis keywords
        # from routing AMS presentations to ESI 1.
        _ar_ams_early = (
            "تغيّر في الوعي", "تغير في الوعي", "تغيّر في مستوى الوعي",
            "كلامه غريب ومش عارف", "مش عارف هو فين",
            "همدان",
        )
        if any(t in text_lower for t in _ar_ams_early):
            return "altered_mental_status"  # → ESI 2

        # ── Arabic prescription refill → prescription_refill (ESI 5) ─────────
        _ar_refill = ("تجديد روشتة", "تصرف علاج", "تجديد الروشتة", "تجديد العلاج")
        if any(t in text_lower for t in _ar_refill):
            return "prescription_refill"  # → ESI 5

        # ── Arabic abdominal pain patterns → abdominal_pain_moderate (ESI 3) ─
        _ar_abd_pain = (
            "وجع أسفل البطن", "وجع اسفل البطن", "ألم أسفل البطن",
            "وجع في البطن", "ألم في البطن", "وجع بطن",
            # Extended Egyptian dialect variants
            "بطني بتوجعني", "بطني وجعاني", "البطن بتوجعني",
            "بطني مقلباني", "بطني ملخبطة", "بطني محرقاني",
            "تقلصات في بطني", "مغص جامد", "مغص مش طبيعي",
            "بطني بتقطع", "بطني فيها حاجة غلط",
            "كرشي بتوجعني", "كرشي وجعاني",  # colloquial "belly"
            "معدتي بتحرقني", "معدتي بتوجعني",
            "وجع فوق السرة", "وجع تحت السرة",
            "وجع في جنبي", "الجنب بيوجعني",
        )
        if any(t in text_lower for t in _ar_abd_pain):
            return "abdominal_pain_moderate"  # → ESI 3

        # ── Arabic negated fever guard ────────────────────────────────────────
        # If the text explicitly negates fever (بينفي سخونية), don't let
        # downstream "سخونية" substring matching trigger a fever category.
        _negated_fever_ar = ("بينفي أي سخونية", "بينفي سخونية", "مفيش سخونية",
                            "من غير سخونية", "بدون سخونية", "بتنفي سخونية",
                            "بينفي حرارة", "مفيش حرارة", "الحرارة طبيعية",
                            "مش سخن", "مش سخنة")
        if any(t in text_lower for t in _negated_fever_ar):
            # If fever is explicitly denied, fall through to non-fever paths
            pass  # Will be handled by static keywords below
        elif "سخونية" in text_lower:
            # Unqualified سخونية → fever, but check for constitutional symptoms
            _constitutional_ar = ("عرق بالليل", "نقص وزن", "خس حوالي")
            if any(t in text_lower for t in _constitutional_ar):
                return "high_fever_toxic"  # → ESI 2
            return "fever_with_symptoms"  # → ESI 3

        # ── Arabic kidney stone / renal colic → moderate pain (ESI 3) ─────
        _ar_kidney = ("مغص كلوي", "حصوة في الكلى", "حصوة", "دم في البول",
                      "حرقان في البول ودم", "وجع في جنبي ودم")
        if any(t in text_lower for t in _ar_kidney):
            return "abdominal_pain_moderate"  # → ESI 3

        # ── Arabic meningitis signals → high_fever_toxic (ESI 2) ──────────
        _ar_meningitis = ("رقبتي محجرة", "رقبته محجرة", "تصلب في الرقبة",
                          "رقبتي ناشفة", "حمى شوكية", "الرقبة واقفة")
        if any(t in text_lower for t in _ar_meningitis) and "صداع" in text_lower:
            return "high_fever_toxic"  # → ESI 2

        # ── Arabic pediatric dehydration → vomiting_dehydration (ESI 3) ───
        _ar_dehydration = ("جفاف", "شفايفه مشققة", "شفايفه ناشفة",
                           "جلده ناشف", "يافوخه هبطان", "يافوخه نزل",
                           "البيبي مش بيرضع", "مش عارف يرضع")
        if any(t in text_lower for t in _ar_dehydration):
            return "vomiting_dehydration"  # → ESI 3

        # ── Arabic asthma exacerbation → respiratory_distress (ESI 2) ─────
        _ar_asthma = ("أزمة ربو", "صدره بيزيق", "صدره بيصفر",
                      "حساسية الصدر زادت", "صدره مقفول", "نوبة ربو",
                      "البخاخة مش نافعة")
        if any(t in text_lower for t in _ar_asthma):
            return "respiratory_distress"  # → ESI 2

        # ── Arabic dyspnea → respiratory_distress (ESI 2) ────────────────
        # "نهجان" = gasping/out of breath (Egyptian), "كرشة نفس" = shortness of breath
        _ar_dyspnea = (
            "نهجان", "كرشة نفس", "بنهج", "كتمة",
        )
        if any(t in normalized_text for t in _ar_dyspnea):
            return "respiratory_distress"  # → ESI 2

        # ── Arabic sepsis pattern → sepsis (ESI 2 via ceiling) ───────────────
        if "تسمم في الدم" in text_lower or "تعفن الدم" in text_lower:
            return "sepsis"  # → category level 1 but ceiling caps to ESI 2

        # ── Reversed chest pain phrasing → chest_pain_cardiac (ESI 2) ────────
        # Korean/international ED format: "pain, chest" or "discomfort, chest"
        _chest_reversed = (
            "pain, chest", "pain chest", "discomfort, chest", "discomfort chest",
            "chest palpitation",
            "ضربات قلب سريعة", "ضربات قلب",
        )
        if any(t in text_lower for t in _chest_reversed):
            return "chest_pain_cardiac"  # → ESI 2

        # ── Unilateral limb weakness — focal neurological deficit → ESI 2 ────
        # "l weakness", "r weakness" = left/right-sided weakness = stroke sign.
        # Extended: "motor weakness", "left side motor weakness", "lt. motor weakness", etc.
        if re.match(r'^[lr]\s+weakness', text_lower.strip()):
            return "stroke_symptoms"  # → ESI 2
        _lateralized_weakness = (
            "motor weakness", "side motor weakness", "side weakness",
            "left side weakness", "right side weakness",
            "left side motor weakness", "right side motor weakness",
            "lt. side weakness", "rt. side weakness",
            "lt. motor weakness", "rt. motor weakness",
            "lt side weakness", "rt side weakness",
            "left motor weakness", "right motor weakness",
            "lower extremity paraparesis", "paraparesis",
            # Arabic stroke / lateralized weakness variants
            "ضعف في الجنب", "ضعف في جنبي",
            "ضعف حركي", "ضعف حركة",
            "تقل في جنبي",
            "ثقل في حركة",
            "مش قادر أحرك جنبي", "مش قادر احرك جنبي",
        )
        if any(t in text_lower for t in _lateralized_weakness):
            return "stroke_symptoms"  # → ESI 2

        # ── "Ped struck" — pedestrian struck by vehicle → high-energy trauma ─
        if "ped struck" in text_lower or "pedestrian hit" in text_lower:
            return "severe_trauma"  # → ESI 1

        # ── Anaphylaxis signals — airway-threatening allergic reaction → ESI 1 ─
        _anaphylaxis_signals = (
            "tongue swelling", "throat swelling", "lip swelling",
            "facial swelling", "face swelling", "swollen throat",
            "swollen tongue", "swollen lips", "angioedema",
            "throat closing", "throat tightening",
            "تورم اللسان", "تورم الحلق", "تورم الوجه", "وجهه ورم",
        )
        if any(t in text_lower for t in _anaphylaxis_signals):
            return "anaphylaxis"

        # ── GI bleeding signals → gi_bleed (ESI 2) ─────────────────────────
        # Guard: abscess complaints (خراج) should NOT be classified as GI bleed
        # even if the text incidentally contains blood/rectal tokens.
        _is_abscess = any(t in text_lower for t in ("خراج", "abscess"))
        _gi_bleed_signals = (
            "hematochezia", "melena", "bloody stool", "blood in stool",
            "rectal bleeding", "gi bleed", "gi bleeding",
            "hematemesis", "vomiting blood", "coffee ground",
            "دم نازل مع البراز", "دم مع البراز", "دم في البراز",
        )
        if not _is_abscess and any(t in text_lower for t in _gi_bleed_signals):
            return "gi_bleed"  # → ESI 2

        # ── Vaginal bleeding → obstetric_emergency (ESI 2) ──────────────────
        _vaginal_bleed_tokens = (
            "vaginal bleeding", "vaginal bleed",
            "نزيف مهبلي",
        )
        if any(t in text_lower for t in _vaginal_bleed_tokens):
            return "obstetric_emergency"  # → ESI 2

        # ── Acute dyspnea → respiratory_distress (ESI 2) ────────────────────
        # "acute dyspnea" is different from chronic dyspnea — implies acute
        # respiratory failure requiring immediate intervention.
        if "acute dyspnea" in text_lower:
            return "respiratory_distress"  # → ESI 2

        # ── Hypoglycemic/hyperglycemic signals → diabetic_emergency (ESI 2) ─
        _diabetic_signals = (
            "hypoglycemic", "hypoglycemia", "hyperglycemic", "hyperglycemia",
            "bst high", "bst low", "blood sugar high", "blood sugar low",
            "sugar high", "sugar low", "dka",
        )
        if any(t in text_lower for t in _diabetic_signals):
            return "diabetic_emergency"  # → ESI 2

        # ── Priapism → urological emergency (ESI 2) ─────────────────────────
        if "priapism" in text_lower or "erection, penile" in text_lower or "انتصاب" in normalized_text:
            return "altered_mental_status"  # → ESI 2 (urological emergency via high-acuity bucket)

        # ── Eye trauma → eye emergency (ESI 2) ──────────────────────────────
        _eye_emergency_signals = (
            "eye trauma", "hyphema", "eye injury", "globe rupture",
            "chemical eye", "eye burn",
            "خبطة في العين",
        )
        if any(t in text_lower for t in _eye_emergency_signals):
            return "altered_mental_status"  # → ESI 2 (via high-acuity bucket)

        # ── "allergic reaction" without airway signs → ESI 2 (moderate) ───────
        if "allergic reaction" in text_lower or "severe allergic" in text_lower:
            return "allergic_reaction_moderate"

        # ── SI / S/I — suicidal ideation abbreviation → ESI 2 ────────────────
        _si_stripped = text_lower.strip()
        _si_is_abbrev = (
            _si_stripped in {"si", "s/i", "s.i."}
            or _si_stripped.startswith("si,")
            or _si_stripped.startswith("s/i,")
        )
        if _si_is_abbrev:
            return "suicidal_homicidal"

        # ── Altered mental status / lethargy / somnolence → ESI 2 ────────────
        # ESI handbook: "somnolent", "lethargic", "not acting right" = ESI 1–2.
        # These appearance descriptions indicate altered consciousness that
        # vitals alone cannot capture.
        _ams_signals = (
            "somnolent", "lethargic", "lethargy", "obtunded",
            "not acting right", "not herself", "not himself",
            "listless", "floppy", "limp",
            "confused and agitated", "acutely confused",
            # Altered mental status phrases (international ED phrasing)
            "mental change", "altered mentality", "altered mental",
            "confuse mentality", "confused mentality",
            "change in mental", "change of mental",
            "loss of consciousness",
            "مش طبيعي", "مش واعي", "خامل", "مش بيرد", "مش بترد",
            "فاقد الوعي", "فاقدة الوعي",
        )
        if any(t in text_lower for t in _ams_signals):
            return "altered_mental_status"  # → ESI 2

        # ── Psychiatric emergency — threatening violence → ESI 2 ─────────────
        # ESI handbook: patient threatening to harm others or actively psychotic
        # (standing in traffic, out of control) = ESI 2 even if calm at triage.
        _psych_signals = (
            "threatening to kill", "threatening to harm",
            "out of control", "verbally and physically",
            "screaming obscenities",
            "standing in the middle of traffic", "standing in traffic",
            "acting out and threatening",
            "screaming about", "end of the world",
            # NHAMCS RFV: actively dangerous psych presentations
            "hostile behavior",
        )
        if any(t in text_lower for t in _psych_signals):
            return "suicidal_homicidal"  # → ESI 2

        # ── Substance adverse effects / acute psychosis → altered_mental_status (ESI 2)
        _substance_psych_signals = (
            "adverse effect of drug abuse",
            "adverse effect of alcohol",
            "delusions or hallucinations",
        )
        if any(t in text_lower for t in _substance_psych_signals):
            return "altered_mental_status"  # → ESI 2

        # ── Sexual assault → ESI 2 ───────────────────────────────────────────
        _sa_signals = (
            "sexually assaulted", "sexual assault", "raped", "rape victim",
            "اغتصاب", "تحرش", "اعتداء جنسي",
        )
        if any(t in text_lower for t in _sa_signals):
            return "suicidal_homicidal"  # → ESI 2 (psych/trauma emergency)

        # ── Severe pain from narrative (10/10, obvious dislocation) → ESI 2 ──
        _severe_pain_signals = (
            "10/10", "10 out of 10", "10 /10",
            "obvious dislocation", "obvious deformity",
        )
        if any(t in text_lower for t in _severe_pain_signals):
            return "severe_pain"  # → ESI 2

        # ── C-spine / backboard immobilisation → ESI 1 ───────────────────────
        # ESI handbook: patient immobilised on backboard with c-collar = high-risk.
        _cspine_signals = (
            "c-collar", "c collar", "cervical collar",
            "back board", "backboard",
            "immobilized on a", "immobilised on a",
            "spinal precautions", "spine precautions",
            "cervical immobilization", "cervical immobilisation",
        )
        if any(t in text_lower for t in _cspine_signals):
            return "severe_trauma"  # → ESI 1 (spinal precautions = high-risk)

        # ── High-energy mechanism of injury → ESI 2 ──────────────────────────
        # ESI handbook: high-speed MVC, hit by car (pediatric), multicar = ESI 2.
        _mechanism_signals = (
            "high-speed", "high speed", "multicar", "multi-car",
            "hit by a car", "hit by car", "struck by car",
            "struck by a car", "pedestrian struck",
            "ran into a tree", "ejected",
            "حادثة سير كبيرة", "سرعة عالية",
        )
        if any(t in text_lower for t in _mechanism_signals):
            return "severe_trauma"  # → ESI 1

        # ── VP shunt concern → ESI 2 ─────────────────────────────────────────
        # Ventriculoperitoneal shunt malfunction = neurosurgical emergency.
        _vpshunt_signals = (
            "ventriculoperitoneal shunt", "ventriculo-peritoneal shunt",
            "vp shunt", "v-p shunt", "shunt malfunction", "shunt may be",
            "shunt blockage", "blocked shunt",
        )
        if any(t in text_lower for t in _vpshunt_signals):
            return "pediatric_emergency"  # → ESI 2

        # ── Petechiae / purpuric rash → ESI 2 (meningococcemia risk) ────────
        _petechiae_signals = (
            "petechiae", "petechial", "purpuric", "purpura",
            "pinpoint purplish", "pinpoint rash",
            "non-blanching rash", "non blanching rash",
        )
        if any(t in text_lower for t in _petechiae_signals):
            return "pediatric_meningitis"  # → ESI 2

        # ── Compartment syndrome risk → ESI 2 ────────────────────────────────
        # Swollen extremity in cast + neurovascular compromise = time-sensitive.
        _compartment_signals = (
            "cast is cutting", "cast is too tight", "cutting off circulation",
            "no pulse distal", "pulseless distal",
            "compartment syndrome",
            "hand is really swollen", "fingers are turning",
            "hand is swollen and the cast",
            "swollen and the cast",
        )
        if any(t in text_lower for t in _compartment_signals):
            return "severe_pain"  # → ESI 2

        # ── Dysphagia with airway concern → ESI 2 ───────────────────────────
        # "Can barely swallow" + voice changes = peritonsillar abscess / epiglottitis.
        _dysphagia_airway_signals = (
            "barely swallow", "can't swallow", "cannot swallow",
            "unable to swallow", "difficulty swallowing",
            "voice is different", "muffled voice", "hot potato voice",
            "uvula deviated", "uvula is deviated", "drooling",
            "peritonsillar", "epiglottitis",
        )
        if any(t in text_lower for t in _dysphagia_airway_signals):
            return "respiratory_distress"  # → ESI 2

        # ── Neonatal / young infant alarm → ESI 1 ───────────────────────────
        # Any sick neonate (<28 days) or young infant with concerning signs.
        _neonatal_signals = (
            "week-old", "week old", "day-old", "day old",
            "newborn", "neonate", "neonatal",
        )
        _infant_concern_signals = (
            "not eating", "not interested in eating", "not feeding",
            "poor feeding", "refuses to eat", "won't eat",
            "not acting right", "fussy", "irritable",
            "mottled", "dusky", "cyanotic",
            "sunken fontanel", "fontanelle",
        )
        _has_neonatal = any(t in text_lower for t in _neonatal_signals)
        _has_infant_concern = any(t in text_lower for t in _infant_concern_signals)
        if _has_neonatal and _has_infant_concern:
            return "pediatric_critical"  # → ESI 1

        # ── Infant with sunken fontanel / listless → ESI 2 ──────────────────
        # Even beyond neonatal age, a listless infant with sunken fontanel = ESI 2.
        if "sunken fontanel" in text_lower or "fontanelle" in text_lower:
            return "pediatric_dehydration"  # → ESI 2

        # ── Diving injury + face/neck struck → ESI 1 (c-spine mechanism) ────
        _has_dive = any(t in text_lower for t in ("dove into", "diving into", "dove in"))
        _has_impact = any(t in text_lower for t in ("face struck", "hit the bottom", "struck the bottom"))
        if _has_dive and _has_impact:
            return "severe_trauma"  # → ESI 1 (c-spine mechanism)

        # Try dynamic keyword database first — but ONLY for short complaints
        # or English-dominant text. Long Arabic clinical vignettes contain too much
        # context and cause false-positive substring matches (e.g., "حساسية من
        # الدوبوتامين" matching allergic_reaction). Arabic text has proper guardrails
        # in the static keyword path below.
        _has_arabic = any('\u0600' <= ch <= '\u06FF' for ch in text_lower[:50])
        _skip_dynamic = _has_arabic and len(text_lower) > 150
        if USE_DYNAMIC_KEYWORDS and not _skip_dynamic:
            try:
                db = get_keyword_database()
                result = db.search_keyword(text_lower)
                if result:
                    category, level = result
                    return category
            except Exception as e:
                print(f"Dynamic keyword search error: {e}")
                # Fall through to static keywords

        # Semantic fallback is used only after deterministic keyword lookup fails.
        semantic_category = self._semantic_offline_match(text)
        if semantic_category:
            return semantic_category
        
        # Static fallback keywords
        # Level 1 keywords (must catch these even without AI)
        level1_keywords = {
            "unconscious": ["unconscious", "unresponsive", "فاقد الوعي", "فاقدة الوعي",
                           "مغمى عليه", "مش بيرد", "مش بترد",
                           "مش بيرد عليا", "مش واعي", "فاقد وعي",
                           # ESI Handbook Egyptian
                           "مبيفوقش خالص", "واقع من طوله ومش بيرد",
                           "لقيناه مغمى عليه", "مش بيفتح عينه"],
            "cardiac_arrest": ["cardiac arrest", "قلبه وقف", "قلبها وقف", "القلب واقف", "قلبه مش شغال",
                              "توقف في عضلة القلب", "مفيش نبض",
                              "العلامات الحيوية كلها كانت أصفار",
                              "العلامات الحيوية مكنتش محسوسة", "مكنتش محسوسة",
                              "إنعاش فوري", "انعاش فوري"],
            "respiratory_arrest": ["not breathing", "مش بيتنفس", "توقف التنفس", "مش قادر يتنفس",
                                  "جهاز تنفس صناعي",
                                  "أنبوبة حنجرية", "انبوبة حنجرية"],
            "active_seizure": ["seizure", "تشنج", "صرع", "بيترعش", "تشنجات",
                             # ESI Handbook Egyptian
                             "بيتنفض", "عينيه قلبت لورا", "طلع رغاوي",
                             "اتخشب", "نوبة صرع"],
            "choking": ["choking", "شرقان", "حاجة في زوره", "مش قادر يبلع", "شرقت", "شرق",
                       "اختناق", "مش قادرة تاخد نفس", "حاجة واقفة في زوره",
                       # ESI Handbook Egyptian
                       "بلع حاجة", "بلع لعبة"],
            "severe_trauma": ["gunshot", "stab wound", "stabbed", "stabbing", "طعن", "رصاص", "حادثة", "اتضرب",
                             "حادثة عربية", "حادث عربية", "خبطته عربية", "اتطعن",
                             # NOTE: "accident" removed — generic English "accident" in NHAMCS
                             # is a catch-all (ESI 2-5). Arabic "حادثة" kept (more specific).
                             # High-energy English accidents caught via "gunshot", "stab", etc.
                             # Vitals safety floors escalate truly critical cases.
                             # NOTE: "كسر مفتوح" removed — routed via fracture_deformity + DEFINITIVE_ESI2_SIGNALS (ESI 2)
                             "أنبوبة الصدر", "انبوبة الصدر"],
            "anaphylaxis": ["anaphylaxis", "anaphylactic", "صدمة تحسسية", "حساسية شديدة", "شفايفه ورمت",
                          # Gemini-expanded Egyptian
                          "وشي ورم", "لساني كبر في بقي", "زوري قفل",
                          "شفايفي ورمت", "جسمي كله مأكلل ومورم"],
            "poisoning_overdose": ["overdose", "poison", "تسمم", "جرعة زيادة", "جرعة زيادة متعمدة",
                                  "أخد دوا كتير",
                                  "بلع دوا", "شرب دوا", "أخد حبوب كتير", "جرعة زايدة",
                                  "محاولة انتحار", "تسمم في الدم",
                                  # Gemini-expanded Egyptian
                                  "بلع شريط برشام", "شرب كلور", "شرب كلوركس",
                                  "شرب مبيد", "أكل سم", "سم فئران",
                                  "شرب ماء نار", "بلع سم", "رشت زرع واستنشقت"],
            "drowning": ["drowning", "drown", "غرق", "غرقان", "طلعوه من المية", "وقع في المية",
                        "حمام السباحة", "البحر", "النيل", "اتغرق"],
            "severe_bleeding": ["severe bleeding", "نزيف شديد", "بينزف جامد", "دم كتير",
                               # Gemini-expanded Egyptian
                               "الدم مش بيوقف", "بينزف من بقه", "بينزف بغزارة",
                               "الجرح بيخر دم", "بتترجع دم"],
        }

        for category, keywords in level1_keywords.items():
            for kw in keywords:
                if kw in text_lower:
                    return category
        
        # Level 2 keywords
        level2_keywords = {
            "chest_pain_cardiac": ["chest pain", "pain, chest", "pain chest",
                                  "discomfort, chest", "discomfort chest", "chest discomfort",
                                  "chest palpitation",
                                  "ألم صدر", "صدري بيوجعني", "قلبي بيوجعني",
                                  "وجع في الصدر", "وجع في صدرها", "وجع في صدره",
                                  "وجع في صدري",
                                  # ESI Handbook + Gemini Egyptian
                                  "نغزة في القلب وعرق ساقع",
                                  "دبحة في الصدر", "تقل على صدري وعمال أعرق",
                                  "عرقان غرقان", "بيسمّع في دراعي"],
            "stroke_symptoms": [
                "stroke", "جلطة", "جلطة في المخ", "سكتة", "سكتة دماغية", "شلل",
                "aphasia", "dysarthria", "slurred speech", "speech difficulty",
                "can not speak", "can't speak", "cannot speak", "unable to speak",
                "difficulty speaking", "speech loss", "inability to speak", "sudden inability to speak",
                "facial droop", "face drooping",
                "one side weakness", "one sided weakness", "hemiplegia",
                # Lateralized motor weakness patterns (Korean/international ED phrasing)
                "motor weakness", "left side weakness", "right side weakness",
                "left side motor weakness", "right side motor weakness",
                "lt. side weakness", "rt. side weakness",
                "lt. motor weakness", "rt. motor weakness",
                "left motor weakness", "right motor weakness",
                "paraparesis",
                "مش قادر يتكلم", "مش قادر اتكلم", "مش قادر أتكلم", "مبقتش قادر اتكلم",
                "كلامي اتلخبط", "كلامه اتلخبط", "بيتكلم غريب", "كلامي مش واضح",
                "فقدان النطق", "فقدان الكلام", "عدم القدرة على الكلام", "عدم القدرة على التكلم",
                "لساني اتلت", "لسانه اتلت", "لساني تقيل", "لسانه تقيل",
                "وشه مايل", "وشي مايل", "نص وشه وقع", "نص وشي وقع", "وشي اتعوج",
                "نص جسمي مش بيتحرك", "نص جسمه مش بيتحرك", "ايدي مش بتتحرك", "ايده مش بتتحرك",
                # Egyptian colloquial lateralized weakness
                "ضعف في الناحية الشمال", "ضعف في الناحية اليمين",
                "الناحية الشمال مرتخية", "الناحية اليمين مرتخية",
                "مش بتحرك الناحية", "مش بيحرك الناحية",
                "رجلي مش بتتحرك", "الجنب ده كله مش بيتحرك", "ايده وقعت", "ايدي وقعت",
            ],
            "respiratory_distress": ["can't breathe", "مش عارف آخد نفسي", "ضيق تنفس",
                                    "مش قادرة آخد نفسي", "صعوبة تنفس", "مش قادر اتنفس",
                                    "تنفسه سطحي", "تنفسها سطحي",
                                    # Gemini-expanded Egyptian
                                    "بشحت النفس", "نفسي قصير", "مكتوم على نفسي",
                                    "صدري بيزيق", "نفسي بيطلع بطلوع الروح",
                                    "مش طايق الهدوم على صدري",
                                    "البخاخة مش نافعة", "الصدر قافل عليا"],
            "suicidal_homicidal": ["suicidal", "kill myself", "عايز أموت", "عايز يموت",
                                  "يقتل نفسه", "عايز يقتل نفسه", "ينتحر", "عايز ينتحر",
                                  "هيأذي نفسه", "مش عايز يعيش",
                                  "محاولة انتحار", "جرعة زيادة متعمدة",
                                  "suicidal ideation", "suicidal with plan",
                                  # Gemini-expanded Egyptian + ESI Handbook
                                  "حاسس إني لوحدي والدنيا سودة",
                                  "بلع سم عشان ينتحر",
                                  "بيهدد يقتل", "هيقتل", "عايز يقتل"],
            "obstetric_emergency": ["pregnant bleeding", "حامل بتنزف", "حامل وبتنزف",
                                   "حامل في", "حامل ونزيف", "نزيف حمل", "الحمل بينزف",
                                   # Gemini-expanded Egyptian
                                   "حامل ودم بينزل", "حامل واغمى عليها"],
            "diabetic_emergency": ["sugar low", "السكر واطي", "السكر عالي", "سكر منخفض",
                                  "عنده سكر وبيترعش", "هبوط سكر",
                                  # Gemini-expanded Egyptian
                                  "غرقان في عرقه وجسمه متلج", "مهبط خالص",
                                  "ريحة بقه زي الفاكهة", "السكر سرح منه",
                                  "ريقه ناشف وبيدلق مية"],
            "severe_headache": ["worst headache", "صداع شديد", "راسي هتنفجر", "صداع مفاجئ",
                               "دماغي هتنفجر"],
            "severe_pain": ["severe pain", "ألم شديد", "بيوجعني جدا جدا", "ألم شديد جداً",
                           "بيقطع في جسمي", "مش طايق الوجع"],
            "high_fever_toxic": ["سخونية عالية جداً", "حرارة عالية جداً", "معياش جداً",
                                "جسمي ولع نار", "جسمي ولع", "سخونية مش بتنزل",
                                "حرارتي فوق الأربعين"],
        }
        
        for category, keywords in level2_keywords.items():
            for kw in keywords:
                if kw in text_lower:
                    return category
        
        # Level 3 keywords
        # NOTE: order matters — specific categories before broad ones.
        # "abscess" must precede "bleeding" to prevent perianal/rectal
        # abscess vignettes from matching moderate_bleeding via "bloody".
        # NOTE: "حرارة" removed from fever_with_symptoms to avoid false
        # positives when Arabic text reports normal temperature in vitals
        # (e.g. "وحرارة 37.4 مئوية"). A separate negation-aware check below
        # handles "حرارة" correctly.
        level3_keywords = {
            "abdominal_pain_moderate": ["abdominal pain", "stomach pain",
                                        "ألم بطن", "بطني بتوجعني",
                                        "معدتي", "مغص", "وجع بطن",
                                        "أسفل البطن", "وجع في البطن",
                                        "ألم في البطن", "البطن بتوجعني",
                                        "بطني وجعاني", "مغص شديد"],
            "fever_with_symptoms": ["fever", "سخونية", "سخن",
                                    "جسمي حر", "حرارتي عالية"],
            "vomiting_dehydration": ["vomiting", "بيرجع", "استفراغ", "ترجيع",
                                      "بتترجع", "بيستفرغ", "رجع كتير",
                                      "جفاف", "مش بيشرب", "لسانه ناشف"],
            "fracture_deformity": ["fracture", "broken", "deformity", "كسر", "مكسور", "ملوي",
                                    "عضمه طلع", "العضمة بارزة", "رجله مكسورة",
                                    "ايده مكسورة", "كسر مفتوح",
                                    "عوجة واضحة", "شكله معووج", "العظم مش في مكانه",
                                    "دراعه اتكسر", "رجله اتكسرت"],
            "moderate_bleeding": ["bleeding", "بينزف", "نزيف", "نزيف دم",
                                  "دم بينزل", "دم كتير", "بينزف دم"],
            "pediatric_distress": ["child sick", "طفل", "ابني", "بنتي",
                                    "طفلي", "العيل", "البيبي", "الرضيع"],
            # ESI 3 — Panic/anxiety. Phrases like "خايف أموت" are colloquial
            # Egyptian panic expressions, not cardiac complaints. Placed here
            # to match SYMPTOM_CATEGORIES which maps panic_anxiety → ESI 3.
            "panic_anxiety": ["panic attack", "anxiety",
                             "خنقة في زوري", "خايف أموت",
                             "روحي بتطلع", "قلبي هيقف وحاسس بخنقة",
                             "جسمي بيترعش من غير سبب"],
        }

        for category, keywords in level3_keywords.items():
            for kw in keywords:
                if kw in text_lower:
                    return category

        # Separate negation-aware check for Arabic "حرارة" as fever signal.
        # Only triggers fever_with_symptoms when "حرارة" is NOT followed by a
        # normal value (35-37.x).
        if "حرارة" in text_lower:
            if not _AR_NORMAL_TEMP_RE.search(text_lower):
                return "fever_with_symptoms"
        
        # Level 4 keywords
        level4_keywords = {
            "minor_trauma": ["fell", "fall", "وقعت", "وقع", "اتخبط", "خبطة", "ضربة", "وارم", "ورم",
                            "اتزحلقت", "اتكعبلت", "وقعت على", "ضربني", "اتلكمت",
                            "لطشني", "خبطة خفيفة", "اترمت"],
            "laceration_simple": ["cut", "laceration", "جرح", "قطع", "خياطة", "غرز",
                                   "اتجرحت", "السكينة فاتت", "جرح مفتوح",
                                   "جرح في ايدي", "اتقطعت", "بينزف من الجرح"],
            "uri_symptoms": ["cold", "flu", "cough", "برد", "كحة", "زكام", "رشح", "انفلونزا",
                            "عطس", "نفسي مسدود", "مناخيري مسدودة",
                            "بلغم", "كحة بلغم", "كحة ناشفة", "زور حامي"],
            "sore_throat": ["sore throat", "زور", "حلق", "بلع",
                           "زوري بيوجعني", "حلقي واجعني", "مش قادر ابلع",
                           "التهاب لوز", "اللوز وارمة", "التهاب حلق"],
            "earache": ["ear pain", "earache", "ودني", "أذني",
                       "ودني بتوجعني", "وداني بتوجعني",
                       "التهاب أذن", "ودني بتنقط", "طنين"],
            "uti_symptoms": ["burning urination", "حرقان بول", "التهاب مجرى", "حرقان في البول",
                           "رايح الحمام كتير", "بول كتير", "التهاب بولي",
                           "حرقان وقت البول", "بيحرقني لما بتبول",
                           "لون البول غامق", "البول فيه ريحة"],
            "mild_allergic": ["rash", "allergy", "طفح", "حكة", "هرش",
                             "حساسية جلد", "جلدي بيحكني", "بقع حمرا",
                             "حبوب في جسمي", "ارتيكاريا", "جسمي بيهرشني"],
            "back_pain_chronic": ["back pain", "ظهري", "وجع ضهر",
                                   "ضهري بيوجعني", "ضهري واجعني",
                                   "ألم في ظهري", "ضهري مخلعني",
                                   "ضهري بيقطع", "وسطي بيوجعني"],
            "mild_gi": ["diarrhea", "إسهال", "مشي", "معدة",
                        "بطني بتمشي", "اسهال", "معدتي تعبة",
                        "غثيان", "لوعة", "حموضة", "حرقة معدة"],
            "mild_pain": ["pain", "وجع", "بيوجعني", "ألم"],
            "headache_mild": ["headache", "صداع", "راسي", "دماغي",
                              "راسي بتوجعني", "صداع نصفي", "شقيقة",
                              "دوخة", "دايخ", "دايخة", "عيني بتزغلل"],
            "eye_complaint": ["عيني", "عين", "حمرا", "مدمعة", "رمد",
                             "عيني بتوجعني", "عيني حمرا", "عيني ورمت",
                             "مش شايف كويس", "نظري ضعف", "عيني فيها حاجة"],
            # Gemini-expanded Egyptian categories
            "dental_pain": ["toothache", "tooth pain", "dental",
                           "درسي", "سنتي", "اللثة وارمة", "وجع دروس",
                           "درسي بينقح", "عصب درسي", "خراج في اللثة"],
            "burn_minor": ["burn", "burned", "حرق", "اتحرق", "اتحرقت",
                          "مية سخنة اتلقت", "جلدي اتحرق", "حرق زيت",
                          "وشه اتحرق", "جلده قبب"],
            "musculoskeletal": ["sprain", "strain", "muscle", "joint",
                               "ركبتي بتخونني", "رجلي اتلوت", "شد عضلي",
                               "رقبتي ملووحة", "كتفي تقيل", "مفاصلي بتزيق",
                               "كعب رجلي بيوجعني", "عضمي مكسر"],
            "skin_wound": ["abscess", "خراج", "دمل", "صديد",
                          "الجرح صديد", "الحتة دي قابة", "قرصة حشرة",
                          "الخياطة فكت", "خراج محتاج يتفتح"],
        }

        for category, keywords in level4_keywords.items():
            for kw in keywords:
                if kw in text_lower:
                    return category
        
        # Level 5 keywords
        level5_keywords = {
            "prescription_refill": ["refill", "prescription", "روشتة", "تجديد", "الدوا خلص", "عايز دوا",
                                    "محتاج روشتة", "الروشتة خلصت", "عايز تجديد",
                                    "محتاج دوا", "الأدوية خلصت"],
            "medical_certificate": ["certificate", "تقرير", "شهادة", "إجازة مرضية",
                                     "عايز تقرير طبي", "عايز إجازة"],
            "suture_removal": ["remove stitches", "suture removal", "فك غرز", "فك الغرز",
                               "شيل الغرز", "مواعيد الغرز"],
            "chronic_stable": ["follow up", "متابعة", "كشف", "مراجعة",
                               "عايز أتابع", "مواعيد متابعة"],
            "minor_complaint": ["check up", "فحص", "اطمن", "اطمئنان",
                                "عايز أعمل تحاليل", "عايز أشيك"],
        }
        
        for category, keywords in level5_keywords.items():
            for kw in keywords:
                if kw in text_lower:
                    return category
        
        # Default to unclear - will be triaged as Level 3 (safe default)
        return "unclear"



# =============================================================================
# DETERMINISTIC TRIAGE ENGINE
# =============================================================================
# Main engine combining NEWS2 + ESI with constrained AI classification
#
# Decision Flow (PHASE 2 AUDIT FIX - ESI v4 Compliant):
# 1. Check for Level 1 (Resuscitation) - Immediate life-saving intervention
# 2. Check for Level 2 (Emergent) - High risk, altered mental status, severe pain
# 3. Calculate NEWS2 score from vitals
# 4. Classify complaint using AI (constrained to predefined categories)
# 5. Estimate resources needed (ESI Decision Points C-E)
# 6. Apply clinical modifiers
# 7. Final level based on resource prediction for Levels 3-5

@dataclass
class DeterministicTriageResult:
    """Complete triage result with full decision audit trail"""
    # Final Result
    final_level: int
    extraction_method: str
    color_code: str
    label_ar: str
    label_en: str
    
    # Decision Components (for auditability)
    news2_score: int
    news2_level: int
    category: str
    category_ar: str
    category_en: str
    category_level: int
    modifiers_applied: List[str]
    
    # Clinical Information
    alerts_ar: List[str]
    alerts_en: List[str]
    missing_vitals: List[str]
    
    # Decision Path (for documentation/audit)
    decision_path: str
    decision_path_ar: str
    decision_path_en: str
    ai_used: bool
    
    # Time recommendations
    time_to_physician: str
    recommended_action_ar: str
    recommended_action_en: str
    
    # PHASE 2: Resource prediction info
    estimated_resources: int = 0
    resource_details: List[str] = None
    requires_review: bool = False
    review_message: str = ""

    # RAG context (citations)
    rag_context: Optional[Dict[str, Any]] = None
    
    # ICD-10 Coding for GAHAR Compliance (Egyptian hospitals)
    icd10_code: str = ""
    icd10_description: str = ""
    icd10_category: str = ""


# =============================================================================
# ESI RESOURCE PREDICTION (PHASE 2 AUDIT FIX)
# =============================================================================
# Reference: ESI v4 Handbook, AHRQ 2011, Chapter 4: ESI Decision Points C-E
#
# ESI distinguishes Levels 3, 4, 5 by expected resource utilization:
# - Level 3: ≥2 resources expected
# - Level 4: 1 resource expected
# - Level 5: 0 resources expected
#
# Resources include: Labs, ECG, X-ray/CT/US, IV fluids, IM/IV meds,
# Specialty consults, Simple procedures (suturing, splinting)

RESOURCE_LABELS = {
    "labs": {"en": "Lab tests", "ar": "تحاليل معملية"},
    "imaging": {"en": "Imaging", "ar": "تصوير طبي"},
    "possible_imaging": {"en": "Possible imaging", "ar": "قد يحتاج تصوير"},
    "ecg": {"en": "ECG", "ar": "رسم قلب"},
    "xray": {"en": "X-ray", "ar": "أشعة سينية"},
    "iv_fluids": {"en": "IV fluids", "ar": "سوائل وريدية"},
    "pain_meds_iv": {"en": "IV pain meds", "ar": "مسكنات وريدية"},
    "pain_meds_oral": {"en": "Oral pain meds", "ar": "مسكنات فموية"},
    "pain_meds": {"en": "Pain meds", "ar": "مسكنات"},
    "laceration_repair": {"en": "Laceration repair", "ar": "خياطة جرح"},
    "suture_kit": {"en": "Suture kit", "ar": "أدوات خياطة"},
    "splinting": {"en": "Splinting", "ar": "تجبير"},
    "orthopedic_consult": {"en": "Orthopedic consult", "ar": "استشارة عظام"},
    "nebulizer": {"en": "Nebulizer", "ar": "جلسة بخار"},
    "steroids": {"en": "Steroids", "ar": "ستيرويدات"},
    "strep_test": {"en": "Rapid strep test", "ar": "اختبار السترب السريع"},
    "exam_only": {"en": "Clinical exam only", "ar": "فحص سريري فقط"},
    "urinalysis": {"en": "Urinalysis", "ar": "تحليل بول"},
    "antihistamine_im": {"en": "IM antihistamine", "ar": "مضاد حساسية عضلي"},
    "antihistamine": {"en": "Antihistamine", "ar": "مضاد حساسية"},
    "eye_exam": {"en": "Eye exam", "ar": "فحص عين"},
    "evaluation": {"en": "Clinical evaluation", "ar": "تقييم سريري"},
    "sedation": {"en": "Sedation", "ar": "مهدئ"},
    "security": {"en": "Security", "ar": "أمن"},
    "psych_consult": {"en": "Psych consult", "ar": "استشارة نفسية"},
}


def format_resource_list(resources: List[str]) -> Tuple[str, str]:
    labels_en = []
    labels_ar = []
    for resource in resources or []:
        label = RESOURCE_LABELS.get(resource)
        if label:
            labels_en.append(label["en"])
            labels_ar.append(label["ar"])
        else:
            # Fallback: prettify unknown resource codes
            pretty = resource.replace("_", " ")
            labels_en.append(pretty.title())
            labels_ar.append(pretty)
    return ", ".join(labels_ar), ", ".join(labels_en)

# Categories that typically need multiple resources (Level 3)
MULTI_RESOURCE_CATEGORIES = {
    "abdominal_pain_moderate": {
        "resources": ["labs", "imaging", "iv_fluids"],
        "count": 3,
        "rationale": "Likely needs CBC, CMP, CT/US, IV hydration"
    },
    "chest_pain_noncardiac": {
        "resources": ["ecg", "labs", "imaging"],
        "count": 3,
        "rationale": "Needs ECG, troponin, possible CXR"
    },
    "moderate_dyspnea": {
        "resources": ["labs", "imaging", "nebulizer"],
        "count": 3,
        "rationale": "Needs ABG/labs, CXR, respiratory treatment"
    },
    "fever_with_symptoms": {
        "resources": ["labs", "imaging"],
        "count": 2,
        "rationale": "Needs CBC, possible CXR/UA"
    },
    "vomiting_dehydration": {
        "resources": ["labs", "iv_fluids"],
        "count": 2,
        "rationale": "Needs electrolytes, IV rehydration"
    },
    "fracture_deformity": {
        "resources": ["xray", "splinting", "orthopedic_consult"],
        "count": 3,
        "rationale": "Needs X-ray, reduction/splinting, possible consult"
    },
    "moderate_bleeding": {
        "resources": ["laceration_repair", "labs"],
        "count": 2,
        "rationale": "Complex laceration repair, possible CBC"
    },
    "pediatric_distress": {
        "resources": ["labs", "imaging", "iv_fluids"],
        "count": 3,
        "rationale": "Pediatric workup typically comprehensive"
    },
    "asthma_exacerbation": {
        "resources": ["nebulizer", "steroids", "labs"],
        "count": 3,
        "rationale": "Multiple nebulizers, steroids, possible ABG"
    },
    "kidney_stone": {
        "resources": ["labs", "imaging", "iv_fluids", "pain_meds_iv"],
        "count": 4,
        "rationale": "UA, CT, IV fluids, IV pain control"
    },
}

# Categories that typically need one resource (Level 4)
SINGLE_RESOURCE_CATEGORIES = {
    "minor_trauma": {
        "resources": ["xray"],
        "count": 1,
        "rationale": "Usually just needs X-ray to rule out fracture"
    },
    "laceration_simple": {
        "resources": ["suture_kit"],
        "count": 1,
        "rationale": "Simple laceration repair"
    },
    "sore_throat": {
        "resources": ["strep_test"],
        "count": 1,
        "rationale": "Rapid strep test"
    },
    "earache": {
        "resources": ["exam_only"],
        "count": 1,
        "rationale": "Otoscopic exam, oral antibiotics"
    },
    "uti_symptoms": {
        "resources": ["urinalysis"],
        "count": 1,
        "rationale": "UA/dipstick, oral antibiotics"
    },
    "mild_allergic": {
        "resources": ["antihistamine_im"],
        "count": 1,
        "rationale": "IM/oral antihistamine"
    },
    "ankle_sprain": {
        "resources": ["xray"],
        "count": 1,
        "rationale": "X-ray per Ottawa rules"
    },
    "back_pain_chronic": {
        "resources": ["pain_meds_oral"],
        "count": 1,
        "rationale": "Oral pain management"
    },
    "headache_mild": {
        "resources": ["pain_meds_oral"],
        "count": 1,
        "rationale": "Oral pain management"
    },
    "dental": {
        "resources": ["pain_meds_oral"],
        "count": 1,
        "rationale": "Oral pain meds, dental referral"
    },
    "eye_complaint": {
        "resources": ["eye_exam"],
        "count": 1,
        "rationale": "Slit lamp exam or visual acuity"
    },
}

# Categories that typically need zero resources (Level 5)
ZERO_RESOURCE_CATEGORIES = {
    "prescription_refill": {
        "resources": [],
        "count": 0,
        "rationale": "Prescription only"
    },
    "medical_certificate": {
        "resources": [],
        "count": 0,
        "rationale": "Documentation only"
    },
    "suture_removal": {
        "resources": [],
        "count": 0,
        "rationale": "Simple procedure, no workup"
    },
    "chronic_stable": {
        "resources": [],
        "count": 0,
        "rationale": "Follow-up, no acute intervention"
    },
    "minor_complaint": {
        "resources": [],
        "count": 0,
        "rationale": "Reassurance, oral meds only"
    },
    "wound_check": {
        "resources": [],
        "count": 0,
        "rationale": "Visual inspection only"
    },
    "rash_minor": {
        "resources": [],
        "count": 0,
        "rationale": "Topical treatment or reassurance"
    },
    "uri_symptoms": {
        "resources": [],
        "count": 0,
        "rationale": "Supportive care, oral meds"
    },
    "mild_gi": {
        "resources": [],
        "count": 0,
        "rationale": "Oral rehydration, diet advice"
    },
    "skin_fungal": {
        "resources": [],
        "count": 0,
        "rationale": "Topical antifungal"
    },
    "hiccups": {
        "resources": [],
        "count": 0,
        "rationale": "Reassurance, simple maneuvers"
    },
    "insect_bite": {
        "resources": [],
        "count": 0,
        "rationale": "Topical treatment"
    },
}


class ESIResourcePredictor:
    """
    ESI v4 Resource Prediction Engine
    
    Reference: ESI v4 Handbook, AHRQ 2011
    
    Estimates the number of ED resources a patient will need to reach
    a disposition (admission, discharge, transfer).
    
    Resources counted:
    - Labs (blood, urine)
    - ECG
    - Imaging (X-ray, CT, US, MRI)
    - IV fluids
    - IV/IM medications (beyond oral meds)
    - Specialty consults
    - Simple procedures (suturing, splinting, I&D)
    
    NOT counted as resources:
    - History and physical exam
    - Point-of-care tests (fingerstick glucose)
    - Saline lock (without IV fluids)
    - Oral medications
    - Tetanus immunization
    - Prescription refills
    - Simple wound care (bandaging)
    - Crutches, slings
    """
    
    def estimate_resources(self, category: str, chief_complaint: str = "",
                          vitals: dict = None, age: float = 30) -> dict:
        """
        Estimate number of ED resources needed.
        
        Args:
            category: Classified symptom category
            chief_complaint: Original complaint text (for additional hints)
            vitals: Vital signs dict (may influence resource needs)
            age: Patient age (pediatric/geriatric may need more workup)
            
        Returns:
            dict with:
            - count: int (number of resources)
            - resources: list of expected resources
            - rationale: explanation
            - esi_level: suggested ESI level (3, 4, or 5)
        """
        complaint_lower = _normalize_guardrail_text(chief_complaint)

        active_hemorrhage_signal = _contains_any(
            complaint_lower,
            [
                "uncontrolled bleeding",
                "spurting",
                "won't stop bleeding",
                "arterial",
                "massive blood loss",
                "active hemorrhage",
                "bleeding heavily",
            ],
        ) or _text_has_tachycardia_signal(complaint_lower) or _text_has_hypotension_signal(complaint_lower)

        needs_laceration_repair = (
            (
                "facial laceration" in complaint_lower
                or (
                    _contains_any(complaint_lower, ["laceration", "cut"])
                    and _contains_any(complaint_lower, ["sutures", "stitches", "repair"])
                )
            )
            and not active_hemorrhage_signal
        )
        if needs_laceration_repair:
            return {
                "count": 1,
                "resources": ["laceration_repair"],
                "rationale": "Repair-only laceration needs one ED resource but remains urgent",
                "esi_level": 3,
            }

        uncomplicated_heartburn = _contains_any(
            complaint_lower,
            ["heartburn", "gerd", "acid reflux"],
        ) and not _contains_any(complaint_lower, INSTABILITY_SIGNALS)
        if uncomplicated_heartburn:
            return {
                "count": 1,
                "resources": ["ecg"],
                "rationale": "Heartburn without alarm features typically needs one resource",
                "esi_level": 4,
            }

        # Check multi-resource categories first
        if category in MULTI_RESOURCE_CATEGORIES:
            info = MULTI_RESOURCE_CATEGORIES[category]
            return {
                "count": info["count"],
                "resources": info["resources"],
                "rationale": info["rationale"],
                "esi_level": 3
            }
        
        # Check single-resource categories
        if category in SINGLE_RESOURCE_CATEGORIES:
            info = SINGLE_RESOURCE_CATEGORIES[category]
            return {
                "count": info["count"],
                "resources": info["resources"],
                "rationale": info["rationale"],
                "esi_level": 4
            }
        
        # Check zero-resource categories
        if category in ZERO_RESOURCE_CATEGORIES:
            info = ZERO_RESOURCE_CATEGORIES[category]
            return {
                "count": info["count"],
                "resources": info["resources"],
                "rationale": info["rationale"],
                "esi_level": 5
            }
        
        # Age-based adjustments for uncategorized complaints
        base_resources = 1  # Default assumption
        resources = ["evaluation"]
        rationale = "Uncategorized complaint, standard workup"
        
        # Pediatric patients often need more workup
        if age < 2:
            base_resources = 2
            resources = ["labs", "possible_imaging"]
            rationale = "Young pediatric patient - comprehensive workup likely"
        
        # Elderly patients often need more workup
        elif age >= 65:
            base_resources = 2
            resources = ["labs", "ecg"]
            rationale = "Geriatric patient - broader workup likely"
        
        # Check complaint text for resource hints
        # Keywords suggesting labs needed
        if any(word in complaint_lower for word in ["سخونية", "fever", "infection"]):
            if "labs" not in resources:
                resources.append("labs")
                base_resources += 1
        
        # Keywords suggesting imaging needed
        if any(word in complaint_lower for word in ["سقط", "وقع", "fell", "trauma", "حادث"]):
            if "imaging" not in resources:
                resources.append("imaging")
                base_resources += 1
        
        # Keywords suggesting IV needed
        if any(word in complaint_lower for word in ["جفاف", "dehydration", "بيرجع", "vomiting"]):
            if "iv_fluids" not in resources:
                resources.append("iv_fluids")
                base_resources += 1
        
        # Determine ESI level based on resource count
        if base_resources >= 2:
            esi_level = 3
        elif base_resources == 1:
            esi_level = 4
        else:
            esi_level = 5
        
        return {
            "count": base_resources,
            "resources": resources,
            "rationale": rationale,
            "esi_level": esi_level
        }


class DeterministicTriageEngine:
    """
    Hybrid Deterministic Triage Engine
    
    Combines:
    - NEWS2 vital sign scoring (RCP 2017)
    - ESI complaint categorization (AHRQ 2011)
    - Constrained AI for Arabic NLP (Shortliffe & Sepúlveda, JAMA 2018)
    
    Key Principle: "AI classifies, rules decide"
    
    The AI component only performs classification into predefined categories.
    All triage decisions are made by deterministic rules based on:
    - NEWS2 score thresholds
    - ESI category → level mapping
    - Clinical modifier rules (age, history, etc.)
    """

    UNKNOWN_COMPLAINT_REVIEW_MESSAGE = (
        "Complaint not recognized — conservative default applied. Manual assessment required | "
        "الشكوى غير معروفة — تم تطبيق التصنيف الاحتياطي. يحتاج تقييم يدوي"
    )
    
    # Triage level metadata
    LEVEL_INFO = {
        1: {
            "color": "red",
            "label_ar": "إنعاش",
            "label_en": "Resuscitation",
            "time": "فوري / Immediate",
            "action_ar": "غرفة الإنعاش فوراً - تدخل منقذ للحياة",
            "action_en": "Resuscitation room immediately - Life-saving intervention"
        },
        2: {
            "color": "orange",
            "label_ar": "طوارئ",
            "label_en": "Emergent",
            "time": "< 10 دقائق / < 10 minutes",
            "action_ar": "تقييم طبيب فوري - حالة عالية الخطورة",
            "action_en": "Immediate physician assessment - High-risk situation"
        },
        3: {
            "color": "yellow",
            "label_ar": "عاجل",
            "label_en": "Urgent",
            "time": "< 30 دقيقة / < 30 minutes",
            "action_ar": "تقييم طبيب في أقرب وقت - يحتاج فحوصات متعددة",
            "action_en": "Physician assessment soon - Multiple resources needed"
        },
        4: {
            "color": "green",
            "label_ar": "أقل إلحاحاً",
            "label_en": "Less Urgent",
            "time": "< 60 دقيقة / < 60 minutes",
            "action_ar": "انتظار للتقييم - يحتاج فحص واحد",
            "action_en": "Wait for assessment - One resource needed"
        },
        5: {
            "color": "blue",
            "label_ar": "غير عاجل",
            "label_en": "Non-Urgent",
            "time": "< 120 دقيقة / < 120 minutes",
            "action_ar": "يمكن الانتظار - لا يحتاج فحوصات طوارئ",
            "action_en": "Can wait - No emergency resources needed"
        }
    }
    
    def __init__(self, use_ai: bool = False):
        """
        Initialize the deterministic triage engine.
        
        Args:
            use_ai: If False (default), only use keyword matching (FAST).
                   If True, attempt AI classification with fallback.
        """
        self.use_ai = use_ai
        self.news2_calculator = NEWS2Calculator()
        self.ai_classifier = AISymptomClassifier()
        # PHASE 2: Add ESI Resource Predictor
        self.resource_predictor = ESIResourcePredictor()

    def apply_esi_v5_compliance(
        self, patient_input, vitals, current_esi: int
    ) -> Tuple[int, List[str]]:
        """
        Apply ESI v5 compliance checks and return adjusted ESI level.
        """
        def _get_field(field: str, default=None):
            if isinstance(patient_input, dict):
                return patient_input.get(field, default)
            return getattr(patient_input, field, default)

        consciousness = _get_field("consciousness", "A")
        gcs_value = self._acvpu_to_gcs(consciousness)

        # Build vitals dict
        vitals_dict = {
            "hr": vitals.hr,
            "rr": vitals.rr,
            "spo2": vitals.spo2,
            "sbp": vitals.sbp,
            "dbp": vitals.dbp,
            "temp_c": vitals.temp,
            "gcs": gcs_value,
        }

        # Get optional fields from patient_input
        pain_scale = _get_field("pain_scale")
        pain_context = _get_field("pain_context")
        is_immunocompromised = _get_field("is_immunocompromised", False)
        immunocompromised_reason = _get_field("immunocompromised_reason")
        immunizations_complete = _get_field("immunizations_complete", True)
        is_pregnant = _get_field("is_pregnant", False)
        gestational_weeks = _get_field("gestational_weeks")
        pregnancy_complaint = _get_field("pregnancy_complaint")

        # Run ESI v5 evaluation
        result = evaluate_esi_v5(
            age_years=_get_field("age", 0),
            vitals=vitals_dict,
            pain_scale=pain_scale,
            pain_context=pain_context,
            is_immunocompromised=is_immunocompromised,
            immunocompromised_reason=immunocompromised_reason,
            immunizations_complete=immunizations_complete,
            is_pregnant=is_pregnant,
            gestational_weeks=gestational_weeks,
            pregnancy_complaint=pregnancy_complaint,
            has_seizure=self._check_for_seizure(patient_input),
            has_trauma=self._check_for_trauma(patient_input),
        )

        # Use minimum (most acute) between current and ESI v5 suggested
        esi_v5 = result.get("esi_v5_suggested")
        if esi_v5 is not None:
            final_esi = min(current_esi, esi_v5)
        else:
            final_esi = current_esi

        return final_esi, result.get("esi_v5_alerts", [])

    def _build_rag_context(
        self,
        complaint_text: str,
        comorbidities: Optional[List[str]] = None,
        k: int = 3,
        source_filter: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """Retrieve RAG chunks and format response."""
        if rag_retrieve is None:
            return None
        if not complaint_text or not str(complaint_text).strip():
            return None
        query = str(complaint_text).strip()
        comorb_list = []
        if comorbidities:
            if isinstance(comorbidities, (list, tuple, set)):
                comorb_list = [str(c).strip() for c in comorbidities if str(c).strip()]
            else:
                value = str(comorbidities).strip()
                if value:
                    comorb_list = [value]
        if comorb_list:
            query = f"{query} {' '.join(comorb_list)}"
        try:
            results = rag_retrieve(query=query, k=k, source_filter=source_filter)
        except Exception:
            return None
        if not results:
            return None
        sources = sorted({r.get("source", "unknown") for r in results})
        citations = []
        for r in results:
            citations.append(
                {
                    "source": r.get("source", "unknown"),
                    "text": r.get("text", ""),
                    "relevance": r.get("score"),
                }
            )
        return {
            "sources_used": sources,
            "citations": citations,
        }

    def _check_for_seizure(self, patient_input) -> bool:
        """Check if chief complaint or history indicates seizure."""
        seizure_keywords = ["seizure", "تشنج", "صرع", "convulsion", "fitting"]
        if isinstance(patient_input, dict):
            complaint = (
                patient_input.get("chief_complaint_text")
                or patient_input.get("chief_complaint")
                or patient_input.get("complaint")
                or ""
            )
        else:
            complaint = (
                getattr(patient_input, "chief_complaint_text", None)
                or getattr(patient_input, "chief_complaint", None)
                or getattr(patient_input, "complaint", None)
                or ""
            )
        complaint = str(complaint).lower()
        return any(kw in complaint for kw in seizure_keywords)

    def _check_for_trauma(self, patient_input) -> bool:
        """Check if chief complaint indicates trauma.

        NOTE: Generic English "accident" removed — NHAMCS uses it as a
        catch-all code (ESI 2-5). True high-energy mechanisms are caught
        by "trauma", "hit", "injury", or Arabic equivalents.
        """
        trauma_keywords = [
            "trauma",
            "fall",
            "حادث",
            "وقع",
            "سقوط",
            "injury",
            "hit",
            "اصابة",
        ]
        if isinstance(patient_input, dict):
            complaint = (
                patient_input.get("chief_complaint_text")
                or patient_input.get("chief_complaint")
                or patient_input.get("complaint")
                or ""
            )
        else:
            complaint = (
                getattr(patient_input, "chief_complaint_text", None)
                or getattr(patient_input, "chief_complaint", None)
                or getattr(patient_input, "complaint", None)
                or ""
            )
        complaint = str(complaint).lower()
        return any(kw in complaint for kw in trauma_keywords)

    def _acvpu_to_gcs(self, consciousness: str) -> int:
        """Approximate GCS from ACVPU for internal use (ESI v5 level-1 override)."""
        mapping = {
            "A": 15,
            "C": 14,
            "V": 12,
            "P": 8,
            "U": 3,
        }
        key = str(consciousness or "A").upper()
        return mapping.get(key, 15)
    
    def triage(self, patient_data: dict) -> DeterministicTriageResult:
        """
        Perform deterministic triage on patient data.
        
        AUDIT FIXES IMPLEMENTED:
        - Passes new NEWS2 parameters (is_copd, on_supplemental_o2, consciousness)
        - Uses pediatric vital sign thresholds
        - Enhanced pregnancy detection for ectopic risk
        
        Args:
            patient_data: dict with keys:
                - age: float
                - gender: str
                - chief_complaint_text: str
                - vitals: dict or Vitals object
                - history_cardiac: bool (optional)
                - history_stroke: bool (optional)
                - is_copd: bool (optional) - Use SpO2 Scale 2
                - on_supplemental_o2: bool (optional) - Add +2 NEWS2 points
                - consciousness: str (optional) - ACVPU scale (A, C, V, P, U)
                - is_pregnant: bool (optional) - Enable obstetric emergency detection
                
        Returns:
            DeterministicTriageResult with complete decision audit trail
        """
        # Extract data
        age = patient_data.get('age', 30)
        gender = patient_data.get('gender', 'male')
        if hasattr(gender, 'value'):
            gender = gender.value
        complaint = (
            patient_data.get('chief_complaint_text')
            or patient_data.get('chief_complaint')
            or patient_data.get('complaint', '')
        )
        vitals = patient_data.get('vitals', {})
        
        # AUDIT FIX: Extract new NEWS2 compliance fields
        is_copd = patient_data.get('is_copd', False)
        on_supplemental_o2 = patient_data.get('on_supplemental_o2', False)
        consciousness = patient_data.get('consciousness', 'A')
        is_pregnant = patient_data.get('is_pregnant', False)
        
        # Convert vitals dict to object-like access
        class VitalsWrapper:
            def __init__(self, d):
                self.hr = d.get('hr')
                self.rr = d.get('rr')
                self.spo2 = d.get('spo2')
                self.sbp = d.get('sbp')
                self.dbp = d.get('dbp')
                self.temp = d.get('temp')
                self.blood_glucose = d.get('blood_glucose')
                self.pain_score = d.get('pain_score', 0)
        
        if isinstance(vitals, dict):
            vitals = VitalsWrapper(vitals)
        
        # Step 1: Classify complaint (allow explicit override from upstream AI/RAG)
        category_override = patient_data.get("category_override")
        if category_override in SYMPTOM_CATEGORIES:
            category = category_override
            extraction_method = (
                patient_data.get("extraction_method_override")
                or ("gemini_online" if self.use_ai else "keyword_offline")
            )
        else:
            # PERFORMANCE FIX: Only use AI when explicitly enabled
            if self.use_ai:
                category = self.ai_classifier.classify(complaint, age, gender)
            else:
                # Standard mode: Use ONLY keyword matching (fast, deterministic)
                category = self.ai_classifier._fallback_keyword_match(complaint)
            extraction_method = getattr(self.ai_classifier, "last_extraction_method", "keyword_offline")
        category_info = SYMPTOM_CATEGORIES.get(category, SYMPTOM_CATEGORIES["unclear"])
        category_level = category_info.esi_level
        category_requires_immediate_intervention = category_info.requires_immediate_intervention

        ai_guardrail_reasons: List[str] = []
        if extraction_method in ("gemini_online", "keyword_offline", "egybert_offline"):
            ai_proposed_esi = 1 if category_requires_immediate_intervention else category_level
            guarded_esi, ai_guardrail_reasons = apply_safety_guardrails(complaint, category, ai_proposed_esi)
            ceiling_esi, ceiling_reason = apply_severity_ceiling(complaint, guarded_esi, ai_category=category)
            if ceiling_reason != "PASS":
                ai_guardrail_reasons.append(ceiling_reason)
            final_ai_esi = max(guarded_esi, ceiling_esi)
            if final_ai_esi > ai_proposed_esi:
                # These guardrails only suppress AI-driven escalation. NEWS2 and deterministic
                # modifiers still run after this and can independently force ESI 1/2.
                category_requires_immediate_intervention = False
                category_level = max(category_level, final_ai_esi)

        # Step 2: Calculate NEWS2 (Deterministic) after AI guardrails settle the category ceiling.
        news2_result = self.news2_calculator.calculate(
            vitals,
            age=age,
            is_copd=is_copd,
            on_supplemental_o2=on_supplemental_o2,
            consciousness=consciousness
        )
        news2_plus_result = calculate_news2_plus(news2_result, vitals)
        news2_effective_total = int(news2_plus_result["news2_plus_total"])
        news2_effective_level = int(news2_plus_result["triage_level"])

        complaint_lower = str(complaint or "").lower()
        normalized_complaint = (
            complaint_lower.replace("أ", "ا").replace("إ", "ا").replace("آ", "ا")
        )
        pain_context = str(patient_data.get("pain_context") or "").strip().lower()
        comorbidities_text = " ".join(str(item).lower() for item in (patient_data.get("comorbidities") or []))
        has_diabetes_risk = any(token in comorbidities_text for token in ["diabet", "dm", "سكر"])
        has_smoker_risk = any(token in comorbidities_text for token in ["smok", "مدخ"])
        has_hyperlipidemia_risk = any(token in comorbidities_text for token in ["hyperlipidemia", "lipid", "دهون"])
        chest_discomfort_tokens = [
            "chest pain",
            "chest discomfort",
            "burning chest",
            "chest burning",
            "angina",
            "ألم صدر",
            "الم صدر",
            "وجع صدر",
            "وجع في الصدر",
            "وجع في صدرها",
            "وجع في صدره",
            "وجع في صدري",
            "حرقان صدر",
            "حارق بالصدر",
            "ضغط على الصدر",
        ]
        syncope_tokens = [
            "syncope",
            "passed out",
            "fainted",
            "blacked out",
            "lost consciousness",
            "passed out briefly",
            "اغمى عليه",
            "اغمي عليه",
            "اغمى عليا",
            "اغمي عليا",
            "دوخ ووقع",
            "فقد الوعي",
        ]
        dissection_specific_tokens = [
            "tearing",
            "ripping",
            "ripped",
            "radiates to back",
            "to the back",
            "back pain",
            "pulsatile",
            "pulse difference",
            "sudden severe back pain",
            "يمتد للظهر",
            "للظهر",
            "ظهره بيوجعه",
            "ظهره واجعه",
            "الم شديد مفاجئ",
            "ألم شديد مفاجئ",
        ]
        gi_bleed_tokens = [
            "hematemesis",
            "coffee ground",
            "melena",
            "black tarry stools",
            "tarry stools",
            "black stool",
            "قىء دم",
            "قيء دم",
            "بيرجع دم",
            "يرجع دم",
            "براز اسود",
            "براز أسود",
        ]
        gi_bleed_action_tokens = [
            "vomit",
            "vomiting",
            "throwing up",
            "throw up",
            "throwing blood",
            "بيرجع",
            "يرجع",
            "قيء",
            "قىء",
        ]
        gi_bleed_blood_tokens = [
            "blood",
            "bloody",
            "دم",
        ]
        massive_bleed_tokens = [
            "large amounts",
            "massive",
            "profuse",
            "feeling faint",
            "faint",
            "soaking",
            "near syncope",
            "كمية كبيرة",
            "دم كتير",
            "غزير",
            "هيغمى عليه",
            "هيغمي عليه",
            "دوخة شديدة",
        ]
        atypical_gi_tokens = [
            "indigestion",
            "epigastr",
            "heartburn",
            "dyspepsia",
            "عسر هضم",
            "سوء هضم",
            "حرقان",
            "فم المعدة",
            "فم المعده",
            "المعده",
        ]
        autonomic_fatigue_tokens = [
            "عرقان",
            "عرق",
            "sweat",
            "diaphores",
            "fatigue",
            "تعب",
            "ارهاق",
            "إرهاق",
            "هبطان",
            "weak",
            "ضعف",
        ]
        has_chest_discomfort = any(token in normalized_complaint for token in chest_discomfort_tokens)
        has_syncope_signal = any(token in normalized_complaint for token in syncope_tokens)
        has_dissection_specific_signal = any(token in normalized_complaint for token in dissection_specific_tokens)
        _is_abscess_complaint = any(t in normalized_complaint for t in ("خراج", "abscess"))
        has_gi_bleed_signal = not _is_abscess_complaint and (
            any(token in normalized_complaint for token in gi_bleed_tokens) or (
                any(token in normalized_complaint for token in gi_bleed_action_tokens)
                and any(token in normalized_complaint for token in gi_bleed_blood_tokens)
            )
        )
        has_massive_bleed_signal = any(token in normalized_complaint for token in massive_bleed_tokens)
        has_atypical_gi = any(token in normalized_complaint for token in atypical_gi_tokens)
        has_autonomic_fatigue = any(token in normalized_complaint for token in autonomic_fatigue_tokens)

        # AI guardrail: protect massive GI bleed from being softened to generic GI bleed.
        if category == "gi_bleed" and has_gi_bleed_signal:
            hemodynamically_unstable = bool(
                (vitals.sbp is not None and vitals.sbp <= 90)
                or (vitals.hr is not None and vitals.hr >= 120)
            )
            if hemodynamically_unstable or has_massive_bleed_signal:
                category = "severe_bleeding"
                category_info = SYMPTOM_CATEGORIES.get(category, category_info)
                category_level = category_info.esi_level

        # AI guardrail: chest pain + syncope should not become dissection without classic descriptors.
        if category == "aortic_dissection" and has_chest_discomfort and has_syncope_signal and not has_dissection_specific_signal:
            category = "chest_pain_cardiac"
            category_info = SYMPTOM_CATEGORIES.get(category, category_info)
            category_level = category_info.esi_level
            category_requires_immediate_intervention = category_info.requires_immediate_intervention
        
        # Step 3: Apply clinical modifiers (Deterministic rules)
        modifiers = ai_guardrail_reasons.copy()
        modifier_level = 5  # Start with lowest urgency

        # ===== PEDIATRIC MODIFIERS (AUDIT FIX - CRITICAL) =====
        # ESI v4 Chapter 5: Pediatric Considerations
        
        # Infant (<28 days) with fever = HIGH sepsis risk
        if age < 0.08 and vitals.temp and vitals.temp >= 38.0:  # <28 days
            modifier_level = min(modifier_level, 2)
            modifiers.append("🚨 رضيع <28 يوم مع حمى - خطر تعفن دم / Neonate <28 days with fever - SEPSIS RISK")
        
        # Young infant (28-90 days) with fever
        elif age < 0.25 and vitals.temp and vitals.temp >= 38.0:  # 28-90 days
            modifier_level = min(modifier_level, 2)
            modifiers.append("⚠️ رضيع صغير مع حمى - يحتاج تقييم عاجل / Young infant with fever - urgent evaluation")
        
        # Infant with abnormal vitals (existing rule, kept)
        if age < 2 and news2_result.total_score >= 2:
            modifier_level = min(modifier_level, 2)
            modifiers.append("طفل رضيع مع علامات حيوية غير طبيعية / Infant with abnormal vitals")

        # ===== CHEST PAIN SAFETY FLOOR =====
        if pain_context == "chest_pain" or has_chest_discomfort:
            modifier_level = min(modifier_level, 2)
            modifiers.append("🚨 ألم/انزعاج صدري - حد أدنى ESI 2 / Chest pain/discomfort - minimum ESI 2")

        # ===== SILENT MI / ATYPICAL ACS SAFETY FLOOR =====
        if (
            has_atypical_gi
            and (has_autonomic_fatigue or has_chest_discomfort)
            and (
                bool(patient_data.get("history_cardiac"))
                or has_diabetes_risk
                or has_smoker_risk
                or has_hyperlipidemia_risk
                or age >= 50
            )
        ):
            modifier_level = min(modifier_level, 2)
            if category in {"mild_gi", "mild_pain", "unclear", "abdominal_pain_moderate", "chest_pain_noncardiac"}:
                category = "silent_mi"
                category_info = SYMPTOM_CATEGORIES.get(category, category_info)
                category_level = category_info.esi_level
            modifiers.append(
                "⚠️ نمط جلطة صامتة/ACS غير نمطي (أعراض معدية + تعب/تعرق مع عوامل خطورة) / "
                "Atypical ACS pattern (GI symptoms + fatigue/sweating with risk factors)"
            )

        # ===== ELDERLY MODIFIERS =====
        if age >= 65 and category in ["chest_pain_cardiac", "chest_pain_noncardiac"]:
            modifier_level = min(modifier_level, 2)
            modifiers.append("مسن مع ألم صدر / Elderly with chest pain")

        # Elderly + epigastric pain + hypertension → ACS screening (ESI 2)
        _epigastric_tokens = ("epigastr", "فم المعدة", "فم المعده")
        if (
            age >= 60
            and any(tok in normalized_complaint for tok in _epigastric_tokens)
            and vitals.sbp is not None and vitals.sbp >= 150
        ):
            modifier_level = min(modifier_level, 2)
            modifiers.append(
                "⚠️ مسن + ألم شرسوفي + ارتفاع ضغط → فحص ACS / "
                "Elderly + epigastric pain + hypertension → ACS screening → ESI 2"
            )
        
        # ===== PAIN SCORE MODIFIER =====
        # ESI v4: Severe pain (≥8/10) triggers ESI 2 EXCEPT for isolated
        # musculoskeletal/extremity complaints where high pain scores are
        # common and do not indicate a high-risk situation.
        # Reference: ESI v4 Handbook, Decision Point B — "severe pain/distress"
        # applies to conditions like chest pain, abdominal pain, headache,
        # NOT isolated extremity injuries (wrist, ankle, foot, knee pain).
        _EXTREMITY_CATEGORIES = frozenset({
            "mild_pain", "minor_trauma", "fracture_deformity",
            "back_pain_chronic", "laceration_simple",
        })
        _EXTREMITY_CC_TOKENS_EN = (
            "wrist", "ankle", "foot", "knee", "elbow", "finger",
            "toe", "hand", "arm", "leg", "shoulder", "hip",
        )
        # Arabic tokens use word-boundary regex to avoid substring collisions
        # (e.g. "إيد" matching inside "إيدز" (AIDS), "رجل" inside "راجل" (man))
        _EXTREMITY_CC_RE_AR = re.compile(
            r'(?:^|[\s،,.])'     # preceded by start/whitespace/punctuation
            r'('
            r'رسغ|كاحل|كوع|ركبة|صباع|إصبع|كتف|إيد|ايد|رجل|قدم|ورك'
            r')'
            r'(?:[\s،,.]|$)'     # followed by end/whitespace/punctuation
        )
        complaint_lower_for_pain = (complaint or "").lower()
        is_extremity = (
            category in _EXTREMITY_CATEGORIES
            and (
                any(tok in complaint_lower_for_pain for tok in _EXTREMITY_CC_TOKENS_EN)
                or bool(_EXTREMITY_CC_RE_AR.search(complaint_lower_for_pain))
            )
        )
        if vitals.pain_score and vitals.pain_score >= 8 and not is_extremity:
            # Pain ≥8 with instability signals → ESI 2 (emergent).
            # Pain ≥8 without instability signals → ESI 3 (urgent).
            # This prevents over-triage of stable patients with high pain
            # (e.g., pelvic pain 9/10 with normal vitals → ESI 3, not 2).
            complaint_for_pain_check = _normalize_guardrail_text(complaint or "")
            has_pain_instability = _contains_any(complaint_for_pain_check, INSTABILITY_SIGNALS)
            if has_pain_instability or vitals.pain_score >= 10:
                modifier_level = min(modifier_level, 2)
            else:
                modifier_level = min(modifier_level, 3)
            modifiers.append(f"ألم شديد {vitals.pain_score}/10 / Severe pain")
        
        # ===== MODERATE PAIN WITH SWELLING MODIFIER =====
        # Pain ≥7 with swelling suggests need for imaging (DVT, fracture,
        # infection) → 2+ resources → ESI 3 minimum.
        _SWELLING_TOKENS = ("swelling", "edema", "swollen", "ورم", "تورم", "وارم")
        if (
            vitals.pain_score and vitals.pain_score >= 7
            and category in ("mild_pain", "minor_trauma")
            and any(tok in complaint_lower_for_pain for tok in _SWELLING_TOKENS)
        ):
            modifier_level = min(modifier_level, 3)
            modifiers.append(
                f"ألم {vitals.pain_score}/10 مع تورم - يحتاج تصوير / "
                f"Pain {vitals.pain_score}/10 with swelling - imaging likely needed"
            )

        # ===== CARDIAC HISTORY MODIFIER =====
        if patient_data.get('history_cardiac') and category in [
            "chest_pain_cardiac", "chest_pain_noncardiac", "respiratory_distress"
        ]:
            modifier_level = min(modifier_level, 2)
            modifiers.append("تاريخ قلبي مع شكوى ذات صلة / Cardiac history + relevant complaint")
        
        # ===== PREGNANCY MODIFIERS (AUDIT FIX - Enhanced) =====
        if is_pregnant:
            # Pregnant with abdominal pain = Ectopic risk (Level 2)
            if category in ["abdominal_pain_moderate", "severe_pain"]:
                modifier_level = min(modifier_level, 2)
                modifiers.append("🚨 حامل مع ألم بطن - خطر حمل خارج الرحم / Pregnant + abdominal pain - ECTOPIC RISK")
            # Pregnant with bleeding = Obstetric emergency
            elif category in ["moderate_bleeding", "severe_bleeding"]:
                modifier_level = min(modifier_level, 1)
                modifiers.append("🚨 حامل مع نزيف - طوارئ ولادة / Pregnant + bleeding - OBSTETRIC EMERGENCY")
            # Any other complaint while pregnant
            elif category not in ["chronic_stable", "prescription_refill"]:
                modifier_level = min(modifier_level, 3)
                modifiers.append("حامل / Pregnant")
        
        # ===== IMMUNOCOMPROMISED MODIFIER =====
        if patient_data.get('immuno_compromised') and category in [
            "fever_with_symptoms", "high_fever_toxic"
        ]:
            modifier_level = min(modifier_level, 2)
            modifiers.append("نقص مناعة مع حمى / Immunocompromised with fever")
        
        # ===== REDUCED CONSCIOUSNESS MODIFIER =====
        if consciousness and str(consciousness).upper() != "A":
            modifier_level = min(modifier_level, 2)
            modifiers.append("🚨 مستوى وعي منخفض - يحتاج تقييم عاجل / Reduced consciousness - urgent evaluation needed")
        
        # =================================================================
        # PHASE 2: ESI RESOURCE PREDICTION FOR LEVELS 3-5
        # =================================================================
        # Reference: ESI v4 Handbook, Decision Points D & E
        # 
        # After checking for Level 1 (resuscitation) and Level 2 (high risk),
        # we use resource prediction to determine final level:
        # - ≥2 resources = Level 3
        # - 1 resource = Level 4
        # - 0 resources = Level 5
        # =================================================================
        
        glucose_flags = check_glucose_red_flags(vitals, patient_data)
        for glucose_flag in glucose_flags:
            min_esi = int(glucose_flag.get("min_esi", 5))
            modifier_level = min(modifier_level, min_esi)
            modifiers.append(
                f"{glucose_flag.get('alert', 'Glucose risk detected')} / "
                f"{glucose_flag.get('action', 'Requires urgent evaluation')}"
            )

        # Step 4: Determine preliminary level from NEWS2+, category, and modifiers
        preliminary_level = min(
            news2_effective_level,
            category_level,
            modifier_level
        )
        
        # Level 1 override: Immediate life-threat categories
        if category_requires_immediate_intervention:
            final_level = 1
        # Level 2 already determined by high-risk modifiers or NEWS2
        elif preliminary_level <= 2:
            final_level = preliminary_level
        else:
            # For levels 3-5, use ESI resource prediction
            # This is the key Phase 2 fix: resource count determines final level
            vitals_dict = {
                'hr': vitals.hr,
                'rr': vitals.rr,
                'spo2': vitals.spo2,
                'sbp': vitals.sbp,
                'temp': vitals.temp,
            }
            
            resource_result = self.resource_predictor.estimate_resources(
                category=category,
                chief_complaint=complaint,
                vitals=vitals_dict,
                age=age
            )
            
            resource_count = resource_result["count"]
            suggested_resource_level = int(resource_result.get("esi_level", 5))
            
            # ESI Decision Points D & E
            if resource_count >= 2:
                resources_ar, resources_en = format_resource_list(resource_result["resources"])
                final_level = 3  # Urgent - multiple resources needed
                if resources_en:
                    modifiers.append(f"موارد متعددة ({resources_ar}) / Multiple resources ({resources_en})")
                else:
                    modifiers.append(f"موارد متعددة: {resource_count} / Multiple resources: {resource_count}")
            elif resource_count == 1:
                if suggested_resource_level == 3:
                    final_level = 3
                    resources_ar, resources_en = format_resource_list(resource_result["resources"])
                    if resources_en:
                        modifiers.append(f"مورد عاجل واحد: {resources_ar} / One urgent resource: {resources_en}")
                    else:
                        modifiers.append("مورد عاجل واحد / One urgent resource")
                # SPECIAL CASE: 'unclear' category should default to Level 3 even with 1 resource
                # to align with "Ambiguous defaults to L3" principle
                elif category == "unclear":
                    final_level = 3
                    modifiers.append("حالة غير واضحة - اختيار المستوى 3 كإجراء وقائي / Ambiguous - defaulting to Level 3")
                else:
                    final_level = 4  # Less urgent - one resource
                    resources_ar, resources_en = format_resource_list(resource_result["resources"])
                    if resources_en:
                        modifiers.append(f"مورد واحد: {resources_ar} / One resource: {resources_en}")
                    else:
                        modifiers.append("مورد واحد / One resource")
            else:
                # Final safeguard for unclear cases with 0 resources
                if category == "unclear":
                    final_level = 3
                else:
                    final_level = 5  # Non-urgent - no resources
                modifiers.append("بدون موارد طوارئ / No ED resources needed")

            # Enforce modifier ceiling: if clinical modifiers indicate a
            # higher acuity (e.g., pain+swelling → ESI 3), the resource
            # prediction should not override to a lower acuity.
            if modifier_level < final_level:
                final_level = modifier_level

            if final_level == 5:
                esi5_check = ESI5Criteria.is_eligible(
                    patient_data=patient_data,
                    news2_plus_total=news2_effective_total,
                    category=category,
                )
                if not esi5_check.get("eligible", False):
                    final_level = int(esi5_check.get("recommended_esi", 4))
                    modifiers.append(
                        f"ESI5 not eligible: {esi5_check.get('reason')} / "
                        f"غير مؤهل لمستوى ESI5: {esi5_check.get('reason')}"
                    )

        # Apply ESI v5 compliance
        final_level, esi_v5_alerts = self.apply_esi_v5_compliance(
            patient_data, vitals, final_level
        )

        # =================================================================
        # CRITICAL VITAL-SIGN SAFETY FLOOR — ESI 1 ESCALATION
        # =================================================================
        # Regardless of keyword/AI classification, extreme vital signs
        # MUST escalate to ESI 1 (resuscitation). These are physiological
        # states where delayed intervention risks death.
        #
        # Thresholds based on:
        #   - ESI v4 Handbook: "Does the patient require immediate
        #     life-saving intervention?"
        #   - NEWS2: score of 3 in any single parameter = urgent review
        #   - Clinical consensus: SBP < 80, RR > 35, HR extremes
        # =================================================================
        vital_esi1_reasons = []
        if vitals and vitals.sbp is not None and vitals.sbp < 80:
            vital_esi1_reasons.append(
                f"ضغط دم انقباضي خطير ({vitals.sbp}) / "
                f"Critical SBP ({vitals.sbp} < 80) - hemodynamic collapse"
            )
        if vitals and vitals.rr is not None and vitals.rr >= 35:
            vital_esi1_reasons.append(
                f"معدل تنفس خطير ({vitals.rr}) / "
                f"Critical RR ({vitals.rr} >= 35) - respiratory failure"
            )
        if vitals and vitals.hr is not None and vitals.hr >= 150:
            vital_esi1_reasons.append(
                f"نبض قلب خطير ({vitals.hr}) / "
                f"Critical HR ({vitals.hr} >= 150) - unstable tachycardia"
            )
        if vitals and vitals.hr is not None and vitals.hr < 40:
            vital_esi1_reasons.append(
                f"بطء قلب خطير ({vitals.hr}) / "
                f"Critical bradycardia (HR {vitals.hr} < 40)"
            )
        if vitals and vitals.spo2 is not None and vitals.spo2 < 85:
            vital_esi1_reasons.append(
                f"نقص أكسجين خطير ({vitals.spo2}%) / "
                f"Critical hypoxia (SpO2 {vitals.spo2}% < 85%)"
            )

        if vital_esi1_reasons and final_level > 1:
            final_level = 1
            for reason in vital_esi1_reasons:
                modifiers.append(f"🚨 {reason}")

        # =================================================================
        # VITAL-SIGN SAFETY FLOOR — ESI 2 ESCALATION
        # =================================================================
        # Less extreme but still dangerous vital signs force ESI 2 minimum.
        # =================================================================
        vital_esi2_reasons = []
        if vitals and vitals.sbp is not None and vitals.sbp < 90 and final_level > 2:
            vital_esi2_reasons.append(
                f"ضغط دم منخفض ({vitals.sbp}) / "
                f"Hypotension (SBP {vitals.sbp} < 90)"
            )
        if vitals and vitals.hr is not None and vitals.hr >= 130 and final_level > 2:
            vital_esi2_reasons.append(
                f"تسارع القلب ({vitals.hr}) / "
                f"Significant tachycardia (HR {vitals.hr} >= 130)"
            )
        if vitals and vitals.spo2 is not None and vitals.spo2 < 90 and final_level > 2:
            vital_esi2_reasons.append(
                f"نقص أكسجين ({vitals.spo2}%) / "
                f"Hypoxia (SpO2 {vitals.spo2}% < 90%)"
            )

        # Hypertensive emergency: SBP >= 200
        if vitals and vitals.sbp is not None and vitals.sbp >= 200 and final_level > 2:
            vital_esi2_reasons.append(
                f"ارتفاع ضغط دم شديد ({vitals.sbp}) / "
                f"Hypertensive emergency (SBP {vitals.sbp} >= 200)"
            )

        # Hypertensive urgency with symptoms: SBP >= 180 + neuro/cardiac symptoms
        _hypertensive_symptoms = ("dizziness", "dizzy", "headache", "visual",
                                  "chest pain", "dyspnea", "shortness of breath",
                                  "vomiting", "weakness", "دوخة", "صداع")
        if (
            vitals and vitals.sbp is not None and vitals.sbp >= 180
            and final_level > 2
            and any(s in (complaint or "").lower() for s in _hypertensive_symptoms)
        ):
            vital_esi2_reasons.append(
                f"ارتفاع ضغط دم مع أعراض ({vitals.sbp}) / "
                f"Hypertensive urgency + symptoms (SBP {vitals.sbp} >= 180)"
            )

        # Fever + tachycardia (sepsis pathway): temp >= 38.0 AND HR > 100
        # NOTE: "حرارة" removed from simple substring check — it false-positives
        # on Arabic normal-temp reporting ("وحرارة 37.4 مئوية").  The temp_elevated
        # flag (vitals.temp >= 38.0) already catches real fevers via structured data.
        complaint_has_fever = any(
            t in (complaint or "").lower()
            for t in ("fever", "سخونية", "سخونة", "حمى")
        )
        temp_elevated = vitals and vitals.temp is not None and vitals.temp >= 38.0
        hr_tachy = vitals and vitals.hr is not None and vitals.hr > 100
        if (complaint_has_fever or temp_elevated) and hr_tachy and final_level > 2:
            temp_val = vitals.temp if vitals and vitals.temp else "N/A"
            vital_esi2_reasons.append(
                f"حمى مع تسارع القلب (BT={temp_val}, HR={vitals.hr}) / "
                f"Fever + tachycardia (temp={temp_val}, HR={vitals.hr}) — sepsis pathway"
            )

        # Symptomatic tachycardia: HR >= 110 with weakness/dizziness/syncope
        _tachy_symptoms = ("weakness", "general weakness", "dizziness", "dizzy",
                           "syncope", "fainted", "passed out", "ضعف", "دوخة")
        if (
            vitals and vitals.hr is not None and vitals.hr >= 110
            and final_level > 2
            and any(s in (complaint or "").lower() for s in _tachy_symptoms)
        ):
            vital_esi2_reasons.append(
                f"تسارع القلب مع أعراض (HR={vitals.hr}) / "
                f"Symptomatic tachycardia (HR {vitals.hr} >= 110 + {complaint})"
            )

        # Significant fever (temp >= 38.5) alone
        if vitals and vitals.temp is not None and vitals.temp >= 38.5 and final_level > 2:
            vital_esi2_reasons.append(
                f"حمى مرتفعة ({vitals.temp}°C) / "
                f"Significant fever (temp {vitals.temp}°C >= 38.5) — infection pathway"
            )

        if vital_esi2_reasons and final_level > 2:
            final_level = 2
            for reason in vital_esi2_reasons:
                modifiers.append(f"⚠️ {reason}")

        # =================================================================
        # ALTERED MENTAL STATUS + MISSING VITALS → ESI 1
        # =================================================================
        # When a patient presents with altered consciousness (C/V/P/U on
        # ACVPU) and most vital signs are unmeasurable/missing, assume the
        # worst — this pattern indicates a patient too unstable to assess.
        # =================================================================
        if final_level > 1 and consciousness in ("C", "V", "P", "U"):
            _ams_vitals_count = sum(1 for v in [
                vitals.hr if vitals else None,
                vitals.rr if vitals else None,
                vitals.sbp if vitals else None,
                vitals.spo2 if vitals else None,
            ] if v is not None)
            if _ams_vitals_count <= 1:
                final_level = 1
                modifiers.append(
                    "🚨 وعي متغير مع عدم توفر علامات حيوية → إنعاش فوري / "
                    "Altered consciousness + missing vitals → assume worst → ESI 1"
                )

        # =================================================================
        # SYMPTOMATIC BRADYCARDIA → ESI 2
        # =================================================================
        # HR 40-50 with symptoms (dizziness, weakness, syncope) suggests
        # hemodynamically significant bradycardia (AV block, sick sinus).
        # =================================================================
        if final_level > 2 and vitals and vitals.hr is not None and 40 <= vitals.hr <= 55:
            _brady_symptoms = ("dizziness", "dizzy", "weakness", "syncope",
                               "fainted", "passed out", "general weakness",
                               "دوخة", "ضعف عام", "اغمى")
            complaint_lower_brady = (complaint or "").lower()
            if any(sym in complaint_lower_brady for sym in _brady_symptoms):
                final_level = 2
                modifiers.append(
                    f"⚠️ بطء قلب مصحوب بأعراض (HR={vitals.hr}) / "
                    f"Symptomatic bradycardia (HR {vitals.hr} + {complaint}) → ESI 2"
                )

        # =================================================================
        # ELDERLY + FEVER + BORDERLINE HYPOTENSION → ESI 2 (SEPSIS)
        # =================================================================
        # Elderly (>=65) with fever and SBP<=100 suggests early sepsis.
        # =================================================================
        if (
            final_level > 2
            and age >= 65
            and vitals and vitals.sbp is not None and vitals.sbp <= 100
            and vitals and vitals.temp is not None and vitals.temp >= 37.8
        ):
            final_level = 2
            modifiers.append(
                f"⚠️ مسن + حمى + ضغط منخفض (SBP={vitals.sbp}, T={vitals.temp}) → مسار تعفن / "
                f"Elderly (age {age}) + fever ({vitals.temp}°C) + borderline hypotension (SBP {vitals.sbp}) → sepsis pathway → ESI 2"
            )

        # =================================================================
        # TEXT-BASED LIFE-THREAT SAFETY FLOOR — ESI 1 ESCALATION
        # =================================================================
        # If the clinical text contains explicit life-threat signals
        # (e.g., "intubated", "cardiac arrest", "unresponsive",
        # "hemodynamically unstable", "overdose", "seizure activity"),
        # force ESI 1 regardless of what keyword classification produced.
        #
        # This is the counterpart to apply_severity_ceiling: the ceiling
        # prevents FALSE escalation to ESI 1, while this floor prevents
        # FALSE de-escalation away from ESI 1.
        # =================================================================
        if final_level > 1:
            complaint_lower = _normalize_guardrail_text(complaint or "")
            life_threat_matches = [
                sig for sig in LIFE_THREAT_SIGNALS if sig in complaint_lower
            ]
            # Require at least one strong signal. "transfer" alone is not
            # sufficient — it must be paired with another life-threat signal.
            strong_matches = [
                m for m in life_threat_matches
                if m not in ("transfer", "altered mental status")
            ]
            if strong_matches:
                final_level = 1
                top_signals = strong_matches[:3]
                modifiers.append(
                    f"🚨 إشارات تهديد الحياة: {', '.join(top_signals)} / "
                    f"Life-threat signals detected: {', '.join(top_signals)} → ESI 1"
                )

        # =================================================================
        # TEXT-BASED INSTABILITY SAFETY FLOOR — ESI 2 ESCALATION
        # =================================================================
        # If the text contains instability signals (stroke symptoms, etc.)
        # and the case is currently ESI 3+, escalate to ESI 2.
        # =================================================================
        if final_level > 2:
            complaint_lower = _normalize_guardrail_text(complaint or "")
            instability_matches = [
                sig for sig in INSTABILITY_SIGNALS if sig in complaint_lower
            ]
            # Filter out weak/ambiguous signals
            strong_instability = [
                m for m in instability_matches
                if m not in ("tia", "spo2", "transferred to", "was transferred", "transfer from")
            ]
            # Some signals are definitive ESI 2 on their own (no threshold needed)
            DEFINITIVE_ESI2_SIGNALS = frozenset({
                "open fracture", "compound fracture", "bone exposed",
                "open tibia", "open femur", "open humerus",
                "open left tibia", "open right tibia",
                "open left femur", "open right femur",
                "acute stroke", "facial droop", "hemiplegia", "hemiparesis",
                "flaccid", "gaze deviation", "amnesia",
                "visual acuity", "visual abnormality", "vision abnormality",
                "melena", "hematemesis",
                "sepsis", "septic",
                "anaphylaxis", "anaphylactic",
                "dissection", "aortic dissection",
                "testicular torsion",
                # Arabic definitive ESI 2 signals
                "كسر مفتوح",                # open fracture
                "تسمم في الدم",              # sepsis
                "تعفن الدم",                 # sepsis
                "حادثة عربية",              # MVC (car accident)
                "أنبوبة الصدر",             # chest tube
                "انبوبة الصدر",             # chest tube (no hamza)
            })
            has_definitive = any(m in DEFINITIVE_ESI2_SIGNALS for m in strong_instability)

            if has_definitive or len(strong_instability) >= 2:
                final_level = 2
                top_signals = strong_instability[:3]
                modifiers.append(
                    f"⚠️ إشارات عدم استقرار: {', '.join(top_signals)} / "
                    f"Instability signals: {', '.join(top_signals)} → ESI 2"
                )

        # =================================================================
        # AGE-BASED RESPIRATORY SAFETY FLOOR
        # =================================================================
        # Elderly patients (>= 70) presenting with dyspnea have high
        # mortality risk regardless of initial vital stability. ESI protocol
        # and clinical guidelines recommend minimum ESI 2 for elderly
        # respiratory complaints.
        # =================================================================
        if final_level > 2 and age >= 65:
            complaint_lower_resp = (complaint or "").lower()
            _resp_signals = ("dyspnea", "shortness of breath", "breathing difficulty",
                             "can't breathe", "difficulty breathing", "ضيق تنفس",
                             "مش قادر اتنفس", "مش عارف آخد نفسي")
            if any(sig in complaint_lower_resp for sig in _resp_signals):
                final_level = 2
                modifiers.append(
                    "⚠️ مريض مسن + ضيق تنفس → مستوى 2 / "
                    "Elderly (>=65) + respiratory complaint → ESI 2 safety floor"
                )

        # =================================================================
        # DYSPNEA + HYPOXIA/INSTABILITY → ESI 2
        # =================================================================
        # Dyspnea with SpO2 < 95% or SBP <= 100 indicates respiratory or
        # hemodynamic compromise requiring emergent evaluation.
        # =================================================================
        if final_level > 2:
            complaint_lower_dh = (complaint or "").lower()
            _dyspnea_signals = ("dyspnea", "shortness of breath", "can't breathe",
                                "cannot breathe", "difficulty breathing",
                                "breathing difficulty", "acute dyspnea",
                                "ضيق تنفس", "مش قادر اتنفس")
            has_dyspnea = any(sig in complaint_lower_dh for sig in _dyspnea_signals)
            has_resp_instability = (
                (vitals and vitals.spo2 is not None and vitals.spo2 < 95)
                or (vitals and vitals.sbp is not None and vitals.sbp <= 100)
                or (vitals and vitals.hr is not None and vitals.hr >= 100)
            )
            if has_dyspnea and has_resp_instability:
                final_level = 2
                modifiers.append(
                    "⚠️ ضيق تنفس مع عدم استقرار فسيولوجي → مستوى 2 / "
                    "Dyspnea + physiologic instability → ESI 2 safety floor"
                )

        # =================================================================
        # MISSING-VITALS + RESPIRATORY COMPLAINT SAFETY FLOOR
        # =================================================================
        # When a patient presents with a respiratory complaint but NO vital
        # signs are available, assume worst case. Missing vitals for a
        # dyspneic patient suggests chaotic presentation (e.g. ambulance
        # arrival, too unstable to measure). Minimum ESI 2.
        # =================================================================
        if final_level > 2:
            complaint_lower_mv = (complaint or "").lower()
            _resp_mv_signals = ("dyspnea", "can't breathe", "cannot breathe",
                                "shortness of breath", "difficulty breathing",
                                "ضيق تنفس", "مش قادر اتنفس")
            has_resp_complaint = any(sig in complaint_lower_mv for sig in _resp_mv_signals)
            all_vitals_missing = (
                vitals is None
                or (
                    vitals.hr is None
                    and vitals.rr is None
                    and vitals.sbp is None
                    and vitals.spo2 is None
                )
            )
            if has_resp_complaint and all_vitals_missing:
                final_level = 2
                modifiers.append(
                    "⚠️ شكوى تنفسية بدون علامات حيوية → مستوى 2 / "
                    "Respiratory complaint + no vital signs available → ESI 2 safety floor"
                )

        # =================================================================
        # UPPER BACK PAIN IN OLDER ADULTS → ESI 2
        # =================================================================
        # Upper/mid back pain in patients >=50 can represent aortic
        # dissection or atypical MI. Minimum ESI 2 for safety.
        # =================================================================
        if final_level > 2:
            complaint_lower_bp = (complaint or "").lower()
            _upper_back_tokens = ("upper back pain", "mid back pain",
                                  "interscapular", "between shoulder blades",
                                  "وجع أعلى الظهر", "ألم أعلى الظهر", "وجع اعلى الظهر")
            if any(tok in complaint_lower_bp for tok in _upper_back_tokens) and age >= 50:
                final_level = 2
                modifiers.append(
                    "⚠️ ألم أعلى الظهر في مريض >=50 → فحص تسلخ/ACS / "
                    "Upper back pain in patient >=50 → dissection/ACS screening → ESI 2"
                )

        # Offline fallback safety policy for unrecognized complaints.
        requires_review = False
        review_message = ""
        complaint_text = (complaint or "").strip()
        if category == "unclear" and complaint_text:
            requires_review = True
            review_message = self.UNKNOWN_COMPLAINT_REVIEW_MESSAGE
            extreme_component_count = sum(
                1 for score in (news2_result.component_scores or {}).values() if score == 3
            )
            if news2_effective_total >= 7 or extreme_component_count >= 2:
                # Ultimate safety net for unknown complaints with high NEWS2.
                final_level = 1
                modifiers.append(
                    "شكوى غير معروفة + نيوز2 خطير (>=7 أو معياران شديدان) → إنعاش فوري / "
                    "Unrecognized complaint + critical NEWS2 (>=7 or >=2 extreme components) -> immediate resuscitation"
                )
            elif news2_effective_total >= 5:
                # Maintain at least urgent/emergent response for physiologic risk.
                final_level = min(final_level, 3)
            elif final_level > 3:
                # Conservative default for unknown complaints should never be ESI 4/5.
                final_level = 3
                modifiers.append(
                    "شكوى غير معروفة - تصنيف احتياطي محافظ مستوى 3 / "
                    "Unrecognized complaint - conservative fallback Level 3"
                )
        
        # Build decision path string for audit (bilingual)
        decision_path = (
            f"NEWS2+={news2_effective_total} (base={news2_result.total_score}, glucose={news2_plus_result['glucose_score']})→L{news2_effective_level} | "
            f"Category={category}→L{category_level} | "
            f"Modifiers→L{modifier_level} | "
            f"Final=L{final_level}"
        )
        
        decision_path_ar = (
            f"نيوز2+={news2_effective_total} (أساسي={news2_result.total_score}, جلوكوز={news2_plus_result['glucose_score']})→م{news2_effective_level} | "
            f"التصنيف={category_info.name_ar}→م{category_level} | "
            f"المعدلات→م{modifier_level} | "
            f"النهائي=م{final_level}"
        )
        
        decision_path_en = (
            f"NEWS2+={news2_effective_total} (base={news2_result.total_score}, glucose={news2_plus_result['glucose_score']})→L{news2_effective_level} | "
            f"Category={category_info.name_en}→L{category_level} | "
            f"Modifiers→L{modifier_level} | "
            f"Final=L{final_level}"
        )
        
        # Get level metadata
        level_info = self.LEVEL_INFO[final_level]
        
        # Combine alerts
        all_alerts_ar = news2_result.alerts_ar.copy()
        all_alerts_en = news2_result.alerts_en.copy()
        all_alerts_en.extend(esi_v5_alerts)

        # Surface glucose-specific risk signals in alert lists, not only modifiers.
        for glucose_flag in glucose_flags:
            alert_text = glucose_flag.get("alert")
            if alert_text:
                all_alerts_en.append(f"⚠️ {alert_text}")

        if category_level <= 2:
            all_alerts_ar.append(f"⚠️ {category_info.name_ar}")
            all_alerts_en.append(f"⚠️ {category_info.name_en}")
        
        rag_context = self._build_rag_context(
            complaint_text=complaint,
            comorbidities=patient_data.get('comorbidities'),
            k=3
        )

        return DeterministicTriageResult(
            final_level=final_level,
            extraction_method=str(extraction_method),
            color_code=level_info["color"],
            label_ar=level_info["label_ar"],
            label_en=level_info["label_en"],
            news2_score=news2_effective_total,
            news2_level=news2_effective_level,
            category=category,
            category_ar=category_info.name_ar,
            category_en=category_info.name_en,
            category_level=category_level,
            modifiers_applied=modifiers,
            alerts_ar=all_alerts_ar,
            alerts_en=all_alerts_en,
            missing_vitals=news2_result.missing_vitals,
            decision_path=decision_path,
            decision_path_ar=decision_path_ar,
            decision_path_en=decision_path_en,
            ai_used=(self.ai_classifier.model is not None),
            time_to_physician=level_info["time"],
            recommended_action_ar=level_info["action_ar"],
            recommended_action_en=level_info["action_en"],
            rag_context=rag_context,
            # ICD-10 coding for GAHAR compliance
            icd10_code=ICD10_MAPPING.get(category, {}).get("code", "R69"),
            icd10_description=ICD10_MAPPING.get(category, {}).get("description", "Illness, unspecified"),
            icd10_category=ICD10_MAPPING.get(category, {}).get("category", "Unspecified"),
            requires_review=requires_review,
            review_message=review_message,
        )
    
    def get_triage_level(self, patient_data: dict) -> int:
        """
        Simplified method returning just the triage level (1-5).
        For compatibility with existing test suite.
        """
        result = self.triage(patient_data)
        return result.final_level

    def evaluate(self, patient) -> 'TriageResult':
        """
        API-compatible method that returns TriageResult format.
        Converts from DeterministicTriageResult to TriageResult.
        
        Args:
            patient: PatientInput object from API
            
        Returns:
            TriageResult compatible with API response model
        """
        # Import here to avoid circular imports
        try:
            from models import TriageResult, TriageLevel
        except ImportError:
            from models import TriageResult, TriageLevel
        
        # Convert PatientInput to dict for internal triage method
        # PHASE 2 FIX: Include clinical risk factors for NEWS2 compliance
        patient_dict = {
            'age': patient.age,
            'gender': patient.gender.value if hasattr(patient.gender, 'value') else patient.gender,
            'chief_complaint_text': patient.chief_complaint_text,
            'vitals': {
                'hr': patient.vitals.hr,
                'rr': patient.vitals.rr,
                'spo2': patient.vitals.spo2,
                'sbp': patient.vitals.sbp,
                'dbp': patient.vitals.dbp,
                'temp': patient.vitals.temp,
                'blood_glucose': getattr(patient.vitals, 'blood_glucose', None),
                'pain_score': patient.vitals.pain_score
            } if patient.vitals else {},
            # ===== PHASE 2: Clinical Risk Factors =====
            'is_copd': getattr(patient, 'is_copd', False),
            'on_supplemental_o2': getattr(patient, 'on_supplemental_o2', False),
            'consciousness': getattr(patient, 'consciousness', 'A'),
            'is_pregnant': getattr(patient, 'is_pregnant', False),
            'gestational_weeks': getattr(patient, 'gestational_weeks', None),
            'pregnancy_complaint': getattr(patient, 'pregnancy_complaint', None),
            # Red flags are direct fields on PatientInput (not nested)
            'history_cardiac': getattr(patient, 'history_cardiac', False),
            'history_stroke': getattr(patient, 'history_stroke', False),
            'immuno_compromised': getattr(patient, 'immuno_compromised', False),
            'comorbidities': getattr(patient, 'comorbidities', None),
            # ===== ESI v5 Compliance Fields =====
            'pain_scale': getattr(patient, 'pain_scale', None),
            'pain_context': getattr(patient, 'pain_context', None),
            'is_immunocompromised': getattr(patient, 'is_immunocompromised', False),
            'immunocompromised_reason': getattr(patient, 'immunocompromised_reason', None),
            'immunizations_complete': getattr(patient, 'immunizations_complete', True),
        }
        
        # Get internal result
        internal_result = self.triage(patient_dict)
        
        # Build reasoning list (bilingual)
        reasoning = []
        reasoning_ar = []
        reasoning_en = []
        
        # Add category info
        reasoning_ar.append(f"التصنيف: {internal_result.category_ar}")
        reasoning_en.append(f"Category: {internal_result.category_en}")
        reasoning.append(f"التصنيف: {internal_result.category_ar} / Category: {internal_result.category_en}")
        
        # Add NEWS2 if significant
        if internal_result.news2_score > 0:
            reasoning_ar.append(f"نيوز2: {internal_result.news2_score} نقاط")
            reasoning_en.append(f"NEWS2: {internal_result.news2_score} points")
            reasoning.append(f"نيوز2: {internal_result.news2_score} نقاط / NEWS2: {internal_result.news2_score} points")
        
        # Add modifiers
        for mod in internal_result.modifiers_applied:
            reasoning.append(mod)
            if ' / ' in mod:
                reasoning_ar.append(mod.split(' / ')[0])
                reasoning_en.append(mod.split(' / ')[1])
            else:
                reasoning_ar.append(mod)
                reasoning_en.append(mod)
        
        # Map level to TriageLevel enum
        level_map = {
            1: TriageLevel.RESUSCITATION,
            2: TriageLevel.EMERGENT,
            3: TriageLevel.URGENT,
            4: TriageLevel.LESS_URGENT,
            5: TriageLevel.NON_URGENT
        }
        
        # Color codes
        color_map = {
            1: "#ef4444",  # Red
            2: "#f97316",  # Orange
            3: "#eab308",  # Yellow
            4: "#22c55e",  # Green
            5: "#3b82f6"   # Blue
        }
        
        return TriageResult(
            level=level_map.get(internal_result.final_level, TriageLevel.URGENT),
            color_code=color_map.get(internal_result.final_level, "#eab308"),
            label_ar=internal_result.label_ar,
            label_en=internal_result.label_en,
            extraction_method=internal_result.extraction_method,
            description_ar=internal_result.category_ar,
            description_en=internal_result.category_en,
            description=f"{internal_result.category_ar} / {internal_result.category_en}",
            action_ar=internal_result.recommended_action_ar,
            action_en=internal_result.recommended_action_en,
            recommended_action=f"{internal_result.recommended_action_ar} / {internal_result.recommended_action_en}",
            time_ar=internal_result.time_to_physician.split(' / ')[0] if ' / ' in internal_result.time_to_physician else internal_result.time_to_physician,
            time_en=internal_result.time_to_physician.split(' / ')[1] if ' / ' in internal_result.time_to_physician else internal_result.time_to_physician,
            time_to_physician=internal_result.time_to_physician,
            red_flags=internal_result.alerts_en + internal_result.alerts_ar,
            reasoning_ar=reasoning_ar,
            reasoning_en=reasoning_en,
            reasoning=reasoning,
            confidence="High" if not internal_result.ai_used else "Medium",
            rag_context=internal_result.rag_context,
            requires_review=internal_result.requires_review,
            review_message=internal_result.review_message,
            # ICD-10 coding for GAHAR compliance
            icd10_code=internal_result.icd10_code,
            icd10_description=internal_result.icd10_description,
            icd10_category=internal_result.icd10_category
        )



# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def create_triage_engine() -> DeterministicTriageEngine:
    """Factory function to create a configured triage engine."""
    return DeterministicTriageEngine()


def quick_triage(
    complaint: str,
    age: float = 30,
    gender: str = "male",
    hr: int = None,
    rr: int = None,
    spo2: float = None,
    sbp: int = None,
    temp: float = None,
    consciousness: str = "A",
    pain_score: int = 0
) -> DeterministicTriageResult:
    """
    Convenience function for quick triage assessment.
    
    Example:
        result = quick_triage(
            complaint="عندي ألم في صدري",
            age=55,
            hr=110,
            sbp=90
        )
        print(f"Level: {result.final_level}, Path: {result.decision_path}")
    """
    engine = DeterministicTriageEngine()
    return engine.triage({
        'age': age,
        'gender': gender,
        'chief_complaint_text': complaint,
        'vitals': {
            'hr': hr,
            'rr': rr,
            'spo2': spo2,
            'sbp': sbp,
            'temp': temp,
            'pain_score': pain_score
        },
        'consciousness': consciousness
    })


# =============================================================================
# MODULE TEST
# =============================================================================

if __name__ == "__main__":
    print("=" * 70)
    print("SAFE-Triage - Deterministic Hybrid Engine Test")
    print("NEWS2 + ESI with Constrained AI Classification")
    print("=" * 70)
    
    engine = DeterministicTriageEngine()
    
    test_cases = [
        # Level 1 tests
        {
            "name": "Unconscious patient",
            "data": {
                "age": 45,
                "gender": "male",
                "chief_complaint_text": "فاقد الوعي",
                "vitals": {},
                "consciousness": "U"
            },
            "expected": 1
        },
        {
            "name": "Cardiac arrest",
            "data": {
                "age": 60,
                "gender": "female",
                "chief_complaint_text": "قلبه وقف",
                "vitals": {}
            },
            "expected": 1
        },
        
        # Level 2 tests
        {
            "name": "Chest pain - elderly",
            "data": {
                "age": 70,
                "gender": "male",
                "chief_complaint_text": "صدري بيوجعني من ساعة",
                "vitals": {"hr": 95, "sbp": 150, "rr": 20, "spo2": 96}
            },
            "expected": 2
        },
        {
            "name": "High NEWS2 score",
            "data": {
                "age": 50,
                "gender": "female",
                "chief_complaint_text": "عندي سخونية",
                "vitals": {"hr": 135, "sbp": 85, "rr": 26, "spo2": 92, "temp": 39.5}
            },
            "expected": 2
        },
        
        # Level 3 tests
        {
            "name": "Abdominal pain",
            "data": {
                "age": 35,
                "gender": "female", 
                "chief_complaint_text": "بطني بتوجعني جدا من امبارح",
                "vitals": {"hr": 88, "sbp": 120, "rr": 18, "spo2": 98, "temp": 37.8}
            },
            "expected": 3
        },
        
        # Level 4 tests
        {
            "name": "Minor trauma",
            "data": {
                "age": 25,
                "gender": "male",
                "chief_complaint_text": "وقعت وايدي وارمة شوية",
                "vitals": {"hr": 80, "sbp": 120, "rr": 16, "spo2": 99}
            },
            "expected": 4
        },
        
        # Level 5 tests
        {
            "name": "Prescription refill",
            "data": {
                "age": 45,
                "gender": "male",
                "chief_complaint_text": "عايز أجدد الروشتة بتاعتي",
                "vitals": {"hr": 72, "sbp": 125, "rr": 14, "spo2": 99}
            },
            "expected": 5
        },
        
        # Missing vitals test
        {
            "name": "Missing vitals - should still triage",
            "data": {
                "age": 40,
                "gender": "female",
                "chief_complaint_text": "عندي صداع",
                "vitals": {}
            },
            "expected": 4  # Mild complaint, no concerning vitals data
        },
    ]
    
    passed = 0
    failed = 0
    
    for test in test_cases:
        result = engine.triage(test["data"])
        status = "✅ PASS" if result.final_level == test["expected"] else "❌ FAIL"
        
        if result.final_level == test["expected"]:
            passed += 1
        else:
            failed += 1
        
        print(f"\n{status} | {test['name']}")
        print(f"       Expected: Level {test['expected']} | Got: Level {result.final_level}")
        print(f"       Path: {result.decision_path}")
        if result.missing_vitals:
            print(f"       Missing: {', '.join(result.missing_vitals)}")
    
    print("\n" + "=" * 70)
    print(f"RESULTS: {passed} passed, {failed} failed out of {len(test_cases)} tests")
    print("=" * 70)
