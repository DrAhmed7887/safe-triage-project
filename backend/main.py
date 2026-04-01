from fastapi import FastAPI, HTTPException, Depends, UploadFile, File, Form, Header, Body
from fastapi.responses import StreamingResponse, JSONResponse
from validators import validate_gender_complaint
from audit_service import audit_service
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any, Tuple
import tempfile
import os
import io
import re
import time
import uuid
from pathlib import Path
from datetime import datetime, timedelta
from threading import Lock
from pydantic import BaseModel

from google.oauth2 import id_token
from google.auth.transport import requests as google_requests

from models import (
    PatientInput,
    TriageResult,
    TriageConfirmationRequest,
    TriageConfirmationStart,
    TriageConfirmationPending,
)
from logic.deterministic_triage import DeterministicTriageEngine, VitalSignsValidator
from database import engine, Base, get_db
from sql_models import Patient
import uvicorn
from ai_service import ai_service, ComplaintValidator
from medasr_service import medasr_service
from alert_service import (
    AlertLevel,
    GAHAR_NOTICE,
    send_alert_sync,
    flush_alert_queue_sync,
    get_queue_size,
    register_fcm_device,
    retry_queued_alerts,
    get_queue_status,
    get_notification_config_status,
)
from logic.icd10_integration import enrich_triage_with_icd10, check_silent_mi_pattern, format_icd10_for_hospital_record
from logic.esi_v5_engine import (
    triage_patient as run_esi_v5_triage,
    PatientFeatures as ESIv5PatientFeatures,
    VitalSigns as ESIv5VitalSigns,
    NEWS2Result as ESIv5NEWS2Result,
)
from logic.english_keyword_sqlite import (
    keyword_row_count,
    load_keyword_index_from_sqlite,
    load_keywords_json_to_sqlite,
)
from qa_agent import qa_agent
from report_service import (
    generate_daily_report,
    export_triage_csv_with_metadata,
    export_system_wide_csv,
    PERSONAL_EXPORT_SCOPE,
    SYSTEM_EXPORT_SCOPE,
)
from resource_labels import get_resources_for_category, get_resources_for_workup
from monitor_service import register_monitor_service
from analytics_service import register_analytics_service, require_supervisor_role
from medgemma_hourly_job import run_hourly_job
from stats_service import (
    get_triage_stats as get_periodic_stats,
    get_realtime_shift_stats,
)

# Create Tables
Base.metadata.create_all(bind=engine)

app = FastAPI(title="SAFE-Triage AI System", version="2.0.0")

# CORS Setup
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://safe-triage-ai.web.app",
        "https://safe-triage-ai.firebaseapp.com",
        "http://localhost:5173",  # Vite dev server
        "http://localhost:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

register_monitor_service(app)
register_analytics_service(app)

# Use the deterministic engine with keyword database
# STANDARD MODE: No AI, only keyword matching (fast)
engine_logic = DeterministicTriageEngine(use_ai=False)

# AI-ENHANCED MODE: Uses AI classification with fallback
engine_logic_ai = DeterministicTriageEngine(use_ai=True)

ENGLISH_KEYWORD_JSON_PATH = Path(__file__).resolve().parent / "logic" / "english_clinical_keywords.json"
ENGLISH_KEYWORD_INDEX: Dict[str, Dict[str, Any]] = {}

# Warmup to reduce cold starts
@app.on_event("startup")
async def startup_warmup():
    """Preload heavy resources to reduce cold start latency."""
    global ENGLISH_KEYWORD_INDEX
    try:
        if ENGLISH_KEYWORD_JSON_PATH.exists():
            print("🔥 Warmup: loading english_clinical_keywords into sqlite", flush=True)
            loaded_count = load_keywords_json_to_sqlite(ENGLISH_KEYWORD_JSON_PATH)
            ENGLISH_KEYWORD_INDEX = load_keyword_index_from_sqlite()
            print(
                f"✅ English keyword rows loaded/updated={loaded_count}, indexed={len(ENGLISH_KEYWORD_INDEX)}",
                flush=True,
            )
        else:
            existing_count = keyword_row_count()
            ENGLISH_KEYWORD_INDEX = load_keyword_index_from_sqlite()
            print(
                f"ℹ️ English keyword JSON not found at {ENGLISH_KEYWORD_JSON_PATH}; "
                f"using existing sqlite rows={existing_count}",
                flush=True,
            )
    except Exception as e:
        print(f"Warmup english keyword load failed: {e}", flush=True)

    try:
        print("🔥 Warmup: initializing UMLS cache", flush=True)
        ai_service.umls_rag.search_snomed("chest pain")
    except Exception as e:
        print(f"Warmup UMLS failed: {e}", flush=True)

    try:
        print("🔥 Warmup: deterministic engine", flush=True)
        engine_logic.triage(
            {
                "age": 30,
                "gender": "male",
                "chief_complaint_text": "warmup",
                "vitals": {"hr": 80, "sbp": 120, "dbp": 80, "rr": 16, "temp": 37, "spo2": 98},
            }
        )
    except Exception as e:
        print(f"Warmup deterministic engine failed: {e}", flush=True)

# ============ HUMAN CONFIRMATION PLACEHOLDERS ============
CONFIRMATION_TIMEOUT_SECONDS = int(os.getenv("CONFIRMATION_TIMEOUT_SECONDS", "300"))
SUPERVISOR_PIN = os.getenv("SUPERVISOR_PIN", "0000")
DOWNGRADE_ROLE = os.getenv("DOWNGRADE_ROLE", "supervisor")

_pending_lock = Lock()
_pending_confirmations = {}
TEMP_ID_PATTERN = re.compile(r"^TEMP-\d{8}-[A-Z0-9]{4}$")


class FCMTokenRequest(BaseModel):
    token: str
    user_id: str
    role: str

IMMEDIATE_TRIAGE_KEYWORDS = [
    "صدر",
    "chest",
    "نفس",
    "breath",
    "دم",
    "blood",
    "وعي",
    "conscious",
    "اتنفس",
    "قلب",
    "heart",
    "تشنج",
    "seizure",
    "حادث",
    "accident",
    "طعن",
    "stab",
    "طلق",
    "gun",
    "حامل",
    "pregnant",
    "سم",
    "poison",
    "بلع",
    "swallow",
    "اموت",
    "die",
    "نزيف",
    "bleed",
    "stroke",
    "جلطة",
    "سكتة",
    "وشي مايل",
    "وشه مايل",
    "وشي اتعوج",
    "وشه اتعوج",
    "نص وشي وقع",
    "نص وشه وقع",
    "نص جسمي مش بيتحرك",
    "نص جسمه مش بيتحرك",
    "مش قادر اتكلم",
    "مش قادر أتكلم",
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
    "slurred speech",
    "unable to speak",
    "cannot speak",
    "can't speak",
    "facial droop",
    "arm weakness",
]

STROKE_EXPLICIT_TOKENS = [
    "stroke",
    "cva",
    "aphasia",
    "dysarthria",
    "speech loss",
    "slurred speech",
    "speech difficulty",
    "difficulty speaking",
    "inability to speak",
    "unable to speak",
    "cannot speak",
    "can't speak",
    "sudden inability to speak",
    "جلطة",
    "جلطه",
    "سكتة",
    "سكتة دماغية",
    "جلطة في المخ",
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
]

STROKE_SPEECH_HIGH_RISK_TOKENS = [
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
]

STROKE_SINGLE_FAST_TOKENS = [
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
    "hemiplegia",
    "hemiparesis",
    "نص جسمي مش بيتحرك",
    "نص جسمه مش بيتحرك",
    "ايدي مش بتتحرك",
    "ايده مش بتتحرك",
    "رجلي مش بتتحرك",
    "ايده وقعت",
    "ايدي وقعت",
]

STROKE_SPEECH_TOKENS = [
    "speech",
    "slurred",
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
]

STROKE_FACE_TOKENS = [
    "facial droop",
    "face droop",
    "face drooping",
    "facial asymmetry",
    "وش",
    "وشي",
    "وشه",
    "مايل",
    "اتعوج",
    "معوج",
]

STROKE_WEAKNESS_TOKENS = [
    "arm weakness",
    "one side weakness",
    "one sided weakness",
    "one-sided weakness",
    "hemiplegia",
    "hemiparesis",
    "نص جسمي",
    "نص جسمه",
    "مش بيتحرك",
    "ايدي مش بتتحرك",
    "ايده مش بتتحرك",
    "رجلي مش بتتحرك",
    "ايده وقعت",
]

STROKE_SUDDEN_TOKENS = [
    "sudden",
    "acute",
    "abrupt",
    "فجأة",
    "فجاه",
    "فجاة",
    "من شوية",
    "لسه",
    "دلوقتي",
    "النهارده",
]

MI_REASONING_TOKENS = [
    "myocardial",
    "heart attack",
    "acute coronary",
    "acs",
    "ذبحة",
    "جلطة قلبية",
    "جلطة في القلب",
    "الم صدر",
    "ألم صدر",
]

SEPSIS_REASONING_TOKENS = [
    "sepsis",
    "septic",
    "septic shock",
    "تعفن",
    "تسمم",
    "تجرثم",
]

AIRWAY_REASONING_TOKENS = [
    "airway",
    "cannot breathe",
    "can't breathe",
    "respiratory distress",
    "مجرى الهواء",
    "اختناق",
    "مش قادر اتنفس",
    "مش قادر أتنفس",
]

TIME_CRITICAL_CATEGORIES = {
    "stroke",
    "stroke_symptoms",
    "neurological_emergency",
    "chest_pain",
    "chest_pain_cardiac",
    "cardiac",
    "sepsis",
    "sepsis_concern",
    "respiratory_distress",
    "airway",
    "airway_obstruction",
    "anaphylaxis",
    "seizure",
    "trauma_major",
    "major_trauma",
    "silent_mi",
}

CRITICAL_REASONING_TOKENS = [
    "stroke",
    "جلطة",
    "سكتة",
    "myocardial",
    "heart attack",
    "sepsis",
    "pulmonary embolism",
    "aneurysm",
    "meningitis",
    "airway",
    "neurological",
    "aphasia",
    "speech",
    "كلام",
    "نطق",
]

AI_CATEGORY_ALIASES = {
    "respiratory": "uri_symptoms",
    "respiratory_symptoms": "uri_symptoms",
    "upper_respiratory_infection": "uri_symptoms",
    "uri": "uri_symptoms",
    "dyspnea": "respiratory_distress",
    "moderate_dyspnea": "respiratory_distress",
    "cardiac": "chest_pain_cardiac",
    "chest_pain": "chest_pain_cardiac",
    "neurological": "stroke_symptoms",
    "stroke": "stroke_symptoms",
    "gi": "abdominal_pain",
    "followup": "follow_up",
    "non_urgent_consultation": "minor_complaint",
    "simple_non_urgent_consultation": "minor_complaint",
    "simple_consultation": "minor_complaint",
}

AI_RESPIRATORY_DISTRESS_TOKENS = [
    "shortness of breath",
    "cannot breathe",
    "can't breathe",
    "can not breathe",
    "difficulty breathing",
    "dyspnea",
    "respiratory distress",
    "air hunger",
    "ضيق نفس",
    "مش قادر اتنفس",
    "مش قادر أتنفس",
    "اختناق",
    "نهجان شديد",
]

AI_NEGATED_RESPIRATORY_TOKENS = [
    "without respiratory distress",
    "no respiratory distress",
    "denies respiratory distress",
    "no shortness of breath",
    "without shortness of breath",
    "denies shortness of breath",
    "without dyspnea",
    "بدون ضيق نفس",
    "لا يوجد ضيق نفس",
    "مافيش ضيق نفس",
]

AI_LOW_ACUITY_RESPIRATORY_TOKENS = [
    "runny nose",
    "common cold",
    "cold",
    "flu",
    "cough",
    "mild cough",
    "sore throat",
    "nasal congestion",
    "رشح",
    "زكام",
    "برد",
    "كحة",
    "التهاب حلق",
]

AI_SORE_THROAT_TOKENS = [
    "sore throat",
    "throat pain",
    "التهاب حلق",
    "وجع حلق",
    "حلق",
]

AI_NON_URGENT_TOKENS = [
    "non urgent",
    "non-urgent",
    "simple consultation",
    "routine consultation",
    "routine check",
    "check up",
    "consultation",
    "administrative",
    "minor complaint",
    "غير عاجل",
    "غير طارئ",
    "استشارة",
    "فحص",
]

AI_FOLLOW_UP_TOKENS = [
    "follow up",
    "follow-up",
    "review visit",
    "متابعة",
]

AI_REFILL_TOKENS = [
    "prescription refill",
    "medication refill",
    "refill",
    "renew prescription",
    "تجديد روشتة",
    "تجديد علاج",
    "روشتة",
]

AI_MILD_GI_TOKENS = [
    "indigestion",
    "heartburn",
    "dyspepsia",
    "epigastric discomfort",
    "حرقان",
    "حموضة",
    "عسر هضم",
]

AI_HIGH_RISK_GI_TOKENS = [
    "severe abdominal pain",
    "abdominal guarding",
    "rebound tenderness",
    "persistent vomiting",
    "blood in stool",
    "hematemesis",
    "melena",
    "قيء مستمر",
    "قيء دم",
    "براز اسود",
    "الم بطن شديد",
    "ألم بطن شديد",
]

AI_ABDOMINAL_PAIN_TOKENS = [
    "abdominal pain",
    "abd pain",
    "abdomen pain",
    "pain abdomen",
    "stomach pain",
    "belly pain",
    "abdominal discomfort",
    "abd discomfort",
    "وجع بطن",
    "الم بطن",
    "ألم بطن",
    "بطني",
]

AI_BACK_PAIN_TOKENS = [
    "back pain",
    "lower back pain",
    "low back pain",
    "lower back",
    "low back",
    "lumbar pain",
    "musculoskeletal back pain",
    "flank pain",
    "pain in back",
    "وجع ظهر",
    "الم ظهر",
    "ألم ظهر",
    "اسفل الظهر",
]

ENGLISH_COMPLAINT_SPLIT_PATTERN = re.compile(r"[,;&+]|\s+w/|\s+and\s+|\s+with\s+", re.IGNORECASE)
ENGLISH_ABBREVIATIONS = {
    "cp": "chest pain",
    "sob": "shortness of breath",
    "n/v": "nausea vomiting",
    "n+v": "nausea vomiting",
    "ams": "altered mental status",
    "etoh": "alcohol intoxication",
    "mvc": "motor vehicle collision",
    "mva": "motor vehicle accident",
    "abd pain": "abdominal pain",
    "abd": "abdominal",
    "h/a": "headache",
    "ha": "headache",
    "sz": "seizure",
    "si": "suicidal ideation",
    "uti": "urinary tract infection",
    "uri": "upper respiratory infection",
    "lbp": "low back pain",
    "gi bleed": "gastrointestinal bleeding",
    "fb": "foreign body",
    "lac": "laceration",
    "fx": "fracture",
    "inj": "injury",
    "lle": "left lower extremity pain",
    "rle": "right lower extremity pain",
}
ENGLISH_STOP_WORDS = {
    "pt",
    "patient",
    "c/o",
    "complains",
    "of",
    "states",
    "reports",
    "s/p",
    "hx",
    "the",
    "a",
    "an",
    "for",
    "to",
    "er",
    "ed",
    "eval",
    "evaluation",
    "follow",
    "up",
    "f/u",
}

LOW_ACUITY_BACK_PAIN_KEYWORDS = {
    "back pain",
    "lower back pain",
    "low back pain",
    "lumbar pain",
    "musculoskeletal back pain",
}

AI_FEVER_TOKENS = [
    "fever",
    "febrile",
    "temperature",
    "temp",
    "حمى",
    "سخونية",
    "سخونه",
    "حرارة",
]

RESOURCE_URINARY_RETENTION_TOKENS = [
    "urinary retention",
    "acute urinary retention",
    "retention of urine",
    "احتباس بول",
]

RESOURCE_WOUND_LACERATION_TOKENS = [
    "wound eval",
    "wound evaluation",
    "wound",
    "laceration",
    "abrasion",
    "جرح",
    "قطع",
]

RESOURCE_WOUND_FOLLOW_UP_TOKENS = [
    "wound check",
    "post op wound",
    "post-op wound",
    "suture removal",
    "dressing change",
]

RESOURCE_WOUND_COMPLEXITY_TOKENS = [
    "deep laceration",
    "complex laceration",
    "foreign body",
    "tendon",
    "neurovascular",
    "open fracture",
    "fracture",
    "dislocation",
    "crush injury",
    "penetrating injury",
    "head injury",
    "loss of consciousness",
    "motor vehicle collision",
    "gunshot",
    "stab",
    "جرح عميق",
    "جرح معقد",
    "كسر",
    "خلع",
    "اصابة سحق",
    "فقدان الوعي",
]

RESOURCE_WOUND_SHORT_TOKEN_PATTERN = re.compile(r"\b(?:lac|lacs|cut|cuts)\b", re.IGNORECASE)

RESOURCE_EXPECTED_ALIASES = {
    "labs": "labs",
    "lab": "labs",
    "blood_work": "labs",
    "bloodwork": "labs",
    "urinalysis": "labs",
    "cultures": "labs",
    "ecg": "ecg",
    "ekg": "ecg",
    "electrocardiogram": "ecg",
    "imaging": "imaging",
    "xray": "imaging",
    "x_ray": "imaging",
    "ct": "imaging",
    "ultrasound": "imaging",
    "mri": "imaging",
    "iv_meds_or_fluids": "iv_meds_or_fluids",
    "iv_meds": "iv_meds_or_fluids",
    "iv_fluids": "iv_meds_or_fluids",
    "iv_medications": "iv_meds_or_fluids",
    "procedure": "procedure",
    "sutures": "procedure",
    "splinting": "procedure",
    "catheter": "procedure",
    "foley": "procedure",
    "i_d": "procedure",
    "specialty_consult": "specialty_consult",
    "consult": "specialty_consult",
    "consultation": "specialty_consult",
    "monitoring": "monitoring",
    "cardiac_monitoring": "monitoring",
    "continuous_pulse_ox": "monitoring",
}

CRITICAL_TRANSFER_KEYWORDS = [
    "transfer",
    "transferred",
    "xfer",
    "direct admit",
    "outside hospital",
    "osh",
]

CRITICAL_PSYCH_EMERGENCY_KEYWORDS = [
    "suicidal",
    "suicidal ideation",
    "suicide",
    "suicide attempt",
    "self harm",
    "self-harm",
    "wants to die",
    "kill myself",
    "homicidal",
    "homicidal ideation",
    "انتحار",
    "عايز اموت",
    "عاوز اموت",
    "بياذي نفسه",
    "بيأذي نفسه",
    "محاولة انتحار",
]

CRITICAL_PSYCH_EMERGENCY_ABBREVIATIONS = ("si", "hi")

CRITICAL_GI_BLEED_KEYWORDS = [
    "brbpr",
    "bright red blood per rectum",
    "rectal bleeding",
    "gi bleed",
    "gi bleeding",
    "gastrointestinal bleed",
    "hematemesis",
    "vomiting blood",
    "vomited blood",
    "melena",
    "black stool",
    "black tarry stool",
    "bloody stool",
    "coffee ground",
    "coffee-ground emesis",
    "blood in stool",
    "hematochezia",
    "دم في البراز",
    "نزيف شرجي",
    "بيرجع دم",
    "براز اسود",
    "نزيف من المعدة",
]

CRITICAL_BLEEDING_KEYWORDS = [
    "bleed",
    "blood",
    "brbpr",
    "hematemesis",
    "melena",
    "hemorrhag",
    "نزيف",
    "دم",
]

CRITICAL_SAFETY_CATEGORIES = {
    "transfer_patient",
    "psychiatric_emergency",
    "gi_bleed",
    "hemorrhagic_shock_risk",
}

CRITICAL_FLOOR_NAME_BY_CATEGORY = {
    "transfer_patient": "transfer",
    "psychiatric_emergency": "psych_si_hi",
    "gi_bleed": "gi_bleed",
    "hemorrhagic_shock_risk": "tachycardia_bleeding",
}

AI_OBJECTIVE_RED_FLAG_HINTS = {
    "stroke",
    "facial_droop",
    "arm_weakness",
    "slurred_speech",
    "chest_pain",
    "radiation_to_arm",
    "radiation_to_jaw",
    "respiratory_distress",
    "dyspnea",
    "airway",
    "sepsis",
    "shock",
    "severe_bleeding",
    "hemorrhage",
    "altered_mental_status",
    "anaphylaxis",
    "ectopic",
    "pregnancy_risk",
    "dka",
    "severe_hypoglycemia",
    "silent_mi",
    "atypical_acs",
}

UNCLEAR_BODY_SYSTEM_VALUES = {
    "",
    "unclear",
    "unclear_needs_evaluation",
    "insufficient_information",
    "unknown",
    "general",
    "other",
    "none",
    "null",
    "n/a",
    "na",
}


class ExportDateRange(BaseModel):
    start: Optional[datetime] = None
    end: Optional[datetime] = None


def _normalize_match_text(value: str) -> str:
    return (
        (value or "")
        .strip()
        .lower()
        .replace("أ", "ا")
        .replace("إ", "ا")
        .replace("آ", "ا")
    )


def _has_vitals_for_triage(patient: PatientInput) -> bool:
    if not patient.vitals:
        return False
    for field in ("hr", "sbp", "rr", "spo2", "temp", "dbp", "gcs"):
        value = getattr(patient.vitals, field, None)
        if value is None:
            continue
        if isinstance(value, str) and not value.strip():
            continue
        try:
            if float(value) == 0:
                continue
        except (TypeError, ValueError):
            pass
        return True
    return False


def _has_immediate_triage_keyword(complaint_text: str) -> bool:
    normalized = _normalize_match_text(complaint_text)
    return any(_normalize_match_text(keyword) in normalized for keyword in IMMEDIATE_TRIAGE_KEYWORDS)


def _contains_any_token(text: str, tokens: List[str]) -> bool:
    normalized = _normalize_match_text(text)
    return any(_normalize_match_text(token) in normalized for token in tokens)


def _contains_wound_laceration_signal(text: str) -> bool:
    normalized = _normalize_match_text(text)
    if _contains_any_token(normalized, RESOURCE_WOUND_LACERATION_TOKENS):
        return True
    return bool(RESOURCE_WOUND_SHORT_TOKEN_PATTERN.search(normalized))


def _safe_float(value: Any) -> Optional[float]:
    try:
        if value is None:
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _atomize_compound_complaint(text: str) -> List[str]:
    if not text:
        return []
    parts = ENGLISH_COMPLAINT_SPLIT_PATTERN.split(str(text).lower().strip())
    cleaned = [part.strip() for part in parts if len(part.strip()) > 1]
    if not cleaned:
        return [str(text).strip().lower()]
    return list(dict.fromkeys(cleaned))


def _expand_english_abbreviations(text: str) -> str:
    expanded = f" {text} "
    for src, dst in sorted(ENGLISH_ABBREVIATIONS.items(), key=lambda item: len(item[0]), reverse=True):
        expanded = re.sub(rf"\b{re.escape(src)}\b", dst, expanded)
    return expanded.strip()


def _normalize_english_fragment(fragment: str) -> str:
    text = _expand_english_abbreviations(str(fragment or "").lower().strip())
    text = re.sub(r"[^a-z0-9\s/+.-]", " ", text)
    text = text.replace("/", " ").replace("+", " ").replace("-", " ")
    tokens = [token for token in re.split(r"\s+", text) if token]
    filtered_tokens = [token for token in tokens if token not in ENGLISH_STOP_WORDS]
    return " ".join(filtered_tokens).strip()


def _apply_english_compound_overrides(
    complaint_text: str,
    aggregated_match: Dict[str, Any],
) -> Dict[str, Any]:
    normalized_compound = _normalize_english_fragment(complaint_text or "")
    raw_lower = str(complaint_text or "").lower()

    matched_keywords = set(str(item).strip().lower() for item in (aggregated_match.get("matched_keywords") or []))
    base_esi = int(aggregated_match.get("base_esi", 3) or 3)
    resource_estimate = int(aggregated_match.get("resource_estimate", 2) or 2)
    is_red_flag = bool(aggregated_match.get("is_red_flag", False))
    risk_tiers = set(str(item).strip().lower() for item in (aggregated_match.get("risk_tiers") or []) if str(item).strip())

    def _has(token: str) -> bool:
        token_n = token.strip().lower()
        return token_n in normalized_compound or token_n in raw_lower

    def _apply(label: str, *, base: int, resource: int, red_flag: bool) -> None:
        nonlocal base_esi, resource_estimate, is_red_flag
        matched_keywords.add(label)
        base_esi = min(base_esi, int(base))
        resource_estimate = max(resource_estimate, int(resource))
        is_red_flag = bool(is_red_flag or red_flag)
        risk_tiers.add("compound_override")

    if _has("gunshot wound") or _has("gsw"):
        _apply("gunshot wound", base=2, resource=3, red_flag=True)
        _apply("gsw", base=2, resource=3, red_flag=True)

    if _has("word finding difficulty"):
        _apply("word finding difficulty", base=2, resource=3, red_flag=True)

    if _has("scalp lac") or _has("scalp laceration"):
        _apply("scalp lac", base=3, resource=2, red_flag=False)

    has_back_pain = _has("back pain") or _has("low back pain") or _has("lower back pain")
    if (
        (_has("mva") or _has("mvc") or _has("motor vehicle accident") or _has("motor vehicle collision"))
        and not has_back_pain
    ):
        _apply("mva mvc", base=3, resource=2, red_flag=False)

    has_numbness = _has("numbness")
    has_fall = _has("fall") or _has("s p fall")
    has_etoh = _has("etoh") or _has("alcohol intoxication")
    has_lac = _has("laceration") or _has("lac") or _has("wound")
    has_back_cancer = _has("cancer") or _has("malignancy") or _has("tumor")
    has_back_urinary_red_flag = _has("oliguria") or _has("urinary retention") or _has("incontinence")
    has_back_leg_weakness = _has("weakness in legs") or _has("leg weakness") or _has("bilateral leg weakness")
    has_transfer = _has("transfer")

    if has_back_pain and (has_numbness or has_back_cancer or has_back_urinary_red_flag or has_back_leg_weakness):
        _apply("back pain + numbness", base=2, resource=3, red_flag=True)

    if has_back_pain and has_fall:
        _apply("back pain + fall", base=3, resource=2, red_flag=False)

    if has_back_pain and has_transfer:
        _apply("back pain + transfer", base=3, resource=2, red_flag=False)

    if has_etoh and has_fall and has_lac:
        _apply("etoh + fall + laceration", base=3, resource=2, red_flag=False)

    if (_has("sore throat") or _has("throat pain")) and _has("abscess"):
        _apply("sore throat + abscess", base=2, resource=3, red_flag=True)

    return {
        "matched_keywords": sorted(matched_keywords),
        "base_esi": int(base_esi),
        "is_red_flag": bool(is_red_flag),
        "resource_estimate": int(resource_estimate),
        "risk_tiers": sorted(risk_tiers),
    }


def _lookup_english_keyword_matches(complaint_text: str) -> Optional[Dict[str, Any]]:
    if not ENGLISH_KEYWORD_INDEX:
        return None
    matches: List[Tuple[str, Dict[str, Any]]] = []
    exact_match_terms: List[str] = []
    inferred_match_terms: List[str] = []
    keyword_items = list(ENGLISH_KEYWORD_INDEX.items())
    for fragment in _atomize_compound_complaint(complaint_text):
        normalized = _normalize_english_fragment(fragment)
        if not normalized:
            continue
        row = ENGLISH_KEYWORD_INDEX.get(normalized)
        if row:
            matches.append((normalized, row))
            exact_match_terms.append(normalized)
            continue

        best_keyword: Optional[str] = None
        best_row: Optional[Dict[str, Any]] = None
        best_length = 0
        best_coverage = 0.0
        for keyword, candidate_row in keyword_items:
            if len(keyword) < 4:
                continue
            if keyword in normalized:
                coverage = len(keyword) / max(len(normalized), 1)
                if coverage < 0.80:
                    continue
                if len(keyword) > best_length or (len(keyword) == best_length and coverage > best_coverage):
                    best_keyword = keyword
                    best_row = candidate_row
                    best_length = len(keyword)
                    best_coverage = coverage
        if best_keyword and best_row:
            matches.append((best_keyword, best_row))
            inferred_match_terms.append(best_keyword)

    if not matches:
        override_only = _apply_english_compound_overrides(
            complaint_text,
            {
                "matched_keywords": [],
                "base_esi": 3,
                "is_red_flag": False,
                "resource_estimate": 2,
                "risk_tiers": [],
            },
        )
        if override_only.get("matched_keywords"):
            return override_only
        return None

    base_esi_values = [int(match["base_esi"]) for _, match in matches]
    resource_values = [int(match.get("resource_estimate", 2) or 2) for _, match in matches]
    aggregated = {
        "matched_keywords": sorted({keyword for keyword, _ in matches}),
        "base_esi": min(base_esi_values),
        "is_red_flag": any(bool(match.get("is_red_flag")) for _, match in matches),
        "resource_estimate": max(resource_values) if resource_values else 2,
        "match_mode": "inferred_only" if inferred_match_terms and not exact_match_terms else (
            "mixed" if inferred_match_terms and exact_match_terms else "exact"
        ),
        "risk_tiers": sorted({str(match.get("risk_tier") or "") for _, match in matches if str(match.get("risk_tier") or "").strip()}),
    }
    return _apply_english_compound_overrides(complaint_text, aggregated)


def _english_match_has_low_acuity_back_pain(keyword_match: Optional[Dict[str, Any]]) -> bool:
    if not keyword_match:
        return False
    matched = {str(item).strip().lower() for item in (keyword_match.get("matched_keywords") or [])}
    if matched.intersection(LOW_ACUITY_BACK_PAIN_KEYWORDS):
        return True
    return False


def _canonical_low_acuity_back_pain_match(
    keyword_match: Optional[Dict[str, Any]],
) -> Optional[Dict[str, Any]]:
    if not keyword_match:
        return None
    matched = sorted(
        {
            str(item).strip().lower()
            for item in (keyword_match.get("matched_keywords") or [])
            if str(item).strip().lower() in LOW_ACUITY_BACK_PAIN_KEYWORDS
        }
    )
    if not matched:
        return None
    return {
        "matched_keywords": matched,
        "base_esi": 4,
        "is_red_flag": False,
        "resource_estimate": 1,
        "risk_tiers": ["low"],
    }


def _triage_with_compound_keyword_split(patient_payload: Dict[str, Any], complaint_text: str):
    best_result = engine_logic.triage(patient_payload)
    best_level = int(getattr(best_result, "final_level", 3))
    fragments = _atomize_compound_complaint(complaint_text)
    if len(fragments) <= 1:
        return best_result

    for fragment in fragments:
        fragment_payload = dict(patient_payload)
        fragment_payload["chief_complaint_text"] = fragment
        fragment_payload["chief_complaint"] = fragment
        fragment_payload["complaint"] = fragment
        try:
            fragment_result = engine_logic.triage(fragment_payload)
        except Exception:
            continue
        fragment_level = int(getattr(fragment_result, "final_level", 3))
        if fragment_level < best_level:
            best_result = fragment_result
            best_level = fragment_level
    return best_result


def _vitals_for_low_acuity_are_normal(vitals: Optional[Dict[str, Any]]) -> bool:
    """Gate ESI 4/5 assignment to objectively stable patients only."""
    if not vitals:
        return False

    hr = _safe_float(vitals.get("hr"))
    rr = _safe_float(vitals.get("rr"))
    spo2 = _safe_float(vitals.get("spo2"))
    sbp = _safe_float(vitals.get("sbp"))
    temp = _safe_float(vitals.get("temp"))

    if None in (hr, rr, spo2, sbp, temp):
        return False

    # Accept Fahrenheit payloads and normalize before stability checks.
    if temp is not None and 80.0 <= temp <= 120.0:
        temp = (temp - 32.0) * 5.0 / 9.0

    return bool(
        50.0 <= hr <= 110.0
        and 10.0 <= rr <= 22.0
        and 90.0 <= sbp <= 180.0
        and spo2 >= 95.0
        and 35.0 <= temp <= 38.0
    )


def _apply_normalized_vitals_to_patient(
    patient: PatientInput,
    normalized_vitals: Optional[Dict[str, Any]],
) -> None:
    if not patient.vitals or not isinstance(normalized_vitals, dict):
        return

    for field in ("hr", "sbp", "dbp", "rr", "spo2", "temp", "blood_glucose"):
        if field not in normalized_vitals:
            continue
        value = normalized_vitals.get(field)
        if value is None:
            continue
        if isinstance(value, str) and not value.strip():
            continue
        try:
            setattr(patient.vitals, field, value)
        except Exception:
            continue


def _normalize_patient_vitals_for_triage(patient: PatientInput) -> None:
    if not patient.vitals:
        return
    normalized = VitalSignsValidator.normalize_vitals(patient.vitals.model_dump())
    _apply_normalized_vitals_to_patient(patient, normalized)


def _normalize_expected_resource_name(value: Any) -> Optional[str]:
    normalized = _normalize_match_text(str(value or "")).replace("-", "_").replace(" ", "_")
    if not normalized:
        return None
    return RESOURCE_EXPECTED_ALIASES.get(normalized)


def _extract_expected_resources(ai_result: Optional[Dict[str, Any]]) -> List[str]:
    if not ai_result:
        return []

    raw = ai_result.get("expected_resources")
    if isinstance(raw, str):
        raw = raw.strip()
        if raw:
            if raw.startswith("["):
                try:
                    parsed = json.loads(raw)
                    raw = parsed if isinstance(parsed, list) else [raw]
                except Exception:
                    raw = [item.strip() for item in raw.strip("[]").split(",") if item.strip()]
            else:
                raw = [item.strip() for item in raw.split(",") if item.strip()]
        else:
            raw = []

    if not isinstance(raw, list):
        return []

    deduped: List[str] = []
    seen = set()
    for item in raw:
        mapped = _normalize_expected_resource_name(item)
        if not mapped or mapped in seen:
            continue
        deduped.append(mapped)
        seen.add(mapped)
    return deduped


def _resources_from_workup(ai_result: Optional[Dict[str, Any]]) -> List[str]:
    if not ai_result:
        return []

    workup_items = ai_result.get("recommended_workup") or []
    mapped = get_resources_for_workup(workup_items)
    inferred: List[str] = []
    for item in mapped:
        code = str(item.get("code") or "").strip()
        code_upper = code.upper()
        if code_upper in {"LABS", "CARDIAC_LABS", "SEPSIS_LABS"}:
            inferred.append("labs")
        elif code_upper == "ECG":
            inferred.append("ecg")
        elif code_upper in {"X-RAY", "CT", "CT_HEAD", "US_ABD", "ORTHO_XRAY", "CT_ANGIO"}:
            inferred.append("imaging")
        elif code_upper == "IV_ACCESS":
            inferred.append("iv_meds_or_fluids")
        elif code_upper in {"SPLINT", "ORTHOPEDIC_EVAL"}:
            inferred.append("procedure")
        elif code_upper == "MONITOR":
            inferred.append("monitoring")
        elif code_upper == "CUSTOM":
            label = _normalize_match_text(item.get("label_en") or "")
            if any(token in label for token in {"lab", "blood", "urinalysis", "culture"}):
                inferred.append("labs")
            if any(token in label for token in {"ecg", "ekg", "electrocardio"}):
                inferred.append("ecg")
            if any(token in label for token in {"xray", "x-ray", "ct", "ultrasound", "imaging"}):
                inferred.append("imaging")
            if any(token in label for token in {"iv", "fluid", "intravenous"}):
                inferred.append("iv_meds_or_fluids")
            if any(token in label for token in {"suture", "splint", "catheter", "foley", "procedure"}):
                inferred.append("procedure")
            if any(token in label for token in {"consult", "specialist"}):
                inferred.append("specialty_consult")
            if any(token in label for token in {"monitor", "telemetry", "pulse ox"}):
                inferred.append("monitoring")

    deduped: List[str] = []
    seen = set()
    for item in inferred:
        mapped_name = _normalize_expected_resource_name(item)
        if not mapped_name or mapped_name in seen:
            continue
        deduped.append(mapped_name)
        seen.add(mapped_name)
    return deduped


def _resolve_resource_count(
    ai_result: Optional[Dict[str, Any]],
    *,
    complaint_text: str,
    normalized_category: str,
    minimum_resource_count: int = 0,
    maximum_resource_count: Optional[int] = None,
    minimum_expected_resources: Optional[List[str]] = None,
) -> tuple[int, List[str]]:
    expected_resources = _extract_expected_resources(ai_result)
    expected_resources.extend(_resources_from_workup(ai_result))
    if minimum_expected_resources:
        expected_resources.extend(
            [
                mapped
                for mapped in (
                    _normalize_expected_resource_name(item)
                    for item in minimum_expected_resources
                )
                if mapped
            ]
        )
    expected_resources = _dedupe_floor_names(expected_resources)

    raw_count = ai_result.get("resource_count") if ai_result else None
    try:
        resource_count = int(float(raw_count))
    except (TypeError, ValueError):
        resource_count = len(expected_resources)
    min_resource_floor = max(0, int(minimum_resource_count or 0))
    resource_count = max(resource_count, len(expected_resources))
    resource_count = max(resource_count, min_resource_floor)

    ai_context_chunks = [complaint_text or "", normalized_category or ""]
    if ai_result:
        ai_context_chunks.extend(str(item) for item in (ai_result.get("extracted_symptoms") or []))
        ai_context_chunks.append(str(ai_result.get("clinical_impression") or ""))
        ai_context_chunks.append(str(ai_result.get("reasoning") or ""))
    context_text = _normalize_match_text(" ".join(ai_context_chunks))
    normalized_category = _normalize_match_text(normalized_category or "")

    has_transfer = _contains_any_token(context_text, CRITICAL_TRANSFER_KEYWORDS) or "transfer_patient" in normalized_category
    has_urinary_retention = _contains_any_token(context_text, RESOURCE_URINARY_RETENTION_TOKENS) or "urinary_retention" in normalized_category
    has_wound = _contains_wound_laceration_signal(context_text) or normalized_category in {
        "minor_laceration",
        "laceration",
        "minor_trauma",
        "wound_check",
    }
    is_wound_followup = _contains_any_token(context_text, RESOURCE_WOUND_FOLLOW_UP_TOKENS) or normalized_category == "wound_check"
    has_complex_wound_features = _contains_any_token(context_text, RESOURCE_WOUND_COMPLEXITY_TOKENS)
    is_minor_wound_context = (
        normalized_category in {"minor_laceration", "laceration", "minor_trauma", "wound_check"}
        and not has_complex_wound_features
    )
    has_sore_throat = _contains_any_token(context_text, AI_SORE_THROAT_TOKENS) or normalized_category == "sore_throat"
    has_fever = _contains_any_token(context_text, AI_FEVER_TOKENS) or normalized_category in {"fever", "sepsis_concern"}

    if has_transfer:
        expected_resources = _dedupe_floor_names(expected_resources + ["specialty_consult", "monitoring"])
        resource_count = max(resource_count, 2)

    if has_urinary_retention:
        expected_resources = _dedupe_floor_names(expected_resources + ["procedure", "labs"])
        resource_count = max(resource_count, 2)

    if has_wound:
        expected_resources = _dedupe_floor_names(expected_resources + ["procedure"])
        if is_wound_followup or is_minor_wound_context:
            resource_count = max(resource_count, 1)
        else:
            expected_resources = _dedupe_floor_names(expected_resources + ["imaging"])
            resource_count = max(resource_count, 2)

    if has_sore_throat and has_fever:
        expected_resources = _dedupe_floor_names(expected_resources + ["labs", "imaging"])
        resource_count = max(resource_count, 2)
    elif has_sore_throat:
        expected_resources = _dedupe_floor_names(expected_resources + ["labs"])
        resource_count = max(resource_count, 1)

    resource_count = max(resource_count, min_resource_floor)
    resource_count = max(resource_count, len(expected_resources))
    if maximum_resource_count is not None:
        max_resource_cap = max(0, int(maximum_resource_count))
        resource_count = min(resource_count, max_resource_cap)
    resource_count = max(0, min(int(resource_count), 10))
    return resource_count, expected_resources


def _apply_resource_count_esi_logic(
    esi_level: int,
    resource_count: int,
    *,
    news2_score: Optional[int] = None,
    has_red_flags: bool = False,
    vitals_normal_for_low_acuity: bool = False,
    ai_confidence: Optional[float] = None,
) -> int:
    level = int(esi_level)
    if level <= 2:
        return level

    resources = max(0, int(resource_count))
    if resources >= 2:
        return 3

    candidate = 4 if resources == 1 else 5
    try:
        news2_value = int(news2_score) if news2_score is not None else 99
    except (TypeError, ValueError):
        news2_value = 99
    confidence_value = 0.0 if ai_confidence is None else max(0.0, min(1.0, float(ai_confidence)))

    # Safety constraint for low-acuity assignments (ESI 4/5):
    # NEWS2 < 5, no red flags, no vital abnormalities, confidence >= 0.70.
    if (
        news2_value < 5
        and not has_red_flags
        and vitals_normal_for_low_acuity
        and confidence_value >= 0.70
    ):
        return candidate

    # Default conservative floor when low-acuity safety gate does not pass.
    return 3


def apply_critical_safety_rules(
    complaint_text: str,
    vitals: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, Any]]:
    """
    Critical deterministic safety floors applied before AI categorization.
    These rules can only increase acuity (lower ESI number).
    """
    floors: List[Dict[str, Any]] = []
    normalized_complaint = _normalize_match_text(complaint_text or "")
    if not normalized_complaint:
        return floors

    for keyword in CRITICAL_TRANSFER_KEYWORDS:
        if _normalize_match_text(keyword) in normalized_complaint:
            floors.append(
                {
                    "min_esi": 2,
                    "reason": f'Transfer patient detected ("{keyword}")',
                    "category": "transfer_patient",
                }
            )
            break

    psych_triggered = False
    for keyword in CRITICAL_PSYCH_EMERGENCY_KEYWORDS:
        if _normalize_match_text(keyword) in normalized_complaint:
            floors.append(
                {
                    "min_esi": 2,
                    "reason": f'Psychiatric emergency signal ("{keyword}")',
                    "category": "psychiatric_emergency",
                }
            )
            psych_triggered = True
            break

    if not psych_triggered:
        for abbreviation in CRITICAL_PSYCH_EMERGENCY_ABBREVIATIONS:
            if re.search(rf"\b{re.escape(abbreviation)}\b", normalized_complaint):
                floors.append(
                    {
                        "min_esi": 2,
                        "reason": f'Psychiatric emergency abbreviation "{abbreviation.upper()}"',
                        "category": "psychiatric_emergency",
                    }
                )
                psych_triggered = True
                break

    for keyword in CRITICAL_GI_BLEED_KEYWORDS:
        if _normalize_match_text(keyword) in normalized_complaint:
            floors.append(
                {
                    "min_esi": 2,
                    "reason": f'GI bleeding signal ("{keyword}")',
                    "category": "gi_bleed",
                }
            )
            break

    hr_value = _safe_float((vitals or {}).get("hr")) if isinstance(vitals, dict) else None
    if hr_value is not None and hr_value > 100:
        for keyword in CRITICAL_BLEEDING_KEYWORDS:
            if _normalize_match_text(keyword) in normalized_complaint:
                floors.append(
                    {
                        "min_esi": 2,
                        "reason": f"Tachycardia (HR={int(hr_value)}) + bleeding concern",
                        "category": "hemorrhagic_shock_risk",
                    }
                )
                break

    return floors


def _slugify_floor_name(value: str) -> str:
    normalized = _normalize_match_text(str(value or ""))
    slug = re.sub(r"[^a-z0-9]+", "_", normalized).strip("_")
    return slug or "unknown_floor"


def _critical_rule_floor_name(rule: Dict[str, Any]) -> str:
    category = _slugify_floor_name(str(rule.get("category") or ""))
    return CRITICAL_FLOOR_NAME_BY_CATEGORY.get(category, f"critical_{category}")


def _map_esi_v5_floor_note_to_name(note: str) -> str:
    text = _normalize_match_text(note or "")
    category_match = re.search(r"high-risk category '([^']+)'", text)
    if category_match:
        return f"high_risk_category_{_slugify_floor_name(category_match.group(1))}"
    if "news2 floor applied" in text and ">= 7" in text:
        return "news2_ge7"
    if "news2 upgrade applied" in text and ">= 5" in text:
        return "news2_ge5"
    if "news2 upgrade applied" in text and ">= 3" in text:
        return "news2_ge3"
    if "chest pain floor applied" in text:
        return "chest_pain"
    if "fast stroke protocol override applied" in text:
        return "stroke_fast_esi1"
    if "stroke fast floor applied" in text:
        return "stroke_fast_esi2"
    if "high-risk red flag floor applied" in text:
        return "high_risk_red_flag"
    if "ectopic-risk floor applied" in text:
        return "ectopic_risk"
    if "silent mi category floor applied" in text:
        return "silent_mi_category"
    if "silent mi floor applied" in text:
        return "silent_mi"
    if "high-risk fever + abdominal pain floor applied" in text:
        return "fever_abdominal_pain"
    if "unknown presentation default applied" in text:
        return "unknown_presentation_default"
    if "unknown-category low-acuity complaint detected" in text:
        return "unknown_low_acuity_skip"
    if "low-risk safeguard applied" in text:
        return "low_risk_safeguard"
    return f"esi_v5_{_slugify_floor_name(text)}"


def _extract_esi_v5_floor_names(esi_v5_result: Any) -> List[str]:
    names: List[str] = []
    if str(getattr(esi_v5_result, "confidence_action", "")).strip().lower() == "offline_conservative_floor":
        names.append("offline_conservative")
    for note in list(getattr(esi_v5_result, "safety_floors_applied", []) or []):
        names.append(_map_esi_v5_floor_note_to_name(str(note)))
    return names


def _dedupe_floor_names(floors_applied: List[str]) -> List[str]:
    deduped: List[str] = []
    seen = set()
    for floor in floors_applied or []:
        value = str(floor or "").strip()
        if not value or value in seen:
            continue
        deduped.append(value)
        seen.add(value)
    return deduped


def _attach_floor_observation(
    payload: Dict[str, Any],
    *,
    esi_baseline: Optional[int],
    esi_safe: Optional[int],
    floors_applied: Optional[List[str]],
) -> Dict[str, Any]:
    deduped = _dedupe_floor_names([str(item) for item in (floors_applied or []) if str(item).strip()])
    payload["esi_baseline"] = int(esi_baseline) if esi_baseline is not None else None
    payload["esi_safe"] = int(esi_safe) if esi_safe is not None else None
    payload["safety_floors_applied"] = deduped
    payload["safety_floor_count"] = len(deduped)
    if esi_safe is not None:
        payload["esi_level"] = int(esi_safe)
    elif "esi_level" not in payload:
        payload["esi_level"] = None
    return payload


def _enforce_critical_safety_floors(
    level: int,
    safety_rules: List[Dict[str, Any]],
) -> tuple[int, List[str], List[str], List[str]]:
    final_level = int(level)
    reasoning_updates: List[str] = []
    safety_floor_notes: List[str] = []
    floor_names: List[str] = []

    for rule in safety_rules or []:
        min_esi = int(rule.get("min_esi", 5))
        if final_level > min_esi:
            final_level = min_esi
            reason = str(rule.get("reason") or "Critical safety signal")
            note = f"Critical safety floor applied: {reason} -> minimum ESI {min_esi}"
            reasoning_updates.append(note)
            safety_floor_notes.append(note)
            floor_names.append(_critical_rule_floor_name(rule))

    return final_level, reasoning_updates, safety_floor_notes, floor_names


def _collect_ai_reasoning_text(ai_result: Optional[Dict[str, Any]]) -> str:
    if not ai_result:
        return ""

    chunks: List[str] = []
    text_fields = [
        "reasoning",
        "clinical_reasoning",
        "clinical_impression",
        "reasoning_ar",
        "confidence_rationale",
    ]
    list_fields = [
        "recommended_workup",
        "differential_diagnosis",
        "risk_factors",
        "extracted_symptoms",
        "red_flags",
    ]

    for key in text_fields:
        value = ai_result.get(key)
        if isinstance(value, str) and value.strip():
            chunks.append(value)

    for key in list_fields:
        value = ai_result.get(key)
        if isinstance(value, list):
            chunks.extend([str(item) for item in value if str(item).strip()])

    return " ".join(chunks)


def _has_stroke_fast_signal(text: str) -> bool:
    normalized = _normalize_match_text(text)

    if any(_normalize_match_text(token) in normalized for token in STROKE_EXPLICIT_TOKENS):
        return True

    if any(_normalize_match_text(token) in normalized for token in STROKE_SPEECH_HIGH_RISK_TOKENS):
        return True

    if any(_normalize_match_text(token) in normalized for token in STROKE_SINGLE_FAST_TOKENS):
        return True

    has_speech = any(_normalize_match_text(token) in normalized for token in STROKE_SPEECH_TOKENS)
    has_face = any(_normalize_match_text(token) in normalized for token in STROKE_FACE_TOKENS)
    has_weakness = any(_normalize_match_text(token) in normalized for token in STROKE_WEAKNESS_TOKENS)
    has_sudden = any(_normalize_match_text(token) in normalized for token in STROKE_SUDDEN_TOKENS)

    if has_speech and (has_sudden or has_face or has_weakness):
        return True
    if has_face and has_weakness:
        return True

    return False


def _derive_reasoning_safety(ai_result: Optional[Dict[str, Any]], complaint_text: str) -> Dict[str, Any]:
    reasoning_text = _collect_ai_reasoning_text(ai_result)
    combined_text = f"{reasoning_text} {complaint_text or ''}".strip()
    normalized = _normalize_match_text(combined_text)

    stroke_signal = _has_stroke_fast_signal(combined_text)
    mi_signal = _contains_any_token(normalized, MI_REASONING_TOKENS)
    sepsis_signal = _contains_any_token(normalized, SEPSIS_REASONING_TOKENS)
    airway_signal = _contains_any_token(normalized, AIRWAY_REASONING_TOKENS) and not _contains_any_token(
        normalized,
        AI_NEGATED_RESPIRATORY_TOKENS,
    )
    critical_signal = (
        stroke_signal
        or mi_signal
        or sepsis_signal
        or airway_signal
        or _contains_any_token(normalized, CRITICAL_REASONING_TOKENS)
    )

    red_flags: List[str] = []
    override_category = None

    if stroke_signal:
        red_flags.extend(["stroke_symptoms", "neurological_emergency"])
        override_category = "stroke_symptoms"
    elif mi_signal:
        red_flags.extend(["chest_pain", "cardiac_risk"])
        override_category = "chest_pain_cardiac"
    elif sepsis_signal:
        red_flags.extend(["sepsis", "sepsis_concern"])
        override_category = "sepsis_concern"
    elif airway_signal:
        red_flags.extend(["respiratory_distress", "airway_risk"])
        override_category = "respiratory_distress"

    if critical_signal:
        red_flags.append("reasoning_high_risk_signal")

    return {
        "combined_text": combined_text,
        "stroke_signal": stroke_signal,
        "critical_signal": critical_signal,
        "override_category": override_category,
        "red_flags": sorted(set(red_flags)),
        "floor_esi": 2 if critical_signal else None,
    }


def _build_ai_context_text(ai_result: Optional[Dict[str, Any]], complaint_text: str) -> str:
    if not ai_result:
        return complaint_text or ""

    chunks: List[str] = [complaint_text or ""]
    for key in ("clinical_impression", "reasoning", "reasoning_ar", "followup_question", "followup_question_ar"):
        value = ai_result.get(key)
        if isinstance(value, str) and value.strip():
            chunks.append(value.strip())

    for key in ("extracted_symptoms", "risk_factors", "differential_diagnosis", "recommended_workup"):
        value = ai_result.get(key)
        if isinstance(value, list):
            chunks.extend(str(item).strip() for item in value if str(item).strip())

    return " ".join(chunks).strip()


def _normalize_ai_category_for_esi(ai_result: Optional[Dict[str, Any]], complaint_text: str) -> str:
    raw_category = str((ai_result or {}).get("category") or "").strip().lower().replace(" ", "_").replace("-", "_")
    normalized_category = AI_CATEGORY_ALIASES.get(raw_category, raw_category)
    ai_text = _build_ai_context_text(ai_result, complaint_text)
    normalized_text = _normalize_match_text(ai_text)

    if _contains_any_token(normalized_text, CRITICAL_TRANSFER_KEYWORDS):
        return "transfer_patient"

    if _contains_any_token(normalized_text, RESOURCE_URINARY_RETENTION_TOKENS):
        return "urinary_retention"

    if _contains_wound_laceration_signal(normalized_text):
        if _contains_any_token(normalized_text, RESOURCE_WOUND_FOLLOW_UP_TOKENS):
            return "wound_check"
        return "minor_laceration"

    if _contains_any_token(normalized_text, AI_SORE_THROAT_TOKENS):
        return "sore_throat"

    if _has_stroke_fast_signal(ai_text):
        return "stroke_symptoms"

    chest_pain_tokens = [
        "chest pain",
        "radiating to left arm",
        "radiating to jaw",
        "angina",
        "الم صدر",
        "ألم صدر",
        "وجع صدر",
    ]
    if _contains_any_token(normalized_text, chest_pain_tokens):
        return "chest_pain_cardiac"

    if _contains_any_token(normalized_text, AI_ABDOMINAL_PAIN_TOKENS):
        return "abdominal_pain"

    if _contains_any_token(normalized_text, AI_REFILL_TOKENS):
        return "prescription_refill"
    if _contains_any_token(normalized_text, AI_FOLLOW_UP_TOKENS):
        return "follow_up"
    if _contains_any_token(normalized_text, AI_NON_URGENT_TOKENS):
        return "minor_complaint"

    if normalized_category in {"respiratory_distress", "respiratory", "respiratory_symptoms", "uri_symptoms", "uri"}:
        has_positive_distress_signal = _contains_any_token(normalized_text, AI_RESPIRATORY_DISTRESS_TOKENS)
        has_negated_distress_signal = _contains_any_token(normalized_text, AI_NEGATED_RESPIRATORY_TOKENS)
        if has_positive_distress_signal and not has_negated_distress_signal:
            return "respiratory_distress"
        if _contains_any_token(normalized_text, AI_SORE_THROAT_TOKENS):
            return "sore_throat"
        return "uri_symptoms"

    if normalized_category in {"abdominal_pain", "gi", "mild_gi", "indigestion", "heartburn"}:
        if _contains_any_token(normalized_text, AI_BACK_PAIN_TOKENS) and not _contains_any_token(
            normalized_text,
            AI_ABDOMINAL_PAIN_TOKENS,
        ):
            return "simple_back_pain"
        if _contains_any_token(normalized_text, AI_HIGH_RISK_GI_TOKENS):
            return "abdominal_pain"
        if _contains_any_token(normalized_text, AI_MILD_GI_TOKENS):
            return "mild_gi"

    if normalized_category in {"", "unclear", "unknown", "general", "other", "insufficient_information"}:
        if _contains_any_token(normalized_text, AI_LOW_ACUITY_RESPIRATORY_TOKENS):
            if _contains_any_token(normalized_text, AI_SORE_THROAT_TOKENS):
                return "sore_throat"
            return "uri_symptoms"
        if _contains_any_token(normalized_text, AI_MILD_GI_TOKENS) and not _contains_any_token(
            normalized_text, AI_HIGH_RISK_GI_TOKENS
        ):
            return "mild_gi"
        return "unclear_needs_evaluation"

    return normalized_category or "unclear_needs_evaluation"


def _sanitize_ai_red_flags(
    red_flags: Optional[List[Any]],
    *,
    complaint_text: str,
    normalized_category: str,
) -> List[str]:
    sanitized: List[str] = []
    normalized_complaint = _normalize_match_text(complaint_text or "")
    has_chest_signal = _contains_any_token(
        normalized_complaint,
        ["chest pain", "الم صدر", "ألم صدر", "radiating to left arm", "radiating to jaw"],
    )
    has_stroke_signal = _has_stroke_fast_signal(complaint_text or "")
    has_resp_distress_signal = _contains_any_token(normalized_complaint, AI_RESPIRATORY_DISTRESS_TOKENS) and not _contains_any_token(
        normalized_complaint, AI_NEGATED_RESPIRATORY_TOKENS
    )

    for item in red_flags or []:
        cleaned = _normalize_match_text(str(item)).replace("-", "_").replace(" ", "_")
        if not cleaned:
            continue
        if any(hint in cleaned for hint in AI_OBJECTIVE_RED_FLAG_HINTS):
            if any(token in cleaned for token in {"chest_pain", "radiation_to_arm", "radiation_to_jaw"}):
                if not has_chest_signal and (normalized_category or "").strip().lower() != "chest_pain_cardiac":
                    continue
            if any(token in cleaned for token in {"stroke", "facial_droop", "arm_weakness", "slurred_speech"}):
                if not has_stroke_signal and (normalized_category or "").strip().lower() != "stroke_symptoms":
                    continue
            if any(token in cleaned for token in {"respiratory_distress", "dyspnea", "airway"}):
                if not has_resp_distress_signal and (normalized_category or "").strip().lower() != "respiratory_distress":
                    continue
            sanitized.append(cleaned)

    category = (normalized_category or "").strip().lower()
    if category == "stroke_symptoms":
        sanitized.append("stroke_symptoms")
    elif category == "chest_pain_cardiac":
        sanitized.append("chest_pain")
    elif category == "respiratory_distress":
        sanitized.append("respiratory_distress")
    elif category == "sepsis_concern":
        sanitized.append("sepsis")

    if _has_stroke_fast_signal(complaint_text):
        sanitized.append("stroke_symptoms")

    return list(dict.fromkeys(flag for flag in sanitized if flag))


def _is_parseable_body_system(value: Any) -> bool:
    cleaned = _normalize_match_text(str(value or "")).replace("-", "_").replace(" ", "_")
    return cleaned not in UNCLEAR_BODY_SYSTEM_VALUES


def _resolve_gemini_body_system(
    ai_result: Optional[Dict[str, Any]],
    normalized_ai_category: str,
) -> str:
    if not ai_result:
        return normalized_ai_category or "unclear_needs_evaluation"

    candidates = [
        ai_result.get("body_system"),
        ai_result.get("category_raw"),
        ai_result.get("category"),
        normalized_ai_category,
    ]
    for candidate in candidates:
        if not _is_parseable_body_system(candidate):
            continue
        normalized = _normalize_category(
            str(candidate).strip().lower().replace(" ", "_").replace("-", "_")
        )
        if _is_parseable_body_system(normalized):
            return normalized
        fallback = _normalize_match_text(str(candidate)).replace("-", "_").replace(" ", "_")
        if _is_parseable_body_system(fallback):
            return fallback
    return normalized_ai_category or "unclear_needs_evaluation"


def _has_meaningful_triage_field(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        cleaned = value.strip().lower()
        return cleaned not in {"", "unknown", "unclear", "unspecified", "none", "n/a", "na"}
    if isinstance(value, (list, tuple, dict, set)):
        return len(value) > 0
    return True


def _safe_stable_reasoning_context(
    *,
    level: int,
    objective_red_flag_present: bool,
    news2_value: Optional[float],
    vitals: Optional[Dict[str, Any]],
    reasoning_stroke_signal: bool,
) -> bool:
    return bool(
        level >= 3
        and not objective_red_flag_present
        and (news2_value is None or news2_value < 5)
        and _vitals_for_low_acuity_are_normal(vitals or {})
        and not reasoning_stroke_signal
    )


def _collect_followup_questions(ai_result: Optional[Dict[str, Any]]) -> List[str]:
    if not ai_result:
        return []

    questions: List[str] = []
    for key in ("followup_question", "followup_question_ar"):
        value = ai_result.get(key)
        if isinstance(value, str) and value.strip():
            questions.append(value.strip())

    ask_patient = ai_result.get("ask_patient")
    if isinstance(ask_patient, list):
        for item in ask_patient:
            item_text = str(item).strip()
            if item_text:
                questions.append(item_text)

    deduped: List[str] = []
    seen = set()
    for question in questions:
        normalized = _normalize_match_text(question)
        if normalized in seen:
            continue
        seen.add(normalized)
        deduped.append(question)
    return deduped


def _check_complaint_sufficiency(
    complaint_text: str,
    ai_result: Optional[Dict[str, Any]],
    *,
    fallback_category: str = "",
    reasoning_safety: Optional[Dict[str, Any]] = None,
) -> Optional[Dict[str, Any]]:
    words = [token for token in re.split(r"\s+", (complaint_text or "").strip()) if token]
    is_brief = len(words) < 5

    ai_payload = ai_result or {}
    has_onset = _has_meaningful_triage_field(ai_payload.get("onset"))
    has_duration = _has_meaningful_triage_field(ai_payload.get("duration"))
    has_severity = _has_meaningful_triage_field(ai_payload.get("severity"))

    missing_fields: List[str] = []
    if not has_onset:
        missing_fields.append("onset / بداية الأعراض")
    if not has_duration:
        missing_fields.append("duration / مدة الأعراض")
    if not has_severity:
        missing_fields.append("severity / شدة الأعراض")

    is_insufficient = is_brief or len(missing_fields) >= 2
    if not is_insufficient:
        return None

    reasoning_safety = reasoning_safety or {}
    category = _normalize_category(
        str(
            ai_payload.get("category")
            or fallback_category
            or reasoning_safety.get("override_category")
            or ""
        )
    )
    combined_text = str(reasoning_safety.get("combined_text") or complaint_text or "")
    reasoning_red_flags = {str(flag).strip().lower() for flag in (reasoning_safety.get("red_flags") or [])}
    is_time_critical = (
        category in TIME_CRITICAL_CATEGORIES
        or bool(reasoning_safety.get("critical_signal"))
        or _has_stroke_fast_signal(combined_text)
        or bool(reasoning_red_flags.intersection(TIME_CRITICAL_CATEGORIES))
    )

    followup_questions = _collect_followup_questions(ai_payload)
    category_label = (category or "high-risk emergency").replace("_", " ")
    missing_text = ", ".join(missing_fields) if missing_fields else "onset / duration / severity"

    if is_time_critical:
        return {
            "type": "insufficient_info_red_flag",
            "severity": "critical",
            "message_en": (
                "BRIEF COMPLAINT - COLLECT MORE INFO BUT DO NOT DELAY TREATMENT. "
                f"This presentation may indicate {category_label}. "
                f"Start protocol while collecting: {missing_text}."
            ),
            "message_ar": (
                "شكوى مختصرة - اجمع معلومات أكثر بدون تأخير العلاج. "
                f"قد تشير الحالة إلى {category_label}. "
                f"ابدأ البروتوكول واسأل عن: {missing_text}."
            ),
            "missing_fields": missing_fields,
            "ask_patient": followup_questions,
            "dismissible": False,
        }

    return {
        "type": "insufficient_info",
        "severity": "warning",
        "message_en": (
            "INSUFFICIENT INFORMATION - Please collect more details before finalizing triage. "
            f"Missing: {missing_text}."
        ),
        "message_ar": (
            "معلومات غير كافية - من فضلك اجمع تفاصيل إضافية قبل تأكيد الفرز. "
            f"الناقص: {missing_text}."
        ),
        "missing_fields": missing_fields,
        "ask_patient": followup_questions,
        "dismissible": True,
    }


def _build_needs_more_info_response() -> Dict[str, Any]:
    response = {
        "status": "needs_more_info",
        "esi_level": None,
        "message_en": "Your complaint is brief. For accurate triage, please tell us more:",
        "message_ar": "الشكوى قصيرة. لتقييم دقيق، من فضلك قولنا أكتر:",
        "questions": [
            {"en": "Where exactly is the pain/problem?", "ar": "الألم أو المشكلة فين بالظبط؟"},
            {"en": "How severe is it? (1-10)", "ar": "شدته كام من ١٠؟"},
            {"en": "When did it start?", "ar": "بدأ إمتى؟"},
            {
                "en": "Any other symptoms? (fever, vomiting, bleeding)",
                "ar": "فيه أعراض تانية؟ (سخونية، ترجيع، نزيف)",
            },
            {
                "en": "Any medical conditions? (diabetes, heart disease)",
                "ar": "عندك أمراض مزمنة؟ (سكر، قلب، ضغط)",
            },
        ],
        "safety_note_en": "If this is a life-threatening emergency, go to the nearest ER immediately.",
        "safety_note_ar": "لو الحالة طارئة وخطيرة، روح أقرب طوارئ فوراً.",
    }
    return _attach_floor_observation(
        response,
        esi_baseline=None,
        esi_safe=None,
        floors_applied=[],
    )


def _send_alert_for_level(
    level: int,
    patient_id: str,
    complaint: str,
    news2_score: int = 0,
    icd10_code: str = "",
    icd10_description: str = "",
    snomed_code: str = "",
    snomed_term: str = "",
    recommended: list = None,
    clinician: str = "Unassigned | غير محدد",
):
    if level is None or level > 2:
        return None
    payload = {
        "alert_level": AlertLevel.CODE_RED if level == 1 else AlertLevel.HIGH_ALERT,
        "patient_id": patient_id,
        "esi_level": level,
        "news2_score": news2_score,
        "complaint": complaint,
        "icd10_code": icd10_code,
        "icd10_description": icd10_description,
        "snomed_code": snomed_code,
        "snomed_term": snomed_term,
        "recommended": recommended or [],
        "clinician": clinician,
        "timestamp": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
    }
    return send_alert_sync(payload)


def _build_red_flag_summary(vitals: dict, news2_score: int, complaint_text: str = "") -> list:
    summary = []
    try:
        spo2 = vitals.get("spo2")
        sbp = vitals.get("sbp")
        hr = vitals.get("hr")
        if spo2 is not None and spo2 < 90:
            summary.append("SpO2 < 90% → Critical hypoxia | تشبع الأكسجين < 90% → نقص أكسجة حاد")
        if sbp is not None and sbp < 90:
            summary.append("SBP < 90 → Hypotension | ضغط انقباضي < 90 → هبوط ضغط")
        if hr is not None and hr > 130:
            summary.append("HR > 130 → Severe tachycardia | نبض > 130 → تسارع شديد")
        if news2_score is not None and news2_score >= 7:
            summary.append("NEWS2 ≥ 7 → Critical early warning | نيوز2 ≥ 7 → إنذار حرج مبكر")
        if complaint_text and _has_stroke_fast_signal(complaint_text):
            summary.append(
                "FAST-positive stroke signal (speech/face/limb) → ESI 1 immediate | "
                "علامات جلطة إيجابية (FAST) → ESI 1 فوري"
            )
    except Exception:
        return summary
    return summary


def _validation_failed_response(
    *,
    error_type: str,
    message: str,
    message_ar: str,
    details: Optional[List[Dict[str, Any]]] = None,
    action: str = "require_reentry",
) -> JSONResponse:
    return JSONResponse(
        status_code=400,
        content={
            "success": False,
            "esi_level": None,
            "esi_baseline": None,
            "esi_safe": None,
            "safety_floors_applied": [],
            "safety_floor_count": 0,
            "error": "validation_failed",
            "error_type": error_type,
            "message": message,
            "message_ar": message_ar,
            "details": details or [],
            "action": action,
            "gahar_notice": GAHAR_NOTICE,
        },
    )


def _validate_complaint_or_raise(complaint_text: str) -> Optional[JSONResponse]:
    validation = ComplaintValidator.validate(complaint_text)
    if validation.get("valid", False):
        return None
    return _validation_failed_response(
        error_type="invalid_complaint",
        message=validation.get(
            "message",
            "Complaint validation failed - enter a clear clinical complaint",
        ),
        message_ar=validation.get(
            "message_ar",
            "فشل التحقق من الشكوى - يرجى إدخال شكوى طبية واضحة",
        ),
        details=[
            {
                "validator_error": validation.get("error", "invalid_complaint"),
                "action": validation.get("action", "require_reentry"),
            }
        ],
        action="require_reentry",
    )


def _build_no_complaint_default_response(
    patient: PatientInput, *, extraction_method: str = "keyword_offline"
) -> Dict[str, Any]:
    level = 3
    labels_en = {1: "Resuscitation", 2: "Emergent", 3: "Urgent", 4: "Less Urgent", 5: "Non-Urgent"}
    labels_ar = {1: "إنعاش", 2: "طوارئ", 3: "عاجل", 4: "أقل إلحاحاً", 5: "غير عاجل"}
    times_en = {1: "Immediate", 2: "< 15 minutes", 3: "< 30 minutes", 4: "< 60 minutes", 5: "< 120 minutes"}
    times_ar = {1: "فوري", 2: "< 15 دقيقة", 3: "< 30 دقيقة", 4: "< 60 دقيقة", 5: "< 120 دقيقة"}
    selected_action = _action_text_for_level_and_category(
        level,
        "unclear",
        complaint_text="",
        extracted_symptoms=[],
    )
    note_en = "No complaint text provided; conservative default ESI 3 applied."
    note_ar = "لم يتم إدخال شكوى؛ تم تطبيق التصنيف التحفظي الافتراضي مستوى 3."
    response = {
        "level": level,
        "extraction_method": extraction_method,
        "color_code": "#eab308",
        "label_en": labels_en[level],
        "label_ar": labels_ar[level],
        "description": f"{selected_action['ar']} / {selected_action['en']}",
        "description_ar": selected_action["ar"],
        "description_en": selected_action["en"],
        "recommended_action": f"{selected_action['ar']} / {selected_action['en']}",
        "action_ar": selected_action["ar"],
        "action_en": selected_action["en"],
        "time_to_physician": f"{times_ar[level]} / {times_en[level]}",
        "time_ar": times_ar[level],
        "time_en": times_en[level],
        "red_flags": [],
        "red_flag_summary": [],
        "reasoning": [note_en],
        "reasoning_ar": [note_ar],
        "reasoning_en": [note_en],
        "ai_data": None,
        "confidence": "Deterministic (No Complaint Default)",
        "icd10_coding": {
            "primary_code": "R69",
            "description_en": "Illness, unspecified",
            "description_ar": "مرض غير محدد",
            "coding_system": "ICD-10-CM",
            "coding_version": "2024",
            "gahar_compliant": True,
        },
        "icd10_code": "R69",
        "icd10_description": "Illness, unspecified",
        "snomed_code": "",
        "snomed_term": "",
        "resource_plan": [],
        "alerts_sent": None,
        "silent_mi_alert": None,
        "requires_review": True,
        "review_message": note_en,
        "requires_confirmation": True,
        "stage_reached": "no_complaint_default",
        "resources_estimated": 2,
        "confidence_action": "no_complaint_default",
        "news2_override": False,
        "safety_floors": ["No complaint default: conservative ESI 3"],
        "context_rules_triggered": [],
        "confidence_flag": "missing_complaint",
        "low_confidence_warning": note_en,
        "gahar_notice": GAHAR_NOTICE,
    }
    return _attach_floor_observation(
        response,
        esi_baseline=level,
        esi_safe=level,
        floors_applied=["no_complaint_default"],
    )


def _validate_vitals_or_raise(
    patient: PatientInput,
    extracted_features: dict | None = None,
) -> Optional[JSONResponse]:
    vitals_payload = patient.vitals.model_dump() if patient.vitals else {}
    vitals_payload["consciousness"] = getattr(patient, "consciousness", "A")
    validation = VitalSignsValidator.validate(
        vitals=vitals_payload,
        complaint_text=patient.chief_complaint_text,
        extracted_features=extracted_features,
    )
    _apply_normalized_vitals_to_patient(patient, validation.get("normalized_vitals"))
    if validation.get("valid", False):
        return None
    errors = validation.get("errors", [])
    return _validation_failed_response(
        error_type="invalid_vitals",
        message=(
            "Vital signs validation failed - required fields missing or out of range"
        ),
        message_ar="فشل التحقق من العلامات الحيوية - الحقول المطلوبة ناقصة أو خارج النطاق",
        details=errors,
        action="require_complete_vitals",
    )


def _validate_patient_id_or_raise(patient_id: Optional[str]) -> None:
    normalized = str(patient_id or "").strip()
    if not normalized:
        return
    if normalized.isdigit():
        return
    if TEMP_ID_PATTERN.match(normalized):
        return
    raise HTTPException(
        status_code=400,
        detail="MRN must contain numbers only",
    )


def _resolve_clinician_id(user: Dict[str, Any]) -> str:
    for key in ("uid", "user_id", "sub"):
        value = user.get(key)
        if value:
            return str(value).strip()
    # Fallback to email for backward compatibility with older records
    for key in ("email", "username", "name"):
        value = user.get(key)
        if value:
            return str(value).strip()
    return ""


def _resolve_clinician_id_variants(user: Dict[str, Any]) -> list:
    """Return all possible clinician_id values for this user (uid, email, name).
    Used by export queries to match records stored under any identifier format."""
    variants = []
    for key in ("uid", "user_id", "sub", "email", "username", "name"):
        value = user.get(key)
        if value:
            v = str(value).strip()
            if v and v not in variants:
                variants.append(v)
    return variants


def _normalize_category(category: str) -> str:
    normalized = (category or "").strip().lower()
    if any(token in normalized for token in ["trauma", "fracture", "orthopedic", "hip_fracture"]):
        return "trauma_fracture"
    if any(token in normalized for token in ["stroke", "cva", "neuro", "aphasia", "dysarthria"]):
        return "stroke_symptoms"
    if normalized == "dyspnea":
        return "respiratory_distress"
    if "sepsis" in normalized or "infection" in normalized:
        return "sepsis_concern"
    if "allerg" in normalized or "anaphyl" in normalized:
        return "allergic_reaction"
    if (
        "psych" in normalized
        or "suicid" in normalized
        or "agitation" in normalized
        or "homicid" in normalized
    ):
        return "psychiatric"
    if normalized in CRITICAL_SAFETY_CATEGORIES and normalized != "transfer_patient":
        if normalized == "psychiatric_emergency":
            return "psychiatric"
        return "abdominal_pain"
    if "abdominal" in normalized or "abdomen" in normalized:
        return "abdominal_pain"
    return normalized


def _map_consciousness_to_mental_status(consciousness: str) -> str:
    mapped = (consciousness or "A").strip().upper()
    if mapped in {"U"}:
        return "unresponsive"
    if mapped in {"P"}:
        return "pain_only"
    if mapped in {"V"}:
        return "voice_only"
    if mapped in {"C"}:
        return "confused"
    return "alert"


def _safe_ai_confidence(ai_result: dict | None) -> float:
    if not ai_result:
        return 0.80
    raw = ai_result.get("confidence_score", ai_result.get("confidence"))
    if raw is None:
        return 0.80
    try:
        parsed = float(raw)
    except (TypeError, ValueError):
        parsed = 0.80
    return max(0.0, min(1.0, parsed))


def _silent_mi_supporting_vitals(patient_data: Dict[str, Any]) -> bool:
    vitals = patient_data.get("vitals") or {}
    try:
        hr = float(vitals.get("hr")) if vitals.get("hr") is not None else None
        sbp = float(vitals.get("sbp")) if vitals.get("sbp") is not None else None
        rr = float(vitals.get("rr")) if vitals.get("rr") is not None else None
        spo2 = float(vitals.get("spo2")) if vitals.get("spo2") is not None else None
        temp = float(vitals.get("temp")) if vitals.get("temp") is not None else None
    except (TypeError, ValueError):
        return False

    return bool(
        (hr is not None and hr >= 95)
        or (sbp is not None and sbp < 110)
        or (rr is not None and rr >= 20)
        or (spo2 is not None and spo2 < 95)
        or (temp is not None and temp >= 37.8)
    )


def _should_apply_silent_mi_floor(patient_data: Dict[str, Any], silent_mi: Dict[str, Any]) -> bool:
    if not silent_mi.get("pattern_detected"):
        return False

    age = int(patient_data.get("age") or 0)
    gender = str(patient_data.get("gender") or "").strip().lower()
    demographic_high_risk = (gender == "male" and age >= 50) or age >= 65
    if not demographic_high_risk:
        return False

    comorb_text = str(patient_data.get("comorbidities", "")).lower()
    diabetic = "diabetes" in comorb_text or "سكري" in comorb_text or bool(patient_data.get("diabetic", False))
    if not diabetic:
        return False

    complaint = str(
        patient_data.get("chief_complaint")
        or patient_data.get("chief_complaint_text")
        or patient_data.get("complaint")
        or ""
    ).lower()
    extracted = " ".join(str(item) for item in (patient_data.get("extracted_symptoms") or [])).lower()
    combined = f"{complaint} {extracted}"
    gi_signal = any(
        token in combined
        for token in ["nausea", "غثيان", "indigestion", "heartburn", "stomach", "epigastric", "حرقان", "فم المعدة"]
    )
    if not gi_signal:
        return False

    return _silent_mi_supporting_vitals(patient_data)


def _severity_from_level(level: int) -> str:
    if level <= 1:
        return "critical"
    if level == 2:
        return "severe"
    if level == 3:
        return "moderate"
    return "mild"


def _offline_mode_enabled() -> bool:
    return str(os.getenv("TRIAGE_OFFLINE_MODE", "false")).strip().lower() in {"1", "true", "yes"}


def _deterministic_confidence(det_result, *, force_offline: bool = False) -> tuple[float, bool]:
    """
    Confidence policy for keyword/deterministic paths:
    - exact keyword match: 0.75
    - matched with modifiers: 0.70
    - unknown/no match: 0.50
    - offline mode: 0.60 and is_offline=True
    """
    if force_offline:
        return 0.60, True

    category = str(getattr(det_result, "category", "") or "").strip().lower()
    if category in {"", "unclear", "unclear_needs_evaluation", "insufficient_information", "unknown"}:
        return 0.50, False

    modifiers = list(getattr(det_result, "modifiers_applied", []) or [])
    if modifiers:
        return 0.70, False

    return 0.75, False


def _run_esi_v5_for_patient(
    patient: PatientInput,
    *,
    body_system: str,
    news2_score: int,
    news2_level: int,
    severity: str = "moderate",
    onset: str = "unknown",
    red_flags: Optional[List[str]] = None,
    snomed_codes: Optional[List[str]] = None,
    ai_confidence: float = 0.70,
    is_offline: bool = False,
):
    features = ESIv5PatientFeatures(
        chief_complaint=patient.chief_complaint_text,
        snomed_codes=[str(code) for code in (snomed_codes or [])],
        body_system=body_system or "unclear",
        severity=severity,
        onset=onset,
        red_flags=[str(flag) for flag in (red_flags or [])],
        age=int(patient.age or 0),
        gender=str(patient.gender.value if hasattr(patient.gender, "value") else patient.gender),
        comorbidities=[str(item) for item in (patient.comorbidities or [])],
        mental_status=_map_consciousness_to_mental_status(getattr(patient, "consciousness", "A")),
        pain_score=getattr(patient.vitals, "pain_score", None) if patient.vitals else None,
        ai_confidence=max(0.0, min(1.0, float(ai_confidence))),
        is_offline=is_offline,
    )
    vitals = ESIv5VitalSigns(
        heart_rate=getattr(patient.vitals, "hr", None) if patient.vitals else None,
        systolic_bp=getattr(patient.vitals, "sbp", None) if patient.vitals else None,
        diastolic_bp=getattr(patient.vitals, "dbp", None) if patient.vitals else None,
        respiratory_rate=getattr(patient.vitals, "rr", None) if patient.vitals else None,
        spo2=getattr(patient.vitals, "spo2", None) if patient.vitals else None,
        temperature=getattr(patient.vitals, "temp", None) if patient.vitals else None,
        gcs=getattr(patient.vitals, "gcs", None) if patient.vitals else None,
    )
    news2 = ESIv5NEWS2Result(
        total_score=int(news2_score or 0),
        risk_level="high" if news2_score >= 7 else ("medium" if news2_score >= 5 else "low"),
        parameter_scores={},
        single_param_3=news2_level <= 2 and news2_score > 0,
    )
    return run_esi_v5_triage(features, vitals, news2)


def _action_text_for_level_and_category(
    level: int,
    category: str,
    complaint_text: str = "",
    extracted_symptoms: list = None,
) -> dict:
    normalized = _normalize_category(category)
    combined_text = " ".join(
        [complaint_text or ""] + [str(item) for item in (extracted_symptoms or [])]
    ).lower()

    if any(token in combined_text for token in ["fracture", "broken", "trauma", "dislocation", "كسر", "اصابة", "إصابة"]):
        normalized = "trauma_fracture"
    elif normalized in {"unclear", "unclear_needs_evaluation", "general", "other", ""}:
        if any(token in combined_text for token in ["shortness of breath", "dyspnea", "can not breathe", "ضيق نفس", "مش قادر اتنفس"]):
            normalized = "respiratory_distress"
        elif any(token in combined_text for token in [
            "stroke", "facial droop", "face drooping", "weakness", "slurred speech",
            "speech difficulty", "unable to speak", "cannot speak", "inability to speak", "aphasia", "dysarthria",
            "سكتة", "جلطة", "شلل", "مش قادر اتكلم", "مش قادر أتكلم",
            "كلامي اتلخبط", "لساني تقيل", "وشي مايل", "وشه مايل", "نص جسمي مش بيتحرك",
        ]):
            normalized = "stroke_symptoms"
        elif any(token in combined_text for token in ["chest pain", "radiating", "angina", "ألم صدر"]):
            normalized = "chest_pain_cardiac"
        elif any(token in combined_text for token in ["sepsis", "infection", "حمى", "تعفن", "عدوى"]):
            normalized = "sepsis_concern"

    if level == 1:
        return {"en": "Resuscitation room immediately", "ar": "غرفة الإنعاش فوراً"}

    if level == 2:
        if normalized == "chest_pain_cardiac":
            return {"en": "ECG room, continuous monitoring", "ar": "غرفة رسم القلب، مراقبة مستمرة"}
        if normalized == "stroke_symptoms":
            return {"en": "Stroke bay, CT immediately", "ar": "سرير السكتة، أشعة مقطعية فوراً"}
        if normalized == "respiratory_distress":
            return {"en": "Resuscitation area, oxygen", "ar": "منطقة الإنعاش، أكسجين"}
        if normalized == "trauma_fracture":
            return {"en": "Trauma bay, imaging", "ar": "سرير الإصابات، أشعة"}
        if normalized == "abdominal_pain":
            return {"en": "Acute care, assessment", "ar": "رعاية حادة، تقييم"}
        if normalized == "sepsis_concern":
            return {"en": "Acute care, IV access, labs", "ar": "رعاية حادة، كانيولا، تحاليل"}
        if normalized == "allergic_reaction":
            return {"en": "Acute care, medication", "ar": "رعاية حادة، علاج"}
        if normalized == "psychiatric":
            return {"en": "Safe room, assessment", "ar": "غرفة آمنة، تقييم"}
        if normalized in {"unclear", "unclear_needs_evaluation"}:
            return {
                "en": "Assessment area, physician evaluation",
                "ar": "منطقة التقييم، فحص طبيب",
            }
        return {
            "en": "Acute care area, physician within 15 min",
            "ar": "منطقة الرعاية الحادة، طبيب خلال 15 دقيقة",
        }

    if level == 3:
        return {"en": "Urgent care area", "ar": "منطقة الرعاية العاجلة"}

    return {"en": "Waiting area, routine", "ar": "منطقة الانتظار، روتيني"}


def _register_pending_confirmation(patient_id: str, recommended_esi: int) -> dict:
    now = datetime.utcnow()
    expires = now + timedelta(seconds=CONFIRMATION_TIMEOUT_SECONDS)
    record = {
        "patient_id": patient_id,
        "recommended_esi": recommended_esi,
        "created_at": now,
        "expires_at": expires,
    }
    with _pending_lock:
        _pending_confirmations[patient_id] = record
    return record


def _resolve_pending_confirmation(patient_id: str) -> dict:
    with _pending_lock:
        return _pending_confirmations.pop(patient_id, None)


def require_firebase_user(authorization: str = Header(None)) -> dict:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing Authorization token")
    token = authorization.split(" ", 1)[1].strip()
    try:
        request = google_requests.Request()
        audience = os.getenv("FIREBASE_PROJECT_ID", "safe-triage-ai")
        claims = id_token.verify_firebase_token(token, request, audience=audience)
        return claims or {}
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid or expired token")


@app.get("/")
def read_root():
    return {"message": "SAFE-Triage AI System Active", "version": "2.0.0", "features": ["Voice Input", "AI Triage", "ESI v5", "FCM Push Alerts"]}

VOICE_NOTES_DIR = os.path.join(os.path.dirname(__file__), "voice_notes")
os.makedirs(VOICE_NOTES_DIR, exist_ok=True)


@app.post("/transcribe")
async def transcribe_audio(
    audio: UploadFile = File(...),
    language: str = Form("auto"),
    patient_id: str = Form(""),
    save_recording: str = Form("false"),
):
    """🎤 Voice Input: Convert speech to medical text via Gemini"""
    tmp_path = None
    try:
        ALLOWED_AUDIO_EXTENSIONS = {".wav", ".webm", ".mp3", ".ogg", ".m4a", ".flac"}
        raw_suffix = os.path.splitext(audio.filename or "")[1].lower()
        suffix = raw_suffix if raw_suffix in ALLOWED_AUDIO_EXTENSIONS else ".wav"
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            content = await audio.read()
            audio_size = len(content or b"")
            print(
                f"[ASR] /transcribe received bytes={audio_size} content_type={audio.content_type} language={language}",
                flush=True,
            )
            if audio_size == 0:
                raise HTTPException(status_code=400, detail="Empty audio payload")
            if audio_size < 1000:
                print(f"[ASR] WARNING: audio payload is very small ({audio_size} bytes)", flush=True)
            tmp.write(content)
            tmp_path = tmp.name

        result = medasr_service.transcribe(
            tmp_path,
            language_code=language,
            content_type=audio.content_type,
        )

        voice_note_id = None
        if result.get("success") and save_recording.lower() in ("true", "1", "yes"):
            voice_note_id = f"vn_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"
            saved_path = os.path.join(VOICE_NOTES_DIR, f"{voice_note_id}.webm")
            try:
                import shutil
                shutil.copy2(tmp_path, saved_path)
                # Save metadata
                meta = {
                    "voice_note_id": voice_note_id,
                    "patient_id": patient_id,
                    "transcription": result["transcription"],
                    "language": language,
                    "timestamp": datetime.utcnow().isoformat(),
                    "audio_size_bytes": audio_size,
                }
                import json as _json
                with open(os.path.join(VOICE_NOTES_DIR, f"{voice_note_id}.json"), "w") as mf:
                    _json.dump(meta, mf)
                print(f"[ASR] Voice note saved: {voice_note_id}", flush=True)
            except Exception as save_err:
                print(f"[ASR] WARNING: Failed to save voice note: {save_err}", flush=True)

        if result.get("success"):
            return {
                "success": True,
                "transcription": result["transcription"],
                "voice_note_id": voice_note_id,
            }
        error_detail = result.get("error", "Voice transcription failed")
        status_code = 503 if error_detail == "Voice transcription disabled" else 500
        raise HTTPException(status_code=status_code, detail=error_detail)
    except HTTPException:
        raise
    except Exception as e:
        print(f"[ERROR] Internal server error: {e}", flush=True)
        raise HTTPException(status_code=500, detail="An internal error occurred. Contact support.")
    finally:
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.unlink(tmp_path)
            except OSError:
                pass


@app.get("/voice-notes/{patient_id}")
def list_voice_notes(patient_id: str, user: dict = Depends(require_firebase_user)):
    """List saved voice notes for a patient. Requires authentication (HIPAA: PHI access control)."""
    import json as _json
    notes = []
    if not os.path.isdir(VOICE_NOTES_DIR):
        return {"patient_id": patient_id, "voice_notes": [], "count": 0}
    for fname in os.listdir(VOICE_NOTES_DIR):
        if fname.endswith(".json"):
            try:
                with open(os.path.join(VOICE_NOTES_DIR, fname)) as f:
                    meta = _json.load(f)
                if meta.get("patient_id") == patient_id:
                    # Strip audio file path from response (only accessible server-side)
                    safe_meta = {
                        "voice_note_id": meta.get("voice_note_id"),
                        "transcription": meta.get("transcription"),
                        "language": meta.get("language"),
                        "timestamp": meta.get("timestamp"),
                    }
                    notes.append(safe_meta)
            except Exception:
                continue
    notes.sort(key=lambda n: n.get("timestamp", ""), reverse=True)
    return {"patient_id": patient_id, "voice_notes": notes, "count": len(notes)}


@app.post("/api/fcm/register")
async def register_fcm_token(request: FCMTokenRequest):
    """Register a browser/device token for critical push notifications."""
    return register_fcm_device(
        user_id=request.user_id,
        token=request.token,
        role=request.role,
    )


@app.post("/api/alerts/retry")
async def retry_alerts():
    """Retry queued push/email alerts."""
    return retry_queued_alerts()


@app.get("/api/alerts/queue")
async def alert_queue_status():
    """Expose queued alert and device registration state."""
    return get_queue_status()


@app.post("/test-alert")
def test_alert(user: dict = Depends(require_firebase_user)):
    """Send a test alert to verify push + email delivery. Requires authentication."""
    payload = {
        "alert_level": AlertLevel.CODE_RED,
        "patient_id": "PT-001",
        "esi_level": 1,
        "news2_score": 8,
        "complaint": "chest pain radiating to left arm",
        "icd10_code": "I20.9",
        "icd10_description": "Angina pectoris",
        "snomed_code": "225566008",
        "snomed_term": "Ischemic chest pain",
        "recommended": ["12-Lead ECG", "Troponin", "Monitor"],
        "clinician": "Dr. Ahmed",
        "timestamp": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
    }
    result = send_alert_sync(payload)
    return {"success": True, "alerts_sent": result, "gahar_notice": GAHAR_NOTICE}


@app.post("/confirm-triage/request", response_model=TriageConfirmationPending)
def request_confirmation(request: TriageConfirmationStart):
    """Register a pending confirmation (placeholder storage)."""
    record = _register_pending_confirmation(request.patient_id, request.recommended_esi)
    return record


@app.get("/pending-confirmations", response_model=List[TriageConfirmationPending])
def get_pending_confirmations():
    """List pending confirmations (in-memory placeholder)."""
    with _pending_lock:
        records = list(_pending_confirmations.values())
    return records


@app.post("/confirm-triage")
def confirm_triage(confirmation: TriageConfirmationRequest):
    """
    Record human confirmation of AI recommendation.

    Placeholders:
    - Supervisor PIN: SUPERVISOR_PIN (default 0000)
    - Downgrade role: DOWNGRADE_ROLE (default supervisor)
    """
    is_downgrade = confirmation.confirmed_esi > confirmation.recommended_esi

    if is_downgrade:
        if confirmation.clinician_role != DOWNGRADE_ROLE:
            raise HTTPException(status_code=403, detail="Only supervisors can downgrade ESI")
        if confirmation.supervisor_pin != SUPERVISOR_PIN:
            raise HTTPException(status_code=401, detail="Invalid supervisor PIN")

    if confirmation.action == "overridden" and not confirmation.override_reason:
        raise HTTPException(status_code=400, detail="override_reason required for overrides")

    pending = _resolve_pending_confirmation(confirmation.patient_id)
    response_time = None
    if pending:
        response_time = int((datetime.utcnow() - pending["created_at"]).total_seconds())

    audit_service.log_confirmation(
        patient_id=confirmation.patient_id,
        recommended_esi=confirmation.recommended_esi,
        confirmed_esi=confirmation.confirmed_esi,
        clinician_id=confirmation.clinician_id,
        clinician_role=confirmation.clinician_role,
        action=confirmation.action,
        override_reason=confirmation.override_reason,
        supervisor_id=confirmation.clinician_id if confirmation.clinician_role == "supervisor" else None,
        response_time_seconds=response_time,
        escalated=False,
    )

    alerts_sent = _send_alert_for_level(
        level=confirmation.confirmed_esi,
        patient_id=confirmation.patient_id,
        complaint=f"Confirmed ESI {confirmation.confirmed_esi}",
        clinician=confirmation.clinician_id,
    )

    return {
        "status": "confirmed",
        "response_time_seconds": response_time,
        "alerts_sent": alerts_sent,
        "gahar_notice": GAHAR_NOTICE,
    }

@app.post("/triage", response_model=TriageResult)
def triage_patient(patient: PatientInput, db: Session = Depends(get_db)):
    _validate_patient_id_or_raise(patient.patient_id)
    _normalize_patient_vitals_for_triage(patient)
    complaint_text = (patient.chief_complaint_text or "").strip()
    if not complaint_text:
        vitals_validation = _validate_vitals_or_raise(patient)
        if vitals_validation:
            return vitals_validation
        return _build_no_complaint_default_response(
            patient,
            extraction_method="keyword_offline",
        )

    vitals_dict = patient.vitals.model_dump() if patient.vitals else {}
    critical_safety_rules = apply_critical_safety_rules(complaint_text, vitals_dict)
    complaint_validation = _validate_complaint_or_raise(complaint_text)
    if complaint_validation and not critical_safety_rules:
        return complaint_validation

    # Gender-complaint validation
    gender_check = validate_gender_complaint(patient.gender, complaint_text)
    if not gender_check["valid"]:
        raise HTTPException(status_code=400, detail=gender_check)
    vitals_validation = _validate_vitals_or_raise(patient)
    if vitals_validation:
        return vitals_validation

    try:
        det_result = engine_logic.triage(patient.model_dump())
        deterministic_confidence, deterministic_offline = _deterministic_confidence(
            det_result,
            force_offline=_offline_mode_enabled(),
        )
        esi_v5_result = _run_esi_v5_for_patient(
            patient,
            body_system=det_result.category,
            news2_score=det_result.news2_score,
            news2_level=det_result.news2_level,
            severity=_severity_from_level(det_result.final_level),
                ai_confidence=deterministic_confidence,
                is_offline=deterministic_offline,
        )
        final_level = esi_v5_result.final_esi
        esi_baseline = int(getattr(esi_v5_result, "esi_level", final_level))
        floors_applied = _extract_esi_v5_floor_names(esi_v5_result)
        final_level, critical_floor_reasoning, critical_floor_notes, critical_floor_names = _enforce_critical_safety_floors(
            final_level,
            critical_safety_rules,
        )
        floors_applied.extend(critical_floor_names)
        floors_applied = _dedupe_floor_names(floors_applied)

        result = engine_logic.evaluate(patient)
        red_flag_summary = _build_red_flag_summary(
            vitals_dict,
            det_result.news2_score,
            complaint_text=patient.chief_complaint_text,
        )
        if critical_floor_notes:
            red_flag_summary.extend(critical_floor_notes)

        # Add ICD-10 coding for GAHAR compliance
        result_dict = result.model_dump() if hasattr(result, 'model_dump') else vars(result)
        result_dict["chief_complaint"] = patient.chief_complaint_text
        result_dict["category"] = det_result.category
        result_dict["extraction_method"] = det_result.extraction_method
        result_dict["red_flag_summary"] = red_flag_summary

        colors = {1: "#ef4444", 2: "#f97316", 3: "#eab308", 4: "#22c55e", 5: "#3b82f6"}
        labels_en = {1: "Resuscitation", 2: "Emergent", 3: "Urgent", 4: "Less Urgent", 5: "Non-Urgent"}
        labels_ar = {1: "إنعاش", 2: "طوارئ", 3: "عاجل", 4: "أقل إلحاحاً", 5: "غير عاجل"}
        times_en = {1: "Immediate", 2: "< 15 minutes", 3: "< 30 minutes", 4: "< 60 minutes", 5: "< 120 minutes"}
        times_ar = {1: "فوري", 2: "< 15 دقيقة", 3: "< 30 دقيقة", 4: "< 60 دقيقة", 5: "< 120 دقيقة"}
        selected_action = _action_text_for_level_and_category(
            final_level,
            det_result.category,
            complaint_text=patient.chief_complaint_text,
            extracted_symptoms=[],
        )

        result_dict["level"] = final_level
        result_dict["color_code"] = colors.get(final_level, "#eab308")
        result_dict["label_en"] = labels_en.get(final_level, "Urgent")
        result_dict["label_ar"] = labels_ar.get(final_level, "عاجل")
        result_dict["action_ar"] = selected_action["ar"]
        result_dict["action_en"] = selected_action["en"]
        result_dict["recommended_action"] = f"{selected_action['ar']} / {selected_action['en']}"
        result_dict["time_ar"] = times_ar.get(final_level, "< 30 دقيقة")
        result_dict["time_en"] = times_en.get(final_level, "< 30 minutes")
        result_dict["time_to_physician"] = f"{result_dict['time_ar']} / {result_dict['time_en']}"
        result_dict["confidence"] = "Deterministic (ESI v5 Offline)"
        result_dict["reasoning"] = (
            (esi_v5_result.reasoning or [])
            + critical_floor_reasoning
            + (result_dict.get("reasoning") or [])
        )
        result_dict["requires_review"] = bool(result_dict.get("requires_review") or esi_v5_result.requires_review)
        result_dict["review_message"] = result_dict.get("review_message") or (
            "Manual review recommended by ESI v5 confidence/safety gate" if esi_v5_result.requires_review else ""
        )
        result_dict["stage_reached"] = esi_v5_result.stage_reached
        result_dict["resources_estimated"] = esi_v5_result.resources_estimated
        result_dict["confidence_action"] = esi_v5_result.confidence_action
        result_dict["news2_override"] = esi_v5_result.news2_override
        result_dict["safety_floors"] = (esi_v5_result.safety_floors_applied or []) + critical_floor_notes
        _attach_floor_observation(
            result_dict,
            esi_baseline=esi_baseline,
            esi_safe=final_level,
            floors_applied=floors_applied,
        )
        deterministic_reasoning_safety = _derive_reasoning_safety(None, complaint_text)
        result_dict["insufficient_info_warning"] = _check_complaint_sufficiency(
            complaint_text,
            None,
            fallback_category=det_result.category,
            reasoning_safety=deterministic_reasoning_safety,
        )

        enriched = enrich_triage_with_icd10(result_dict)
        
        # Check Silent MI pattern for diabetic patients
        patient_data = patient.model_dump()
        silent_mi = check_silent_mi_pattern(patient_data)
        if _should_apply_silent_mi_floor(patient_data, silent_mi):
            enriched["silent_mi_alert"] = silent_mi
        
        # Send alert for critical patients
        alerts_sent = _send_alert_for_level(
            level=final_level,
            patient_id=patient.patient_id,
            complaint=patient.chief_complaint_text,
            news2_score=det_result.news2_score,
            icd10_code=enriched.get("icd10_coding", {}).get("code", ""),
            icd10_description=enriched.get("icd10_coding", {}).get("description_en", ""),
            clinician="Unassigned | غير محدد",
        )
        
        # Audit logging for GAHAR compliance
        audit_service.log_triage(
            patient_id=patient.patient_id,
            age=patient.age,
            gender=patient.gender,
            chief_complaint=patient.chief_complaint_text,
            vitals=patient.vitals.model_dump() if patient.vitals else {},
            news2_score=det_result.news2_score,
            news2_breakdown=getattr(det_result, "news2_breakdown", {}),
            recommended_esi=final_level,
            final_esi=final_level,
            esi_baseline=esi_baseline,
            esi_safe=final_level,
            safety_floors_applied=floors_applied,
            safety_floor_count=len(floors_applied),
            icd10_codes=[enriched.get("icd10_coding", {}).get("code")],
            ai_confidence=deterministic_confidence,
            session_mode="standard"
        )
        
        return result_dict
    except Exception as e:
        print(f"[ERROR] Internal server error: {e}", flush=True)
        raise HTTPException(status_code=500, detail="An internal error occurred. Contact support.")

@app.post("/ai-triage")
def ai_triage_patient(patient: PatientInput, db: Session = Depends(get_db)):
    """
    AI-enhanced triage endpoint.
    
    AUDIT FIX: Properly handles AI fallback flag.
    When AI fails, uses deterministic engine instead of hardcoded Level 3.
    """
    try:
        endpoint_started = time.perf_counter()
        print("=" * 50, flush=True)
        print("🏥 AI-TRIAGE ENDPOINT CALLED", flush=True)
        print(f"   ai_service.client = {ai_service.client}", flush=True)
        print(f"   ai_service.mode = {getattr(ai_service, 'mode', 'unknown')}", flush=True)
        print("=" * 50, flush=True)

        _validate_patient_id_or_raise(patient.patient_id)
        _normalize_patient_vitals_for_triage(patient)
        complaint_text = (patient.chief_complaint_text or "").strip()
        if not complaint_text:
            vitals_validation = _validate_vitals_or_raise(patient)
            if vitals_validation:
                return vitals_validation
            response_payload = _build_no_complaint_default_response(
                patient,
                extraction_method="keyword_offline",
            )
            print(
                f"[Timing] AI-TRIAGE total endpoint time: {(time.perf_counter() - endpoint_started):.3f}s",
                flush=True,
            )
            return response_payload

        vitals_dict = patient.vitals.model_dump() if patient.vitals else {}
        critical_safety_rules = apply_critical_safety_rules(complaint_text, vitals_dict)
        complaint_validation = _validate_complaint_or_raise(complaint_text)
        if complaint_validation and not critical_safety_rules:
            return complaint_validation

        critical_safety_flags = [
            str(rule.get("category"))
            for rule in critical_safety_rules
            if str(rule.get("category") or "").strip()
        ]
        has_vitals = _has_vitals_for_triage(patient)
        has_red_flag_keyword = _has_immediate_triage_keyword(complaint_text) or bool(critical_safety_rules)
        arrived_by_ambulance = bool(getattr(patient, "arrived_by_ambulance", False))
        if (
            len(complaint_text.strip()) < 20
            and not has_vitals
            and not has_red_flag_keyword
            and not arrived_by_ambulance
        ):
            return _build_needs_more_info_response()

        # Gender-complaint validation
        gender_check = validate_gender_complaint(patient.gender, complaint_text)
        if not gender_check["valid"]:
            raise HTTPException(status_code=400, detail=gender_check)
        allow_missing_vitals_for_immediate = (
            not has_vitals and (has_red_flag_keyword or arrived_by_ambulance)
        )
        if not allow_missing_vitals_for_immediate:
            vitals_validation = _validate_vitals_or_raise(patient)
            if vitals_validation:
                return vitals_validation

        pre_ai_english_match = _lookup_english_keyword_matches(complaint_text)
        pre_ai_back_pain_short_circuit = bool(
            _english_match_has_low_acuity_back_pain(pre_ai_english_match)
            and _vitals_for_low_acuity_are_normal(vitals_dict)
            and not critical_safety_rules
        )

        if pre_ai_back_pain_short_circuit:
            ai_result = {
                "fallback": True,
                "error": "pre_ai_back_pain_keyword",
                "fallback_reason": "pre_ai_back_pain_keyword",
                "message": "Pre-AI low-acuity back pain keyword route applied",
                "message_ar": "تم تطبيق مسار كلمات مفتاحية لآلام الظهر منخفضة الخطورة قبل الذكاء الاصطناعي",
                "confidence_score": 0.85,
                "red_flags": [],
                "resource_count": 1,
                "expected_resources": ["imaging"],
            }
            print("[Timing] AI service analyze_triage: skipped (pre-AI back pain keyword route)", flush=True)
        else:
            ai_started = time.perf_counter()
            ai_result = ai_service.analyze_triage(patient.model_dump())
            print(
                f"[Timing] AI service analyze_triage: {(time.perf_counter() - ai_started):.3f}s",
                flush=True,
            )
        print(f"   ai_result = {ai_result}", flush=True) if ai_result is None else print(f"   ai_result keys = {list(ai_result.keys())}", flush=True)
        if ai_result and ai_result.get("success") is False:
            ai_failure_error = str(ai_result.get("error") or "").strip().lower()
            ai_infra_failure = ai_failure_error in {"gemini_timeout", "gemini_parse_error", "gemini_api_error"}
            if ai_infra_failure:
                ai_result = {
                    "fallback": True,
                    "error": ai_failure_error or "gemini_api_error",
                    "fallback_reason": ai_result.get("fallback_reason") or "api_error",
                    "message": ai_result.get("message", "AI service unavailable; deterministic fallback applied"),
                    "message_ar": ai_result.get("message_ar", "خدمة الذكاء الاصطناعي غير متاحة؛ تم تطبيق الفرز الحتمي"),
                    "confidence_score": 0.0,
                    "red_flags": critical_safety_flags,
                }
            elif critical_safety_rules:
                # Do not reject short/ambiguous text when a deterministic critical rule is already triggered.
                ai_result = {
                    "fallback": True,
                    "error": ai_result.get("error", "critical_rule_forced_fallback"),
                    "fallback_reason": ai_result.get("fallback_reason"),
                    "message": ai_result.get("message", "AI validation bypassed due to critical safety rule"),
                    "message_ar": ai_result.get("message_ar", "تم تجاوز تحقق الذكاء الاصطناعي بسبب قاعدة أمان حرجة"),
                    "confidence_score": 0.0,
                    "red_flags": critical_safety_flags,
                }
            else:
                return _validation_failed_response(
                    error_type="invalid_complaint",
                    message=ai_result.get("message", "Unable to process complaint"),
                    message_ar=ai_result.get("message_ar", "تعذر معالجة الشكوى"),
                    details=[
                        {
                            "validator_error": ai_result.get("error", "invalid_input"),
                            "confidence_score": ai_result.get("confidence_score", 0.0),
                            "action": ai_result.get("action", "require_reentry"),
                        }
                    ],
                    action=ai_result.get("action", "require_reentry"),
                )
        normalized_ai_category = _normalize_ai_category_for_esi(ai_result, complaint_text) if ai_result else ""
        if ai_result:
            raw_ai_category = str(ai_result.get("category") or "").strip()
            if raw_ai_category and raw_ai_category != normalized_ai_category:
                ai_result["category_raw"] = raw_ai_category
            ai_result["category"] = normalized_ai_category
            raw_ai_red_flags = [str(flag) for flag in (ai_result.get("red_flags") or [])]
            if raw_ai_red_flags:
                ai_result["red_flags_raw"] = raw_ai_red_flags
            ai_result["red_flags"] = _sanitize_ai_red_flags(
                raw_ai_red_flags,
                complaint_text=complaint_text,
                normalized_category=normalized_ai_category,
            )
        ai_confidence = ai_result.get("confidence_score") if ai_result else None
        try:
            ai_confidence = float(ai_confidence) if ai_confidence is not None else None
        except (TypeError, ValueError):
            ai_confidence = None

        if (
            ai_confidence is not None
            and ai_confidence < 0.50
            and not critical_safety_rules
            and not _contains_any_token(complaint_text, AI_ABDOMINAL_PAIN_TOKENS)
        ):
            ai_result = {
                "fallback": True,
                "error": "requires_clarification",
                "fallback_reason": "requires_clarification",
                "message": f"Unable to interpret complaint (confidence: {ai_confidence:.2%})",
                "message_ar": "تعذر تفسير الشكوى بدقة كافية - يرجى التوضيح",
                "action": "requires_supervisor_review",
                "ui_action": "show_clarification_dialog",
                "esi_level": None,
                "confidence_score": ai_confidence,
                "suggested_questions": [
                    "Can you describe your symptoms in more detail?",
                    "What brought you to the emergency department today?",
                    "Where is your pain or discomfort located?",
                    "When did these symptoms start?",
                ],
                "red_flags": critical_safety_flags,
            }
        low_confidence = ai_confidence is not None and ai_confidence < 0.70
        unclear_category = normalized_ai_category in {
            "unclear_needs_evaluation",
            "unclear",
            "insufficient_information",
        }
        gemini_body_system = _resolve_gemini_body_system(ai_result, normalized_ai_category) if ai_result else ""
        gemini_has_parseable_body_system = _is_parseable_body_system(gemini_body_system)
        gemini_has_severity = _has_meaningful_triage_field(ai_result.get("severity")) if ai_result else False
        gemini_has_red_flags_array = isinstance(ai_result.get("red_flags"), list) if ai_result else False
        gemini_low_confidence_for_esi = bool(ai_confidence is not None and ai_confidence < 0.60)
        gemini_missing_core_features = bool(not gemini_has_parseable_body_system and not gemini_has_severity)
        gemini_valid_but_unclear_category = bool(
            ai_result
            and unclear_category
            and not gemini_low_confidence_for_esi
            and not gemini_missing_core_features
            and gemini_has_red_flags_array
            and ai_confidence is not None
            and ai_confidence >= 0.60
        )
        reasoning_safety = _derive_reasoning_safety(ai_result, complaint_text)
        reasoning_red_flags = list(reasoning_safety.get("red_flags", []))
        reasoning_override_category = reasoning_safety.get("override_category")
        reasoning_floor_esi = reasoning_safety.get("floor_esi")
        reasoning_stroke_signal = bool(reasoning_safety.get("stroke_signal"))
        reasoning_critical_signal = bool(reasoning_safety.get("critical_signal"))
        insufficient_info_warning = _check_complaint_sufficiency(
            complaint_text,
            ai_result,
            fallback_category=reasoning_override_category or "",
            reasoning_safety=reasoning_safety,
        )
        requires_explicit_confirmation = low_confidence or unclear_category or reasoning_critical_signal
        
        # Fallback to deterministic keyword path only for true AI extraction failures.
        force_keyword_fallback = bool(
            ai_result is None
            or ai_result.get("fallback")
            or "error" in ai_result
            or gemini_low_confidence_for_esi
            or gemini_missing_core_features
        )
        if force_keyword_fallback:
            # AI already failed for this request; use deterministic keyword engine directly.
            fallback_triage_started = time.perf_counter()
            fallback_payload = patient.model_dump()
            if pre_ai_back_pain_short_circuit:
                fallback_payload["category_override"] = "simple_back_pain"
                fallback_payload["extraction_method_override"] = "keyword_mimic_enriched"
            std_det_result = _triage_with_compound_keyword_split(
                fallback_payload,
                patient.chief_complaint_text,
            )
            if pre_ai_back_pain_short_circuit:
                english_keyword_match = _canonical_low_acuity_back_pain_match(pre_ai_english_match)
            else:
                english_keyword_match = pre_ai_english_match or _lookup_english_keyword_matches(
                    patient.chief_complaint_text
                )
            fallback_extraction_method = getattr(std_det_result, "extraction_method", "keyword_offline")
            if english_keyword_match:
                fallback_extraction_method = "keyword_mimic_enriched"
            print(
                f"[Timing] Deterministic fallback classify/evaluate: {(time.perf_counter() - fallback_triage_started):.3f}s",
                flush=True,
            )
            fallback_confidence, fallback_is_offline = _deterministic_confidence(
                std_det_result,
                force_offline=_offline_mode_enabled(),
            )
            fallback_esi_started = time.perf_counter()
            esi_v5_fallback = _run_esi_v5_for_patient(
                patient,
                body_system=std_det_result.category,
                news2_score=std_det_result.news2_score,
                news2_level=std_det_result.news2_level,
                severity=_severity_from_level(std_det_result.final_level),
                red_flags=[
                    str(flag)
                    for flag in (
                        list(getattr(std_det_result, "alerts_en", []) or [])
                        + list(getattr(std_det_result, "alerts_ar", []) or [])
                    )
                ],
                ai_confidence=fallback_confidence,
                is_offline=fallback_is_offline,
            )
            print(
                f"[Timing] ESI v5 fallback calculation: {(time.perf_counter() - fallback_esi_started):.3f}s",
                flush=True,
            )
            vitals_dict = patient.vitals.model_dump() if patient.vitals else {}
            red_flag_summary = _build_red_flag_summary(
                vitals_dict,
                std_det_result.news2_score,
                complaint_text=patient.chief_complaint_text,
            )
            
            # Build informative response showing deterministic fallback was used
            if ai_result is None:
                fallback_reason_code = "ai_unavailable_unspecified"
                fallback_reason = "AI unavailable"
            elif gemini_low_confidence_for_esi:
                fallback_reason_code = "gemini_low_confidence"
                fallback_reason = f"Gemini confidence below threshold ({ai_confidence:.0%})"
            elif gemini_missing_core_features:
                fallback_reason_code = "gemini_missing_body_system_and_severity"
                fallback_reason = "Gemini response missing both body system and severity"
            else:
                fallback_reason_code = str(
                    ai_result.get("fallback_reason")
                    or ai_result.get("error")
                    or "ai_unavailable_unspecified"
                )
                fallback_reason = ai_result.get("message", ai_result.get("error", "AI unavailable"))
            
            # Add ICD-10 coding for GAHAR compliance
            fallback_dict = {
                "level": int(getattr(std_det_result, "final_level", 3)),
                "category": reasoning_override_category or getattr(std_det_result, "category", "general"),
                "chief_complaint": patient.chief_complaint_text
            }
            enriched = enrich_triage_with_icd10(fallback_dict)
            icd10_coding = enriched.get("icd10_coding", {})

            alerts_sent = None
            fallback_level = int(esi_v5_fallback.final_esi)
            fallback_resource_floor = int(getattr(esi_v5_fallback, "resources_estimated", 0) or 0)
            fallback_has_red_flags = bool(
                list(getattr(std_det_result, "alerts_en", []) or [])
                or list(getattr(std_det_result, "alerts_ar", []) or [])
                or reasoning_red_flags
                or critical_safety_flags
            )
            fallback_news2 = _safe_float(getattr(std_det_result, "news2_score", None))
            fallback_low_acuity_cap = bool(
                fallback_level >= 4
                and fallback_resource_floor <= 1
                and fallback_news2 is not None
                and fallback_news2 < 5
                and not fallback_has_red_flags
                and _vitals_for_low_acuity_are_normal(vitals_dict)
                and fallback_confidence >= 0.70
            )
            fallback_resource_count, fallback_expected_resources = _resolve_resource_count(
                ai_result,
                complaint_text=patient.chief_complaint_text,
                normalized_category=reasoning_override_category or std_det_result.category,
                minimum_resource_count=fallback_resource_floor,
                maximum_resource_count=1 if fallback_low_acuity_cap else None,
            )
            if pre_ai_back_pain_short_circuit:
                fallback_resource_count = 1
                fallback_expected_resources = ["imaging"]
            fallback_level = _apply_resource_count_esi_logic(
                fallback_level,
                fallback_resource_count,
                news2_score=getattr(std_det_result, "news2_score", None),
                has_red_flags=fallback_has_red_flags,
                vitals_normal_for_low_acuity=_vitals_for_low_acuity_are_normal(vitals_dict),
                ai_confidence=fallback_confidence,
            )
            if pre_ai_back_pain_short_circuit:
                fallback_level = max(fallback_level, 4)
            if english_keyword_match:
                fallback_level = min(fallback_level, int(english_keyword_match["base_esi"]))
                fallback_resource_count = max(
                    int(fallback_resource_count),
                    int(english_keyword_match.get("resource_estimate", 2) or 2),
                )
                if bool(english_keyword_match.get("is_red_flag")):
                    fallback_has_red_flags = True
                matched_terms = ", ".join(english_keyword_match.get("matched_keywords", [])[:5])
                red_flag_summary.append(
                    f"MIMIC EN keyword match ({matched_terms}) -> base ESI {english_keyword_match['base_esi']}"
                )
            else:
                fallback_category_norm = _normalize_match_text(getattr(std_det_result, "category", "")).replace("-", "_")
                if fallback_category_norm in {
                    "",
                    "unclear",
                    "unclear_needs_evaluation",
                    "insufficient_information",
                    "unknown",
                    "general",
                    "other",
                }:
                    fallback_level = min(fallback_level, 3)
            fallback_esi_baseline = int(fallback_level)
            if ai_result is not None:
                ai_result["resource_count"] = fallback_resource_count
                ai_result["expected_resources"] = fallback_expected_resources
            fallback_floors_applied = _extract_esi_v5_floor_names(esi_v5_fallback)
            fallback_action_category = reasoning_override_category or std_det_result.category
            fallback_action = _action_text_for_level_and_category(
                fallback_level,
                fallback_action_category,
                complaint_text=patient.chief_complaint_text,
                extracted_symptoms=ai_result.get("extracted_symptoms") if ai_result else [],
            )
            fallback_red_flags = list(getattr(std_det_result, "alerts_en", []) or []) + list(
                getattr(std_det_result, "alerts_ar", []) or []
            )
            fallback_red_flags.extend(reasoning_red_flags)
            fallback_red_flags.extend(critical_safety_flags)
            if english_keyword_match and bool(english_keyword_match.get("is_red_flag")):
                fallback_red_flags.append("english_keyword_red_flag")
            reasoning_floor_note = None
            fallback_safe_stable_context = _safe_stable_reasoning_context(
                level=fallback_level,
                objective_red_flag_present=fallback_has_red_flags,
                news2_value=fallback_news2,
                vitals=vitals_dict,
                reasoning_stroke_signal=reasoning_stroke_signal,
            )
            if reasoning_floor_esi and fallback_level > int(reasoning_floor_esi) and not fallback_safe_stable_context:
                fallback_level = int(reasoning_floor_esi)
                reasoning_floor_note = (
                    "AI reasoning flagged critical risk with objective instability -> conservative ESI 2 override"
                )
                fallback_floors_applied.append("ai_reasoning_critical_risk")
                red_flag_summary.append(
                    "AI reasoning indicates critical risk with objective instability -> escalated to ESI 2 | "
                    "الاستدلال الطبي للذكاء الاصطناعي يشير لخطر حرج مع عدم استقرار موضوعي -> التصعيد إلى ESI 2"
                )
                fallback_action_category = reasoning_override_category or fallback_action_category
                fallback_action = _action_text_for_level_and_category(
                    fallback_level,
                    fallback_action_category,
                    complaint_text=patient.chief_complaint_text,
                    extracted_symptoms=ai_result.get("extracted_symptoms") if ai_result else [],
                )
            if reasoning_stroke_signal and (
                not icd10_coding.get("primary_code")
                or str(icd10_coding.get("primary_code", "")).upper() == "R69"
            ):
                icd10_coding = {
                    **icd10_coding,
                    "primary_code": "I63.9",
                    "description_en": "Cerebral infarction, unspecified",
                    "gahar_compliant": True,
                }
            patient_data = patient.model_dump()
            patient_data["chief_complaint"] = patient.chief_complaint_text
            if ai_result and ai_result.get("extracted_symptoms"):
                patient_data["extracted_symptoms"] = ai_result.get("extracted_symptoms")
            silent_mi = check_silent_mi_pattern(patient_data)
            if _should_apply_silent_mi_floor(patient_data, silent_mi):
                fallback_floors_applied.append("silent_mi")
                fallback_red_flags.append("silent_mi_risk")
                red_flag_summary.append(
                    "Diabetic + atypical GI symptoms + fatigue → Silent MI risk | مريض سكري مع أعراض معدية غير نمطية + تعب → خطر جلطة صامتة"
                )
                if fallback_level > 2:
                    fallback_level = 2
                    fallback_action = _action_text_for_level_and_category(
                        fallback_level,
                        fallback_action_category,
                        complaint_text=patient.chief_complaint_text,
                        extracted_symptoms=ai_result.get("extracted_symptoms") if ai_result else [],
                    )
                if not icd10_coding.get("primary_code") or str(icd10_coding.get("primary_code")).upper() == "R69":
                    icd10_coding = {
                        **icd10_coding,
                        "primary_code": silent_mi.get("icd10_code") or "R07.89",
                        "description_en": "Other chest pain (silent MI risk)",
                        "gahar_compliant": True,
                    }
            fallback_level, critical_floor_reasoning, critical_floor_notes, critical_floor_names = _enforce_critical_safety_floors(
                fallback_level,
                critical_safety_rules,
            )
            fallback_floors_applied.extend(critical_floor_names)
            fallback_floors_applied = _dedupe_floor_names(fallback_floors_applied)
            if critical_floor_notes:
                red_flag_summary.extend(critical_floor_notes)
                fallback_action = _action_text_for_level_and_category(
                    fallback_level,
                    fallback_action_category,
                    complaint_text=patient.chief_complaint_text,
                    extracted_symptoms=ai_result.get("extracted_symptoms") if ai_result else [],
                )
            if fallback_level <= 2:
                alert_payload = {
                    "alert_level": AlertLevel.CODE_RED if fallback_level == 1 else AlertLevel.HIGH_ALERT,
                    "patient_id": patient.patient_id,
                    "esi_level": fallback_level,
                    "news2_score": 0,
                    "complaint": patient.chief_complaint_text,
                    "icd10_code": icd10_coding.get("primary_code", ""),
                    "icd10_description": icd10_coding.get("description_en", ""),
                    "snomed_code": ai_result.get("snomed_code") if ai_result else "",
                    "snomed_term": ai_result.get("snomed_term") if ai_result else "",
                    "recommended": [],
                    "clinician": "Unassigned | غير محدد",
                    "timestamp": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
                }
                alerts_sent = send_alert_sync(alert_payload)

            # Keep audit trail complete even when AI falls back to deterministic mode.
            try:
                ai_safe = ai_result or {}
                audit_service.log_triage(
                    patient_id=patient.patient_id,
                    age=patient.age,
                    gender=patient.gender,
                    chief_complaint=patient.chief_complaint_text,
                    vitals=patient.vitals.model_dump() if patient.vitals else {},
                    news2_score=std_det_result.news2_score,
                    news2_breakdown=getattr(std_det_result, "news2_breakdown", {}),
                    recommended_esi=fallback_level,
                    final_esi=fallback_level,
                    esi_baseline=fallback_esi_baseline,
                    esi_safe=fallback_level,
                    safety_floors_applied=fallback_floors_applied,
                    safety_floor_count=len(fallback_floors_applied),
                    extracted_features=ai_safe.get("extracted_symptoms"),
                    icd10_codes=[icd10_coding.get("primary_code")] if icd10_coding else [],
                    ai_confidence=fallback_confidence,
                    rag_sources=ai_safe.get("rag_sources"),
                    session_mode="ai_fallback",
                )
            except Exception as audit_exc:
                print(f"Audit logging error in fallback mode (non-blocking): {audit_exc}", flush=True)

            try:
                qa_review = qa_agent.review_triage(
                    triage_result={
                        "esi_level": fallback_level,
                        "news2_score": std_det_result.news2_score,
                    },
                    patient={
                        "age": patient.age,
                        "gender": patient.gender,
                        "comorbidities": patient.comorbidities or [],
                        "chief_complaint": patient.chief_complaint_text,
                    },
                )
                if qa_review["flagged"]:
                    print(
                        f"⚠️ QA FLAG: {qa_review['reason']} - Recommend ESI {qa_review['recommended_esi']}",
                        flush=True,
                    )
            except Exception as qa_exc:
                print(f"QA Agent error in fallback mode (non-blocking): {qa_exc}", flush=True)
            
            colors = {1: "#ef4444", 2: "#f97316", 3: "#eab308", 4: "#22c55e", 5: "#3b82f6"}
            labels_en = {1: "Resuscitation", 2: "Emergent", 3: "Urgent", 4: "Less Urgent", 5: "Non-Urgent"}
            labels_ar = {1: "إنعاش", 2: "طوارئ", 3: "عاجل", 4: "أقل إلحاحاً", 5: "غير عاجل"}
            times_en = {1: "Immediate", 2: "< 15 minutes", 3: "< 30 minutes", 4: "< 60 minutes", 5: "< 120 minutes"}
            times_ar = {1: "فوري", 2: "< 15 دقيقة", 3: "< 30 دقيقة", 4: "< 60 دقيقة", 5: "< 120 دقيقة"}

            print(
                f"[Timing] AI-TRIAGE total endpoint time: {(time.perf_counter() - endpoint_started):.3f}s",
                flush=True,
            )
            response_payload = {
                "level": fallback_level,
                "extraction_method": fallback_extraction_method,
                "color_code": colors.get(fallback_level, "#eab308"),
                "label_en": labels_en.get(fallback_level, "Urgent"),
                "label_ar": labels_ar.get(fallback_level, "عاجل"),
                "description_ar": fallback_action["ar"],
                "description_en": fallback_action["en"],
                "action_ar": fallback_action["ar"],
                "action_en": fallback_action["en"],
                "time_ar": times_ar.get(fallback_level, "< 30 دقيقة"),
                "time_en": times_en.get(fallback_level, "< 30 minutes"),
                "reasoning": (esi_v5_fallback.reasoning or [])
                + [getattr(std_det_result, "decision_path", "Deterministic fallback applied")]
                + [f"⚠️ {fallback_reason}"]
                + [f"Resource-aware ESI assignment: {fallback_resource_count} expected ED resources"]
                + ([reasoning_floor_note] if reasoning_floor_note else [])
                + critical_floor_reasoning,
                "reasoning_ar": [getattr(std_det_result, "decision_path_ar", "تم استخدام الفرز الحتمي")]
                + [ai_result.get("message_ar", "تم استخدام الفرز الحتمي") if ai_result else "تم استخدام الفرز الحتمي"]
                + [f"تقدير الموارد المتوقعة للحالة: {fallback_resource_count}"]
                + (
                    ["تم تطبيق تصعيد احتياطي بناءً على الاستدلال الطبي للذكاء الاصطناعي"]
                    if reasoning_floor_note
                    else []
                ),
                "reasoning_en": (esi_v5_fallback.reasoning or [])
                + [getattr(std_det_result, "decision_path_en", "Deterministic fallback applied")]
                + [fallback_reason]
                + [f"Resource-aware ESI assignment: {fallback_resource_count} expected ED resources"]
                + ([reasoning_floor_note] if reasoning_floor_note else [])
                + critical_floor_reasoning,
                "red_flags": sorted(set(fallback_red_flags)),
                "red_flag_summary": red_flag_summary,
                "ai_data": None,
                "confidence": "Deterministic (AI Fallback)",
                "fallback_reason": fallback_reason_code,
                "icd10_coding": icd10_coding,
                "icd10_code": icd10_coding.get("primary_code", ""),
                "icd10_description": icd10_coding.get("description_en", ""),
                "snomed_code": "",
                "snomed_term": "",
                "resource_plan": get_resources_for_workup(ai_result.get("recommended_workup") or []) if ai_result else [],
                "alerts_sent": alerts_sent,
                "silent_mi_alert": silent_mi if silent_mi["pattern_detected"] else None,
                "requires_review": bool(getattr(std_det_result, "requires_review", False) or esi_v5_fallback.requires_review),
                "review_message": getattr(std_det_result, "review_message", "") or ("Manual review recommended by ESI v5 confidence/safety gate" if esi_v5_fallback.requires_review else ""),
                "requires_confirmation": requires_explicit_confirmation,
                "stage_reached": esi_v5_fallback.stage_reached,
                "resources_estimated": fallback_resource_count,
                "confidence_action": esi_v5_fallback.confidence_action,
                "news2_override": esi_v5_fallback.news2_override,
                "safety_floors": (esi_v5_fallback.safety_floors_applied or [])
                + ([reasoning_floor_note] if reasoning_floor_note else [])
                + critical_floor_notes,
                "context_rules_triggered": getattr(esi_v5_fallback, "context_rules_triggered", []),
                "confidence_flag": "medium" if low_confidence else ("unclear_presentation" if unclear_category else None),
                "low_confidence_warning": (
                    f"Uncertain classification (confidence: {ai_confidence:.2%}) - deterministic triage retained pending review"
                    if low_confidence else None
                ),
                "insufficient_info_warning": insufficient_info_warning,
                "gahar_notice": GAHAR_NOTICE
            }
            return _attach_floor_observation(
                response_payload,
                esi_baseline=fallback_esi_baseline,
                esi_safe=fallback_level,
                floors_applied=fallback_floors_applied,
            )

        # Confidence guard:
        # low-confidence AI extraction must not force a higher-acuity category.
        ai_confidence_value = _safe_ai_confidence(ai_result)
        use_ai_override = bool(
            ai_confidence_value is not None
            and ai_confidence_value >= 0.80
            and not unclear_category
            and not critical_safety_rules
        )
        use_gemini_partial = bool(
            gemini_valid_but_unclear_category
            and not use_ai_override
        )
        use_gemini_features = bool(use_ai_override or use_gemini_partial)
        triage_input = patient.model_dump()
        reasoning_override_applied = False
        if not use_ai_override and not use_gemini_partial and reasoning_override_category:
            triage_input["category_override"] = reasoning_override_category
            triage_input["extraction_method_override"] = "ai_reasoning_safety_override"
            reasoning_override_applied = True
        det_started = time.perf_counter()
        if use_ai_override:
            triage_input["category_override"] = ai_result.get("category")
            triage_input["extraction_method_override"] = "gemini_online"
            det_result = engine_logic_ai.triage(triage_input)
            print(
                f"[Timing] Deterministic engine with AI category override: {(time.perf_counter() - det_started):.3f}s",
                flush=True,
            )
        else:
            det_result = engine_logic.triage(triage_input)
            print(
                f"[Timing] Deterministic engine (NEWS2/context only): {(time.perf_counter() - det_started):.3f}s",
                flush=True,
            )

        if use_gemini_partial:
            resolved_body_system = gemini_body_system
        elif use_ai_override:
            resolved_body_system = normalized_ai_category or gemini_body_system
        else:
            resolved_body_system = det_result.category or "unclear"
        resolved_severity = (
            ai_result.get("severity")
            if (use_gemini_features and _has_meaningful_triage_field(ai_result.get("severity")))
            else _severity_from_level(det_result.final_level)
        )
        resolved_onset = ai_result.get("onset", "unknown") if use_gemini_features else "unknown"
        resolved_red_flags = (
            _sanitize_ai_red_flags(
                ai_result.get("red_flags"),
                complaint_text=patient.chief_complaint_text,
                normalized_category=resolved_body_system,
            )
            if use_gemini_features
            else [
                str(flag)
                for flag in (
                    list(getattr(det_result, "alerts_en", []) or [])
                    + list(getattr(det_result, "alerts_ar", []) or [])
                )
            ]
        )
        objective_red_flags = [str(flag) for flag in resolved_red_flags if str(flag).strip()]
        for flag in reasoning_red_flags:
            if flag not in resolved_red_flags:
                resolved_red_flags.append(flag)
        for flag in critical_safety_flags:
            if flag not in resolved_red_flags:
                resolved_red_flags.append(flag)
        objective_red_flag_present = bool(objective_red_flags or critical_safety_flags)

        if reasoning_override_applied and (resolved_body_system or "").strip().lower() in {
            "",
            "unclear",
            "unclear_needs_evaluation",
            "insufficient_information",
            "unknown",
        }:
            resolved_body_system = reasoning_override_category
        resolved_snomed_codes: List[str] = []
        if use_gemini_features:
            if ai_result.get("snomed_codes"):
                resolved_snomed_codes = [str(code) for code in (ai_result.get("snomed_codes") or [])]
            elif ai_result.get("snomed_code"):
                resolved_snomed_codes = [str(ai_result.get("snomed_code"))]

        esi_started = time.perf_counter()
        esi_v5_result = _run_esi_v5_for_patient(
            patient,
            body_system=resolved_body_system,
            news2_score=det_result.news2_score,
            news2_level=det_result.news2_level,
            severity=resolved_severity,
            onset=resolved_onset,
            red_flags=resolved_red_flags,
            snomed_codes=resolved_snomed_codes,
            ai_confidence=ai_confidence_value,
            is_offline=False,
        )
        print(
            f"[Timing] ESI v5 online calculation: {(time.perf_counter() - esi_started):.3f}s",
            flush=True,
        )
        level = int(esi_v5_result.final_esi)
        resource_floor = int(getattr(esi_v5_result, "resources_estimated", 0) or 0)
        vitals_for_resource_logic = patient.vitals.model_dump() if patient.vitals else {}
        news2_for_cap = _safe_float(getattr(det_result, "news2_score", None))
        low_acuity_guard_for_cap = bool(
            level >= 4
            and resource_floor <= 1
            and news2_for_cap is not None
            and news2_for_cap < 5
            and not objective_red_flag_present
            and _vitals_for_low_acuity_are_normal(vitals_for_resource_logic)
            and ai_confidence_value >= 0.70
        )
        resource_count, expected_resources = _resolve_resource_count(
            ai_result,
            complaint_text=patient.chief_complaint_text,
            normalized_category=resolved_body_system,
            minimum_resource_count=resource_floor,
            maximum_resource_count=1 if low_acuity_guard_for_cap else None,
        )
        ai_result["resource_count"] = resource_count
        ai_result["expected_resources"] = expected_resources
        level = _apply_resource_count_esi_logic(
            level,
            resource_count,
            news2_score=getattr(det_result, "news2_score", None),
            has_red_flags=objective_red_flag_present,
            vitals_normal_for_low_acuity=_vitals_for_low_acuity_are_normal(vitals_for_resource_logic),
            ai_confidence=ai_confidence_value,
        )
        esi_baseline = int(level)
        floors_applied = _extract_esi_v5_floor_names(esi_v5_result)
        patient_data = patient.model_dump()
        patient_data["chief_complaint"] = patient.chief_complaint_text
        patient_data["extracted_symptoms"] = ai_result.get("extracted_symptoms") or []
        silent_mi = check_silent_mi_pattern(patient_data)
        silent_mi_forced_upgrade = False
        silent_mi_floor = _should_apply_silent_mi_floor(patient_data, silent_mi)
        if silent_mi_floor:
            floors_applied.append("silent_mi")
        if silent_mi_floor and level > 2:
            level = 2
            silent_mi_forced_upgrade = True
            print("⚠️ SILENT MI SAFETY FLOOR APPLIED: upgraded to ESI 2", flush=True)
        reasoning_floor_note = None
        safe_stable_context = _safe_stable_reasoning_context(
            level=level,
            objective_red_flag_present=objective_red_flag_present,
            news2_value=news2_for_cap,
            vitals=vitals_for_resource_logic,
            reasoning_stroke_signal=reasoning_stroke_signal,
        )
        if reasoning_floor_esi and level > int(reasoning_floor_esi) and not safe_stable_context:
            level = int(reasoning_floor_esi)
            reasoning_floor_note = (
                "AI reasoning flagged critical risk with objective instability -> conservative ESI 2 override"
            )
            floors_applied.append("ai_reasoning_critical_risk")
            print("⚠️ REASONING SAFETY FLOOR APPLIED: upgraded to ESI 2", flush=True)
        level, critical_floor_reasoning, critical_floor_notes, critical_floor_names = _enforce_critical_safety_floors(
            level,
            critical_safety_rules,
        )
        floors_applied.extend(critical_floor_names)
        floors_applied = _dedupe_floor_names(floors_applied)
        if critical_floor_notes:
            print("⚠️ CRITICAL KEYWORD SAFETY FLOOR APPLIED", flush=True)
        localized_resources = get_resources_for_category(det_result.category)
        ai_workup_resources = get_resources_for_workup(ai_result.get("recommended_workup") or [])
        # Prefer keyword-localized workup if available to avoid category misclassification noise.
        merged_resources = (
            ai_workup_resources[:] if (use_gemini_features and ai_workup_resources) else localized_resources[:]
        )

        vitals_dict = patient.vitals.model_dump() if patient.vitals else {}
        red_flag_summary = _build_red_flag_summary(
            vitals_dict,
            det_result.news2_score,
            complaint_text=patient.chief_complaint_text,
        )
        if silent_mi_floor:
            red_flag_summary.append(
                "Diabetic + atypical GI symptoms + fatigue → Silent MI risk | مريض سكري مع أعراض معدية غير نمطية + تعب → خطر جلطة صامتة"
            )
        if reasoning_floor_note:
            red_flag_summary.append(
                "AI reasoning indicates critical pattern with objective instability -> escalated to ESI 2 | "
                "استدلال الذكاء الاصطناعي كشف نمطًا حرجًا مع عدم استقرار موضوعي -> التصعيد إلى ESI 2"
            )
        if critical_floor_notes:
            red_flag_summary.extend(critical_floor_notes)
        colors = {1:"#ef4444", 2:"#f97316", 3:"#eab308", 4:"#22c55e", 5:"#3b82f6"}
        labels_en = {1:"Resuscitation", 2:"Emergent", 3:"Urgent", 4:"Less Urgent", 5:"Non-Urgent"}
        labels_ar = {1:"إنعاش", 2:"طوارئ", 3:"عاجل", 4:"أقل إلحاحاً", 5:"غير عاجل"}
        
        # ESI v4 time to physician guidelines
        times_en = {1:"Immediate", 2:"< 15 minutes", 3:"< 30 minutes", 4:"< 60 minutes", 5:"< 120 minutes"}
        times_ar = {1:"فوري", 2:"< 15 دقيقة", 3:"< 30 دقيقة", 4:"< 60 دقيقة", 5:"< 120 دقيقة"}
        action_category = reasoning_override_category or resolved_body_system or det_result.category
        if (action_category or "").strip().lower() in {"", "unclear", "unclear_needs_evaluation", "general", "other"}:
            action_category = det_result.category or action_category
        selected_action = _action_text_for_level_and_category(
            level,
            action_category,
            complaint_text=patient.chief_complaint_text,
            extracted_symptoms=ai_result.get("extracted_symptoms"),
        )

        # Add ICD-10 coding for GAHAR compliance
        response_dict = {
            "level": level,
            "category": action_category or det_result.category,
            "chief_complaint": patient.chief_complaint_text
        }
        enriched = enrich_triage_with_icd10(response_dict)
        icd10_coding = enriched.get("icd10_coding", {})
        ai_icd10 = ai_result.get("icd10_coding") or {}
        if ai_icd10.get("primary_code"):
            icd10_coding = {
                **icd10_coding,
                "primary_code": ai_icd10.get("primary_code"),
                "description_en": ai_icd10.get("description_en", icd10_coding.get("description_en")),
                "gahar_compliant": True
            }
        category_for_icd = (action_category or resolved_body_system or det_result.category or "").strip().lower()
        primary_code = (icd10_coding.get("primary_code") or "").strip().upper()
        if primary_code in {"", "R69"}:
            category_icd_fallback = {
                "chest_pain_cardiac": ("I20.9", "Angina pectoris, unspecified"),
                "stroke_symptoms": ("I63.9", "Cerebral infarction, unspecified"),
                "respiratory_distress": ("R06.0", "Dyspnea"),
            }
            if category_for_icd in category_icd_fallback:
                code, desc = category_icd_fallback[category_for_icd]
                icd10_coding = {
                    **icd10_coding,
                    "primary_code": code,
                    "description_en": desc,
                    "gahar_compliant": True,
                }
        if reasoning_stroke_signal and (
            not icd10_coding.get("primary_code")
            or str(icd10_coding.get("primary_code", "")).upper() == "R69"
        ):
            icd10_coding = {
                **icd10_coding,
                "primary_code": "I63.9",
                "description_en": "Cerebral infarction, unspecified",
                "gahar_compliant": True,
            }
        if silent_mi["pattern_detected"] and (
            not icd10_coding.get("primary_code")
            or str(icd10_coding.get("primary_code", "")).upper() == "R69"
        ):
            icd10_coding = {
                **icd10_coding,
                "primary_code": silent_mi.get("icd10_code") or "R07.89",
                "description_en": "Other chest pain (silent MI risk)",
                "gahar_compliant": True,
            }

        if use_gemini_features:
            response_red_flags = _sanitize_ai_red_flags(
                ai_result.get("red_flags"),
                complaint_text=patient.chief_complaint_text,
                normalized_category=action_category or resolved_body_system,
            )
        else:
            response_red_flags = list(getattr(det_result, "alerts_en", []) or []) + list(
                getattr(det_result, "alerts_ar", []) or []
            )
        response_red_flags.extend(reasoning_red_flags)
        response_red_flags.extend(critical_safety_flags)
        stroke_fast_detected = bool(
            reasoning_stroke_signal
            or _has_stroke_fast_signal(patient.chief_complaint_text)
            or "stroke" in (action_category or "").strip().lower()
        )
        if stroke_fast_detected:
            response_red_flags.append("stroke_fast_positive")
            ai_result["red_flag"] = True
            risk_factors = ai_result.get("risk_factors") or []
            if "stroke_fast_positive" not in risk_factors:
                risk_factors.append("stroke_fast_positive")
            ai_result["risk_factors"] = risk_factors
        if silent_mi["pattern_detected"]:
            response_red_flags.append("silent_mi_risk")
            ai_result["red_flag"] = True
            ai_result["esi_default"] = min(int(ai_result.get("esi_default", 3) or 3), 2)
            risk_factors = ai_result.get("risk_factors") or []
            if "silent_mi_risk" not in risk_factors:
                risk_factors.append("silent_mi_risk")
            ai_result["risk_factors"] = risk_factors
        response_red_flags = list(dict.fromkeys(flag for flag in response_red_flags if flag))

        alerts_sent = None
        if level <= 2:
            alert_payload = {
                "alert_level": AlertLevel.CODE_RED if level == 1 else AlertLevel.HIGH_ALERT,
                "patient_id": patient.patient_id,
                "esi_level": level,
                "news2_score": det_result.news2_score,
                "complaint": patient.chief_complaint_text,
                "icd10_code": icd10_coding.get("primary_code", ""),
                "icd10_description": icd10_coding.get("description_en", ""),
                "snomed_code": ai_result.get("snomed_code", "") if use_gemini_features else "",
                "snomed_term": ai_result.get("snomed_term", "") if use_gemini_features else "",
                "recommended": ai_result.get("recommended_workup") or [],
                "clinician": "Unassigned | غير محدد",
                "timestamp": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
            }
            alerts_sent = send_alert_sync(alert_payload)

        # Audit logging for GAHAR compliance
        audit_service.log_triage(
            patient_id=patient.patient_id,
            age=patient.age,
            gender=patient.gender,
            chief_complaint=patient.chief_complaint_text,
            vitals=patient.vitals.model_dump() if patient.vitals else {},
            news2_score=det_result.news2_score,
            news2_breakdown=getattr(det_result, "news2_breakdown", {}),
            recommended_esi=level,
            final_esi=level,
            esi_baseline=esi_baseline,
            esi_safe=level,
            safety_floors_applied=floors_applied,
            safety_floor_count=len(floors_applied),
            extracted_features=ai_result.get("extracted_symptoms"),
            icd10_codes=[icd10_coding.get("primary_code")] if icd10_coding else [],
            ai_confidence=ai_result.get("confidence_score", ai_result.get("confidence")),
            rag_sources=ai_result.get("rag_sources"),
            session_mode="ai" if use_ai_override else ("ai_partial" if use_gemini_partial else "ai_low_confidence_deterministic")
        )

        # QA Agent review
        try:
            final_esi = level
            qa_review = qa_agent.review_triage(
                triage_result={
                    "esi_level": final_esi,
                    "news2_score": det_result.news2_score,
                },
                patient={
                    "age": patient.age,
                    "gender": patient.gender,
                    "comorbidities": patient.comorbidities or [],
                    "chief_complaint": patient.chief_complaint_text,
                },
            )
            if qa_review["flagged"]:
                print(f"⚠️ QA FLAG: {qa_review['reason']} - Recommend ESI {qa_review['recommended_esi']}")
        except Exception as e:
            print(f"QA Agent error (non-blocking): {e}")

        response_payload = {
            "level": level,
            "extraction_method": (
                "gemini_online"
                if use_ai_override
                else ("gemini_partial" if use_gemini_partial else getattr(det_result, "extraction_method", "keyword_offline"))
            ),
            "color_code": colors.get(level, "#eab308"),
            "label_en": f"{labels_en.get(level)} (Level {level})",
            "label_ar": f"{labels_ar.get(level)} (مستوى {level})",
            "description": f"{selected_action['ar']} / {selected_action['en']}",
            "description_ar": selected_action["ar"],
            "description_en": selected_action["en"],
            "recommended_action": f"{selected_action['ar']} / {selected_action['en']}",
            "action_ar": selected_action["ar"],
            "action_en": selected_action["en"],
            "time_to_physician": f"{times_ar.get(level)} / {times_en.get(level)}",
            "time_ar": times_ar.get(level),
            "time_en": times_en.get(level),
            "red_flags": sorted(set(response_red_flags)),
            "red_flag_summary": red_flag_summary,
            "reasoning": (esi_v5_result.reasoning or [])
            + ([ai_result.get("reasoning")] if ai_result.get("reasoning") else [])
            + [f"Resource-aware ESI assignment: {resource_count} expected ED resources"]
            + (["Silent MI safety floor applied to prevent under-triage"] if silent_mi_forced_upgrade else [])
            + ([reasoning_floor_note] if reasoning_floor_note else [])
            + critical_floor_reasoning,
            "reasoning_ar": (
                [ai_result.get("reasoning_ar")] if ai_result.get("reasoning_ar") else []
            ) + [f"تقدير الموارد المتوقعة للحالة: {resource_count}"] + (["تم تطبيق قاعدة أمان الجلطة الصامتة لمنع تقليل شدة الفرز"] if silent_mi_forced_upgrade else [])
            + (
                ["تم تطبيق تصعيد احتياطي بسبب نمط حرج في الاستدلال الطبي"]
                if reasoning_floor_note
                else []
            )
            + (
                ["تم تطبيق قواعد أمان حرجة مبنية على الشكوى قبل تحليل الذكاء الاصطناعي"]
                if critical_floor_notes
                else []
            ),
            "reasoning_en": (esi_v5_result.reasoning or [])
            + ([ai_result.get("reasoning")] if ai_result.get("reasoning") else [])
            + [f"Resource-aware ESI assignment: {resource_count} expected ED resources"]
            + (["Silent MI safety floor applied to prevent under-triage"] if silent_mi_forced_upgrade else [])
            + ([reasoning_floor_note] if reasoning_floor_note else [])
            + critical_floor_reasoning,
            "ai_data": ai_result,
            "confidence": (
                "AI-Generated"
                if use_ai_override
                else ("AI-extracted (Gemini partial) + deterministic ESI rules" if use_gemini_partial else "Hybrid (AI low confidence -> deterministic category)")
            ),
            "fallback_reason": ai_result.get("fallback_reason"),
            "icd10_coding": icd10_coding,
            "icd10_code": icd10_coding.get("primary_code", ""),
            "icd10_description": icd10_coding.get("description_en", ""),
            "snomed_code": ai_result.get("snomed_code", "") if use_gemini_features else "",
            "snomed_term": ai_result.get("snomed_term", "") if use_gemini_features else "",
            "resource_plan": merged_resources,
            "silent_mi_alert": silent_mi if silent_mi["pattern_detected"] else None,
            "alerts_sent": alerts_sent,
            "requires_review": bool(det_result.requires_review or esi_v5_result.requires_review or requires_explicit_confirmation),
            "review_message": det_result.review_message or ("Manual review recommended by ESI v5 confidence/safety gate" if esi_v5_result.requires_review else ""),
            "requires_confirmation": requires_explicit_confirmation,
            "stage_reached": esi_v5_result.stage_reached,
            "resources_estimated": resource_count,
            "confidence_action": esi_v5_result.confidence_action,
            "news2_override": esi_v5_result.news2_override,
            "safety_floors": (esi_v5_result.safety_floors_applied or [])
            + ([reasoning_floor_note] if reasoning_floor_note else [])
            + critical_floor_notes,
            "context_rules_triggered": getattr(esi_v5_result, "context_rules_triggered", []),
            "confidence_flag": "medium" if low_confidence else ("unclear_presentation" if unclear_category else None),
            "low_confidence_warning": (
                f"Uncertain classification (confidence: {ai_confidence:.2%}) - deterministic triage retained pending review"
                if low_confidence else None
            ),
            "insufficient_info_warning": insufficient_info_warning,
            "gahar_notice": GAHAR_NOTICE
        }
        print(
            f"[Timing] AI-TRIAGE total endpoint time: {(time.perf_counter() - endpoint_started):.3f}s",
            flush=True,
        )
        return _attach_floor_observation(
            response_payload,
            esi_baseline=esi_baseline,
            esi_safe=level,
            floors_applied=floors_applied,
        )
    except HTTPException:
        raise
    except Exception as e:
        print(f"[ERROR] Internal server error: {e}", flush=True)
        raise HTTPException(status_code=500, detail="An internal error occurred. Contact support.")


@app.post("/triage-pure-ai")
def triage_pure_ai(patient: PatientInput):
    """Pure AI mode: no deterministic triage rules or NEWS2-based ESI overrides."""
    try:
        _validate_patient_id_or_raise(patient.patient_id)
        _normalize_patient_vitals_for_triage(patient)
        complaint_text = (patient.chief_complaint_text or "").strip()
        if not complaint_text:
            raise HTTPException(
                status_code=400,
                detail="Chief complaint cannot be empty | لا يمكن أن تكون الشكوى فارغة",
            )

        gender_check = validate_gender_complaint(patient.gender, complaint_text)
        if not gender_check["valid"]:
            raise HTTPException(status_code=400, detail=gender_check)

        ai_result = ai_service.analyze_triage(patient.model_dump())
        if not ai_result or ai_result.get("fallback") or "error" in ai_result:
            raise HTTPException(
                status_code=503,
                detail="Pure AI triage unavailable (model response failed).",
            )

        suggested_esi = ai_result.get("suggested_esi", ai_result.get("esi_default", 3))
        try:
            esi_level = int(suggested_esi)
        except Exception:
            esi_level = 3
        esi_level = max(1, min(5, esi_level))

        red_flags = list(ai_result.get("red_flags", []))
        if ai_result.get("red_flag") and "ai_red_flag" not in red_flags:
            red_flags.append("ai_red_flag")
        pure_ai_reasoning_safety = _derive_reasoning_safety(ai_result, complaint_text)
        insufficient_info_warning = _check_complaint_sufficiency(
            complaint_text,
            ai_result,
            fallback_category=ai_result.get("category", ""),
            reasoning_safety=pure_ai_reasoning_safety,
        )

        icd10_coding = ai_result.get("icd10_coding") or {}
        if not icd10_coding:
            fallback_dict = {
                "level": esi_level,
                "category": ai_result.get("category", "unclear_needs_evaluation"),
                "chief_complaint": patient.chief_complaint_text,
            }
            icd10_coding = enrich_triage_with_icd10(fallback_dict).get("icd10_coding", {})

        # Keep audit trail for ablation runs.
        try:
            audit_service.log_triage(
                patient_id=patient.patient_id,
                age=patient.age,
                gender=patient.gender,
                chief_complaint=patient.chief_complaint_text,
                vitals=patient.vitals.model_dump() if patient.vitals else {},
                news2_score=0,
                news2_breakdown={},
                recommended_esi=esi_level,
                final_esi=esi_level,
                esi_baseline=esi_level,
                esi_safe=esi_level,
                safety_floors_applied=[],
                safety_floor_count=0,
                extracted_features=ai_result.get("extracted_symptoms"),
                icd10_codes=[icd10_coding.get("primary_code")] if icd10_coding else [],
                ai_confidence=ai_result.get("confidence_score", ai_result.get("confidence")),
                rag_sources=ai_result.get("rag_sources"),
                session_mode="pure_ai",
            )
        except Exception as audit_exc:
            print(f"Audit logging error in pure AI mode (non-blocking): {audit_exc}", flush=True)

        response_payload = {
            "level": esi_level,
            "mode": "pure_ai",
            "extraction_method": "gemini_online",
            "confidence": ai_result.get("confidence_score", ai_result.get("confidence")),
            "reasoning": [ai_result.get("reasoning") or "Pure AI suggestion (no deterministic rules applied)"],
            "reasoning_ar": [ai_result.get("reasoning_ar")] if ai_result.get("reasoning_ar") else [],
            "red_flags": sorted(set(red_flags)),
            "ai_data": ai_result,
            "icd10_coding": icd10_coding,
            "icd10_code": icd10_coding.get("primary_code", ""),
            "icd10_description": icd10_coding.get("description_en", ""),
            "snomed_code": ai_result.get("snomed_code", ""),
            "snomed_term": ai_result.get("snomed_term", ""),
            "insufficient_info_warning": insufficient_info_warning,
            "gahar_notice": GAHAR_NOTICE,
        }
        return _attach_floor_observation(
            response_payload,
            esi_baseline=esi_level,
            esi_safe=esi_level,
            floors_applied=[],
        )
    except HTTPException:
        raise
    except Exception as e:
        print(f"[ERROR] Internal server error: {e}", flush=True)
        raise HTTPException(status_code=500, detail="An internal error occurred. Contact support.")


@app.get("/patients")
def get_patients(skip: int = 0, limit: int = 50, db: Session = Depends(get_db)):
    patients = db.query(Patient).order_by(Patient.created_at.desc()).offset(skip).limit(limit).all()
    return patients

@app.get("/patients/{patient_id}")
def get_patient(patient_id: int, db: Session = Depends(get_db)):
    patient = db.query(Patient).filter(Patient.id == patient_id).first()
    if not patient:
         raise HTTPException(status_code=404, detail="Patient not found")
    return patient

if __name__ == "__main__":
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)

@app.get("/stats/realtime", tags=["Statistics"])
def get_realtime_stats():
    """
    Current-shift statistics (last 8 hours).
    HIPAA-compliant aggregates only (no PHI).
    """
    return get_realtime_shift_stats(hours=8)


@app.get("/stats/{period}", tags=["Statistics"])
def get_stats_by_period(period: str):
    """
    Period-based statistics endpoint.
    Valid periods: today, week, month.
    """
    normalized = (period or "").strip().lower()
    if normalized not in {"today", "week", "month"}:
        raise HTTPException(status_code=400, detail="Period must be: today, week, month")
    return get_periodic_stats(normalized)


@app.get("/stats")
def get_triage_stats(days: int = 1):
    """Get triage statistics for dashboard. GAHAR compliance monitoring."""
    return audit_service.get_stats(days=days)

@app.get("/health")
def health_check():
    """System health check for monitoring and thesis demo."""
    status = {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "components": {}
    }
    
    # Check AI Service
    ai_service_ref = None
    try:
        from ai_service import ai_service
        ai_service_ref = ai_service
        status["components"]["ai"] = {
            "status": "ok" if ai_service.client else "degraded",
            "mode": getattr(ai_service, 'mode', 'unknown'),
            "model": getattr(ai_service, 'model_name', 'unknown')
        }
    except Exception as e:
        status["components"]["ai"] = {"status": "error", "error": str(e)}
    
    # Check RAG
    try:
        rag_ok = ai_service_ref is not None and getattr(ai_service_ref, "umls_rag", None) is not None
        status["components"]["rag"] = {"status": "ok" if rag_ok else "degraded"}
    except Exception as e:
        status["components"]["rag"] = {"status": "error", "error": str(e)}
    
    # Check QA Agent
    try:
        from qa_agent import qa_agent
        status["components"]["qa_agent"] = {"status": "ok"}
    except Exception as e:
        status["components"]["qa_agent"] = {"status": "error", "error": str(e)}
    
    # Check BigQuery
    try:
        from audit_service import audit_service
        status["components"]["bigquery"] = {
            "status": "ok" if audit_service.client else "degraded"
        }
    except Exception as e:
        status["components"]["bigquery"] = {"status": "error", "error": str(e)}

    # Flush alert queue (offline fallback)
    try:
        flush_result = flush_alert_queue_sync()
        notif_config = get_notification_config_status()
        status["components"]["alerts"] = {
            "status": "ok" if notif_config["fully_operational"] else "degraded",
            "queue_size": get_queue_size(),
            "flush_result": flush_result,
            "email_configured": notif_config["fully_operational"],
            "missing_vars": notif_config["missing_vars"],
        }
    except Exception as e:
        status["components"]["alerts"] = {"status": "error", "error": str(e)}
    
    # Overall status
    all_ok = all(c.get("status") == "ok" for c in status["components"].values())
    status["status"] = "healthy" if all_ok else "degraded"
    
    status["gahar_notice"] = GAHAR_NOTICE
    return status


@app.get("/notification-config-status")
def notification_config_status(user: Dict[str, Any] = Depends(require_supervisor_role)):
    """Check email/push notification configuration (supervisors only)."""
    config = get_notification_config_status()
    config["gahar_notice"] = GAHAR_NOTICE
    if not config["fully_operational"]:
        config["fix_instructions"] = (
            "Set the following environment variables in Cloud Run: "
            + ", ".join(config["missing_vars"])
            + ". Use: gcloud run services update safe-triage-api "
            "--set-env-vars SENDGRID_API_KEY=<key>,ALERT_EMAIL_TO=<email>,ALERT_EMAIL_FROM=<email> "
            "--region me-west1"
        )
    return config


@app.post("/medgemma/hourly-review", tags=["MedGemma QA"])
async def trigger_medgemma_hourly():
    """Manually trigger hourly MedGemma batch QA (Cloud Scheduler target)."""
    try:
        result = await run_hourly_job()
        result["gahar_notice"] = GAHAR_NOTICE
        return result
    except Exception as exc:
        return {
            "status": "error",
            "error": str(exc),
            "gahar_notice": GAHAR_NOTICE,
        }


@app.post("/medgemma/review-now")
async def medgemma_review_now():
    """Backward-compatible alias for immediate manual MedGemma review."""
    return await trigger_medgemma_hourly()


@app.get("/medgemma/status", tags=["MedGemma QA"])
def medgemma_status():
    """Health check for MedGemma service."""
    try:
        from medgemma_client import MedGemmaClient

        client = MedGemmaClient()
        healthy = client.test_connection()
        return {
            "service": "MedGemma QA",
            "model": client.model,
            "provider": "Dr7.ai",
            "status": "operational" if healthy else "degraded",
            "api_accessible": healthy,
            "error_detail": None if healthy else client.last_error,
            "gahar_notice": GAHAR_NOTICE,
        }
    except Exception as exc:
        return {
            "service": "MedGemma QA",
            "provider": "Dr7.ai",
            "status": "error",
            "api_accessible": False,
            "error": str(exc),
            "gahar_notice": GAHAR_NOTICE,
        }


@app.get("/reports/daily-summary")
def daily_summary_report(
    date: str = None,
    department: str = "Emergency Department",
    user: dict = Depends(require_firebase_user),
):
    """Generate daily PDF report with ICD-10 codes."""
    try:
        report_date = datetime.utcnow().date()
        if date:
            report_date = datetime.strptime(date, "%Y-%m-%d").date()

        audit_service.log_report_download(
            report_date=report_date,
            department=department,
            user_id=user.get("uid"),
            user_email=user.get("email"),
            user_name=user.get("name") or user.get("email") or user.get("uid"),
        )

        pdf_bytes = generate_daily_report(report_date, department)
        filename = f"SAFE_Triage_Daily_Report_{report_date.isoformat()}.pdf"
        return StreamingResponse(
            io.BytesIO(pdf_bytes),
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename={filename}"},
        )
    except Exception as e:
        print(f"[ERROR] Internal server error: {e}", flush=True)
        raise HTTPException(status_code=500, detail="An internal error occurred. Contact support.")


@app.post("/export-triage")
def export_personal_triage_csv(user: dict = Depends(require_firebase_user)):
    """Export this clinician's triage cases only, with Safe Harbor de-identification."""
    clinician_id = _resolve_clinician_id(user)
    if not clinician_id:
        raise HTTPException(status_code=401, detail="Unable to resolve clinician identity")

    clinician_variants = _resolve_clinician_id_variants(user)
    csv_text, filename, case_count = export_triage_csv_with_metadata(clinician_id, clinician_variants=clinician_variants)
    audit_service.log_export_download(
        export_type="personal_csv",
        scope=PERSONAL_EXPORT_SCOPE,
        user_id=clinician_id,
        user_email=user.get("email"),
        user_name=user.get("name") or user.get("email") or clinician_id,
        case_count=case_count,
    )

    return StreamingResponse(
        io.BytesIO(csv_text.encode("utf-8-sig")),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@app.post("/export-system-wide")
def export_system_wide(
    date_range: Optional[ExportDateRange] = Body(default=None),
    user: Dict[str, Any] = Depends(require_supervisor_role),
):
    """System-wide export (supervisors only)."""
    start_at = date_range.start if date_range else None
    end_at = date_range.end if date_range else None
    if start_at and end_at and start_at > end_at:
        raise HTTPException(status_code=400, detail="Invalid date range: start must be before end")

    requested_by = _resolve_clinician_id(user) or "supervisor"
    csv_text, filename, case_count = export_system_wide_csv(
        requested_by=requested_by,
        start_at=start_at,
        end_at=end_at,
    )

    audit_service.log_export_download(
        export_type="system_wide_csv",
        scope=SYSTEM_EXPORT_SCOPE,
        user_id=requested_by,
        user_email=user.get("email"),
        user_name=user.get("email") or requested_by,
        case_count=case_count,
        start_at=start_at,
        end_at=end_at,
    )

    return StreamingResponse(
        io.BytesIO(csv_text.encode("utf-8-sig")),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )
