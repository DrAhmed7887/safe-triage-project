"""
SAFE-Triage AI - Triage Engine
Based on ESI (Emergency Severity Index) v5
Vital signs thresholds follow international standards (used in Egyptian hospitals)
"""
from ..models import PatientInput, TriageResult, TriageLevel, Vitals
from ..nlp.processor import NLPProcessor
from typing import List, Tuple

class TriageEngine:
    """
    ESI-based Triage Engine with Egyptian NLP support
    
    Vital Signs Reference (International/Egyptian Standards):
    =========================================================
    ADULTS (>14 years):
        Heart Rate:     Normal 60-100 bpm
                        Critical: <40 or >150 bpm (Level 1)
                        Abnormal: <50 or >100 bpm (Level 2)
        
        Respiratory Rate: Normal 12-20/min
                        Critical: <8 or >36/min (Level 1)
                        Abnormal: <10 or >24/min (Level 2)
        
        SpO2:           Normal ≥95%
                        Critical: <90% (Level 1)
                        Abnormal: 90-94% (Level 2)
        
        Blood Pressure: Normal 90-140/60-90 mmHg
                        Critical: SBP <80 or >220 mmHg (Level 1)
                        Abnormal: SBP <90 or >180 mmHg (Level 2)
        
        Temperature:    Normal 36.5-37.5°C (97.7-99.5°F)
                        High Fever: >39°C (102.2°F)
                        Hypothermia: <35°C (95°F)
        
        GCS:            Normal 15
                        Critical: <9 (Level 1 - Comatose)
                        Abnormal: 9-14 (Level 2 - Altered)
    
    PEDIATRICS (age-based):
        See _check_pediatric_vitals method for age-specific ranges
    """
    
    def __init__(self):
        self.nlp = NLPProcessor()
        
    def _check_critical_vitals(self, age: int, vitals: Vitals) -> Tuple[bool, List[str]]:
        """
        Check for immediately life-threatening vital signs (Level 1).
        Returns (is_critical, list of reasons)
        
        These thresholds indicate IMMEDIATE need for resuscitation.
        """
        reasons = []
        
        # ===== RESPIRATORY RATE - CRITICAL =====
        if vitals.rr is not None:
            if age >= 14:  # Adult
                if vitals.rr < 8:
                    reasons.append(f"معدل التنفس خطير / Critical RR: {vitals.rr}/min (< 8 = respiratory failure)")
                elif vitals.rr > 36:
                    reasons.append(f"معدل التنفس خطير / Critical RR: {vitals.rr}/min (> 36 = severe respiratory distress)")
            else:  # Pediatric
                if vitals.rr < 10:
                    reasons.append(f"معدل التنفس خطير للطفل / Critical pediatric RR: {vitals.rr}/min")
                elif age < 1 and vitals.rr > 60:
                    reasons.append(f"معدل التنفس خطير للرضيع / Critical infant RR: {vitals.rr}/min (> 60)")
                elif age < 5 and vitals.rr > 50:
                    reasons.append(f"معدل التنفس خطير للطفل / Critical child RR: {vitals.rr}/min (> 50)")
        
        # ===== HEART RATE - CRITICAL =====
        if vitals.hr is not None:
            if age >= 14:  # Adult
                if vitals.hr < 40:
                    reasons.append(f"النبض خطير / Critical HR: {vitals.hr}/min (< 40 = severe bradycardia)")
                elif vitals.hr > 150:
                    reasons.append(f"النبض خطير / Critical HR: {vitals.hr}/min (> 150 = unstable tachycardia)")
            else:  # Pediatric
                if vitals.hr < 60:
                    reasons.append(f"النبض خطير للطفل / Critical pediatric HR: {vitals.hr}/min (< 60)")
                elif age < 1 and vitals.hr > 180:
                    reasons.append(f"النبض خطير للرضيع / Critical infant HR: {vitals.hr}/min (> 180)")
                elif age < 5 and vitals.hr > 160:
                    reasons.append(f"النبض خطير للطفل / Critical child HR: {vitals.hr}/min (> 160)")
        
        # ===== SpO2 - CRITICAL =====
        if vitals.spo2 is not None and vitals.spo2 < 90:
            reasons.append(f"نسبة الأكسجين خطيرة / Critical SpO2: {vitals.spo2}% (< 90% = severe hypoxia)")
        
        # ===== GCS - CRITICAL =====
        if vitals.gcs is not None and vitals.gcs < 9:
            reasons.append(f"مستوى الوعي خطير / Critical GCS: {vitals.gcs} (< 9 = coma)")
        
        # ===== BLOOD PRESSURE - CRITICAL =====
        if vitals.sbp is not None:
            if vitals.sbp < 80:
                reasons.append(f"ضغط الدم خطير / Critical BP: {vitals.sbp} (< 80 = shock)")
            elif vitals.sbp > 220:
                reasons.append(f"ضغط الدم خطير / Critical BP: {vitals.sbp} (> 220 = hypertensive crisis)")
        
        # ===== TEMPERATURE - CRITICAL =====
        if vitals.temp is not None:
            if vitals.temp < 35:
                reasons.append(f"درجة الحرارة خطيرة / Critical Temp: {vitals.temp}°C (< 35 = hypothermia)")
            elif vitals.temp > 41:
                reasons.append(f"درجة الحرارة خطيرة / Critical Temp: {vitals.temp}°C (> 41 = hyperpyrexia)")
        
        return (len(reasons) > 0, reasons)
        
    def _check_vitals_danger_zone(self, age: int, vitals: Vitals) -> Tuple[bool, List[str]]:
        """
        Check if vitals are in the danger zone (Level 2).
        Not immediately life-threatening but require urgent attention.
        """
        reasons = []
        
        if age >= 14:  # Adults
            # Heart Rate
            if vitals.hr is not None:
                if vitals.hr > 100:
                    reasons.append(f"تسارع النبض: {vitals.hr}/دقيقة")
                elif vitals.hr < 50:
                    reasons.append(f"بطء النبض: {vitals.hr}/دقيقة")
            
            # Respiratory Rate
            if vitals.rr is not None:
                if vitals.rr > 24:
                    reasons.append(f"سرعة التنفس: {vitals.rr}/دقيقة")
                elif vitals.rr < 10:
                    reasons.append(f"بطء التنفس: {vitals.rr}/دقيقة")
            
            # SpO2
            if vitals.spo2 is not None and 90 <= vitals.spo2 < 94:
                reasons.append(f"نقص الأكسجين: {vitals.spo2}%")
            
            # Blood Pressure
            if vitals.sbp is not None:
                if vitals.sbp > 180:
                    reasons.append(f"ارتفاع الضغط: {vitals.sbp}")
                elif vitals.sbp < 90:
                    reasons.append(f"انخفاض الضغط: {vitals.sbp}")
            
            # Temperature
            if vitals.temp is not None:
                if vitals.temp > 39:
                    reasons.append(f"حمى عالية: {vitals.temp}°C")
                elif vitals.temp < 36:
                    reasons.append(f"انخفاض حرارة: {vitals.temp}°C")
                    
        else:  # Pediatric
            # Simplified pediatric danger zone
            if vitals.hr is not None:
                if age < 1 and vitals.hr > 160:
                    reasons.append(f"تسارع نبض الرضيع: {vitals.hr}")
                elif age < 5 and vitals.hr > 140:
                    reasons.append(f"تسارع نبض الطفل: {vitals.hr}")
            
            if vitals.rr is not None:
                if age < 1 and vitals.rr > 50:
                    reasons.append(f"سرعة تنفس الرضيع: {vitals.rr}")
                elif age < 5 and vitals.rr > 40:
                    reasons.append(f"سرعة تنفس الطفل: {vitals.rr}")
            
            if vitals.spo2 is not None and vitals.spo2 < 94:
                reasons.append(f"نقص أكسجين الطفل: {vitals.spo2}%")
            
            if vitals.temp is not None and vitals.temp > 39:
                reasons.append(f"حمى الطفل: {vitals.temp}°C")
        
        return (len(reasons) > 0, reasons)

    def _calculate_resources(self, patient: PatientInput, symptoms: List[str]) -> int:
        """
        Estimate resources needed based on complaint and vitals.
        Resources: Labs, ECG, X-Ray, CT/MRI, IV Fluids, IV Meds, Consult
        """
        resources = 0
        
        if "abdominal" in symptoms:
            resources += 2  # Labs + possible imaging
        
        if "chest_pain" in symptoms or "cardiac" in symptoms:
            resources += 2  # ECG + Labs/Troponin
            
        if "sob" in symptoms:
            resources += 2  # CXR + Labs/ABG
            
        if "trauma" in symptoms:
            resources += 2  # X-ray + possible labs
        
        if "stroke" in symptoms:
            resources += 2  # CT + Labs
            
        if "fever" in symptoms:
            resources += 1  # Labs
            
        if "laceration" in symptoms:
            resources += 1  # Suture supplies

        if "allergy" in symptoms:
            resources += 1  # IV/IM Meds
        
        if "uti" in symptoms:
            resources += 1  # UA + possible culture
        
        if "burn" in symptoms:
            resources += 1  # Wound care
            
        if "bite_sting" in symptoms:
            resources += 1  # Possible antivenom/antibiotics
            
        return resources

    def evaluate(self, patient: PatientInput) -> TriageResult:
        """
        Main triage evaluation following ESI v5 algorithm
        """
        reasoning = []
        red_flags = []
        
        # NLP Analysis
        symptoms = self.nlp.extract_symptoms(patient.chief_complaint_text)
        danger_keywords = self.nlp.detect_danger_keywords(patient.chief_complaint_text)
        
        # ===== LEVEL 1 - RESUSCITATION =====
        # Immediate life-saving intervention required
        is_level_1 = False
        
        # Check critical vital signs FIRST
        vitals_critical, vitals_reasons = self._check_critical_vitals(patient.age, patient.vitals)
        if vitals_critical:
            is_level_1 = True
            reasoning.extend(vitals_reasons)
            red_flags.extend(vitals_reasons)

        # Check danger keywords (unconscious, unresponsive, etc.)
        if danger_keywords:
            is_level_1 = True
            keywords_str = ', '.join(danger_keywords[:3])  # Limit to 3 for display
            reasoning.append(f"كلمات حرجة / Critical keywords: {keywords_str}")
            red_flags.append(f"حالة حرجة / Critical condition: {keywords_str}")

        if is_level_1:
            return TriageResult(
                level=TriageLevel.RESUSCITATION,
                color_code="#ef4444",
                label_ar="إنعاش (مستوى ١)",
                label_en="Resuscitation (Level 1)",
                description="يتطلب تدخل فوري لإنقاذ الحياة / Requires immediate life-saving intervention",
                recommended_action="تفعيل فريق الإنعاش فوراً / Activate resuscitation team immediately",
                time_to_physician="فوري / Immediate",
                red_flags=red_flags,
                reasoning=reasoning
            )

        # ===== LEVEL 2 - EMERGENT =====
        # High risk, potential for rapid deterioration
        is_level_2 = False
        
        # Severe Pain
        if patient.vitals.pain_score and patient.vitals.pain_score >= 7:
            is_level_2 = True
            reasoning.append(f"ألم شديد / Severe pain: {patient.vitals.pain_score}/10")
            
        # Altered mental status (GCS 9-14)
        if patient.vitals.gcs and 9 <= patient.vitals.gcs < 15:
            is_level_2 = True
            reasoning.append(f"تغير في الوعي / Altered consciousness: GCS {patient.vitals.gcs}")
            
        # Danger Zone Vitals
        danger_zone, danger_reasons = self._check_vitals_danger_zone(patient.age, patient.vitals)
        if danger_zone:
            is_level_2 = True
            reasoning.extend(danger_reasons)
            red_flags.append("علامات حيوية غير طبيعية / Abnormal vital signs")
            
        # High Risk Symptoms
        high_risk_triggers = []
        if "chest_pain" in symptoms: high_risk_triggers.append("ألم صدر / Chest pain")
        if "stroke" in symptoms: high_risk_triggers.append("أعراض جلطة / Stroke symptoms")
        if "psych" in symptoms: high_risk_triggers.append("طوارئ نفسية / Psychiatric emergency")
        if "sob" in symptoms: high_risk_triggers.append("ضيق تنفس / Shortness of breath")
        if "cardiac" in symptoms: high_risk_triggers.append("مشكلة قلبية / Cardiac problem")
        if "diabetic" in symptoms: high_risk_triggers.append("مشكلة سكري / Diabetic problem")
        if "pregnancy" in symptoms: high_risk_triggers.append("حالة حمل / Pregnancy")
        
        if high_risk_triggers:
            is_level_2 = True
            reasoning.append(f"أعراض خطيرة / High-risk symptoms: {', '.join(high_risk_triggers)}")

        if is_level_2:
            return TriageResult(
                level=TriageLevel.EMERGENT,
                color_code="#f97316",
                label_ar="طوارئ (مستوى ٢)",
                label_en="Emergent (Level 2)",
                description="خطورة عالية، احتمال تدهور سريع / High risk, potential for rapid deterioration",
                recommended_action="غرفة العناية المركزة، مراقبة مستمرة / ICU room, continuous monitoring",
                time_to_physician="< 15 دقيقة / < 15 minutes",
                red_flags=red_flags,
                reasoning=reasoning
            )

        # ===== LEVEL 3, 4, 5 - RESOURCE BASED =====
        resource_count = self._calculate_resources(patient, symptoms)
        
        if resource_count >= 2:
            return TriageResult(
                level=TriageLevel.URGENT,
                color_code="#eab308",
                label_ar="عاجل (مستوى ٣)",
                label_en="Urgent (Level 3)",
                description="مستقر، يحتاج موارد متعددة / Stable, needs multiple resources",
                recommended_action="غرفة فحص، طلب تحاليل/أشعة / Exam room, order labs/imaging",
                time_to_physician="< 60 دقيقة / < 60 minutes",
                red_flags=red_flags,
                reasoning=[f"يحتاج تقريباً {resource_count} موارد / Needs approximately {resource_count} resources"]  
            )
            
        elif resource_count == 1:
            return TriageResult(
                level=TriageLevel.LESS_URGENT,
                color_code="#22c55e",
                label_ar="أقل إلحاحاً (مستوى ٤)",
                label_en="Less Urgent (Level 4)",
                description="مستقر، يحتاج مورد واحد / Stable, needs one resource",
                recommended_action="العيادة السريعة / Fast-track clinic",
                time_to_physician="يمكن الانتظار / Can wait",
                red_flags=red_flags,
                reasoning=["يحتاج مورد واحد فقط / Needs only 1 resource"]
            )
            
        else:
            return TriageResult(
                level=TriageLevel.NON_URGENT,
                color_code="#3b82f6",
                label_ar="غير عاجل (مستوى ٥)",
                label_en="Non-Urgent (Level 5)",
                description="لا يحتاج موارد / No resources needed",
                recommended_action="إعادة الروشتة أو الطمأنينة / Prescription refill or reassurance",
                time_to_physician="يمكن الانتظار / تحويل للعيادة / Can wait / Clinic referral",
                red_flags=red_flags,
                reasoning=["لا يحتاج موارد حادة / No acute resources needed"]
            )
