#!/usr/bin/env python3
"""
SAFE-Triage Safety Validation Test Suite
Tests critical safety rules: red flags, NEWS2 override, offline fallback
"""

import sys
import os
sys.path.append(os.path.join(os.getcwd(), 'backend'))

from logic.deterministic_triage import DeterministicTriageEngine
from models import PatientInput, Vitals, Gender
import json

# ANSI colors for terminal output
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
RESET = "\033[0m"

def run_test(engine, name: str, patient: PatientInput, expected_level: int, reason: str):
    """Run a single test case and return pass/fail"""
    result = engine.evaluate(patient)
    passed = int(result.level) == expected_level
    
    # Check for critical under-triage (Level 1-2 triaged as 3-5)
    critical_undertriage = expected_level <= 2 and int(result.level) > expected_level
    
    if passed:
        print(f"{GREEN}✅ PASS{RESET}: {name}")
        print(f"   Expected: L{expected_level} | Got: L{int(result.level)} | Label: {result.label_en}")
    elif critical_undertriage:
        print(f"{RED}🚨 CRITICAL UNDER-TRIAGE{RESET}: {name}")
        print(f"   Expected: L{expected_level} | Got: L{int(result.level)} | Label: {result.label_en}")
        print(f"   Reason: {reason}")
    else:
        print(f"{YELLOW}⚠️ MISMATCH{RESET}: {name}")
        print(f"   Expected: L{expected_level} | Got: L{int(result.level)} | Label: {result.label_en}")
    
    return passed, critical_undertriage

def main():
    print("=" * 60)
    print("SAFE-Triage Safety Validation Test Suite")
    print("=" * 60)
    
    # Initialize engine WITHOUT AI (deterministic only)
    engine = DeterministicTriageEngine(use_ai=False)
    
    test_cases = [
        # ===== RED FLAG COMBINATIONS (Must escalate to Level 2) =====
        {
            "name": "Pregnancy + Abdominal Pain → Ectopic Risk",
            "patient": PatientInput(
                age=28,
                gender=Gender.FEMALE,
                chief_complaint_text="بطني بتوجعني من امبارح وبرجع",
                vitals=Vitals(temp=38.2),
                is_pregnant=True
            ),
            "expected": 2,
            "reason": "Abdominal pain in pregnant female = ectopic until proven otherwise"
        },
        {
            "name": "Chest Pain + Age >35 → Cardiac Risk",
            "patient": PatientInput(
                age=55,
                gender=Gender.MALE,
                chief_complaint_text="صدري بيوجعني",
                vitals=Vitals()  # No vitals recorded
            ),
            "expected": 2,
            "reason": "Chest pain + age >35 = cardiac until proven otherwise"
        },
        {
            "name": "Headache + Fever + Neck Stiffness → Meningitis Risk",
            "patient": PatientInput(
                age=22,
                gender=Gender.MALE,
                chief_complaint_text="راسي بتوجعني جامد وعندي سخونية ورقبتي واجعاني",
                vitals=Vitals(temp=39.5, hr=110)
            ),
            "expected": 2,
            "reason": "Classic meningitis triad"
        },
        
        # ===== NEWS2 OVERRIDE (Vitals alone escalate) =====
        {
            "name": "Critical Vitals → Level 1 Override",
            "patient": PatientInput(
                age=45,
                gender=Gender.MALE,
                chief_complaint_text="مش حاسس بحاجة",  # Vague complaint
                vitals=Vitals(hr=45, sbp=85, spo2=87, rr=28)
            ),
            "expected": 1,
            "reason": "NEWS2 ≥7 with multiple 3-point parameters"
        },
        {
            "name": "Altered Consciousness (AVPU=V) → Level 2",
            "patient": PatientInput(
                age=70,
                gender=Gender.FEMALE,
                chief_complaint_text="مش عارفة مكانها",
                vitals=Vitals(hr=88, sbp=140, avpu="V")
            ),
            "expected": 2,
            "reason": "AVPU ≠ A triggers immediate escalation"
        },
        
        # ===== LEVEL 1 CRITICAL KEYWORDS =====
        {
            "name": "Poisoning - Bleach Ingestion",
            "patient": PatientInput(
                age=3,
                gender=Gender.MALE,
                chief_complaint_text="ابني شرب كلوركس",
                vitals=Vitals()
            ),
            "expected": 1,
            "reason": "Poisoning = immediate life threat"
        },
        {
            "name": "Cardiac Arrest - Pulseless",
            "patient": PatientInput(
                age=60,
                gender=Gender.MALE,
                chief_complaint_text="مفيش نبض وقلبه واقف",
                vitals=Vitals()
            ),
            "expected": 1,
            "reason": "Cardiac arrest = immediate resuscitation"
        },
        {
            "name": "Severe Bleeding",
            "patient": PatientInput(
                age=35,
                gender=Gender.FEMALE,
                chief_complaint_text="بتنزف بشدة والدم مش بيوقف",
                vitals=Vitals(hr=120, sbp=90)
            ),
            "expected": 1,
            "reason": "Hemorrhagic shock risk"
        },
        
        # ===== LEVEL 5 NON-URGENT (Should NOT escalate) =====
        {
            "name": "Prescription Refill - Stable Vitals",
            "patient": PatientInput(
                age=45,
                gender=Gender.MALE,
                chief_complaint_text="عايز أجدد الروشتة بتاعتي",
                vitals=Vitals(hr=72, sbp=120, dbp=80, spo2=98, temp=36.8, rr=14, avpu="A")
            ),
            "expected": 5,
            "reason": "No resources needed, stable vitals"
        },
        {
            "name": "Suture Removal",
            "patient": PatientInput(
                age=30,
                gender=Gender.MALE,
                chief_complaint_text="عايز أفك الغرز",
                vitals=Vitals(hr=75, sbp=118, spo2=99, avpu="A")
            ),
            "expected": 5,
            "reason": "Scheduled procedure, no emergency"
        },
        
        # ===== AMBIGUOUS COMPLAINTS (Default to Level 3) =====
        {
            "name": "Vague Complaint - No Keywords Match",
            "patient": PatientInput(
                age=40,
                gender=Gender.FEMALE,
                chief_complaint_text="حاسة بحاجة غريبة مش عارفة أوصفها",
                vitals=Vitals()
            ),
            "expected": 3,
            "reason": "Ambiguous → Default to 'unclear' (Level 3)"
        },
        
        # ===== EGYPTIAN DIALECT VARIATIONS =====
        {
            "name": "Egyptian Dialect - Stroke",
            "patient": PatientInput(
                age=65,
                gender=Gender.MALE,
                chief_complaint_text="وشه مال ومش قادر يتكلم",
                vitals=Vitals(sbp=180, hr=90)
            ),
            "expected": 2,
            "reason": "Facial droop + speech difficulty = stroke"
        },
        {
            "name": "Egyptian Dialect - Diabetic Emergency",
            "patient": PatientInput(
                age=50,
                gender=Gender.FEMALE,
                chief_complaint_text="السكر واطي جداً وبترعش",
                vitals=Vitals(hr=100, sbp=100)
            ),
            "expected": 2,
            "reason": "Hypoglycemia with symptoms"
        },
    ]
    
    # Run all tests
    passed = 0
    failed = 0
    critical = 0
    
    print("\n" + "-" * 60)
    for tc in test_cases:
        p, c = run_test(engine, tc["name"], tc["patient"], tc["expected"], tc["reason"])
        actual_level = int(engine.evaluate(tc["patient"]).level)
        if p:
            passed += 1
        else:
            failed += 1
            if c:
                critical += 1
        print("-" * 60)
    
    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Total Tests: {len(test_cases)}")
    print(f"{GREEN}Passed: {passed}{RESET}")
    print(f"{YELLOW}Failed: {failed}{RESET}")
    print(f"{RED}Critical Under-triage: {critical}{RESET}")
    
    if critical > 0:
        print(f"\n{RED}⚠️  CRITICAL: {critical} cases of under-triage detected!{RESET}")
        print("These MUST be fixed before production deployment.")
        sys.exit(1)
    elif failed > 0:
        print(f"\n{YELLOW}⚠️  Some tests failed but no critical under-triage.{RESET}")
        sys.exit(0)
    else:
        print(f"\n{GREEN}✅ All safety tests passed!{RESET}")
        sys.exit(0)

if __name__ == "__main__":
    main()
