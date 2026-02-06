from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Literal, Any
from datetime import datetime
from enum import Enum

class Gender(str, Enum):
    MALE = "male"
    FEMALE = "female"

class PainScale(int, Enum):
    NONE = 0
    MILD = 1
    MODERATE_LOW = 4
    MODERATE_HIGH = 6
    SEVERE = 8
    WORST = 10

class TriageLevel(int, Enum):
    RESUSCITATION = 1
    EMERGENT = 2
    URGENT = 3
    LESS_URGENT = 4
    NON_URGENT = 5

class Vitals(BaseModel):
    hr: Optional[int] = Field(None, description="Heart Rate (bpm)")
    rr: Optional[int] = Field(None, description="Respiratory Rate (breaths/min)")
    spo2: Optional[float] = Field(None, description="Oxygen Saturation (%)")
    temp: Optional[float] = Field(None, description="Temperature (C)")
    sbp: Optional[int] = Field(None, description="Systolic Blood Pressure (mmHg)")
    dbp: Optional[int] = Field(None, description="Diastolic Blood Pressure (mmHg)")
    pain_score: Optional[int] = Field(0, description="Pain Scale 0-10", ge=0, le=10)
    gcs: Optional[int] = Field(None, description="Glasgow Coma Scale (3-15)", ge=3, le=15)

class PatientInput(BaseModel):
    # Patient Identification
    patient_id: Optional[str] = Field(None, description="Hospital Patient ID / MRN (Medical Record Number)")
    patient_name: Optional[str] = Field(None, description="Patient full name")
    
    # Demographics - Frontend validates unusual ages, backend allows for confirmed entries
    age: float = Field(..., description="Age in years (use decimals for months, e.g. 0.25 = 3mo)", ge=0)
    gender: Gender = Field(..., description="Patient gender")
    
    # Clinical Info
    chief_complaint_text: str = Field(..., description="Free text complaint (Arabic or English)")
    vitals: Vitals
    
    # Red Flags / History
    history_cardiac: bool = False
    history_stroke: bool = False
    immuno_compromised: bool = False
    comorbidities: Optional[List[str]] = Field(
        default=None,
        description="List of comorbid conditions (e.g., diabetes, CKD)",
    )

    # ========== ESI v5 COMPLIANCE FIELDS ==========
    # === ESI v5 PAIN ASSESSMENT ===
    pain_scale: Optional[int] = Field(
        default=None,
        ge=0,
        le=10,
        description="Pain severity 0-10",
    )
    pain_context: Optional[
        Literal[
            "systemic",
            "chest_pain",
            "abdominal_pain",
            "renal_colic",
            "sickle_cell_crisis",
            "cancer_pain",
            "orthopedic",
            "headache",
            "other",
        ]
    ] = Field(default=None, description="Clinical context of pain")

    # === ESI v5 IMMUNOCOMPROMISED STATUS ===
    is_immunocompromised: bool = Field(
        default=False, description="Patient has compromised immune system"
    )
    immunocompromised_reason: Optional[
        Literal[
            "chemotherapy",
            "transplant",
            "hiv_aids",
            "chronic_steroids",
            "biologics",
            "congenital",
            "other",
        ]
    ] = Field(default=None, description="Reason for immunocompromised state")

    # === ESI v5 PEDIATRIC IMMUNIZATIONS ===
    immunizations_complete: Optional[bool] = Field(
        default=None, description="Are childhood immunizations up to date? None=unknown"
    )
    
    # ========== NEWS2 COMPLIANCE FIELDS (Audit Fix) ==========
    # Reference: Royal College of Physicians NEWS2, 2017
    
    # Supplemental Oxygen - NEWS2 adds +2 points if patient on O2
    on_supplemental_o2: bool = Field(False, description="Patient receiving supplemental oxygen (NEWS2: +2 points)")
    
    # COPD/Hypercapnic - Use SpO2 Scale 2 (target 88-92%)
    is_copd: bool = Field(False, description="COPD/Hypercapnic respiratory failure - use SpO2 Scale 2 (target 88-92%)")
    
    # Consciousness (ACVPU) - NEWS2 uses this instead of GCS
    consciousness: Literal["A", "C", "V", "P", "U"] = Field(
        "A",
        description="Consciousness level using ACVPU: A, C, V, P, U"
    )
    
    # ========== OBSTETRIC SAFETY FIELDS (Audit Fix) ==========
    # Reference: ESI v4 Handbook, Chapter 5 - Special Populations
    
    # Pregnancy status for ectopic/obstetric emergency detection
    is_pregnant: bool = Field(False, description="Patient is currently pregnant")
    gestational_weeks: Optional[int] = Field(
        default=None, ge=1, le=42, description="Weeks of gestation (1-42)"
    )
    pregnancy_complaint: Optional[
        Literal[
            "vaginal_bleeding",
            "abdominal_pain",
            "contractions",
            "decreased_fetal_movement",
            "leaking_fluid",
            "headache_visual_changes",
            "swelling",
            "none",
        ]
    ] = Field(default=None, description="Pregnancy-related complaint if any")
    
class TriageResult(BaseModel):
    level: TriageLevel
    color_code: str
    label_ar: str
    label_en: str
    description_ar: str = ""
    description_en: str = ""
    description: str = ""  # Legacy - combined
    action_ar: str = ""
    action_en: str = ""
    recommended_action: str = ""  # Legacy - combined
    time_ar: str = ""
    time_en: str = ""
    time_to_physician: str = ""  # Legacy - combined
    red_flags: List[str] = []
    red_flag_summary: List[str] = []
    reasoning_ar: List[str] = []
    reasoning_en: List[str] = []
    reasoning: List[str] = []  # Legacy - combined
    confidence: str = "High"  # High, Medium, Low
    rag_context: Optional[Dict[str, Any]] = None
    requires_review: bool = False
    review_message: str = ""
    
    # ICD-10 Coding for GAHAR Compliance (Egyptian hospitals)
    icd10_code: str = ""
    icd10_description: str = ""
    icd10_category: str = ""


class TriageConfirmationRequest(BaseModel):
    patient_id: str
    recommended_esi: int = Field(..., ge=1, le=5)
    confirmed_esi: int = Field(..., ge=1, le=5)
    clinician_id: str
    clinician_role: Literal["nurse", "physician", "supervisor", "other"] = "nurse"
    action: Literal["confirmed", "overridden"] = "confirmed"
    override_reason: Optional[str] = None
    supervisor_pin: Optional[str] = None
    timestamp: Optional[datetime] = None


class TriageConfirmationStart(BaseModel):
    patient_id: str
    recommended_esi: int = Field(..., ge=1, le=5)


class TriageConfirmationPending(BaseModel):
    patient_id: str
    recommended_esi: int = Field(..., ge=1, le=5)
    created_at: datetime
    expires_at: datetime
