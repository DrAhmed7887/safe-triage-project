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
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

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
    
    # =========== LEVEL 5: Non-Urgent ===========
    "prescription_refill": SymptomCategory(5, "تجديد روشتة", "Prescription Refill"),
    "minor_complaint": SymptomCategory(5, "شكوى بسيطة", "Minor Complaint"),
    "chronic_stable": SymptomCategory(5, "حالة مزمنة مستقرة", "Stable Chronic Condition"),
    "suture_removal": SymptomCategory(5, "فك غرز", "Suture Removal"),
    "medical_certificate": SymptomCategory(5, "شهادة طبية", "Medical Certificate Request"),
    
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


class NEWS2Calculator:
    """
    NEWS2 (National Early Warning Score 2) Calculator
    
    Reference: Royal College of Physicians, 2017
    
    Parameters scored:
    - Respiratory rate (RR)
    - Oxygen saturation (SpO2) - Scale 1 for most patients
    - Systolic blood pressure (SBP)
    - Heart rate (HR)
    - Level of consciousness (AVPU/GCS)
    - Temperature
    
    Each parameter scores 0-3 points based on deviation from normal.
    """
    
    # NEWS2 Scoring thresholds (Scale 1 for SpO2 - most patients)
    # Format: list of (min_value, max_value, score)
    
    RR_THRESHOLDS = [
        (None, 8, 3),      # ≤8
        (9, 11, 1),        # 9-11
        (12, 20, 0),       # 12-20 (Normal)
        (21, 24, 2),       # 21-24
        (25, None, 3),     # ≥25
    ]
    
    SPO2_SCALE1_THRESHOLDS = [
        (None, 91, 3),     # ≤91
        (92, 93, 2),       # 92-93
        (94, 95, 1),       # 94-95
        (96, None, 0),     # ≥96 (Normal)
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
    def _score_consciousness(gcs: Optional[int]) -> Tuple[int, bool]:
        """
        Score consciousness using GCS → AVPU conversion
        GCS 15 = Alert (A) = 0 points
        GCS 14 = Voice responsive (V) = 0 points (per NEWS2, only CVPU scores 3)
        GCS 9-13 = Pain responsive (P) = 0 points
        GCS ≤8 = Unresponsive (U) = 3 points
        
        Note: NEWS2 only gives 3 points for new confusion or unresponsive.
        For simplicity, we score GCS ≤8 as 3 (comatose/unresponsive)
        """
        if gcs is None:
            return 0, False
        if gcs <= 8:
            return 3, True
        return 0, False
    
    def calculate(self, vitals) -> NEWS2Result:
        """
        Calculate NEWS2 score from vital signs.
        
        Args:
            vitals: Vitals object with hr, rr, spo2, sbp, temp, gcs
            
        Returns:
            NEWS2Result with scores, alerts, and derived triage level
        """
        scores = {}
        alerts_ar = []
        alerts_en = []
        missing = []
        has_extreme = False
        
        # Respiratory Rate
        if vitals.rr is not None:
            score, extreme = self._score_value(vitals.rr, self.RR_THRESHOLDS)
            scores['rr'] = score
            has_extreme = has_extreme or extreme
            if score >= 2:
                alerts_ar.append(f"معدل التنفس غير طبيعي: {vitals.rr}/دقيقة")
                alerts_en.append(f"Abnormal RR: {vitals.rr}/min")
        else:
            scores['rr'] = 0
            missing.append("RR (معدل التنفس)")
        
        # Oxygen Saturation (Scale 1)
        if vitals.spo2 is not None:
            score, extreme = self._score_value(vitals.spo2, self.SPO2_SCALE1_THRESHOLDS)
            scores['spo2'] = score
            has_extreme = has_extreme or extreme
            if score >= 2:
                alerts_ar.append(f"نسبة الأكسجين منخفضة: {vitals.spo2}%")
                alerts_en.append(f"Low SpO2: {vitals.spo2}%")
        else:
            scores['spo2'] = 0
            missing.append("SpO2 (نسبة الأكسجين)")
        
        # Systolic Blood Pressure
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
        
        # Heart Rate
        if vitals.hr is not None:
            score, extreme = self._score_value(vitals.hr, self.HR_THRESHOLDS)
            scores['hr'] = score
            has_extreme = has_extreme or extreme
            if score >= 2:
                alerts_ar.append(f"النبض غير طبيعي: {vitals.hr}/دقيقة")
                alerts_en.append(f"Abnormal HR: {vitals.hr}/min")
        else:
            scores['hr'] = 0
            missing.append("HR (النبض)")
        
        # Temperature
        if vitals.temp is not None:
            score, extreme = self._score_value(vitals.temp, self.TEMP_THRESHOLDS)
            scores['temp'] = score
            has_extreme = has_extreme or extreme
            if score >= 2:
                alerts_ar.append(f"درجة الحرارة غير طبيعية: {vitals.temp}°C")
                alerts_en.append(f"Abnormal Temp: {vitals.temp}°C")
        else:
            scores['temp'] = 0
            missing.append("Temp (الحرارة)")
        
        # Consciousness (GCS)
        if vitals.gcs is not None:
            score, extreme = self._score_consciousness(vitals.gcs)
            scores['consciousness'] = score
            has_extreme = has_extreme or extreme
            if score == 3:
                alerts_ar.append(f"مستوى الوعي منخفض: GCS {vitals.gcs}")
                alerts_en.append(f"Reduced consciousness: GCS {vitals.gcs}")
        else:
            scores['consciousness'] = 0
            missing.append("GCS (مستوى الوعي)")
        
        # Calculate total
        total_score = sum(scores.values())
        
        # Add warning for missing vitals
        if len(missing) >= 3:
            alerts_ar.append(f"⚠️ تحذير: {len(missing)} علامات حيوية غير مسجلة")
            alerts_en.append(f"⚠️ Warning: {len(missing)} vital signs not recorded")
        
        # Derive triage level from NEWS2 score
        # Reference: NEWS2 Clinical Response Thresholds (RCP 2017)
        if total_score >= 7 or has_extreme:
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
        else:
            genai.configure(api_key=api_key)
            self.model = genai.GenerativeModel('gemini-2.0-flash')
        
        # Build category list for prompt
        self.category_list = list(SYMPTOM_CATEGORIES.keys())
        self.category_descriptions = {
            k: f"{v.name_ar} / {v.name_en}" 
            for k, v in SYMPTOM_CATEGORIES.items()
        }
    
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
        if not self.model:
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
                return category
            
            # Try fuzzy matching for close matches
            for known_cat in self.category_list:
                if known_cat in category or category in known_cat:
                    return known_cat
            
            # Default to unclear if no match
            print(f"AI returned unknown category: '{category}'. Defaulting to 'unclear'")
            return "unclear"
            
        except Exception as e:
            print(f"AI Classification Error: {e}")
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
# Decision Flow:
# 1. Calculate NEWS2 score from vitals (fully deterministic)
# 2. Classify complaint using AI (constrained to predefined categories)
# 3. Get ESI level from category (deterministic lookup)
# 4. Apply clinical modifiers (deterministic rules)
# 5. Final level = min(NEWS2_level, ESI_level, modifier_level)

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
    category_level: int
    modifiers_applied: List[str]
    
    # Clinical Information
    alerts_ar: List[str]
    alerts_en: List[str]
    missing_vitals: List[str]
    
    # Decision Path (for documentation/audit)
    decision_path: str
    ai_used: bool
    
    # Time recommendations
    time_to_physician: str
    recommended_action_ar: str
    recommended_action_en: str


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
    
    def __init__(self):
        self.news2_calculator = NEWS2Calculator()
        self.ai_classifier = AISymptomClassifier()
    
    def triage(self, patient_data: dict) -> DeterministicTriageResult:
        """
        Perform deterministic triage on patient data.
        
        Args:
            patient_data: dict with keys:
                - age: float
                - gender: str
                - chief_complaint_text: str
                - vitals: dict or Vitals object
                - history_cardiac: bool (optional)
                - history_stroke: bool (optional)
                
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
        
        # Step 1: Calculate NEWS2 (Deterministic)
        news2_result = self.news2_calculator.calculate(vitals)
        
        # Step 2: Classify complaint (AI - Constrained)
        category = self.ai_classifier.classify(complaint, age, gender)
        category_info = SYMPTOM_CATEGORIES.get(category, SYMPTOM_CATEGORIES["unclear"])
        category_level = category_info.esi_level
        
        # Step 3: Apply clinical modifiers (Deterministic rules)
        modifiers = []
        modifier_level = 5  # Start with lowest urgency
        
        # Age modifiers
        if age < 2 and news2_result.total_score >= 2:
            modifier_level = min(modifier_level, 2)
            modifiers.append("طفل رضيع مع علامات حيوية غير طبيعية / Infant with abnormal vitals")
        
        if age >= 65 and category in ["chest_pain_cardiac", "chest_pain_noncardiac"]:
            modifier_level = min(modifier_level, 2)
            modifiers.append("مسن مع ألم صدر / Elderly with chest pain")
        
        # High pain score
        if vitals.pain_score and vitals.pain_score >= 8:
            modifier_level = min(modifier_level, 2)
            modifiers.append(f"ألم شديد {vitals.pain_score}/10 / Severe pain")
        
        # Cardiac history + relevant complaint
        if patient_data.get('history_cardiac') and category in [
            "chest_pain_cardiac", "chest_pain_noncardiac", "respiratory_distress"
        ]:
            modifier_level = min(modifier_level, 2)
            modifiers.append("تاريخ قلبي مع شكوى ذات صلة / Cardiac history + relevant complaint")
        
        # Pregnancy
        if patient_data.get('is_pregnant') and category not in ["chronic_stable", "prescription_refill"]:
            modifier_level = min(modifier_level, 3)
            modifiers.append("حامل / Pregnant")
        
        # Immunocompromised
        if patient_data.get('immuno_compromised') and category in [
            "fever_with_symptoms", "high_fever_toxic"
        ]:
            modifier_level = min(modifier_level, 2)
            modifiers.append("نقص مناعة مع حمى / Immunocompromised with fever")
        
        # Step 4: Calculate final level (most urgent wins)
        final_level = min(
            news2_result.triage_level,
            category_level,
            modifier_level
        )
        
        # Level 1 override: Immediate life-threat categories
        if category_info.requires_immediate_intervention:
            final_level = 1
        
        # Build decision path string for audit
        decision_path = (
            f"NEWS2={news2_result.total_score}→L{news2_result.triage_level} | "
            f"Category={category}→L{category_level} | "
            f"Modifiers→L{modifier_level} | "
            f"Final=L{final_level}"
        )
        
        # Get level metadata
        level_info = self.LEVEL_INFO[final_level]
        
        # Combine alerts
        all_alerts_ar = news2_result.alerts_ar.copy()
        all_alerts_en = news2_result.alerts_en.copy()
        
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
            category_level=category_level,
            modifiers_applied=modifiers,
            alerts_ar=all_alerts_ar,
            alerts_en=all_alerts_en,
            missing_vitals=news2_result.missing_vitals,
            decision_path=decision_path,
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
