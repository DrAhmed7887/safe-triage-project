"""
MedGemma QA Agent - Asynchronous triage quality assurance.
Implements "Chief Resident" pattern from SAFE-Triage architecture.
"""

class QAAgent:
    """Quality Assurance Agent for triage review."""
    
    def __init__(self):
        self.high_risk_patterns = [
            {"condition": "diabetes", "complaint": "GI", "age_over": 50, "alert": "Silent MI risk"},
            {"condition": "diabetes", "complaint": "fatigue", "age_over": 50, "alert": "Silent MI risk"},
            {"condition": "hypertension", "complaint": "headache", "severity": "severe", "alert": "Stroke risk"},
        ]
        print("🔬 QA Agent initialized")
    
    def review_triage(self, triage_result: dict, patient: dict) -> dict:
        """
        Review triage decision for potential undertriage.
        
        Args:
            triage_result: {esi_level, news2_score, extracted_features}
            patient: {age, gender, comorbidities, chief_complaint}
        
        Returns:
            {flagged: bool, alert_type: str, reason: str, recommended_esi: int}
        """
        flags = []
        
        # Check high-risk patterns
        for pattern in self.high_risk_patterns:
            if self._matches_pattern(patient, pattern):
                flags.append(pattern["alert"])
        
        # Check ESI 4/5 with concerning vitals
        if triage_result.get("esi_level", 5) >= 4:
            news2 = triage_result.get("news2_score", 0)
            if news2 >= 3:
                flags.append(f"ESI {triage_result['esi_level']} with NEWS2={news2}")
        
        if flags:
            return {
                "flagged": True,
                "alert_type": "UNDERTRIAGE_CONCERN",
                "reason": "; ".join(flags),
                "recommended_esi": max(1, triage_result.get("esi_level", 3) - 1)
            }
        
        return {"flagged": False, "alert_type": None, "reason": None, "recommended_esi": None}
    
    def _matches_pattern(self, patient: dict, pattern: dict) -> bool:
        """Check if patient matches a high-risk pattern."""
        comorbidities = patient.get("comorbidities", [])
        complaint = patient.get("chief_complaint", "").lower()
        age = patient.get("age", 0)
        
        condition_match = pattern.get("condition", "").lower() in [c.lower() for c in comorbidities]
        complaint_match = pattern.get("complaint", "").lower() in complaint
        age_match = age >= pattern.get("age_over", 0) if "age_over" in pattern else True
        
        return condition_match and complaint_match and age_match


# Singleton instance
qa_agent = QAAgent()
