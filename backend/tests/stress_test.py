#!/usr/bin/env python3
"""
SAFE-Triage Keyword Database Stress Test
=========================================
Tests the deterministic (Standard) mode keyword matching
against 100 colloquial Egyptian Arabic medical complaints.

Run: python stress_test.py
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
with open(os.path.join(SCRIPT_DIR, 'stress_test_cases.json'), 'r', encoding='utf-8') as f:
    TEST_CASES = json.load(f)

def run_stress_test():
    """Run all test cases and report failures."""
    
    # Use Standard mode (no AI)
    engine = DeterministicTriageEngine(use_ai=False)
    
    failures = []
    successes = []
    under_triage = []  # Critical: Level 1/2 cases that got Level 4/5
    
    print(f"🚀 Starting Stress Test on {len(TEST_CASES)} scenarios...")
    print(f"   Mode: STANDARD (Deterministic Only, No AI)")
    print("=" * 60)
    print()
    
    for i, case in enumerate(TEST_CASES):
        # Create patient with normal vitals to force keyword-only detection
        patient = PatientInput(
            patient_id=f"STRESS-{i:03d}",
            age=40,
            gender=Gender.MALE,
            chief_complaint_text=case["text"],
            vitals=Vitals(hr=80, rr=16, spo2=98, temp=37.0, sbp=120, gcs=15),
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
            
            # Check for dangerous under-triage
            if actual_level >= 4 and expected_level <= 2:
                # CRITICAL: Life-threatening case missed!
                under_triage.append({
                    "text": case["text"],
                    "translation": case.get("translation", ""),
                    "expected_category": case["category"],
                    "expected_level": expected_level,
                    "actual_level": actual_level,
                    "detected_as": category
                })
                print(f"🚨 CRITICAL MISS: '{case['text']}'")
                print(f"   Translation: {case.get('translation', 'N/A')}")
                print(f"   Expected: Level {expected_level} ({case['category']})")
                print(f"   Got: Level {actual_level} ({category})")
                print()
                
            elif actual_level > expected_level:
                # Under-triage but not critical
                failures.append({
                    "text": case["text"],
                    "translation": case.get("translation", ""),
                    "expected_category": case["category"],
                    "expected_level": expected_level,
                    "actual_level": actual_level,
                    "detected_as": category
                })
                print(f"❌ MISSED: '{case['text'][:40]}...' -> Level {actual_level} (Expected {expected_level})")
                
            else:
                successes.append(case["text"])
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
    print("AUDIT COMPLETE")
    print("=" * 60)
    print(f"✅ Caught: {len(successes)}")
    print(f"❌ Missed (Under-triage): {len(failures)}")
    print(f"🚨 CRITICAL MISSES (Life-threatening → Non-urgent): {len(under_triage)}")
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
            "total_failures": len(all_failures),
            "critical_failures": len(under_triage),
            "by_category": by_category
        }
        
        print(json.dumps(output, ensure_ascii=False, indent=2))
        
        # Save to file
        output_path = os.path.join(SCRIPT_DIR, 'stress_test_failures.json')
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(output, f, ensure_ascii=False, indent=2)
        print(f"\n📄 Failures saved to: {output_path}")
    
    else:
        print("🎉 ALL TESTS PASSED! Keyword database is comprehensive.")
    
    return len(under_triage) == 0 and len(failures) == 0


if __name__ == "__main__":
    success = run_stress_test()
    sys.exit(0 if success else 1)
