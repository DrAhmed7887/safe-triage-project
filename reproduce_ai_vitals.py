
import os
import json
import re
from backend.ai_service import AIService
from backend.models import PatientInput, Gender, Vitals

# Initialize AI Service
service = AIService()

def run_test_case(name, vitals_dict):
    print(f"\n--- Testing: {name} ---")
    print(f"Input Vitals: {vitals_dict}")
    
    patient_data = {
        "age": 30,
        "gender": Gender.MALE,
        "chief_complaint_text": "Feeling dizzy and weak",
        "vitals": vitals_dict
    }

    try:
        response = service.analyze_triage(patient_data)
        reasoning = response.get("reasoning", "")
        print(f"AI Reasoning: {reasoning}")
        
        # Check for forbidden patterns
        forbidden_patterns = [
            r"vitals.*normal",
            r"assuming.*\d+", 
            r"likely.*\d+",
            r"signs.*stable" # sometimes AI says "vital signs appear stable" when none are present
        ]
        
        failures = []
        for pattern in forbidden_patterns:
            if re.search(pattern, reasoning, re.IGNORECASE):
                # Check if it's a false positive (e.g. "vitals are NOT normal")
                # But here we are checking for HALLUCINATIONS where it says things are normal/stable despite missing data
                failures.append(pattern)
                
        if failures:
             print(f"❌ FAILED: Detected assumption patterns: {failures}")
        else:
             print("✅ PASSED: No obvious assumption patterns detected.")

    except Exception as e:
        print(f"❌ ERROR: {e}")

if __name__ == "__main__":
    if not service.model:
        print("Skipping test - No API Key")
        exit(0)

    # Test Cases
    test_cases = [
        # Baseline - All vitals present
        ("All Vitals Present", {"hr": 80, "rr": 16, "sbp": 120, "dbp": 80, "spo2": 98, "temp": 37.0}),
        
        # Single missing vital
        ("Missing BP", {"hr": 80, "rr": 16, "spo2": 98, "temp": 37.0}),
        
        # Multiple missing
        ("Missing HR & BP", {"rr": 16, "spo2": 98, "temp": 37.0}),
        
        # All Vitals Missing
        ("All Vitals Missing", {})
    ]

    for name, v_dict in test_cases:
        run_test_case(name, v_dict)
