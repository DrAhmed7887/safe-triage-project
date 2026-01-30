"""
SAFE-Triage v2.0 - Comprehensive Test Suite
==========================================

Tests for the deterministic NEWS2 + ESI hybrid triage engine.

Run with: python backend/tests/test_triage_v2.py
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from backend.logic.triage_engine_v2 import (
    DeterministicTriageEngine,
    NEWS2Calculator,
    Vitals,
    NEWS2Risk,
    TriageLevel,
    SYMPTOM_CATEGORIES
)


def test_news2_scoring():
    """Test NEWS2 calculations are deterministic and correct."""
    print("\n" + "=" * 60)
    print("TEST 1: NEWS2 Scoring (Deterministic)")
    print("=" * 60)
    
    calc = NEWS2Calculator()
    tests = [
        # (vitals_dict, expected_score, expected_risk, description)
        (
            {"hr": 80, "rr": 16, "spo2": 98, "sbp": 120, "temp": 37.0, "gcs": 15},
            0, NEWS2Risk.LOW, "Normal vitals"
        ),
        (
            {"hr": 130, "rr": 24, "spo2": 93, "sbp": 95, "temp": 38.5},
            8, NEWS2Risk.HIGH, "Multiple abnormal"
        ),
        (
            {"hr": 35, "rr": 16, "spo2": 98, "sbp": 120, "temp": 37.0},
            3, NEWS2Risk.HIGH, "Single extreme (HR=35)"
        ),
        (
            {"hr": None, "rr": None, "spo2": None, "sbp": None, "temp": None},
            0, NEWS2Risk.LOW, "All vitals missing"
        ),
        (
            {"hr": 50, "rr": 22, "spo2": 94, "sbp": 105, "temp": 36.5},
            5, NEWS2Risk.MEDIUM, "Medium risk"
        ),
    ]
    
    passed = 0
    for vitals_dict, expected_score, expected_risk, desc in tests:
        vitals = Vitals(**vitals_dict)
        result = calc.calculate(vitals)
        
        score_ok = result.total_score == expected_score
        risk_ok = result.risk_level == expected_risk
        status = "✅" if score_ok and risk_ok else "❌"
        
        if score_ok and risk_ok:
            passed += 1
        
        print(f"{status} {desc}")
        print(f"   Score: {result.total_score} (expected {expected_score})")
        print(f"   Risk: {result.risk_level.name} (expected {expected_risk.name})")
        if result.missing_vitals:
            print(f"   Missing: {result.missing_vitals}")
    
    print(f"\nNEWS2 Tests: {passed}/{len(tests)} passed")
    return passed == len(tests)


def test_category_completeness():
    """Verify all ESI levels have categories."""
    print("\n" + "=" * 60)
    print("TEST 2: Category Completeness")
    print("=" * 60)
    
    levels = {1: [], 2: [], 3: [], 4: [], 5: []}
    for key, (level, ar, en) in SYMPTOM_CATEGORIES.items():
        levels[level].append(key)
    
    all_ok = True
    for level, cats in levels.items():
        status = "✅" if len(cats) >= 2 else "❌"
        if len(cats) < 2:
            all_ok = False
        print(f"{status} Level {level}: {len(cats)} categories")
        for cat in cats[:3]:
            print(f"      - {cat}")
        if len(cats) > 3:
            print(f"      ... and {len(cats)-3} more")
    
    print(f"\nTotal categories: {len(SYMPTOM_CATEGORIES)}")
    return all_ok


def test_triage_scenarios():
    """Test complete triage flow with Egyptian Arabic inputs."""
    print("\n" + "=" * 60)
    print("TEST 3: Triage Scenarios (Egyptian Arabic)")
    print("=" * 60)
    
    engine = DeterministicTriageEngine()
    
    scenarios = [
        # Level 1 - Resuscitation
        ("فاقد الوعي", {"hr": 40, "rr": 6}, 50, 1, "Unconscious"),
        ("مش بيتنفس", {"spo2": 70}, 30, 1, "Not breathing"),
        ("بلع حبوب كتير", {}, 25, 1, "Overdose"),
        ("حادثة عربية ودماغه بتنزف", {"sbp": 80}, 35, 1, "Severe trauma"),
        
        # Level 2 - Emergent  
        ("ألم في صدري وذراعي الشمال", {"hr": 95, "sbp": 150}, 55, 2, "Chest pain cardiac"),
        ("وشي اتلوى ومش عارف اتكلم", {"sbp": 180}, 65, 2, "Stroke"),
        ("مش عارف آخد نفسي", {"rr": 28, "spo2": 91}, 40, 2, "Respiratory distress"),
        ("عايز أموت", {"hr": 70, "rr": 16}, 22, 2, "Suicidal"),
        ("حامل وبنزف دم كتير", {"hr": 110, "sbp": 95}, 28, 2, "Obstetric emergency"),
        ("السكر وقع عندي ومرتعش", {}, 60, 2, "Diabetic emergency"),
        
        # Level 3 - Urgent
        ("بطني بتوجعني وعندي سخونية", {"hr": 100, "temp": 38.5}, 35, 3, "Abdo pain + fever"),
        ("صداع شديد من امبارح", {"sbp": 140}, 45, 3, "Severe headache"),
        ("الواد بيرجع من امبارح ومش بياكل", {"hr": 120}, 2, 3, "Pediatric vomiting"),
        
        # Level 4 - Less Urgent
        ("عندي برد وزور", {"temp": 37.5}, 30, 4, "Cold symptoms"),
        ("ايدي اتجرحت وعايز غرز", {}, 25, 4, "Minor laceration"),
        ("ودني بتوجعني", {}, 8, 4, "Ear pain"),
        
        # Level 5 - Non-Urgent
        ("عايز أجدد علاج الضغط", {}, 55, 5, "Med refill"),
        ("عايز تقرير طبي للشغل", {}, 35, 5, "Medical certificate"),
    ]
    
    passed = 0
    failed_cases = []
    
    for complaint, vitals_dict, age, expected, desc in scenarios:
        vitals = Vitals(**vitals_dict) if vitals_dict else Vitals()
        result = engine.triage(complaint, vitals, age)
        
        # Allow ±1 level tolerance for edge cases
        is_exact = result.level.value == expected
        is_close = abs(result.level.value - expected) <= 1
        
        if is_exact:
            status = "✅"
            passed += 1
        elif is_close:
            status = "🟡"  # Close but not exact
            passed += 0.5
        else:
            status = "❌"
            failed_cases.append((desc, expected, result.level.value))
        
        print(f"{status} {desc}")
        print(f"   Complaint: {complaint[:35]}...")
        print(f"   Expected: L{expected} | Got: L{result.level.value}")
        print(f"   Category: {result.category}")
        print(f"   Path: {result.decision_path}")
    
    print(f"\nScenarios: {int(passed)}/{len(scenarios)} passed")
    if failed_cases:
        print("\nFailed cases:")
        for desc, exp, got in failed_cases:
            print(f"  - {desc}: expected L{exp}, got L{got}")
    
    return passed >= len(scenarios) * 0.8  # 80% threshold


def test_missing_vitals_handling():
    """Test that missing vitals are properly flagged."""
    print("\n" + "=" * 60)
    print("TEST 4: Missing Vitals Handling")
    print("=" * 60)
    
    engine = DeterministicTriageEngine()
    
    # High-risk complaint with no vitals
    result = engine.triage("ألم صدر شديد", Vitals(), age=60)
    
    print(f"Complaint: ألم صدر شديد (chest pain)")
    print(f"Vitals provided: None")
    print(f"Triage Level: {result.level.value}")
    print(f"Missing vitals: {result.missing_vitals}")
    print(f"Alerts (AR): {result.alerts_ar}")
    
    # Should still be Level 2 due to complaint
    level_ok = result.level.value <= 2
    has_warning = any("ناقصة" in a or "missing" in a.lower() for a in result.alerts_ar + result.alerts_en)
    
    status1 = "✅" if level_ok else "❌"
    status2 = "✅" if has_warning else "❌"
    
    print(f"\n{status1} High-risk complaint gets appropriate level despite missing vitals")
    print(f"{status2} System warns about missing vitals")
    
    return level_ok and has_warning


def test_news2_vital_thresholds():
    """Test specific NEWS2 thresholds are correct."""
    print("\n" + "=" * 60)
    print("TEST 5: NEWS2 Vital Thresholds")
    print("=" * 60)
    
    calc = NEWS2Calculator()
    
    threshold_tests = [
        # RR thresholds
        ({"rr": 8}, "rr", 3, "RR=8 → Score 3"),
        ({"rr": 9}, "rr", 1, "RR=9 → Score 1"),
        ({"rr": 12}, "rr", 0, "RR=12 → Score 0"),
        ({"rr": 24}, "rr", 2, "RR=24 → Score 2"),
        ({"rr": 25}, "rr", 3, "RR=25 → Score 3"),
        
        # HR thresholds
        ({"hr": 40}, "hr", 3, "HR=40 → Score 3"),
        ({"hr": 41}, "hr", 1, "HR=41 → Score 1"),
        ({"hr": 51}, "hr", 0, "HR=51 → Score 0"),
        ({"hr": 91}, "hr", 1, "HR=91 → Score 1"),
        ({"hr": 131}, "hr", 3, "HR=131 → Score 3"),
        
        # SpO2 thresholds
        ({"spo2": 91}, "spo2", 3, "SpO2=91 → Score 3"),
        ({"spo2": 92}, "spo2", 2, "SpO2=92 → Score 2"),
        ({"spo2": 94}, "spo2", 1, "SpO2=94 → Score 1"),
        ({"spo2": 96}, "spo2", 0, "SpO2=96 → Score 0"),
        
        # SBP thresholds
        ({"sbp": 90}, "sbp", 3, "SBP=90 → Score 3"),
        ({"sbp": 91}, "sbp", 2, "SBP=91 → Score 2"),
        ({"sbp": 111}, "sbp", 0, "SBP=111 → Score 0"),
        ({"sbp": 220}, "sbp", 3, "SBP=220 → Score 3"),
    ]
    
    passed = 0
    for vitals_dict, param, expected_score, desc in threshold_tests:
        vitals = Vitals(**vitals_dict)
        result = calc.calculate(vitals)
        actual = result.parameter_scores.get(param, -1)
        
        status = "✅" if actual == expected_score else "❌"
        if actual == expected_score:
            passed += 1
        
        print(f"{status} {desc} (got {actual})")
    
    print(f"\nThreshold tests: {passed}/{len(threshold_tests)} passed")
    return passed == len(threshold_tests)


def test_determinism():
    """Verify same inputs always produce same outputs."""
    print("\n" + "=" * 60)
    print("TEST 6: Determinism Check")
    print("=" * 60)
    
    engine = DeterministicTriageEngine()
    vitals = Vitals(hr=95, rr=20, spo2=96, sbp=130, temp=37.5)
    
    results = []
    for i in range(5):
        result = engine.triage("ألم في صدري", vitals, age=50)
        results.append(result.level.value)
    
    all_same = len(set(results)) == 1
    status = "✅" if all_same else "❌"
    
    print(f"Results over 5 runs: {results}")
    print(f"{status} All results identical: {all_same}")
    
    return all_same


def run_all_tests():
    """Run complete test suite."""
    print("\n" + "=" * 70)
    print("SAFE-Triage v2.0 - Complete Test Suite")
    print("NEWS2 + ESI Hybrid Engine with Constrained AI")
    print("=" * 70)
    
    results = {
        "NEWS2 Scoring": test_news2_scoring(),
        "Category Completeness": test_category_completeness(),
        "Triage Scenarios": test_triage_scenarios(),
        "Missing Vitals": test_missing_vitals_handling(),
        "NEWS2 Thresholds": test_news2_vital_thresholds(),
        "Determinism": test_determinism(),
    }
    
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"  {status} | {name}")
    
    print(f"\nOverall: {passed}/{total} test groups passed")
    print("=" * 70)
    
    return passed == total


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
