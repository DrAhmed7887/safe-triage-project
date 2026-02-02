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

from typing import Optional, List, Tuple, Dict
from dataclasses import dataclass
from enum import Enum
import os
import json
from dotenv import load_dotenv
from logic.esi_v5_compliance import evaluate_esi_v5

load_dotenv()

# ===== PERFORMANCE FIX: Lazy import of google.generativeai =====
# This module takes ~500ms to import, so we defer it until first use
genai = None  # Will be loaded on demand

def _get_genai():
    """Lazy load google.generativeai module."""
    global genai
    if genai is None:
        import google.generativeai as _genai
        genai = _genai
    return genai

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
    3. New confusion (ACVPU 'C') scores 3 points
    4. Pediatric vital sign thresholds
    
    Parameters scored:
    - Respiratory rate (RR) - with pediatric thresholds
    - Oxygen saturation (SpO2) - Scale 1 or Scale 2
    - Systolic blood pressure (SBP)
    - Heart rate (HR) - with pediatric thresholds
    - Level of consciousness (ACVPU including new confusion)
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
    def _score_consciousness(gcs: Optional[int], is_new_confusion: bool = False) -> Tuple[int, bool]:
        """
        Score consciousness using ACVPU scale (AUDIT FIX).
        
        NEWS2 ACVPU Scale:
        - A = Alert (0 points)
        - C = New Confusion (3 points) ← AUDIT FIX: Was missing!
        - V = Voice responsive (3 points)
        - P = Pain responsive (3 points)
        - U = Unresponsive (3 points)
        
        Args:
            gcs: Glasgow Coma Scale score
            is_new_confusion: True if patient has NEW onset confusion
            
        Returns:
            (score, is_extreme)
        """
        # AUDIT FIX: New confusion scores 3 even with GCS 15
        if is_new_confusion:
            return 3, True
        
        if gcs is None:
            return 0, False
        
        # GCS ≤8 = Unresponsive (U)
        if gcs <= 8:
            return 3, True
        
        # GCS 9-13 roughly correlates to V/P on AVPU
        # Per NEWS2, V and P also score 3
        if gcs <= 13:
            return 3, True
        
        # GCS 14-15 = Alert (A)
        return 0, False
    
    def calculate(self, vitals, age: float = 30, is_copd: bool = False, 
                  on_supplemental_o2: bool = False, is_new_confusion: bool = False) -> NEWS2Result:
        """
        Calculate NEWS2 score from vital signs.
        
        AUDIT FIXES:
        - Uses pediatric thresholds for patients <18 years
        - Uses SpO2 Scale 2 for COPD patients
        - Adds +2 for supplemental oxygen
        - Scores new confusion as 3 points
        
        Args:
            vitals: Vitals object with hr, rr, spo2, sbp, temp, gcs
            age: Patient age in years (for pediatric thresholds)
            is_copd: Use SpO2 Scale 2 (target 88-92%)
            on_supplemental_o2: Add +2 points
            is_new_confusion: New onset confusion (ACVPU 'C')
            
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
        
        # ===== Consciousness (ACVPU with new confusion) =====
        # AUDIT FIX: Now includes new confusion scoring
        gcs_value = vitals.gcs if vitals.gcs is not None else 15
        score, extreme = self._score_consciousness(gcs_value, is_new_confusion)
        scores['consciousness'] = score
        has_extreme = has_extreme or extreme
        
        if is_new_confusion:
            alerts_ar.append("🚨 تشوش ذهني جديد (ACVPU: C) - 3 نقاط")
            alerts_en.append("🚨 NEW confusion (ACVPU: C) - 3 points")
        elif score == 3:
            alerts_ar.append(f"مستوى الوعي منخفض: GCS {gcs_value}")
            alerts_en.append(f"Reduced consciousness: GCS {gcs_value}")
        
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
    
    def __init__(self):
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            print("Warning: GEMINI_API_KEY not found. AI classifier disabled.")
            self.model = None
            self._genai_loaded = False
        else:
            # ===== PERFORMANCE FIX: Lazy load genai =====
            # Don't initialize until first actual use
            self._api_key = api_key
            self.model = "deferred"  # Marker for deferred initialization
            self._genai_loaded = False
        
        # Build category list for prompt
        self.category_list = list(SYMPTOM_CATEGORIES.keys())
        self.category_descriptions = {
            k: f"{v.name_ar} / {v.name_en}" 
            for k, v in SYMPTOM_CATEGORIES.items()
        }
        
        # ===== PERFORMANCE FIX: Circuit Breaker Pattern =====
        # After N consecutive failures, stop trying AI for a cooldown period
        self._failure_count = 0
        self._failure_threshold = 3  # After 3 failures, circuit opens
        self._circuit_open_until = 0  # Unix timestamp when circuit can close
        self._cooldown_seconds = 60  # Wait 60 seconds before retrying AI
    
    def _ensure_model_loaded(self):
        """Lazy load the generative AI model on first use."""
        if self.model == "deferred" and not self._genai_loaded:
            try:
                genai = _get_genai()
                genai.configure(api_key=self._api_key)
                self.model = genai.GenerativeModel('gemini-2.0-flash')
                self._genai_loaded = True
                print("[AI] Gemini model loaded on first use")
            except Exception as e:
                print(f"[AI] Failed to load Gemini model: {e}")
                self.model = None
                self._genai_loaded = True
    
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
                self._record_success()  # Reset circuit breaker on success
                return category
            
            # Try fuzzy matching for close matches
            for known_cat in self.category_list:
                if known_cat in category or category in known_cat:
                    self._record_success()  # Reset circuit breaker on success
                    return known_cat
            
            # Default to unclear if no match
            print(f"AI returned unknown category: '{category}'. Defaulting to 'unclear'")
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
        text_lower = text.lower()
        
        # Try dynamic keyword database first
        if USE_DYNAMIC_KEYWORDS:
            try:
                db = get_keyword_database()
                result = db.search_keyword(text_lower)
                if result:
                    category, level = result
                    return category
            except Exception as e:
                print(f"Dynamic keyword search error: {e}")
                # Fall through to static keywords
        
        # Static fallback keywords
        # Level 1 keywords (must catch these even without AI)
        level1_keywords = {
            "unconscious": ["unconscious", "unresponsive", "فاقد الوعي", "مغمى عليه", "مش بيرد", 
                           "مش بيرد عليا", "مش واعي", "فاقد وعي"],
            "cardiac_arrest": ["cardiac arrest", "قلبه وقف", "القلب واقف", "قلبه مش شغال"],
            "respiratory_arrest": ["not breathing", "مش بيتنفس", "توقف التنفس", "مش قادر يتنفس"],
            "active_seizure": ["seizure", "تشنج", "صرع", "بيترعش", "تشنجات"],
            "choking": ["choking", "شرقان", "حاجة في زوره", "مش قادر يبلع", "شرقت", "شرق", 
                       "اختناق", "مش قادرة تاخد نفس", "حاجة واقفة في زوره"],
            "severe_trauma": ["gunshot", "stab", "طعن", "رصاص", "حادثة", "accident", "اتضرب"],
            "anaphylaxis": ["anaphylaxis", "صدمة تحسسية", "حساسية شديدة", "شفايفه ورمت"],
            "poisoning_overdose": ["overdose", "poison", "تسمم", "جرعة زيادة", "أخد دوا كتير", 
                                  "بلع دوا", "شرب دوا", "أخد حبوب كتير", "جرعة زايدة"],
            "drowning": ["drowning", "drown", "غرق", "غرقان", "طلعوه من المية", "وقع في المية",
                        "حمام السباحة", "البحر", "النيل"],
            "severe_bleeding": ["severe bleeding", "نزيف شديد", "بينزف جامد", "دم كتير"],
        }
        
        for category, keywords in level1_keywords.items():
            for kw in keywords:
                if kw in text_lower:
                    return category
        
        # Level 2 keywords
        level2_keywords = {
            "chest_pain_cardiac": ["chest pain", "ألم صدر", "صدري بيوجعني", "قلبي بيوجعني"],
            "stroke_symptoms": ["stroke", "جلطة", "شلل", "مش قادر يتكلم", "وشه مايل"],
            "respiratory_distress": ["can't breathe", "مش عارف آخد نفسي", "ضيق تنفس", 
                                    "مش قادرة آخد نفسي", "صعوبة تنفس"],
            "suicidal_homicidal": ["suicidal", "kill myself", "عايز أموت", "عايز يموت",
                                  "يقتل نفسه", "عايز يقتل نفسه", "ينتحر", "عايز ينتحر",
                                  "هيأذي نفسه", "مش عايز يعيش"],
            "obstetric_emergency": ["pregnant bleeding", "حامل بتنزف", "حامل وبتنزف",
                                   "حامل في", "حامل ونزيف", "نزيف حمل", "الحمل بينزف"],
            "diabetic_emergency": ["sugar low", "السكر واطي", "السكر عالي", "سكر منخفض",
                                  "عنده سكر وبيترعش", "هبوط سكر"],
            "severe_headache": ["worst headache", "صداع شديد", "راسي هتنفجر", "صداع مفاجئ"],
            "severe_pain": ["severe pain", "ألم شديد", "بيوجعني جدا جدا", "ألم شديد جداً"],
            "high_fever_toxic": ["سخونية عالية جداً", "حرارة عالية جداً", "معياش جداً"],
        }
        
        for category, keywords in level2_keywords.items():
            for kw in keywords:
                if kw in text_lower:
                    return category
        
        # Level 3 keywords
        level3_keywords = {
            "abdominal_pain_moderate": ["abdominal pain", "stomach pain", "ألم بطن", "بطني بتوجعني", 
                                        "معدتي", "مغص", "وجع بطن"],
            "fever_with_symptoms": ["fever", "سخونية", "حرارة", "سخن"],
            "vomiting_dehydration": ["vomiting", "بيرجع", "استفراغ", "ترجيع"],
            "moderate_bleeding": ["bleeding", "بينزف", "نزيف", "دم"],
            "fracture_deformity": ["fracture", "broken", "كسر", "مكسور", "ملوي"],
            "pediatric_distress": ["child sick", "طفل", "ابني", "بنتي"],
        }
        
        for category, keywords in level3_keywords.items():
            for kw in keywords:
                if kw in text_lower:
                    return category
        
        # Level 4 keywords
        level4_keywords = {
            "minor_trauma": ["fell", "fall", "وقعت", "وقع", "اتخبط", "خبطة", "ضربة", "وارم", "ورم"],
            "laceration_simple": ["cut", "laceration", "جرح", "قطع", "خياطة", "غرز"],
            "uri_symptoms": ["cold", "flu", "cough", "برد", "كحة", "زكام", "رشح", "انفلونزا"],
            "sore_throat": ["sore throat", "زور", "حلق", "بلع"],
            "earache": ["ear pain", "earache", "ودني", "أذني"],
            "uti_symptoms": ["burning urination", "حرقان بول", "التهاب مجرى", "حرقان في البول",
                           "رايح الحمام كتير", "بول كتير", "التهاب بولي"],
            "mild_allergic": ["rash", "allergy", "حساسية", "طفح", "حكة", "هرش"],
            "back_pain_chronic": ["back pain", "ظهري", "وجع ضهر"],
            "mild_gi": ["diarrhea", "إسهال", "مشي", "معدة"],
            "mild_pain": ["pain", "وجع", "بيوجعني", "ألم"],
            "headache_mild": ["headache", "صداع", "راسي", "دماغي"],
            "eye_complaint": ["عيني", "عين", "حمرا", "مدمعة", "رمد"],
        }
        
        for category, keywords in level4_keywords.items():
            for kw in keywords:
                if kw in text_lower:
                    return category
        
        # Level 5 keywords
        level5_keywords = {
            "prescription_refill": ["refill", "prescription", "روشتة", "تجديد", "الدوا خلص", "عايز دوا"],
            "medical_certificate": ["certificate", "تقرير", "شهادة", "إجازة مرضية"],
            "suture_removal": ["remove stitches", "فك غرز", "فك الغرز"],
            "chronic_stable": ["follow up", "متابعة", "كشف"],
            "minor_complaint": ["check up", "فحص", "اطمن"],
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
        complaint_lower = chief_complaint.lower()
        
        # Keywords suggesting labs needed
        if any(word in complaint_lower for word in ["سخونية", "fever", "infection", "حرارة"]):
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

        # Build vitals dict
        vitals_dict = {
            "hr": vitals.hr,
            "rr": vitals.rr,
            "spo2": vitals.spo2,
            "sbp": vitals.sbp,
            "dbp": vitals.dbp,
            "temp_c": vitals.temp,
            "gcs": vitals.gcs,
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
        """Check if chief complaint indicates trauma."""
        trauma_keywords = [
            "trauma",
            "accident",
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
    
    def triage(self, patient_data: dict) -> DeterministicTriageResult:
        """
        Perform deterministic triage on patient data.
        
        AUDIT FIXES IMPLEMENTED:
        - Passes new NEWS2 parameters (is_copd, on_supplemental_o2, is_new_confusion)
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
                - is_new_confusion: bool (optional) - ACVPU 'C' = 3 points
                - is_pregnant: bool (optional) - Enable obstetric emergency detection
                
        Returns:
            DeterministicTriageResult with complete decision audit trail
        """
        # Extract data
        age = patient_data.get('age', 30)
        gender = patient_data.get('gender', 'male')
        if hasattr(gender, 'value'):
            gender = gender.value
        complaint = patient_data.get('chief_complaint_text', '')
        vitals = patient_data.get('vitals', {})
        
        # AUDIT FIX: Extract new NEWS2 compliance fields
        is_copd = patient_data.get('is_copd', False)
        on_supplemental_o2 = patient_data.get('on_supplemental_o2', False)
        is_new_confusion = patient_data.get('is_new_confusion', False)
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
                self.gcs = d.get('gcs', 15)
                self.pain_score = d.get('pain_score', 0)
        
        if isinstance(vitals, dict):
            vitals = VitalsWrapper(vitals)
        
        # Step 1: Calculate NEWS2 (Deterministic) - AUDIT FIX: Pass new parameters
        news2_result = self.news2_calculator.calculate(
            vitals,
            age=age,
            is_copd=is_copd,
            on_supplemental_o2=on_supplemental_o2,
            is_new_confusion=is_new_confusion
        )
        
        # Step 2: Classify complaint
        # PERFORMANCE FIX: Only use AI when explicitly enabled
        if self.use_ai:
            category = self.ai_classifier.classify(complaint, age, gender)
        else:
            # Standard mode: Use ONLY keyword matching (fast, deterministic)
            category = self.ai_classifier._fallback_keyword_match(complaint)
        category_info = SYMPTOM_CATEGORIES.get(category, SYMPTOM_CATEGORIES["unclear"])
        category_level = category_info.esi_level
        
        # Step 3: Apply clinical modifiers (Deterministic rules)
        modifiers = []
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
        
        # ===== ELDERLY MODIFIERS =====
        if age >= 65 and category in ["chest_pain_cardiac", "chest_pain_noncardiac"]:
            modifier_level = min(modifier_level, 2)
            modifiers.append("مسن مع ألم صدر / Elderly with chest pain")
        
        # ===== PAIN SCORE MODIFIER =====
        if vitals.pain_score and vitals.pain_score >= 8:
            modifier_level = min(modifier_level, 2)
            modifiers.append(f"ألم شديد {vitals.pain_score}/10 / Severe pain")
        
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
        
        # ===== NEW CONFUSION MODIFIER (AUDIT FIX) =====
        if is_new_confusion:
            modifier_level = min(modifier_level, 2)
            modifiers.append("🚨 تشوش ذهني جديد - يحتاج تقييم عاجل / NEW confusion - urgent evaluation needed")
        
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
        
        # Step 4: Determine preliminary level from NEWS2, category, and modifiers
        preliminary_level = min(
            news2_result.triage_level,
            category_level,
            modifier_level
        )
        
        # Level 1 override: Immediate life-threat categories
        if category_info.requires_immediate_intervention:
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
                'gcs': vitals.gcs
            }
            
            resource_result = self.resource_predictor.estimate_resources(
                category=category,
                chief_complaint=complaint,
                vitals=vitals_dict,
                age=age
            )
            
            resource_count = resource_result["count"]
            
            # ESI Decision Points D & E
            if resource_count >= 2:
                final_level = 3  # Urgent - multiple resources needed
                modifiers.append(f"موارد متعددة: {resource_count} / Multiple resources: {resource_count}")
            elif resource_count == 1:
                # SPECIAL CASE: 'unclear' category should default to Level 3 even with 1 resource
                # to align with "Ambiguous defaults to L3" principle
                if category == "unclear":
                    final_level = 3
                    modifiers.append("حالة غير واضحة - اختيار المستوى 3 كإجراء وقائي / Ambiguous - defaulting to Level 3")
                else:
                    final_level = 4  # Less urgent - one resource
                    modifiers.append(f"مورد واحد: {resource_result['resources']} / One resource: {resource_result['resources']}")
            else:
                # Final safeguard for unclear cases with 0 resources
                if category == "unclear":
                    final_level = 3
                else:
                    final_level = 5  # Non-urgent - no resources
                modifiers.append("بدون موارد طوارئ / No ED resources needed")

        # Apply ESI v5 compliance
        final_level, esi_v5_alerts = self.apply_esi_v5_compliance(
            patient_data, vitals, final_level
        )
        
        # Build decision path string for audit (bilingual)
        decision_path = (
            f"NEWS2={news2_result.total_score}→L{news2_result.triage_level} | "
            f"Category={category}→L{category_level} | "
            f"Modifiers→L{modifier_level} | "
            f"Final=L{final_level}"
        )
        
        decision_path_ar = (
            f"نيوز2={news2_result.total_score}→م{news2_result.triage_level} | "
            f"التصنيف={category_info.name_ar}→م{category_level} | "
            f"المعدلات→م{modifier_level} | "
            f"النهائي=م{final_level}"
        )
        
        decision_path_en = (
            f"NEWS2={news2_result.total_score}→L{news2_result.triage_level} | "
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
        
        if category_info.esi_level <= 2:
            all_alerts_ar.append(f"⚠️ {category_info.name_ar}")
            all_alerts_en.append(f"⚠️ {category_info.name_en}")
        
        return DeterministicTriageResult(
            final_level=final_level,
            color_code=level_info["color"],
            label_ar=level_info["label_ar"],
            label_en=level_info["label_en"],
            news2_score=news2_result.total_score,
            news2_level=news2_result.triage_level,
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
            recommended_action_en=level_info["action_en"]
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
            from ..models import TriageResult, TriageLevel
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
                'gcs': patient.vitals.gcs,
                'pain_score': patient.vitals.pain_score
            } if patient.vitals else {},
            # ===== PHASE 2: Clinical Risk Factors =====
            'is_copd': getattr(patient, 'is_copd', False),
            'on_supplemental_o2': getattr(patient, 'on_supplemental_o2', False),
            'is_new_confusion': getattr(patient, 'is_new_confusion', False),
            'is_pregnant': getattr(patient, 'is_pregnant', False),
            'gestational_weeks': getattr(patient, 'gestational_weeks', None),
            'pregnancy_complaint': getattr(patient, 'pregnancy_complaint', None),
            # Red flags are direct fields on PatientInput (not nested)
            'history_cardiac': getattr(patient, 'history_cardiac', False),
            'history_stroke': getattr(patient, 'history_stroke', False),
            'immuno_compromised': getattr(patient, 'immuno_compromised', False),
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
            confidence="High" if not internal_result.ai_used else "Medium"
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
    gcs: int = 15,
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
            'gcs': gcs,
            'pain_score': pain_score
        }
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
                "vitals": {"gcs": 6}
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
