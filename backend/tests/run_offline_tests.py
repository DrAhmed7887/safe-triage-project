"""
SAFE-Triage - Offline Test Runner
==================================

Tests the deterministic triage system using pre-defined scenarios.
No AI API calls required - runs completely offline.

Usage:
    python3 -m tests.run_offline_tests
    python3 -m tests.run_offline_tests --verbose
    python3 -m tests.run_offline_tests --level 2

Author: Ahmed Zayed
"""

import os
import sys
import json
from datetime import datetime
from typing import List, Dict

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from logic.deterministic_triage import DeterministicTriageEngine
from tests.test_scenarios_data import (
    ALL_SCENARIOS,
    LEVEL_1_SCENARIOS,
    LEVEL_2_SCENARIOS,
    LEVEL_3_SCENARIOS,
    LEVEL_4_SCENARIOS,
    LEVEL_5_SCENARIOS,
    EDGE_CASES,
    get_scenarios_by_level
)


class OfflineTestRunner:
    """Run triage tests without AI API calls"""
    
    def __init__(self):
        self.engine = DeterministicTriageEngine()
        self.results = []
        self.misclassifications = []
    
    def test_scenario(self, scenario: dict, verbose: bool = False) -> dict:
        """Test a single scenario"""
        
        patient_data = {
            "age": scenario["age"],
            "gender": scenario["gender"],
            "chief_complaint_text": scenario["complaint_ar"],
            "vitals": scenario.get("vitals", {})
        }
        
        result = self.engine.triage(patient_data)
        
        expected_level = scenario["expected_level"]
        actual_level = result.final_level
        
        # Check if level matches
        level_correct = actual_level == expected_level
        
        # Check if category matches any expected
        expected_categories = scenario.get("expected_categories", [])
        category_correct = result.category in expected_categories if expected_categories else True
        
        # Overall correctness (level is most important)
        is_correct = level_correct
        
        # Severity of misclassification
        level_diff = abs(actual_level - expected_level)
        if is_correct:
            severity = "none"
        elif level_diff == 1:
            severity = "minor"
        elif level_diff == 2:
            severity = "major"
        else:
            severity = "critical"
        
        # Extra critical if under-triaged emergency
        if expected_level <= 2 and actual_level > expected_level:
            severity = "critical"
        
        test_result = {
            "scenario_id": scenario["id"],
            "complaint_ar": scenario["complaint_ar"],
            "complaint_en": scenario["complaint_en"],
            "expected_level": expected_level,
            "actual_level": actual_level,
            "expected_categories": expected_categories,
            "actual_category": result.category,
            "level_correct": level_correct,
            "category_correct": category_correct,
            "is_correct": is_correct,
            "severity": severity,
            "decision_path": result.decision_path
        }
        
        self.results.append(test_result)
        
        if not is_correct:
            self.misclassifications.append(test_result)
        
        if verbose:
            status = "✅" if is_correct else f"❌ [{severity.upper()}]"
            print(f"\n{status} {scenario['id']}")
            print(f"   Complaint: {scenario['complaint_ar']}")
            print(f"   Expected:  Level {expected_level} ({', '.join(expected_categories[:2])})")
            print(f"   Actual:    Level {actual_level} ({result.category})")
            if not is_correct:
                print(f"   Path: {result.decision_path}")
        
        return test_result
    
    def run_all_tests(self, verbose: bool = False) -> dict:
        """Run all pre-defined tests"""
        print("=" * 70)
        print("🧪 SAFE-Triage Offline Test Suite")
        print(f"   Testing {len(ALL_SCENARIOS)} scenarios")
        print("=" * 70)
        
        self.results = []
        self.misclassifications = []
        
        for scenario in ALL_SCENARIOS:
            self.test_scenario(scenario, verbose)
        
        return self._generate_summary()
    
    def run_level_tests(self, level: int, verbose: bool = False) -> dict:
        """Run tests for a specific level"""
        scenarios = get_scenarios_by_level(level)
        
        print("=" * 70)
        print(f"🧪 Testing Level {level} Scenarios ({len(scenarios)} tests)")
        print("=" * 70)
        
        self.results = []
        self.misclassifications = []
        
        for scenario in scenarios:
            self.test_scenario(scenario, verbose)
        
        return self._generate_summary()
    
    def run_edge_cases(self, verbose: bool = True) -> dict:
        """Run edge case tests"""
        print("=" * 70)
        print(f"🧪 Testing Edge Cases ({len(EDGE_CASES)} scenarios)")
        print("=" * 70)
        
        self.results = []
        self.misclassifications = []
        
        for scenario in EDGE_CASES:
            self.test_scenario(scenario, verbose)
        
        return self._generate_summary()
    
    def _generate_summary(self) -> dict:
        """Generate test summary"""
        total = len(self.results)
        correct = sum(1 for r in self.results if r["is_correct"])
        critical = sum(1 for r in self.results if r["severity"] == "critical")
        major = sum(1 for r in self.results if r["severity"] == "major")
        minor = sum(1 for r in self.results if r["severity"] == "minor")
        
        summary = {
            "total": total,
            "correct": correct,
            "accuracy": round(correct / total * 100, 1) if total > 0 else 0,
            "critical_misses": critical,
            "major_misses": major,
            "minor_misses": minor,
            "timestamp": datetime.now().isoformat()
        }
        
        print("\n" + "=" * 70)
        print("📊 TEST SUMMARY")
        print("=" * 70)
        print(f"   Total Tests:     {total}")
        print(f"   Passed:          {correct} ({summary['accuracy']}%)")
        print(f"   Critical Misses: {critical} 🚨")
        print(f"   Major Misses:    {major} ⚠️")
        print(f"   Minor Misses:    {minor} ℹ️")
        print("=" * 70)
        
        if self.misclassifications:
            print("\n❌ MISCLASSIFICATIONS:")
            print("-" * 70)
            for miss in self.misclassifications:
                print(f"\n[{miss['severity'].upper()}] {miss['scenario_id']}")
                print(f"   {miss['complaint_ar']}")
                print(f"   Expected: Level {miss['expected_level']} | Got: Level {miss['actual_level']}")
                print(f"   Category: {miss['actual_category']}")
        
        return summary
    
    def export_results(self, filepath: str = None):
        """Export results to JSON file"""
        if filepath is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filepath = os.path.join(
                os.path.dirname(__file__),
                "teaching_logs",
                f"offline_test_{timestamp}.json"
            )
        
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        
        data = {
            "summary": {
                "total": len(self.results),
                "correct": sum(1 for r in self.results if r["is_correct"]),
                "misclassifications": len(self.misclassifications)
            },
            "results": self.results,
            "misclassifications": self.misclassifications
        }
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        print(f"\n📁 Results exported to: {filepath}")


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="SAFE-Triage Offline Test Runner")
    parser.add_argument("--verbose", "-v", action="store_true", help="Show detailed output")
    parser.add_argument("--level", "-l", type=int, choices=[1,2,3,4,5], help="Test specific level only")
    parser.add_argument("--edge", "-e", action="store_true", help="Test edge cases only")
    parser.add_argument("--export", "-x", action="store_true", help="Export results to JSON")
    
    args = parser.parse_args()
    
    runner = OfflineTestRunner()
    
    if args.edge:
        runner.run_edge_cases(verbose=True)
    elif args.level:
        runner.run_level_tests(args.level, verbose=args.verbose)
    else:
        runner.run_all_tests(verbose=args.verbose)
    
    if args.export:
        runner.export_results()


if __name__ == "__main__":
    main()
