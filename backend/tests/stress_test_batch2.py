#!/usr/bin/env python3
"""
SAFE-Triage Keyword Database Stress Test - Batch 2: Silent & Sneaky
====================================================================
Tests atypical presentations that don't use obvious keywords:
- Silent MI (Diabetics/Elderly): No chest pain, just fatigue/nausea/sweating
- Pediatric Emergencies: Floppy baby, not crying, jelly stool
- DKA: Fast breathing, fruity breath, extreme thirst

Run: python stress_test_batch2.py
"""

import json
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from logic.deterministic_triage import DeterministicTriageEngine
from models import PatientInput, Vitals, Gender

# Load test cases
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(SCRIPT_DIR, 'stress_test_batch2_sneaky.json'), 'r', encoding='utf-8') as f:
    TEST_CASES = json.load(f)

def run_stress_test():
    """Run all test cases and report failures."""
    
    # Use Standard mode (no AI)
    engine = DeterministicTriageEngine(use_ai=False)
    
    failures = []
    successes = []
    under_triage = []  # Critical: Level 1/2 cases that got Level 4/5
    
    print(f"🚀 BATCH 2: Silent & Sneaky Stress Test")
    print(f"   Testing {len(TEST_CASES)} atypical/subtle presentations...")
    print(f"   Mode: STANDARD (Deterministic Only, No AI)")
    print("=" * 60)
    print()
    
    # Group results by category
    category_results = {}
    
    for i, case in enumerate(TEST_CASES):
        # Determine age based on category (pediatric vs adult)
        if 'pediatric' in case['category'] or 'intussusception' in case['category'] or 'febrile' in case['category']:
            age = 2  # Child
        elif 'elderly' in case['category'] or 'جد' in case['text'] or 'ست كبيرة' in case['text'] or 'عجوز' in case['text']:
            age = 75  # Elderly
        else:
            age = 55  # Adult (higher risk for silent MI)
        
        # Create patient with normal vitals to force keyword-only detection
        patient = PatientInput(
            patient_id=f"SNEAKY-{i:03d}",
            age=age,
            gender=Gender.MALE,
            chief_complaint_text=case["text"],
            vitals=Vitals(hr=88, rr=18, spo2=96, temp=37.2, sbp=125, gcs=15),
            is_copd=False,
            on_supplemental_o2=False,
            is_new_confusion=False,
            is_pregnant=False
        )
        
        try:
            result = engine.evaluate(patient)
            actual_level = result.level.value if hasattr(result.level, 'value') else result.level
            expected_level = case['expected_level']
            category = result.description_en
            test_category = case['category']
            
            # Track by category
            if test_category not in category_results:
                category_results[test_category] = {'pass': 0, 'fail': 0, 'critical': 0}
            
            # Check for dangerous under-triage
            if actual_level >= 4 and expected_level <= 2:
                # CRITICAL: Life-threatening case missed!
                under_triage.append({
                    "text": case["text"],
                    "translation": case.get("translation", ""),
                    "expected_category": test_category,
                    "expected_level": expected_level,
                    "actual_level": actual_level,
                    "detected_as": category,
                    "clinical_note": case.get("clinical_note", "")
                })
                category_results[test_category]['critical'] += 1
                print(f"🚨 CRITICAL MISS: '{case['text']}'")
                print(f"   Translation: {case.get('translation', 'N/A')}")
                print(f"   Clinical: {case.get('clinical_note', 'N/A')}")
                print(f"   Expected: Level {expected_level} ({test_category})")
                print(f"   Got: Level {actual_level} ({category})")
                print()
                
            elif actual_level > expected_level:
                # Under-triage but not critical
                failures.append({
                    "text": case["text"],
                    "translation": case.get("translation", ""),
                    "expected_category": test_category,
                    "expected_level": expected_level,
                    "actual_level": actual_level,
                    "detected_as": category,
                    "clinical_note": case.get("clinical_note", "")
                })
                category_results[test_category]['fail'] += 1
                print(f"❌ MISSED: '{case['text'][:40]}...' -> Level {actual_level} (Expected {expected_level})")
                
            else:
                successes.append(case["text"])
                category_results[test_category]['pass'] += 1
                print(f"✅ CAUGHT: '{case['text'][:40]}...' -> Level {actual_level}")
                
        except Exception as e:
            print(f"💥 ERROR on case {i}: {e}")
            failures.append({
                "text": case["text"],
                "error": str(e)
            })
    
    # Summary
    print()
    print("=" * 60)
    print("BATCH 2 AUDIT COMPLETE")
    print("=" * 60)
    print(f"✅ Caught: {len(successes)}")
    print(f"❌ Missed (Under-triage): {len(failures)}")
    print(f"🚨 CRITICAL MISSES (Life-threatening → Non-urgent): {len(under_triage)}")
    print()
    
    # Results by category
    print("RESULTS BY CATEGORY:")
    print("-" * 40)
    for cat, results in sorted(category_results.items()):
        total = results['pass'] + results['fail'] + results['critical']
        pass_rate = (results['pass'] / total * 100) if total > 0 else 0
        status = "✅" if results['critical'] == 0 and results['fail'] == 0 else "❌"
        print(f"  {status} {cat}: {results['pass']}/{total} ({pass_rate:.0f}%)")
        if results['critical'] > 0:
            print(f"     🚨 {results['critical']} CRITICAL misses!")
    print()
    
    # Critical failures need immediate attention
    if under_triage:
        print("=" * 60)
        print("🚨🚨🚨 CRITICAL: LIFE-THREATENING CASES MISSED 🚨🚨🚨")
        print("=" * 60)
        print("These phrases MUST be added to keyword_database.py:")
        print()
        for case in under_triage:
            print(f"  • \"{case['text']}\"")
            print(f"    ({case['translation']})")
            print(f"    Clinical: {case['clinical_note']}")
            print(f"    Should be: {case['expected_category']} (Level {case['expected_level']})")
            print()
    
    # Output for Claude to fix
    if failures or under_triage:
        print()
        print("=" * 60)
        print("COPY THIS TO CLAUDE TO FIX keyword_database.py:")
        print("=" * 60)
        
        all_failures = under_triage + failures
        
        # Group by category
        by_category = {}
        for f in all_failures:
            cat = f.get("expected_category", "unknown")
            if cat not in by_category:
                by_category[cat] = []
            by_category[cat].append(f)
        
        output = {
            "batch": "Batch 2 - Silent & Sneaky",
            "total_failures": len(all_failures),
            "critical_failures": len(under_triage),
            "by_category": by_category
        }
        
        print(json.dumps(output, ensure_ascii=False, indent=2))
        
        # Save to file
        output_path = os.path.join(SCRIPT_DIR, 'stress_test_batch2_failures.json')
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(output, f, ensure_ascii=False, indent=2)
        print(f"\n📄 Failures saved to: {output_path}")
    
    else:
        print("🎉 ALL TESTS PASSED! Keyword database handles atypical presentations.")
    
    return len(under_triage) == 0 and len(failures) == 0


if __name__ == "__main__":
    success = run_stress_test()
    sys.exit(0 if success else 1)
