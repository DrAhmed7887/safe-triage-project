"""
SAFE-Triage AI Teaching Agent
=============================

An AI-powered testing agent that continuously generates clinical scenarios
to test and improve the deterministic triage classification system.

The agent:
1. Generates realistic clinical scenarios using AI
2. Tests them against the deterministic triage engine
3. Identifies misclassifications
4. Logs results for human review and system improvement

This implements a "red team" approach to find edge cases and improve
the keyword-based fallback classifier.

Author: Ahmed Zayed
"""

import os
import sys
import json
import random
from datetime import datetime
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass, asdict

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from logic.deterministic_triage import (
    DeterministicTriageEngine,
    SYMPTOM_CATEGORIES,
    SymptomCategory
)

import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()


@dataclass
class ClinicalScenario:
    """A generated clinical scenario for testing"""
    scenario_id: str
    complaint_ar: str
    complaint_en: str
    age: int
    gender: str
    vitals: Dict
    expected_level: int
    expected_category: str
    clinical_reasoning: str
    dialect: str  # egyptian, levantine, gulf, msa


@dataclass 
class TestResult:
    """Result of testing a scenario"""
    scenario: ClinicalScenario
    actual_level: int
    actual_category: str
    decision_path: str
    is_correct: bool
    severity: str  # "critical", "major", "minor" based on level difference
    timestamp: str


class TeachingAgent:
    """
    AI Teaching Agent for testing and improving triage classification.
    
    Uses Gemini AI to generate realistic clinical scenarios in various
    Arabic dialects and tests them against the deterministic engine.
    """
    
    def __init__(self, log_dir: str = None):
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY not found in environment")
        
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-2.0-flash')
        self.engine = DeterministicTriageEngine()
        
        # Setup logging directory
        if log_dir is None:
            log_dir = os.path.join(os.path.dirname(__file__), "teaching_logs")
        self.log_dir = log_dir
        os.makedirs(log_dir, exist_ok=True)
        
        # Track results
        self.results: List[TestResult] = []
        self.misclassifications: List[TestResult] = []
        
        # Scenario counter
        self.scenario_count = 0
    
    def generate_scenario(self, target_level: int = None, dialect: str = None) -> ClinicalScenario:
        """
        Generate a realistic clinical scenario using AI.
        
        Args:
            target_level: Specific ESI level to generate (1-5), or None for random
            dialect: Arabic dialect ("egyptian", "levantine", "gulf", "msa")
        """
        if target_level is None:
            # Weight towards more critical levels to catch important misses
            target_level = random.choices([1, 2, 3, 4, 5], weights=[15, 25, 30, 20, 10])[0]
        
        if dialect is None:
            dialect = random.choice(["egyptian", "egyptian", "egyptian", "levantine", "gulf", "msa"])
        
        # Get categories for this level
        level_categories = [
            (cat_id, cat) for cat_id, cat in SYMPTOM_CATEGORIES.items() 
            if cat.esi_level == target_level
        ]
        
        if not level_categories:
            level_categories = [("unclear", SYMPTOM_CATEGORIES["unclear"])]
        
        target_category_id, target_category = random.choice(level_categories)
        
        dialect_instructions = {
            "egyptian": "استخدم اللهجة المصرية العامية (مثل: عندي، بيوجعني، مش عارف، حاسس)",
            "levantine": "استخدم اللهجة الشامية (مثل: عندي، بيوجعني، ما بقدر، حاسس)",  
            "gulf": "استخدم اللهجة الخليجية (مثل: عندي، يوجعني، ما أقدر، حاس)",
            "msa": "استخدم اللغة العربية الفصحى الطبية"
        }
        
        prompt = f"""أنت طبيب طوارئ خبير. أنشئ سيناريو مريض واقعي للتدريب.

المطلوب: سيناريو مستوى {target_level} (ESI) - فئة: {target_category.name_ar} ({target_category.name_en})

{dialect_instructions[dialect]}

أنشئ سيناريو يشمل:
1. شكوى المريض بالعربية (كما يقولها المريض بالضبط - عامية)
2. ترجمة الشكوى بالإنجليزية
3. العمر المناسب
4. الجنس
5. العلامات الحيوية المناسبة للحالة
6. سبب طبي مختصر لتصنيف هذا المستوى

مهم جداً:
- اجعل الشكوى واقعية كما يقولها مريض حقيقي (ليست طبية)
- استخدم تعبيرات شائعة ومتنوعة
- لا تذكر اسم المرض مباشرة في شكوى المريض

أجب بصيغة JSON فقط:
{{
    "complaint_ar": "الشكوى بالعربية",
    "complaint_en": "English translation",
    "age": 45,
    "gender": "male",
    "vitals": {{
        "hr": 90,
        "rr": 18,
        "spo2": 98,
        "sbp": 120,
        "dbp": 80,
        "temp": 37.0,
        "gcs": 15,
        "pain_score": 5
    }},
    "clinical_reasoning": "سبب التصنيف"
}}"""

        try:
            response = self.model.generate_content(prompt)
            text = response.text.strip()
            
            # Extract JSON from response
            if "```json" in text:
                text = text.split("```json")[1].split("```")[0]
            elif "```" in text:
                text = text.split("```")[1].split("```")[0]
            
            data = json.loads(text)
            
            self.scenario_count += 1
            
            return ClinicalScenario(
                scenario_id=f"SCN-{datetime.now().strftime('%Y%m%d%H%M%S')}-{self.scenario_count:04d}",
                complaint_ar=data["complaint_ar"],
                complaint_en=data["complaint_en"],
                age=data["age"],
                gender=data["gender"],
                vitals=data["vitals"],
                expected_level=target_level,
                expected_category=target_category_id,
                clinical_reasoning=data["clinical_reasoning"],
                dialect=dialect
            )
            
        except Exception as e:
            print(f"Error generating scenario: {e}")
            # Return a fallback scenario
            return self._fallback_scenario(target_level, target_category_id, dialect)
    
    def _fallback_scenario(self, level: int, category: str, dialect: str) -> ClinicalScenario:
        """Generate a simple fallback scenario if AI fails"""
        self.scenario_count += 1
        
        fallback_complaints = {
            1: ("مش بيرد عليا خالص", "Not responding at all"),
            2: ("صدري بيوجعني جامد", "Severe chest pain"),
            3: ("بطني بتوجعني من امبارح", "Abdominal pain since yesterday"),
            4: ("وقعت وايدي وارمة", "Fell and my hand is swollen"),
            5: ("عايز أجدد الروشتة", "Need prescription refill")
        }
        
        complaint_ar, complaint_en = fallback_complaints.get(level, fallback_complaints[3])
        
        return ClinicalScenario(
            scenario_id=f"SCN-FALLBACK-{self.scenario_count:04d}",
            complaint_ar=complaint_ar,
            complaint_en=complaint_en,
            age=random.randint(20, 70),
            gender=random.choice(["male", "female"]),
            vitals={"hr": 80, "rr": 16, "spo2": 98, "sbp": 120, "gcs": 15},
            expected_level=level,
            expected_category=category,
            clinical_reasoning="Fallback scenario",
            dialect=dialect
        )
    
    def test_scenario(self, scenario: ClinicalScenario) -> TestResult:
        """Test a scenario against the deterministic engine"""
        
        patient_data = {
            "age": scenario.age,
            "gender": scenario.gender,
            "chief_complaint_text": scenario.complaint_ar,
            "vitals": scenario.vitals
        }
        
        result = self.engine.triage(patient_data)
        
        # Determine if correct (allow 1 level tolerance for borderline cases)
        level_diff = abs(result.final_level - scenario.expected_level)
        is_correct = level_diff == 0
        
        # Determine severity of misclassification
        if is_correct:
            severity = "none"
        elif level_diff == 1:
            severity = "minor"
        elif level_diff == 2:
            severity = "major"
        else:
            severity = "critical"
        
        # Extra critical if we under-triaged a level 1 or 2
        if scenario.expected_level <= 2 and result.final_level > scenario.expected_level:
            severity = "critical"
        
        test_result = TestResult(
            scenario=scenario,
            actual_level=result.final_level,
            actual_category=result.category,
            decision_path=result.decision_path,
            is_correct=is_correct,
            severity=severity,
            timestamp=datetime.now().isoformat()
        )
        
        self.results.append(test_result)
        
        if not is_correct:
            self.misclassifications.append(test_result)
        
        return test_result
    
    def run_teaching_session(self, num_scenarios: int = 20, verbose: bool = True) -> Dict:
        """
        Run a teaching session with multiple scenarios.
        
        Args:
            num_scenarios: Number of scenarios to generate and test
            verbose: Print results as they happen
        
        Returns:
            Summary statistics
        """
        print("=" * 70)
        print("🎓 SAFE-Triage Teaching Agent - Starting Session")
        print(f"   Generating and testing {num_scenarios} clinical scenarios")
        print("=" * 70)
        
        session_results = []
        
        for i in range(num_scenarios):
            # Generate scenario
            scenario = self.generate_scenario()
            
            # Test it
            result = self.test_scenario(scenario)
            session_results.append(result)
            
            if verbose:
                status = "✅" if result.is_correct else f"❌ [{result.severity.upper()}]"
                print(f"\n[{i+1}/{num_scenarios}] {status}")
                print(f"   Complaint: {scenario.complaint_ar}")
                print(f"   Expected: Level {scenario.expected_level} ({scenario.expected_category})")
                print(f"   Actual:   Level {result.actual_level} ({result.actual_category})")
                if not result.is_correct:
                    print(f"   Path: {result.decision_path}")
        
        # Calculate statistics
        total = len(session_results)
        correct = sum(1 for r in session_results if r.is_correct)
        critical_misses = sum(1 for r in session_results if r.severity == "critical")
        major_misses = sum(1 for r in session_results if r.severity == "major")
        minor_misses = sum(1 for r in session_results if r.severity == "minor")
        
        summary = {
            "total_scenarios": total,
            "correct": correct,
            "accuracy": round(correct / total * 100, 1) if total > 0 else 0,
            "critical_misses": critical_misses,
            "major_misses": major_misses,
            "minor_misses": minor_misses,
            "timestamp": datetime.now().isoformat()
        }
        
        print("\n" + "=" * 70)
        print("📊 SESSION SUMMARY")
        print("=" * 70)
        print(f"   Total Scenarios: {total}")
        print(f"   Correct:         {correct} ({summary['accuracy']}%)")
        print(f"   Critical Misses: {critical_misses} 🚨")
        print(f"   Major Misses:    {major_misses} ⚠️")
        print(f"   Minor Misses:    {minor_misses} ℹ️")
        print("=" * 70)
        
        # Save session log
        self._save_session_log(session_results, summary)
        
        return summary
    
    def _save_session_log(self, results: List[TestResult], summary: Dict):
        """Save session results to JSON log file"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = os.path.join(self.log_dir, f"session_{timestamp}.json")
        
        log_data = {
            "summary": summary,
            "results": [
                {
                    "scenario_id": r.scenario.scenario_id,
                    "complaint_ar": r.scenario.complaint_ar,
                    "complaint_en": r.scenario.complaint_en,
                    "age": r.scenario.age,
                    "gender": r.scenario.gender,
                    "dialect": r.scenario.dialect,
                    "expected_level": r.scenario.expected_level,
                    "expected_category": r.scenario.expected_category,
                    "actual_level": r.actual_level,
                    "actual_category": r.actual_category,
                    "is_correct": r.is_correct,
                    "severity": r.severity,
                    "decision_path": r.decision_path,
                    "clinical_reasoning": r.scenario.clinical_reasoning
                }
                for r in results
            ],
            "misclassifications": [
                {
                    "scenario_id": r.scenario.scenario_id,
                    "complaint_ar": r.scenario.complaint_ar,
                    "expected_level": r.scenario.expected_level,
                    "expected_category": r.scenario.expected_category,
                    "actual_level": r.actual_level,
                    "actual_category": r.actual_category,
                    "severity": r.severity,
                    "suggestion": self._suggest_fix(r)
                }
                for r in results if not r.is_correct
            ]
        }
        
        with open(log_file, 'w', encoding='utf-8') as f:
            json.dump(log_data, f, ensure_ascii=False, indent=2)
        
        print(f"\n📁 Session log saved to: {log_file}")
        
        # Also save misclassifications to separate file for easy review
        if log_data["misclassifications"]:
            miss_file = os.path.join(self.log_dir, f"misses_{timestamp}.json")
            with open(miss_file, 'w', encoding='utf-8') as f:
                json.dump(log_data["misclassifications"], f, ensure_ascii=False, indent=2)
            print(f"📁 Misclassifications saved to: {miss_file}")
    
    def _suggest_fix(self, result: TestResult) -> str:
        """Suggest a fix for a misclassification"""
        scenario = result.scenario
        
        # Extract key words from the complaint
        words = scenario.complaint_ar.split()
        
        suggestion = (
            f"Add keywords to '{scenario.expected_category}' category: "
            f"Consider adding variations like: {', '.join(words[:5])}"
        )
        
        return suggestion
    
    def get_keyword_suggestions(self) -> Dict[str, List[str]]:
        """
        Analyze misclassifications and suggest new keywords to add.
        
        Returns:
            Dict mapping category -> list of suggested keywords
        """
        suggestions = {}
        
        for result in self.misclassifications:
            category = result.scenario.expected_category
            complaint = result.scenario.complaint_ar
            
            if category not in suggestions:
                suggestions[category] = []
            
            # Extract potential keywords (words > 2 chars)
            words = [w for w in complaint.split() if len(w) > 2]
            suggestions[category].extend(words)
        
        # Deduplicate and sort by frequency
        for category in suggestions:
            word_freq = {}
            for word in suggestions[category]:
                word_freq[word] = word_freq.get(word, 0) + 1
            suggestions[category] = sorted(word_freq.keys(), key=lambda w: -word_freq[w])[:10]
        
        return suggestions
    
    def continuous_learning(self, iterations: int = 5, scenarios_per_iteration: int = 10):
        """
        Run continuous learning sessions.
        
        Args:
            iterations: Number of teaching sessions
            scenarios_per_iteration: Scenarios per session
        """
        print("\n" + "🔄" * 35)
        print("🎓 CONTINUOUS LEARNING MODE")
        print("🔄" * 35 + "\n")
        
        all_summaries = []
        
        for i in range(iterations):
            print(f"\n{'='*70}")
            print(f"📚 ITERATION {i+1}/{iterations}")
            print(f"{'='*70}")
            
            summary = self.run_teaching_session(scenarios_per_iteration, verbose=True)
            all_summaries.append(summary)
            
            # After each iteration, show keyword suggestions
            if self.misclassifications:
                print("\n💡 KEYWORD SUGGESTIONS FOR IMPROVEMENT:")
                suggestions = self.get_keyword_suggestions()
                for category, keywords in suggestions.items():
                    if keywords:
                        print(f"   {category}: {', '.join(keywords[:5])}")
        
        # Final summary
        print("\n" + "=" * 70)
        print("📊 FINAL LEARNING SUMMARY")
        print("=" * 70)
        
        total_scenarios = sum(s["total_scenarios"] for s in all_summaries)
        total_correct = sum(s["correct"] for s in all_summaries)
        total_critical = sum(s["critical_misses"] for s in all_summaries)
        
        print(f"   Total Scenarios Tested: {total_scenarios}")
        print(f"   Overall Accuracy:       {round(total_correct/total_scenarios*100, 1)}%")
        print(f"   Total Critical Misses:  {total_critical}")
        
        # Show accuracy trend
        print("\n   Accuracy Trend:")
        for i, s in enumerate(all_summaries):
            bar = "█" * int(s["accuracy"] / 5)
            print(f"   Iteration {i+1}: {bar} {s['accuracy']}%")
        
        print("=" * 70)


# =============================================================================
# MAIN EXECUTION
# =============================================================================

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="SAFE-Triage Teaching Agent")
    parser.add_argument("--scenarios", "-n", type=int, default=20,
                       help="Number of scenarios to test (default: 20)")
    parser.add_argument("--continuous", "-c", action="store_true",
                       help="Run continuous learning mode")
    parser.add_argument("--iterations", "-i", type=int, default=5,
                       help="Number of iterations for continuous mode (default: 5)")
    
    args = parser.parse_args()
    
    agent = TeachingAgent()
    
    if args.continuous:
        agent.continuous_learning(
            iterations=args.iterations,
            scenarios_per_iteration=args.scenarios
        )
    else:
        agent.run_teaching_session(num_scenarios=args.scenarios)
