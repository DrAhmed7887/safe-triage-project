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
    
    # Demographics - Age validated: 0-120 years (oldest verified human was 122)
    age: float = Field(..., description="Age in years (use decimals for months, e.g. 0.25 = 3mo)", ge=0, le=120)
    gender: Gender = Field(..., description="Patient gender")
    
    # Clinical Info
    chief_complaint_text: str = Field(..., description="Free text complaint (Arabic or English)")
    vitals: Vitals
    
    # Red Flags / History
    history_cardiac: bool = False
    history_stroke: bool = False
    immuno_compromised: bool = False
    
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
