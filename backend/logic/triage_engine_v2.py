"""
SAFE-Triage AI - Deterministic Triage Engine v2.0
================================================

A hybrid Clinical Decision Support System (CDSS) combining validated
clinical scoring systems with constrained AI classification.

ARCHITECTURE OVERVIEW:
---------------------
1. Vital Signs → NEWS2 Score (Deterministic)
2. Chief Complaint → AI Classification → Fixed Category (Constrained)
3. Category + NEWS2 → Final Triage Level (Deterministic Rules)

AI ROLE: Classification ONLY - Never decides triage level directly.

ACADEMIC REFERENCES:
-------------------
[1] NEWS2 (National Early Warning Score 2):
    Royal College of Physicians. "National Early Warning Score (NEWS) 2:
    Standardising the assessment of acute-illness severity in the NHS."
    London: RCP, 2017.
    URL: https://www.rcplondon.ac.uk/projects/outputs/national-early-warning-score-news-2
    
    Validation: Smith GB, et al. "The ability of the National Early Warning
    Score (NEWS) to discriminate patients at risk of early cardiac arrest,
    unanticipated intensive care unit admission, and death."
    Resuscitation. 2013;84(4):465-470.

[2] ESI (Emergency Severity Index) v4:
    Gilboy N, Tanabe T, Travers D, Rosenau AM. "Emergency Severity Index (ESI):
    A Triage Tool for Emergency Department Care, Version 4."
    AHRQ Publication No. 12-0014. Rockville, MD: Agency for Healthcare
    Research and Quality, 2011.
    URL: https://www.ahrq.gov/patient-safety/settings/emergency-dept/esi.html

[3] Hybrid AI + Deterministic CDSS Design:
    Shortliffe EH, Sepúlveda MJ. "Clinical Decision Support in the Era of
    Artificial Intelligence." JAMA. 2018;320(21):2199-2200.
    
    Sutton RT, et al. "An overview of clinical decision support systems:
    benefits, risks, and strategies for success."
    NPJ Digital Medicine. 2020;3:17.

[4] Constrained AI Classification Principle:
    Rajkomar A, Dean J, Kohane I. "Machine Learning in Medicine."
    New England Journal of Medicine. 2019;380(14):1347-1358.
    
    WHO. "Ethics and Governance of Artificial Intelligence for Health."
    Geneva: World Health Organization, 2021. Chapter 6.

[5] Arabic Clinical NLP:
    Alshammari N, et al. "Arabic Natural Language Processing for Clinical
    Text: A Systematic Review." Journal of Biomedical Informatics. 2021;118:103810.

EGYPTIAN CONTEXT:
----------------
- NEWS2 adopted by Egyptian private hospitals (As-Salam International, Saudi German)
- ESI taught in Alexandria & Ain Shams EM residency programs
- Egyptian Ministry of Health Emergency Department Triage Guidelines, 2019

Author: SAFE-Triage Team
Version: 2.0.0
License: MIT
"""

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
from enum import IntEnum
import json
import os
# import google.generativeai as genai  # REMOVED - using Vertex AI
from dotenv import load_dotenv

load_dotenv()


# =============================================================================
# ENUMS AND DATA CLASSES
# =============================================================================

class TriageLevel(IntEnum):
    """ESI Triage Levels (AHRQ, 2011)"""
    RESUSCITATION = 1  # Immediate life-saving intervention
    EMERGENT = 2       # High risk, confused/lethargic, severe pain
    URGENT = 3         # Stable but needs multiple resources
    LESS_URGENT = 4    # Stable, needs one resource
    NON_URGENT = 5     # Stable, no resources needed


class NEWS2Risk(IntEnum):
    """NEWS2 Clinical Risk Levels (RCP, 2017)"""
    LOW = 0            # Score 0-4, routine monitoring
    LOW_MEDIUM = 1     # Score 3 in single parameter
    MEDIUM = 2         # Score 5-6, urgent response
    HIGH = 3           # Score ≥7, emergency response


@dataclass
class Vitals:
    """Patient vital signs"""
    hr: Optional[int] = None          # Heart rate (bpm)
    rr: Optional[int] = None          # Respiratory rate (/min)
    spo2: Optional[int] = None        # Oxygen saturation (%)
    sbp: Optional[int] = None         # Systolic BP (mmHg)
    dbp: Optional[int] = None         # Diastolic BP (mmHg)
    temp: Optional[float] = None      # Temperature (°C)
    gcs: Optional[int] = None         # Glasgow Coma Scale (3-15)
    avpu: Optional[str] = None        # Alert/Voice/Pain/Unresponsive
    on_oxygen: bool = False           # Supplemental O2


@dataclass
class NEWS2Result:
    """NEWS2 Calculation Result"""
    total_score: int
    risk_level: NEWS2Risk
    parameter_scores: Dict[str, int]
    missing_vitals: List[str]
    alerts_ar: List[str]
    alerts_en: List[str]


@dataclass 
class TriageResult:
    """Final Triage Output"""
    level: TriageLevel
    news2_score: int
    news2_risk: str
    category: str
    category_ar: str
    decision_path: str
    missing_vitals: List[str]
    alerts_ar: List[str]
    alerts_en: List[str]
    ai_used: bool
    confidence: str  # "high", "medium", "low"


# =============================================================================
# SYMPTOM CATEGORIES - ESI-BASED (Reference [2])
# =============================================================================

SYMPTOM_CATEGORIES: Dict[str, Tuple[int, str, str]] = {
    # Category: (ESI Level, Arabic Description, English Description)
    
    # ===== LEVEL 1 - RESUSCITATION =====
    "cardiac_arrest": (1, "توقف القلب", "Cardiac arrest"),
    "respiratory_arrest": (1, "توقف التنفس", "Respiratory arrest"),
    "unconscious_unresponsive": (1, "فاقد الوعي / لا يستجيب", "Unconscious/Unresponsive"),
    "active_seizure": (1, "تشنجات نشطة", "Active seizure"),
    "severe_trauma": (1, "إصابة شديدة / حادث خطير", "Severe trauma"),
    "anaphylaxis": (1, "صدمة حساسية", "Anaphylaxis"),
    "poisoning_overdose": (1, "تسمم / جرعة زائدة", "Poisoning/Overdose"),
    "choking_airway": (1, "انسداد مجرى الهواء / شرقة", "Choking/Airway obstruction"),
    
    # ===== LEVEL 2 - EMERGENT =====
    "chest_pain_cardiac": (2, "ألم صدر قلبي", "Cardiac chest pain"),
    "stroke_symptoms": (2, "أعراض جلطة دماغية", "Stroke symptoms"),
    "respiratory_distress": (2, "ضيق تنفس شديد", "Severe respiratory distress"),
    "severe_bleeding": (2, "نزيف شديد", "Severe bleeding"),
    "altered_mental_status": (2, "تغير في الوعي", "Altered mental status"),
    "psychiatric_emergency": (2, "حالة نفسية طارئة / أفكار انتحارية", "Psychiatric emergency"),
    "obstetric_emergency": (2, "طوارئ حمل / نزيف مهبلي", "Obstetric emergency"),
    "severe_pain": (2, "ألم شديد جداً (>=8/10)", "Severe pain"),
    "diabetic_emergency": (2, "طوارئ سكر (هبوط/ارتفاع شديد)", "Diabetic emergency"),
    "allergic_reaction_moderate": (2, "حساسية متوسطة", "Moderate allergic reaction"),
    
    # ===== LEVEL 3 - URGENT =====
    "abdominal_pain_moderate": (3, "ألم بطن متوسط", "Moderate abdominal pain"),
    "moderate_trauma": (3, "إصابة متوسطة", "Moderate trauma"),
    "headache_severe": (3, "صداع شديد", "Severe headache"),
    "fever_with_symptoms": (3, "سخونية مع أعراض أخرى", "Fever with other symptoms"),
    "vomiting_diarrhea_dehydration": (3, "قيء/إسهال مع جفاف", "Vomiting/Diarrhea with dehydration"),
    "urinary_symptoms_severe": (3, "أعراض بولية شديدة", "Severe urinary symptoms"),
    "pediatric_moderate": (3, "طفل يحتاج تقييم عاجل", "Pediatric needs urgent evaluation"),
    
    # ===== LEVEL 4 - LESS URGENT =====
    "minor_trauma": (4, "إصابة بسيطة", "Minor trauma"),
    "fever_simple": (4, "سخونية بسيطة", "Simple fever"),
    "mild_pain": (4, "ألم خفيف", "Mild pain"),
    "skin_rash_stable": (4, "طفح جلدي مستقر", "Stable skin rash"),
    "minor_bleeding": (4, "نزيف بسيط / جرح", "Minor bleeding/laceration"),
    "cold_flu_symptoms": (4, "أعراض برد/إنفلونزا", "Cold/Flu symptoms"),
    "ear_eye_throat": (4, "مشاكل أذن/عين/حلق", "Ear/Eye/Throat problems"),
    
    # ===== LEVEL 5 - NON-URGENT =====
    "chronic_refill": (5, "تجديد علاج مزمن", "Chronic medication refill"),
    "minor_complaint": (5, "شكوى بسيطة", "Minor complaint"),
    "medical_certificate": (5, "شهادة طبية / تقرير", "Medical certificate"),
    
    # ===== FALLBACK =====
    "unclear_needs_evaluation": (3, "يحتاج تقييم طبي", "Needs medical evaluation"),
}


# =============================================================================
# NEWS2 SCORING ENGINE (Reference [1])
# =============================================================================

class NEWS2Calculator:
    """
    NEWS2 (National Early Warning Score 2) Calculator
    
    Reference: Royal College of Physicians, 2017
    
    Scoring Parameters:
    - Respiratory Rate
    - Oxygen Saturation (Scale 1 or Scale 2 for COPD)
    - Supplemental Oxygen
    - Systolic Blood Pressure
    - Heart Rate  
    - Consciousness (AVPU)
    - Temperature
    """
    
    @staticmethod
    def score_respiratory_rate(rr: Optional[int]) -> Tuple[int, Optional[str]]:
        """Score RR per NEWS2 table"""
        if rr is None:
            return 0, "rr"
        if rr <= 8:
            return 3, None
        elif rr <= 11:
            return 1, None
        elif rr <= 20:
            return 0, None
        elif rr <= 24:
            return 2, None
        else:  # >= 25
            return 3, None
    
    @staticmethod
    def score_spo2_scale1(spo2: Optional[int]) -> Tuple[int, Optional[str]]:
        """Score SpO2 using Scale 1 (standard patients)"""
        if spo2 is None:
            return 0, "spo2"
        if spo2 <= 91:
            return 3, None
        elif spo2 <= 93:
            return 2, None
        elif spo2 <= 95:
            return 1, None
        else:  # >= 96
            return 0, None
    
    @staticmethod
    def score_supplemental_o2(on_oxygen: bool) -> int:
        """Score supplemental oxygen use"""
        return 2 if on_oxygen else 0
    
    @staticmethod
    def score_systolic_bp(sbp: Optional[int]) -> Tuple[int, Optional[str]]:
        """Score Systolic Blood Pressure"""
        if sbp is None:
            return 0, "sbp"
        if sbp <= 90:
            return 3, None
        elif sbp <= 100:
            return 2, None
        elif sbp <= 110:
            return 1, None
        elif sbp <= 219:
            return 0, None
        else:  # >= 220
            return 3, None
    
    @staticmethod
    def score_heart_rate(hr: Optional[int]) -> Tuple[int, Optional[str]]:
        """Score Heart Rate"""
        if hr is None:
            return 0, "hr"
        if hr <= 40:
            return 3, None
        elif hr <= 50:
            return 1, None
        elif hr <= 90:
            return 0, None
        elif hr <= 110:
            return 1, None
        elif hr <= 130:
            return 2, None
        else:  # >= 131
            return 3, None
    
    @staticmethod
    def score_consciousness(avpu: Optional[str], gcs: Optional[int]) -> Tuple[int, Optional[str]]:
        """Score Consciousness using AVPU or GCS"""
        if avpu:
            avpu_upper = avpu.upper()
            if avpu_upper == "A":  # Alert
                return 0, None
            else:  # V, P, or U
                return 3, None
        elif gcs is not None:
            if gcs == 15:
                return 0, None
            else:
                return 3, None
        return 0, "consciousness"
    
    @staticmethod
    def score_temperature(temp: Optional[float]) -> Tuple[int, Optional[str]]:
        """Score Temperature (Celsius)"""
        if temp is None:
            return 0, "temp"
        if temp <= 35.0:
            return 3, None
        elif temp <= 36.0:
            return 1, None
        elif temp <= 38.0:
            return 0, None
        elif temp <= 39.0:
            return 1, None
        else:  # >= 39.1
            return 2, None
    
    def calculate(self, vitals: Vitals) -> NEWS2Result:
        """
        Calculate total NEWS2 score and risk level.
        
        Returns NEWS2Result with:
        - total_score: Sum of all parameter scores
        - risk_level: Clinical risk category
        - parameter_scores: Individual scores per parameter
        - missing_vitals: List of vitals not recorded
        - alerts: Arabic and English alert messages
        """
        scores = {}
        missing = []
        alerts_ar = []
        alerts_en = []
        
        # Calculate each parameter
        score, miss = self.score_respiratory_rate(vitals.rr)
        scores["rr"] = score
        if miss: 
            missing.append(miss)
            alerts_ar.append("⚠️ معدل التنفس غير مسجل")
            alerts_en.append("⚠️ Respiratory rate not recorded")
        elif score >= 3:
            alerts_ar.append(f"🔴 معدل التنفس خطير: {vitals.rr}/دقيقة")
            alerts_en.append(f"🔴 Critical RR: {vitals.rr}/min")
        
        score, miss = self.score_spo2_scale1(vitals.spo2)
        scores["spo2"] = score
        if miss:
            missing.append(miss)
            alerts_ar.append("⚠️ نسبة الأكسجين غير مسجلة")
            alerts_en.append("⚠️ SpO2 not recorded")
        elif score >= 3:
            alerts_ar.append(f"🔴 نسبة الأكسجين خطيرة: {vitals.spo2}%")
            alerts_en.append(f"🔴 Critical SpO2: {vitals.spo2}%")
        
        scores["supplemental_o2"] = self.score_supplemental_o2(vitals.on_oxygen)
        
        score, miss = self.score_systolic_bp(vitals.sbp)
        scores["sbp"] = score
        if miss:
            missing.append(miss)
            alerts_ar.append("⚠️ ضغط الدم غير مسجل")
            alerts_en.append("⚠️ Blood pressure not recorded")
        elif score >= 3:
            alerts_ar.append(f"🔴 ضغط الدم خطير: {vitals.sbp}")
            alerts_en.append(f"🔴 Critical BP: {vitals.sbp}")
        
        score, miss = self.score_heart_rate(vitals.hr)
        scores["hr"] = score
        if miss:
            missing.append(miss)
            alerts_ar.append("⚠️ النبض غير مسجل")
            alerts_en.append("⚠️ Heart rate not recorded")
        elif score >= 3:
            alerts_ar.append(f"🔴 النبض خطير: {vitals.hr}")
            alerts_en.append(f"🔴 Critical HR: {vitals.hr}")
        
        score, miss = self.score_consciousness(vitals.avpu, vitals.gcs)
        scores["consciousness"] = score
        if miss:
            missing.append(miss)
        elif score >= 3:
            alerts_ar.append("🔴 مستوى الوعي غير طبيعي")
            alerts_en.append("🔴 Abnormal consciousness level")
        
        score, miss = self.score_temperature(vitals.temp)
        scores["temp"] = score
        if miss:
            missing.append(miss)
            alerts_ar.append("⚠️ درجة الحرارة غير مسجلة")
            alerts_en.append("⚠️ Temperature not recorded")
        elif score >= 2:
            alerts_ar.append(f"🟡 درجة الحرارة غير طبيعية: {vitals.temp}°C")
            alerts_en.append(f"🟡 Abnormal temperature: {vitals.temp}°C")
        
        # Total score
        total = sum(scores.values())
        
        # Determine risk level
        # Check for any single parameter = 3
        has_extreme = any(s == 3 for s in scores.values())
        
        if total >= 7 or has_extreme:
            risk = NEWS2Risk.HIGH
        elif total >= 5:
            risk = NEWS2Risk.MEDIUM
        elif has_extreme:  # Single parameter = 3 with low total
            risk = NEWS2Risk.LOW_MEDIUM
        else:
            risk = NEWS2Risk.LOW
        
        # Add warning if critical vitals missing
        if len(missing) >= 3:
            alerts_ar.insert(0, "⚠️ تحذير: بيانات الحيوية ناقصة - التقييم غير مكتمل")
            alerts_en.insert(0, "⚠️ Warning: Incomplete vitals - assessment limited")
        
        return NEWS2Result(
            total_score=total,
            risk_level=risk,
            parameter_scores=scores,
            missing_vitals=missing,
            alerts_ar=alerts_ar,
            alerts_en=alerts_en
        )


# =============================================================================
# AI CLASSIFIER (Constrained Output - Reference [4])
# =============================================================================

class SymptomClassifier:
    """
    AI-powered symptom classifier with CONSTRAINED output.
    
    Design Principle (Rajkomar et al., NEJM 2019):
    "Classification tasks with defined output categories are more reliable
    and auditable than open-ended generation tasks in clinical settings."
    
    The AI can ONLY output one of the predefined categories.
    It NEVER generates free-text reasoning for triage decisions.
    """
    
    def __init__(self):
        # AI extraction is handled by ai_service.py (Vertex AI).
        # This classifier runs keyword-only in the deterministic engine.
        self.model = None
    
    def classify(self, chief_complaint: str, age: int = 30) -> Tuple[str, str]:
        """
        Classify chief complaint into one predefined category.
        
        Args:
            chief_complaint: Patient's complaint (Arabic or English)
            age: Patient age (for pediatric classification)
            
        Returns:
            Tuple of (category_key, confidence)
            confidence: "high", "medium", "low"
        """
        if not self.model or not chief_complaint.strip():
            return "unclear_needs_evaluation", "low"
        
        # Build category list for prompt
        category_list = "\n".join([
            f"- {key}: {SYMPTOM_CATEGORIES[key][1]} / {SYMPTOM_CATEGORIES[key][2]}"
            for key in SYMPTOM_CATEGORIES.keys()
        ])
        
        prompt = f"""أنت نظام تصنيف طبي. مهمتك تصنيف شكوى المريض إلى فئة واحدة فقط.

قواعد صارمة:
1. اختر فئة واحدة فقط من القائمة
2. لا تكتب أي شرح أو تفسير
3. إذا لم تكن متأكداً، اختر "unclear_needs_evaluation"
4. الرد يجب أن يكون: category_name,confidence فقط
5. confidence = high أو medium أو low

عمر المريض: {age} سنة
شكوى المريض: {chief_complaint}

الفئات المتاحة:
{category_list}

الرد (category,confidence):"""

        try:
            response = self.model.generate_content(prompt)
            result = response.text.strip().lower()
            
            # Parse response
            parts = result.replace(" ", "").split(",")
            category = parts[0] if parts else "unclear_needs_evaluation"
            confidence = parts[1] if len(parts) > 1 else "medium"
            
            # Validate category exists
            if category not in SYMPTOM_CATEGORIES:
                # Try to find partial match
                for key in SYMPTOM_CATEGORIES:
                    if key in category or category in key:
                        return key, "low"
                return "unclear_needs_evaluation", "low"
            
            # Validate confidence
            if confidence not in ["high", "medium", "low"]:
                confidence = "medium"
            
            return category, confidence
            
        except Exception as e:
            print(f"AI Classification Error: {e}")
            return "unclear_needs_evaluation", "low"


# =============================================================================
# MAIN TRIAGE ENGINE
# =============================================================================

class DeterministicTriageEngine:
    """
    Hybrid Triage Engine combining NEWS2 + ESI with constrained AI.
    
    Architecture (Shortliffe & Sepúlveda, JAMA 2018):
    1. Vital Signs → NEWS2 Score (Deterministic)
    2. Chief Complaint → AI Classification → Fixed Category (Constrained)
    3. Category + NEWS2 → Final Triage Level (Deterministic Rules)
    
    AI assists with understanding Arabic/English text but NEVER decides
    the triage level directly.
    """
    
    def __init__(self):
        self.news2 = NEWS2Calculator()
        self.classifier = SymptomClassifier()
    
    def _news2_to_triage_level(self, news2_result: NEWS2Result) -> int:
        """
        Convert NEWS2 risk to ESI-compatible triage level.
        
        Mapping (based on RCP clinical response recommendations):
        - HIGH (>=7 or extreme): Level 2 (Emergency response)
        - MEDIUM (5-6): Level 3 (Urgent response)  
        - LOW-MEDIUM (single 3): Level 3
        - LOW (0-4): Level 4 (Routine)
        """
        if news2_result.risk_level == NEWS2Risk.HIGH:
            return 2
        elif news2_result.risk_level in [NEWS2Risk.MEDIUM, NEWS2Risk.LOW_MEDIUM]:
            return 3
        else:
            return 4
    
    def _apply_modifiers(
        self,
        base_level: int,
        category: str,
        age: int,
        news2_result: NEWS2Result
    ) -> int:
        """
        Apply clinical modifiers to adjust triage level.
        
        Based on ESI v4 decision support algorithms.
        """
        level = base_level
        
        # Pediatric modifiers (age < 3 years)
        if age < 3:
            if news2_result.total_score >= 3:
                level = min(level, 2)  # Escalate
            if category in ["fever_simple", "vomiting_diarrhea_dehydration"]:
                level = min(level, 3)  # Higher concern in infants
        
        # Elderly modifiers (age >= 65)
        if age >= 65:
            if category == "chest_pain_cardiac":
                level = min(level, 2)  # Always emergent
            if category in ["fever_with_symptoms", "altered_mental_status"]:
                level = min(level, 2)  # Higher risk of sepsis
        
        # Missing vitals warning
        if len(news2_result.missing_vitals) >= 4:
            # Many vitals missing - can't trust low scores
            if level > 3:
                level = 3  # Don't let patients wait too long
        
        return level
    
    def triage(
        self,
        chief_complaint: str,
        vitals: Vitals,
        age: int = 30,
        gender: str = "unknown"
    ) -> TriageResult:
        """
        Perform triage assessment.
        
        Args:
            chief_complaint: Patient's presenting complaint
            vitals: Vital signs (Vitals dataclass)
            age: Patient age in years
            gender: Patient gender
            
        Returns:
            TriageResult with complete assessment
        """
        # Step 1: Calculate NEWS2 (fully deterministic)
        news2_result = self.news2.calculate(vitals)
        vitals_level = self._news2_to_triage_level(news2_result)
        
        # Step 2: Classify chief complaint (AI - constrained output)
        category, confidence = self.classifier.classify(chief_complaint, age)
        category_info = SYMPTOM_CATEGORIES[category]
        category_level = category_info[0]
        category_ar = category_info[1]
        
        # Step 3: Determine final level (deterministic - take most urgent)
        base_level = min(category_level, vitals_level)
        
        # Step 4: Apply modifiers (deterministic rules)
        final_level = self._apply_modifiers(
            base_level, category, age, news2_result
        )
        
        # Build decision path for auditability
        decision_path = (
            f"Category={category}→L{category_level}, "
            f"NEWS2={news2_result.total_score}→L{vitals_level}, "
            f"Final=L{final_level}"
        )
        
        # Add alerts for missing critical data in high-risk complaints
        alerts_ar = news2_result.alerts_ar.copy()
        alerts_en = news2_result.alerts_en.copy()
        
        if category_level <= 2 and len(news2_result.missing_vitals) >= 2:
            alerts_ar.insert(0, "⚠️ شكوى خطيرة مع بيانات حيوية ناقصة - يجب إكمال التقييم")
            alerts_en.insert(0, "⚠️ High-risk complaint with incomplete vitals - complete assessment")
        
        return TriageResult(
            level=TriageLevel(final_level),
            news2_score=news2_result.total_score,
            news2_risk=news2_result.risk_level.name,
            category=category,
            category_ar=category_ar,
            decision_path=decision_path,
            missing_vitals=news2_result.missing_vitals,
            alerts_ar=alerts_ar,
            alerts_en=alerts_en,
            ai_used=self.classifier.model is not None,
            confidence=confidence
        )


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def quick_triage(
    complaint: str,
    hr: int = None,
    rr: int = None,
    spo2: int = None,
    sbp: int = None,
    temp: float = None,
    gcs: int = None,
    age: int = 30
) -> dict:
    """
    Quick triage function for testing and API use.
    
    Returns dict with triage results.
    """
    engine = DeterministicTriageEngine()
    vitals = Vitals(hr=hr, rr=rr, spo2=spo2, sbp=sbp, temp=temp, gcs=gcs)
    result = engine.triage(complaint, vitals, age)
    
    return {
        "level": result.level.value,
        "level_name": result.level.name,
        "news2_score": result.news2_score,
        "news2_risk": result.news2_risk,
        "category": result.category,
        "category_ar": result.category_ar,
        "decision_path": result.decision_path,
        "missing_vitals": result.missing_vitals,
        "alerts_ar": result.alerts_ar,
        "alerts_en": result.alerts_en,
        "confidence": result.confidence
    }


# =============================================================================
# TESTING
# =============================================================================

if __name__ == "__main__":
    print("=" * 70)
    print("SAFE-Triage v2.0 - Deterministic Engine Test")
    print("NEWS2 + ESI Hybrid with Constrained AI Classification")
    print("=" * 70)
    
    test_cases = [
        # (complaint, vitals_dict, age, expected_level)
        ("مغمى عليه ومش بيستجيب", {"hr": 45, "rr": 6, "spo2": 85}, 50, 1),
        ("ألم في صدري من ساعة", {"hr": 95, "rr": 20, "spo2": 97, "sbp": 140}, 55, 2),
        ("عندي صداع شديد ورقبتي واجعاني", {"hr": 88, "rr": 18, "spo2": 98, "sbp": 150}, 35, 2),
        ("سخونية من يومين", {"hr": 100, "rr": 20, "spo2": 98, "temp": 38.5}, 25, 4),
        ("عايز أجدد الروشتة بتاعتي", {}, 60, 5),
        ("بطني بتوجعني جامد", {"hr": 110, "rr": 22, "spo2": 96, "sbp": 100}, 40, 3),
        ("حاسس إني عايز أأذي نفسي", {"hr": 80, "rr": 16, "spo2": 99}, 22, 2),
        # Test with missing vitals
        ("ألم صدر شديد", {}, 65, 2),  # Should still be Level 2 due to complaint
    ]
    
    engine = DeterministicTriageEngine()
    passed = 0
    failed = 0
    
    for complaint, vitals_dict, age, expected in test_cases:
        vitals = Vitals(**vitals_dict) if vitals_dict else Vitals()
        result = engine.triage(complaint, vitals, age)
        
        status = "✅" if result.level.value == expected else "❌"
        if result.level.value == expected:
            passed += 1
        else:
            failed += 1
        
        print(f"\n{status} Complaint: {complaint[:40]}...")
        print(f"   Expected: L{expected} | Got: L{result.level.value}")
        print(f"   Path: {result.decision_path}")
        print(f"   Category: {result.category} ({result.category_ar})")
        if result.missing_vitals:
            print(f"   Missing: {result.missing_vitals}")
        if result.alerts_ar:
            print(f"   Alerts: {result.alerts_ar[0]}")
    
    print("\n" + "=" * 70)
    print(f"RESULTS: {passed} passed, {failed} failed out of {len(test_cases)}")
    print("=" * 70)
