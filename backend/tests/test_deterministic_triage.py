"""
SAFE-Triage - Comprehensive Test Suite for Deterministic Hybrid Engine
=======================================================================

Tests for NEWS2 + ESI hybrid triage system.

References:
- NEWS2: Royal College of Physicians, 2017
- ESI v4: AHRQ/Gilboy et al., 2011
"""

from backend.logic.deterministic_triage import (
    DeterministicTriageEngine,
    NEWS2Calculator,
    SYMPTOM_CATEGORIES
)
from backend.models import Vitals


def test_news2_scoring():
    """Test NEWS2 vital sign scoring against RCP thresholds"""
    print("\n" + "=" * 70)
    print("NEWS2 SCORING TESTS")
    print("=" * 70)
    
    calc = NEWS2Calculator()
    
    test_cases = [
        # (vitals_dict, expected_score, expected_level, description)
        ({"hr": 75, "rr": 16, "spo2": 98, "sbp": 120, "temp": 37.0, "gcs": 15}, 0, 5, "Normal vitals"),
        ({"hr": 135, "rr": 26, "spo2": 92, "sbp": 85, "temp": 39.5, "gcs": 15}, 13, 2, "Multiple abnormal"),
        ({"hr": 35}, 3, 2, "Extreme bradycardia (single 3)"),
        ({"spo2": 88}, 3, 2, "Severe hypoxia"),
        ({"sbp": 85}, 3, 2, "Hypotension"),
        ({"gcs": 6}, 3, 2, "Unresponsive"),
        ({}, 0, 5, "All vitals missing"),
    ]
    
    passed = 0
    for vitals, expected_score, expected_level, desc in test_cases:
        class V:
            def __init__(self, d):
                self.hr = d.get('hr')
                self.rr = d.get('rr')
                self.spo2 = d.get('spo2')
                self.sbp = d.get('sbp')
                self.temp = d.get('temp')
                self.gcs = d.get('gcs', 15) if 'gcs' in d else None
        
        result = calc.calculate(V(vitals))
        status = "✅" if result.total_score == expected_score else "❌"
        if result.total_score == expected_score:
            passed += 1
        print(f"{status} {desc}: Score={result.total_score} (expected {expected_score}), Level={result.triage_level}")
    
    print(f"\nNEWS2 Tests: {passed}/{len(test_cases)} passed")
    return passed == len(test_cases)


def test_deterministic_triage_levels():
    """Test full triage engine across all ESI levels"""
    print("\n" + "=" * 70)
    print("DETERMINISTIC TRIAGE ENGINE TESTS")
    print("Reference: ESI v4 (AHRQ 2011)")
    print("=" * 70)
    
    engine = DeterministicTriageEngine()
    
    test_cases = [
        # LEVEL 1 - Resuscitation
        {"name": "فاقد الوعي (Unconscious)", "complaint": "فاقد الوعي", "expected": 1},
        {"name": "Cardiac arrest", "complaint": "قلبه وقف", "expected": 1},
        {"name": "Not breathing", "complaint": "مش بيتنفس", "expected": 1},
        {"name": "Active seizure", "complaint": "عنده تشنجات", "expected": 1},
        {"name": "Gunshot wound", "complaint": "إصابة رصاص", "expected": 1},
        {"name": "Stab wound", "complaint": "طعن في البطن", "expected": 1},
        {"name": "Choking", "complaint": "شرقان ومش قادر ياخد نفسه", "expected": 1},
        {"name": "Overdose", "complaint": "جرعة زيادة من الدوا", "expected": 1},
        {"name": "Anaphylaxis", "complaint": "حساسية شديدة وورم", "expected": 1},
        {"name": "Severe bleeding", "complaint": "بينزف جامد ومش بيوقف", "expected": 1},
        
        # LEVEL 2 - Emergent
        {"name": "Chest pain (cardiac)", "complaint": "صدري بيوجعني", "vitals": {"hr": 100}, "age": 55, "expected": 2},
        {"name": "Stroke symptoms", "complaint": "وشه مايل ومش قادر يتكلم", "expected": 2},
        {"name": "Can't breathe", "complaint": "مش عارف آخد نفسي", "expected": 2},
        {"name": "Suicidal", "complaint": "عايز أموت", "expected": 2},
        {"name": "Pregnant bleeding", "complaint": "حامل وبتنزف", "expected": 2},
        {"name": "Low sugar", "complaint": "السكر واطي", "expected": 2},
        {"name": "High NEWS2 (no specific complaint)", "complaint": "تعبان", "vitals": {"hr": 140, "rr": 28, "spo2": 91, "sbp": 85}, "expected": 2},
        
        # LEVEL 3 - Urgent  
        {"name": "Abdominal pain", "complaint": "بطني بتوجعني جدا", "expected": 3},
        {"name": "Fever with symptoms", "complaint": "عندي سخونية عالية", "expected": 3},
        {"name": "Vomiting", "complaint": "بيرجع كتير", "expected": 3},
        {"name": "Fracture", "complaint": "رجلي مكسورة", "expected": 3},
        
        # LEVEL 4 - Less Urgent
        {"name": "Minor trauma", "complaint": "وقعت وايدي وارمة", "expected": 4},
        {"name": "Simple cut", "complaint": "عندي جرح محتاج خياطة", "expected": 4},
        {"name": "Cold symptoms", "complaint": "عندي برد وكحة", "expected": 4},
        {"name": "Ear pain", "complaint": "ودني بتوجعني", "expected": 4},
        {"name": "Sore throat", "complaint": "زوري بيوجعني", "expected": 4},
        {"name": "Mild headache", "complaint": "عندي صداع", "expected": 4},
        
        # LEVEL 5 - Non-Urgent
        {"name": "Prescription refill", "complaint": "عايز أجدد الروشتة", "expected": 5},
        {"name": "Medical certificate", "complaint": "عايز شهادة طبية", "expected": 5},
        {"name": "Follow up", "complaint": "جاي للمتابعة", "expected": 5},
    ]
    
    passed = 0
    failed_cases = []
    
    for case in test_cases:
        patient_data = {
            "age": case.get("age", 30),
            "gender": "male",
            "chief_complaint_text": case["complaint"],
            "vitals": case.get("vitals", {})
        }
        
        result = engine.triage(patient_data)
        
        if result.final_level == case["expected"]:
            status = "✅ PASS"
            passed += 1
        else:
            status = "❌ FAIL"
            failed_cases.append(case["name"])
        
        print(f"{status} | {case['name']}")
        print(f"       Expected: Level {case['expected']} | Got: Level {result.final_level}")
        print(f"       Path: {result.decision_path}")
    
    print(f"\n{'=' * 70}")
    print(f"RESULTS: {passed}/{len(test_cases)} passed")
    if failed_cases:
        print(f"Failed: {', '.join(failed_cases)}")
    print("=" * 70)
    
    return passed == len(test_cases)


def test_modifiers():
    """Test clinical modifier rules"""
    print("\n" + "=" * 70)
    print("CLINICAL MODIFIER TESTS")
    print("=" * 70)
    
    engine = DeterministicTriageEngine()
    
    test_cases = [
        # Elderly + chest pain → Level 2
        {
            "name": "Elderly chest pain modifier",
            "data": {"age": 70, "gender": "male", "chief_complaint_text": "صدري بيوجعني شوية", "vitals": {}},
            "expected": 2,
            "expected_modifier": "مسن مع ألم صدر"
        },
        # High pain score → Level 2
        {
            "name": "Severe pain modifier",
            "data": {"age": 30, "gender": "male", "chief_complaint_text": "وجع", "vitals": {"pain_score": 9}},
            "expected": 2,
            "expected_modifier": "ألم شديد"
        },
    ]
    
    passed = 0
    for case in test_cases:
        result = engine.triage(case["data"])
        status = "✅" if result.final_level == case["expected"] else "❌"
        if result.final_level == case["expected"]:
            passed += 1
        modifier_found = any(case["expected_modifier"] in m for m in result.modifiers_applied)
        print(f"{status} {case['name']}: Level={result.final_level}, Modifiers={result.modifiers_applied}")
    
    print(f"\nModifier Tests: {passed}/{len(test_cases)} passed")
    return passed == len(test_cases)


def test_arabic_dialect_coverage():
    """Test Egyptian Arabic dialect recognition"""
    print("\n" + "=" * 70)
    print("EGYPTIAN ARABIC DIALECT TESTS")
    print("=" * 70)
    
    engine = DeterministicTriageEngine()
    
    # Common Egyptian expressions
    expressions = [
        ("قلبي بيوجعني", 2, "Chest pain - formal"),
        ("صدري واجعني", 2, "Chest pain - colloquial"),
        ("مش قادر آخد نفسي", 2, "Dyspnea"),
        ("بطني بتوجعني", 3, "Abdominal pain"),
        ("عندي سخونية", 3, "Fever"),
        ("وقعت", 4, "Fall"),
        ("عندي برد", 4, "Cold"),
        ("عايز روشتة", 5, "Prescription"),
    ]
    
    passed = 0
    for text, expected_level, desc in expressions:
        result = engine.triage({
            "age": 35,
            "gender": "male", 
            "chief_complaint_text": text,
            "vitals": {}
        })
        status = "✅" if result.final_level == expected_level else "❌"
        if result.final_level == expected_level:
            passed += 1
        print(f"{status} '{text}' → Level {result.final_level} (expected {expected_level}) [{desc}]")
    
    print(f"\nArabic Dialect Tests: {passed}/{len(expressions)} passed")
    return passed == len(expressions)


if __name__ == "__main__":
    print("=" * 70)
    print("SAFE-Triage AI - Deterministic Hybrid Engine Test Suite")
    print("NEWS2 (RCP 2017) + ESI v4 (AHRQ 2011)")
    print("=" * 70)
    
    results = []
    results.append(("NEWS2 Scoring", test_news2_scoring()))
    results.append(("Triage Levels", test_deterministic_triage_levels()))
    results.append(("Clinical Modifiers", test_modifiers()))
    results.append(("Arabic Dialect", test_arabic_dialect_coverage()))
    
    print("\n" + "=" * 70)
    print("FINAL SUMMARY")
    print("=" * 70)
    all_passed = True
    for name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status} | {name}")
        if not passed:
            all_passed = False
    
    print("=" * 70)
    if all_passed:
        print("🎉 All test suites passed!")
    else:
        print("⚠️ Some tests failed - review above for details")
