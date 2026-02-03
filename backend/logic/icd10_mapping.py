"""
ICD-10-CM Mapping for SAFE-Triage System
=========================================
Maps chief complaint categories to ICD-10-CM codes (Chapter R: Symptoms & Signs)

Why ICD-10 instead of SNOMED-CT:
1. Used in Egyptian hospitals (GAHAR compliance)
2. WHO standard - available immediately
3. Arabic translations available from WHO
4. Practical for thesis timeline

Reference: ICD-10-CM 2024/2025 Chapter R (R00-R99)
"""

from typing import Dict, List, Optional
from dataclasses import dataclass
from enum import Enum


class TriageUrgency(Enum):
    """ESI-aligned urgency levels"""
    IMMEDIATE = 1      # Life-threatening
    EMERGENT = 2       # High risk
    URGENT = 3         # Needs attention
    LESS_URGENT = 4    # Can wait
    NON_URGENT = 5     # Minor


@dataclass
class ICD10Code:
    """ICD-10-CM code with clinical metadata for triage"""
    code: str
    description_en: str
    description_ar: str
    chapter: str
    base_urgency: TriageUrgency
    red_flags: List[str]
    requires_vitals_check: bool = True


# =============================================================================
# ICD-10 MAPPING FOR SAFE-TRIAGE COMPLAINT CATEGORIES
# =============================================================================

ICD10_TRIAGE_MAP: Dict[str, ICD10Code] = {
    
    # =========================================================================
    # CARDIOVASCULAR / CHEST (R00-R09)
    # =========================================================================
    
    "chest_pain_cardiac": ICD10Code(
        code="R07.9",
        description_en="Chest pain, unspecified",
        description_ar="ألم في الصدر، غير محدد",
        chapter="R00-R09",
        base_urgency=TriageUrgency.EMERGENT,
        red_flags=["radiating to arm/jaw", "diaphoresis", "shortness of breath", "nausea"],
        requires_vitals_check=True
    ),
    
    "chest_pain_non_cardiac": ICD10Code(
        code="R07.89",
        description_en="Other chest pain",
        description_ar="ألم صدري آخر",
        chapter="R00-R09",
        base_urgency=TriageUrgency.URGENT,
        red_flags=["pleuritic", "positional", "reproducible"],
        requires_vitals_check=True
    ),
    
    "palpitations": ICD10Code(
        code="R00.2",
        description_en="Palpitations",
        description_ar="خفقان القلب",
        chapter="R00-R09",
        base_urgency=TriageUrgency.URGENT,
        red_flags=["syncope", "chest pain", "shortness of breath"],
        requires_vitals_check=True
    ),
    
    "tachycardia": ICD10Code(
        code="R00.0",
        description_en="Tachycardia, unspecified",
        description_ar="تسرع القلب، غير محدد",
        chapter="R00-R09",
        base_urgency=TriageUrgency.EMERGENT,
        red_flags=["HR > 150", "hypotension", "altered consciousness"],
        requires_vitals_check=True
    ),
    
    "bradycardia": ICD10Code(
        code="R00.1",
        description_en="Bradycardia, unspecified",
        description_ar="بطء القلب، غير محدد",
        chapter="R00-R09",
        base_urgency=TriageUrgency.EMERGENT,
        red_flags=["HR < 50", "syncope", "hypotension"],
        requires_vitals_check=True
    ),
    
    # =========================================================================
    # RESPIRATORY (R04-R09)
    # =========================================================================
    
    "respiratory_distress": ICD10Code(
        code="R06.00",
        description_en="Dyspnea, unspecified",
        description_ar="ضيق التنفس، غير محدد",
        chapter="R00-R09",
        base_urgency=TriageUrgency.EMERGENT,
        red_flags=["SpO2 < 92%", "cyanosis", "accessory muscle use", "tripod position"],
        requires_vitals_check=True
    ),
    
    "shortness_of_breath": ICD10Code(
        code="R06.02",
        description_en="Shortness of breath",
        description_ar="قصر النفس",
        chapter="R00-R09",
        base_urgency=TriageUrgency.URGENT,
        red_flags=["at rest", "sudden onset", "with chest pain"],
        requires_vitals_check=True
    ),
    
    "wheezing": ICD10Code(
        code="R06.2",
        description_en="Wheezing",
        description_ar="أزيز / صفير في الصدر",
        chapter="R00-R09",
        base_urgency=TriageUrgency.URGENT,
        red_flags=["silent chest", "unable to speak", "cyanosis"],
        requires_vitals_check=True
    ),
    
    "cough": ICD10Code(
        code="R05.9",
        description_en="Cough, unspecified",
        description_ar="سعال، غير محدد",
        chapter="R00-R09",
        base_urgency=TriageUrgency.LESS_URGENT,
        red_flags=["hemoptysis", "fever", "weight loss"],
        requires_vitals_check=True
    ),
    
    "hemoptysis": ICD10Code(
        code="R04.2",
        description_en="Hemoptysis",
        description_ar="نفث الدم / سعال دموي",
        chapter="R00-R09",
        base_urgency=TriageUrgency.EMERGENT,
        red_flags=["massive (>100ml)", "respiratory distress", "hypotension"],
        requires_vitals_check=True
    ),
    
    # =========================================================================
    # GASTROINTESTINAL (R10-R19)
    # =========================================================================
    
    "abdominal_pain": ICD10Code(
        code="R10.9",
        description_en="Unspecified abdominal pain",
        description_ar="ألم بطني غير محدد",
        chapter="R10-R19",
        base_urgency=TriageUrgency.URGENT,
        red_flags=["sudden onset", "rigid abdomen", "rebound tenderness", "radiates to back"],
        requires_vitals_check=True
    ),
    
    "abdominal_pain_rlq": ICD10Code(
        code="R10.31",
        description_en="Right lower quadrant pain",
        description_ar="ألم في الربع السفلي الأيمن",
        chapter="R10-R19",
        base_urgency=TriageUrgency.URGENT,
        red_flags=["fever", "migration from umbilicus", "rebound tenderness"],
        requires_vitals_check=True
    ),
    
    "abdominal_pain_epigastric": ICD10Code(
        code="R10.13",
        description_en="Epigastric pain",
        description_ar="ألم شرسوفي / فم المعدة",
        chapter="R10-R19",
        base_urgency=TriageUrgency.URGENT,
        red_flags=["radiates to back", "diabetic patient", "diaphoresis"],
        requires_vitals_check=True
    ),
    
    "nausea_vomiting": ICD10Code(
        code="R11.2",
        description_en="Nausea with vomiting, unspecified",
        description_ar="غثيان مع قيء",
        chapter="R10-R19",
        base_urgency=TriageUrgency.LESS_URGENT,
        red_flags=["hematemesis", "projectile", "diabetic", "severe dehydration"],
        requires_vitals_check=True
    ),
    
    "hematemesis": ICD10Code(
        code="K92.0",
        description_en="Hematemesis",
        description_ar="قيء دموي",
        chapter="K00-K95",
        base_urgency=TriageUrgency.EMERGENT,
        red_flags=["hypotension", "tachycardia", "altered consciousness"],
        requires_vitals_check=True
    ),
    
    "diarrhea": ICD10Code(
        code="R19.7",
        description_en="Diarrhea, unspecified",
        description_ar="إسهال، غير محدد",
        chapter="R10-R19",
        base_urgency=TriageUrgency.LESS_URGENT,
        red_flags=["bloody", "severe dehydration", "elderly", "immunocompromised"],
        requires_vitals_check=True
    ),
    
    "constipation": ICD10Code(
        code="K59.00",
        description_en="Constipation, unspecified",
        description_ar="إمساك، غير محدد",
        chapter="K00-K95",
        base_urgency=TriageUrgency.NON_URGENT,
        red_flags=["absolute constipation", "abdominal distension", "vomiting"],
        requires_vitals_check=False
    ),
    
    "gi_bleeding": ICD10Code(
        code="K92.2",
        description_en="Gastrointestinal hemorrhage, unspecified",
        description_ar="نزيف معدي معوي",
        chapter="K00-K95",
        base_urgency=TriageUrgency.EMERGENT,
        red_flags=["hypotension", "tachycardia", "melena", "bright red blood"],
        requires_vitals_check=True
    ),
    
    # =========================================================================
    # NEUROLOGICAL (R20-R29, R40-R46)
    # =========================================================================
    
    "headache": ICD10Code(
        code="R51.9",
        description_en="Headache, unspecified",
        description_ar="صداع، غير محدد",
        chapter="R50-R69",
        base_urgency=TriageUrgency.URGENT,
        red_flags=["thunderclap", "worst ever", "fever", "neck stiffness", "focal neuro"],
        requires_vitals_check=True
    ),
    
    "headache_severe": ICD10Code(
        code="R51.0",
        description_en="Headache with orthostatic component",
        description_ar="صداع شديد",
        chapter="R50-R69",
        base_urgency=TriageUrgency.EMERGENT,
        red_flags=["sudden onset", "neurological deficit", "hypertensive"],
        requires_vitals_check=True
    ),
    
    "altered_consciousness": ICD10Code(
        code="R40.4",
        description_en="Transient alteration of awareness",
        description_ar="تغير في الوعي",
        chapter="R40-R46",
        base_urgency=TriageUrgency.EMERGENT,
        red_flags=["GCS < 14", "pupil changes", "focal deficit"],
        requires_vitals_check=True
    ),
    
    "syncope": ICD10Code(
        code="R55",
        description_en="Syncope and collapse",
        description_ar="إغماء وانهيار",
        chapter="R50-R69",
        base_urgency=TriageUrgency.EMERGENT,
        red_flags=["cardiac history", "exertional", "no prodrome", "injury"],
        requires_vitals_check=True
    ),
    
    "dizziness": ICD10Code(
        code="R42",
        description_en="Dizziness and giddiness",
        description_ar="دوخة ودوار",
        chapter="R40-R46",
        base_urgency=TriageUrgency.URGENT,
        red_flags=["vertigo with vomiting", "hearing loss", "focal neuro"],
        requires_vitals_check=True
    ),
    
    "seizure": ICD10Code(
        code="R56.9",
        description_en="Unspecified convulsions",
        description_ar="تشنجات غير محددة",
        chapter="R50-R69",
        base_urgency=TriageUrgency.EMERGENT,
        red_flags=["status epilepticus", "first seizure", "post-ictal > 30min", "fever"],
        requires_vitals_check=True
    ),
    
    "weakness_focal": ICD10Code(
        code="R29.818",
        description_en="Other symptoms and signs involving the nervous system",
        description_ar="ضعف بؤري / شلل جزئي",
        chapter="R20-R29",
        base_urgency=TriageUrgency.IMMEDIATE,
        red_flags=["acute onset", "facial droop", "speech difficulty", "FAST positive"],
        requires_vitals_check=True
    ),
    
    "stroke_symptoms": ICD10Code(
        code="R29.810",
        description_en="Facial weakness",
        description_ar="أعراض سكتة دماغية",
        chapter="R20-R29",
        base_urgency=TriageUrgency.IMMEDIATE,
        red_flags=["any FAST positive", "time of onset < 4.5 hours"],
        requires_vitals_check=True
    ),
    
    # =========================================================================
    # GENERAL SYMPTOMS (R50-R69)
    # =========================================================================
    
    "fever": ICD10Code(
        code="R50.9",
        description_en="Fever, unspecified",
        description_ar="حمى، غير محددة",
        chapter="R50-R69",
        base_urgency=TriageUrgency.URGENT,
        red_flags=["immunocompromised", "recent chemo", "petechial rash", "neck stiffness"],
        requires_vitals_check=True
    ),
    
    "weakness_generalized": ICD10Code(
        code="R53.1",
        description_en="Weakness",
        description_ar="ضعف عام",
        chapter="R50-R69",
        base_urgency=TriageUrgency.URGENT,
        red_flags=["acute onset", "diabetic", "elderly", "unable to stand"],
        requires_vitals_check=True
    ),
    
    "fatigue": ICD10Code(
        code="R53.83",
        description_en="Other fatigue",
        description_ar="إرهاق",
        chapter="R50-R69",
        base_urgency=TriageUrgency.LESS_URGENT,
        red_flags=["weight loss", "night sweats", "elderly with new onset"],
        requires_vitals_check=True
    ),
    
    "malaise": ICD10Code(
        code="R53.81",
        description_en="Other malaise",
        description_ar="توعك",
        chapter="R50-R69",
        base_urgency=TriageUrgency.LESS_URGENT,
        red_flags=["diabetic", "elderly", "immunocompromised"],
        requires_vitals_check=True
    ),
    
    # =========================================================================
    # PAIN SYNDROMES (R52, M-codes)
    # =========================================================================
    
    "pain_generalized": ICD10Code(
        code="R52",
        description_en="Pain, unspecified",
        description_ar="ألم، غير محدد",
        chapter="R50-R69",
        base_urgency=TriageUrgency.URGENT,
        red_flags=["severe (>7/10)", "acute onset", "with vital sign changes"],
        requires_vitals_check=True
    ),
    
    "back_pain": ICD10Code(
        code="M54.9",
        description_en="Dorsalgia, unspecified",
        description_ar="ألم الظهر",
        chapter="M00-M99",
        base_urgency=TriageUrgency.LESS_URGENT,
        red_flags=["sudden tearing", "pulsatile mass", "neuro deficit", "saddle anesthesia"],
        requires_vitals_check=True
    ),
    
    "flank_pain": ICD10Code(
        code="R10.9",
        description_en="Flank pain",
        description_ar="ألم في الخاصرة",
        chapter="R10-R19",
        base_urgency=TriageUrgency.URGENT,
        red_flags=["hematuria", "fever", "unable to find comfortable position"],
        requires_vitals_check=True
    ),
    
    # =========================================================================
    # GENITOURINARY (R30-R39)
    # =========================================================================
    
    "dysuria": ICD10Code(
        code="R30.0",
        description_en="Dysuria",
        description_ar="عسر التبول / حرقان البول",
        chapter="R30-R39",
        base_urgency=TriageUrgency.LESS_URGENT,
        red_flags=["fever", "flank pain", "elderly", "catheterized"],
        requires_vitals_check=True
    ),
    
    "hematuria": ICD10Code(
        code="R31.9",
        description_en="Hematuria, unspecified",
        description_ar="دم في البول",
        chapter="R30-R39",
        base_urgency=TriageUrgency.URGENT,
        red_flags=["gross hematuria", "clots", "urinary retention"],
        requires_vitals_check=True
    ),
    
    "urinary_retention": ICD10Code(
        code="R33.9",
        description_en="Retention of urine, unspecified",
        description_ar="احتباس البول",
        chapter="R30-R39",
        base_urgency=TriageUrgency.URGENT,
        red_flags=["complete retention", "renal failure", "overflow incontinence"],
        requires_vitals_check=True
    ),
    
    # =========================================================================
    # SKIN & SOFT TISSUE (R20-R23)
    # =========================================================================
    
    "rash": ICD10Code(
        code="R21",
        description_en="Rash and other nonspecific skin eruption",
        description_ar="طفح جلدي",
        chapter="R20-R23",
        base_urgency=TriageUrgency.LESS_URGENT,
        red_flags=["petechial", "fever", "mucosal involvement", "rapid spread"],
        requires_vitals_check=True
    ),
    
    "swelling": ICD10Code(
        code="R60.9",
        description_en="Edema, unspecified",
        description_ar="تورم",
        chapter="R50-R69",
        base_urgency=TriageUrgency.URGENT,
        red_flags=["facial/airway", "unilateral leg", "sudden onset"],
        requires_vitals_check=True
    ),
    
    # =========================================================================
    # ALLERGIC / ANAPHYLAXIS
    # =========================================================================
    
    "allergic_reaction": ICD10Code(
        code="T78.40XA",
        description_en="Allergy, unspecified, initial encounter",
        description_ar="تفاعل تحسسي",
        chapter="T66-T78",
        base_urgency=TriageUrgency.URGENT,
        red_flags=["airway swelling", "wheezing", "hypotension", "rapid progression"],
        requires_vitals_check=True
    ),
    
    "anaphylaxis": ICD10Code(
        code="T78.2XXA",
        description_en="Anaphylactic shock, unspecified, initial encounter",
        description_ar="صدمة تأقية",
        chapter="T66-T78",
        base_urgency=TriageUrgency.IMMEDIATE,
        red_flags=["any sign of anaphylaxis"],
        requires_vitals_check=True
    ),
    
    # =========================================================================
    # TRAUMA (S/T codes - simplified for triage)
    # =========================================================================
    
    "trauma_minor": ICD10Code(
        code="T14.90XA",
        description_en="Injury, unspecified, initial encounter",
        description_ar="إصابة طفيفة",
        chapter="S00-T88",
        base_urgency=TriageUrgency.LESS_URGENT,
        red_flags=["head injury", "anticoagulation", "elderly"],
        requires_vitals_check=True
    ),
    
    "trauma_major": ICD10Code(
        code="T07.XXXA",
        description_en="Unspecified multiple injuries",
        description_ar="إصابات متعددة",
        chapter="S00-T88",
        base_urgency=TriageUrgency.IMMEDIATE,
        red_flags=["any major trauma mechanism"],
        requires_vitals_check=True
    ),
    
    "fall": ICD10Code(
        code="W19.XXXA",
        description_en="Unspecified fall, initial encounter",
        description_ar="سقوط",
        chapter="V00-Y99",
        base_urgency=TriageUrgency.URGENT,
        red_flags=["head strike", "anticoagulation", "loss of consciousness", "elderly"],
        requires_vitals_check=True
    ),
    
    # =========================================================================
    # PSYCHIATRIC / BEHAVIORAL (R45-R46)
    # =========================================================================
    
    "anxiety": ICD10Code(
        code="R45.0",
        description_en="Nervousness",
        description_ar="قلق / توتر",
        chapter="R40-R46",
        base_urgency=TriageUrgency.LESS_URGENT,
        red_flags=["chest pain", "shortness of breath", "suicidal ideation"],
        requires_vitals_check=True
    ),
    
    "agitation": ICD10Code(
        code="R45.1",
        description_en="Restlessness and agitation",
        description_ar="هياج",
        chapter="R40-R46",
        base_urgency=TriageUrgency.URGENT,
        red_flags=["violent behavior", "altered consciousness", "hyperthermia"],
        requires_vitals_check=True
    ),
    
    "suicidal_ideation": ICD10Code(
        code="R45.851",
        description_en="Suicidal ideation",
        description_ar="أفكار انتحارية",
        chapter="R40-R46",
        base_urgency=TriageUrgency.EMERGENT,
        red_flags=["active plan", "means available", "recent attempt"],
        requires_vitals_check=True
    ),
    
    # =========================================================================
    # SPECIAL POPULATIONS
    # =========================================================================
    
    "pregnancy_complaint": ICD10Code(
        code="O26.90",
        description_en="Pregnancy related condition, unspecified",
        description_ar="شكوى متعلقة بالحمل",
        chapter="O00-O9A",
        base_urgency=TriageUrgency.URGENT,
        red_flags=["bleeding", "abdominal pain", "decreased fetal movement", ">20 weeks"],
        requires_vitals_check=True
    ),
    
    "pediatric_fever": ICD10Code(
        code="R50.9",
        description_en="Fever in pediatric patient",
        description_ar="حمى عند الأطفال",
        chapter="R50-R69",
        base_urgency=TriageUrgency.URGENT,
        red_flags=["age < 3 months", "petechial rash", "lethargy", "poor feeding"],
        requires_vitals_check=True
    ),
    
    # =========================================================================
    # SILENT MI / ATYPICAL PRESENTATIONS (Critical for thesis)
    # =========================================================================
    
    "silent_mi_pattern": ICD10Code(
        code="R07.89",
        description_en="Atypical chest discomfort (Silent MI pattern)",
        description_ar="أعراض غير نمطية لاحتشاء عضلة القلب",
        chapter="R00-R09",
        base_urgency=TriageUrgency.EMERGENT,
        red_flags=["diabetic", "elderly", "female", "nausea/indigestion", "fatigue", "diaphoresis"],
        requires_vitals_check=True
    ),
    
    # =========================================================================
    # CATCH-ALL
    # =========================================================================
    
    "other_complaint": ICD10Code(
        code="R69",
        description_en="Illness, unspecified",
        description_ar="شكوى أخرى",
        chapter="R50-R69",
        base_urgency=TriageUrgency.URGENT,  # Conservative default
        red_flags=["abnormal vitals", "elderly", "immunocompromised"],
        requires_vitals_check=True
    ),
}


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def get_icd10_code(category: str) -> Optional[ICD10Code]:
    """Get ICD-10 code for a complaint category"""
    return ICD10_TRIAGE_MAP.get(category)


def get_icd10_by_code(code: str) -> Optional[ICD10Code]:
    """Reverse lookup: find category by ICD-10 code"""
    for category, icd in ICD10_TRIAGE_MAP.items():
        if icd.code == code:
            return icd
    return None


def get_all_emergent_codes() -> List[str]:
    """Get all ICD-10 codes that default to ESI 1-2"""
    return [
        icd.code for icd in ICD10_TRIAGE_MAP.values()
        if icd.base_urgency in [TriageUrgency.IMMEDIATE, TriageUrgency.EMERGENT]
    ]


def format_icd10_for_output(category: str) -> dict:
    """Format ICD-10 data for API response"""
    icd = get_icd10_code(category)
    if not icd:
        return {"code": "R69", "description": "Unspecified"}
    
    return {
        "icd10_code": icd.code,
        "icd10_description_en": icd.description_en,
        "icd10_description_ar": icd.description_ar,
        "chapter": icd.chapter,
        "base_urgency": icd.base_urgency.value,
        "red_flags": icd.red_flags
    }


# =============================================================================
# ARABIC KEYWORD TO ICD-10 QUICK LOOKUP
# For faster matching without full AI processing
# =============================================================================

ARABIC_TO_ICD10_QUICK = {
    # Chest/Cardiac
    "صدري": "R07.9",
    "قلبي": "R07.9",
    "خفقان": "R00.2",
    "ضيق نفس": "R06.00",
    "مخنوق": "R06.00",
    
    # Abdominal
    "بطني": "R10.9",
    "معدتي": "R10.13",
    "مغص": "R10.9",
    "استفراغ": "R11.2",
    "قيء": "R11.2",
    
    # Neurological
    "صداع": "R51.9",
    "دوخة": "R42",
    "إغماء": "R55",
    "تنميل": "R20.2",
    
    # General
    "حرارة": "R50.9",
    "سخونية": "R50.9",
    "تعب": "R53.83",
    "إرهاق": "R53.81",
}


if __name__ == "__main__":
    # Test the mapping
    print("=" * 60)
    print("SAFE-Triage ICD-10 Mapping Test")
    print("=" * 60)
    
    test_categories = [
        "chest_pain_cardiac",
        "respiratory_distress", 
        "abdominal_pain",
        "stroke_symptoms",
        "silent_mi_pattern"
    ]
    
    for cat in test_categories:
        icd = get_icd10_code(cat)
        if icd:
            print(f"\n{cat}:")
            print(f"  Code: {icd.code}")
            print(f"  EN: {icd.description_en}")
            print(f"  AR: {icd.description_ar}")
            print(f"  Base ESI: {icd.base_urgency.value}")
            print(f"  Red Flags: {', '.join(icd.red_flags[:3])}...")
    
    print(f"\n\nTotal categories mapped: {len(ICD10_TRIAGE_MAP)}")
    print(f"Emergent codes (ESI 1-2): {len(get_all_emergent_codes())}")
