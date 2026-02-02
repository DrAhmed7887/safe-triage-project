from pydantic import BaseModel, Field
from typing import Optional, List, Dict
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
    gcs: Optional[int] = Field(15, description="Glasgow Coma Scale", ge=3, le=15)
    pain_score: Optional[int] = Field(0, description="Pain Scale 0-10", ge=0, le=10)

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

    # ========== ESI v5 COMPLIANCE FIELDS ==========
    # ESI v5 Pain Assessment
    pain_scale: Optional[int] = Field(None, ge=0, le=10, description="Pain scale 0-10")
    pain_context: Optional[str] = Field(
        None,
        description="Pain context: renal_colic, cancer_pain, sickle_cell, orthopedic, etc.",
    )

    # ESI v5 Immunocompromised
    is_immunocompromised: bool = Field(
        False, description="Is patient immunocompromised?"
    )
    immunocompromised_reason: Optional[str] = Field(
        None, description="Reason: chemotherapy, transplant, HIV, steroids"
    )

    # ESI v5 Pediatric
    immunizations_complete: bool = Field(
        True, description="Are immunizations up to date? (pediatric)"
    )
    
    # ========== NEWS2 COMPLIANCE FIELDS (Audit Fix) ==========
    # Reference: Royal College of Physicians NEWS2, 2017
    
    # Supplemental Oxygen - NEWS2 adds +2 points if patient on O2
    on_supplemental_o2: bool = Field(False, description="Patient receiving supplemental oxygen (NEWS2: +2 points)")
    
    # COPD/Hypercapnic - Use SpO2 Scale 2 (target 88-92%)
    is_copd: bool = Field(False, description="COPD/Hypercapnic respiratory failure - use SpO2 Scale 2 (target 88-92%)")
    
    # New Confusion - NEWS2 ACVPU 'C' scores 3 points even with GCS 15
    is_new_confusion: bool = Field(False, description="New onset confusion (NEWS2 ACVPU 'C' = 3 points)")
    
    # ========== OBSTETRIC SAFETY FIELDS (Audit Fix) ==========
    # Reference: ESI v4 Handbook, Chapter 5 - Special Populations
    
    # Pregnancy status for ectopic/obstetric emergency detection
    is_pregnant: bool = Field(False, description="Patient is pregnant - enables obstetric emergency detection")
    
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
    reasoning_ar: List[str] = []
    reasoning_en: List[str] = []
    reasoning: List[str] = []  # Legacy - combined
    confidence: str = "High"  # High, Medium, Low
