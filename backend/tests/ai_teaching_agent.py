"""
SAFE-Triage AI Teaching Agent with Auto-Learning
=================================================

An AI-powered agent that uses Gemini to:
1. Generate realistic clinical scenarios in Arabic dialects
2. Test them against the deterministic triage engine
3. Identify misclassifications
4. AUTOMATICALLY suggest and apply keyword improvements
5. Save learned keywords for permanent improvement

This creates a continuous learning loop where AI teaches
the deterministic system to be more accurate.

Author: Ahmed Zayed
"""

import os
import sys
import json
import random
import time
from datetime import datetime
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass, asdict

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from logic.deterministic_triage import (
    DeterministicTriageEngine,
    SYMPTOM_CATEGORIES,
    SymptomCategory
)

import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()


# =============================================================================
# LEARNED KEYWORDS DATABASE
# =============================================================================
# This file stores keywords learned by the AI agent

LEARNED_KEYWORDS_FILE = os.path.join(
    os.path.dirname(__file__), 
    "learned_keywords.json"
)


def load_learned_keywords() -> Dict[str, List[str]]:
    """Load previously learned keywords"""
    if os.path.exists(LEARNED_KEYWORDS_FILE):
        with open(LEARNED_KEYWORDS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}


def save_learned_keywords(keywords: Dict[str, List[str]]):
    """Save learned keywords to file"""
    with open(LEARNED_KEYWORDS_FILE, 'w', encoding='utf-8') as f:
        json.dump(keywords, f, ensure_ascii=False, indent=2)


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
    dialect: str
    key_phrases: List[str]  # Important phrases that should trigger classification


@dataclass 
class TestResult:
    """Result of testing a scenario"""
    scenario: ClinicalScenario
    actual_level: int
    actual_category: str
    decision_path: str
    is_correct: bool
    severity: str
    suggested_keywords: List[str]
    timestamp: str


class AITeachingAgent:
    """
    AI Teaching Agent with Auto-Learning Capabilities
    
    Uses Gemini to:
    1. Generate diverse clinical scenarios
    2. Identify misclassifications
    3. Extract keywords that should have triggered correct classification
    4. Update the keyword database for continuous improvement
    """
    
    def __init__(self, log_dir: str = None, rate_limit_delay: float = 1.5):
        """
        Initialize the teaching agent.
        
        Args:
            log_dir: Directory for logs
            rate_limit_delay: Seconds to wait between API calls (to avoid quota)
        """
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY not found in environment")
        
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-2.0-flash')
        self.engine = DeterministicTriageEngine()
        self.rate_limit_delay = rate_limit_delay
        
        # Setup logging
        if log_dir is None:
            log_dir = os.path.join(os.path.dirname(__file__), "teaching_logs")
        self.log_dir = log_dir
        os.makedirs(log_dir, exist_ok=True)
        
        # Load learned keywords
        self.learned_keywords = load_learned_keywords()
        
        # Track results
        self.results: List[TestResult] = []
        self.misclassifications: List[TestResult] = []
        self.new_keywords_learned: Dict[str, List[str]] = {}
        
        self.scenario_count = 0
        self.api_calls = 0
    
    def _api_call_with_retry(self, prompt: str, max_retries: int = 3) -> Optional[str]:
        """Make API call with retry and rate limiting"""
        for attempt in range(max_retries):
            try:
                # Rate limit
                time.sleep(self.rate_limit_delay)
                self.api_calls += 1
                
                response = self.model.generate_content(prompt)
                return response.text.strip()
                
            except Exception as e:
                error_msg = str(e)
                if "429" in error_msg or "quota" in error_msg.lower():
                    wait_time = (attempt + 1) * 30  # Exponential backoff
                    print(f"⏳ Rate limited. Waiting {wait_time}s before retry...")
                    time.sleep(wait_time)
                else:
                    print(f"❌ API Error: {e}")
                    if attempt == max_retries - 1:
                        return None
        return None
    
    def generate_scenario(self, target_level: int = None, dialect: str = None) -> Optional[ClinicalScenario]:
        """Generate a clinical scenario using AI"""
        
        if target_level is None:
            target_level = random.choices([1, 2, 3, 4, 5], weights=[15, 25, 30, 20, 10])[0]
        
        if dialect is None:
            dialect = random.choice(["egyptian", "egyptian", "levantine", "gulf"])
        
        # Get categories for this level
        level_categories = [
            (cat_id, cat) for cat_id, cat in SYMPTOM_CATEGORIES.items() 
            if cat.esi_level == target_level
        ]
        
        if not level_categories:
            return None
        
        target_category_id, target_category = random.choice(level_categories)
        
        dialect_instructions = {
            "egyptian": "استخدم اللهجة المصرية العامية الشائعة (مثل: عندي، بيوجعني، مش عارف)",
            "levantine": "استخدم اللهجة الشامية (مثل: عندي، بيوجعني، ما بقدر)",
            "gulf": "استخدم اللهجة الخليجية (مثل: عندي، يوجعني، ما أقدر)",
        }
        
        prompt = f"""أنت طبيب طوارئ مصري خبير. أنشئ سيناريو مريض واقعي.

المطلوب: سيناريو مستوى {target_level} - فئة: {target_category.name_ar} ({target_category.name_en})

{dialect_instructions.get(dialect, dialect_instructions["egyptian"])}

أنشئ شكوى واقعية كما يقولها مريض حقيقي (ليست طبية).
استخدم تعبيرات مختلفة ومتنوعة عن المعتاد.

أجب بـ JSON فقط:
{{
    "complaint_ar": "شكوى المريض بالعربية العامية",
    "complaint_en": "English translation",
    "age": 45,
    "gender": "male",
    "vitals": {{"hr": 90, "rr": 18, "spo2": 98, "sbp": 120, "temp": 37.0, "gcs": 15, "pain_score": 5}},
    "clinical_reasoning": "سبب التصنيف",
    "key_phrases": ["عبارة1", "عبارة2"]
}}

الـ key_phrases: أهم الكلمات/العبارات في الشكوى التي يجب أن تؤدي للتصنيف الصحيح."""

        response = self._api_call_with_retry(prompt)
        
        if not response:
            return None
        
        try:
            # Extract JSON
            if "```json" in response:
                response = response.split("```json")[1].split("```")[0]
            elif "```" in response:
                response = response.split("```")[1].split("```")[0]
            
            data = json.loads(response)
            self.scenario_count += 1
            
            return ClinicalScenario(
                scenario_id=f"AI-{datetime.now().strftime('%H%M%S')}-{self.scenario_count:04d}",
                complaint_ar=data["complaint_ar"],
                complaint_en=data["complaint_en"],
                age=data["age"],
                gender=data["gender"],
                vitals=data.get("vitals", {}),
                expected_level=target_level,
                expected_category=target_category_id,
                clinical_reasoning=data.get("clinical_reasoning", ""),
                dialect=dialect,
                key_phrases=data.get("key_phrases", [])
            )
        except Exception as e:
            print(f"❌ JSON Parse Error: {e}")
            return None
    
    def extract_keywords_for_fix(self, scenario: ClinicalScenario, actual_category: str) -> List[str]:
        """Use AI to extract keywords that should fix the misclassification"""
        
        prompt = f"""أنت خبير في معالجة اللغة العربية الطبية.

حدثت مشكلة في تصنيف شكوى مريض:
- الشكوى: "{scenario.complaint_ar}"
- التصنيف المتوقع: {scenario.expected_category} (المستوى {scenario.expected_level})
- التصنيف الفعلي: {actual_category}

استخرج الكلمات المفتاحية العربية (2-4 كلمات) من الشكوى التي يجب إضافتها لقاموس الكلمات المفتاحية لفئة "{scenario.expected_category}" لتجنب هذا الخطأ مستقبلاً.

أجب بـ JSON فقط:
{{"keywords": ["كلمة1", "كلمة2"]}}"""

        response = self._api_call_with_retry(prompt)
        
        if not response:
            # Fallback: extract words from complaint
            words = [w for w in scenario.complaint_ar.split() if len(w) > 2]
            return words[:3]
        
        try:
            if "```json" in response:
                response = response.split("```json")[1].split("```")[0]
            elif "```" in response:
                response = response.split("```")[1].split("```")[0]
            
            data = json.loads(response)
            return data.get("keywords", [])
        except:
            words = [w for w in scenario.complaint_ar.split() if len(w) > 2]
            return words[:3]
    
    def test_scenario(self, scenario: ClinicalScenario) -> TestResult:
        """Test a scenario and extract improvement keywords if needed"""
        
        patient_data = {
            "age": scenario.age,
            "gender": scenario.gender,
            "chief_complaint_text": scenario.complaint_ar,
            "vitals": scenario.vitals
        }
        
        result = self.engine.triage(patient_data)
        
        # Check correctness
        level_diff = abs(result.final_level - scenario.expected_level)
        is_correct = level_diff == 0
        
        # Determine severity
        if is_correct:
            severity = "none"
        elif level_diff == 1:
            severity = "minor"
        elif level_diff == 2:
            severity = "major"
        else:
            severity = "critical"
        
        # Critical if under-triaged emergency
        if scenario.expected_level <= 2 and result.final_level > scenario.expected_level:
            severity = "critical"
        
        # Extract keywords for improvement if misclassified
        suggested_keywords = []
        if not is_correct:
            suggested_keywords = self.extract_keywords_for_fix(scenario, result.category)
            
            # Store learned keywords
            category = scenario.expected_category
            if category not in self.new_keywords_learned:
                self.new_keywords_learned[category] = []
            self.new_keywords_learned[category].extend(suggested_keywords)
        
        test_result = TestResult(
            scenario=scenario,
            actual_level=result.final_level,
            actual_category=result.category,
            decision_path=result.decision_path,
            is_correct=is_correct,
            severity=severity,
            suggested_keywords=suggested_keywords,
            timestamp=datetime.now().isoformat()
        )
        
        self.results.append(test_result)
        if not is_correct:
            self.misclassifications.append(test_result)
        
        return test_result
    
    def run_teaching_session(self, num_scenarios: int = 10, verbose: bool = True) -> Dict:
        """Run a teaching session"""
        
        print("=" * 70)
        print("🎓 AI Teaching Agent - Learning Session")
        print(f"   Target: {num_scenarios} scenarios | Rate limit: {self.rate_limit_delay}s")
        print("=" * 70)
        
        self.results = []
        self.misclassifications = []
        self.new_keywords_learned = {}
        
        successful = 0
        for i in range(num_scenarios):
            print(f"\n[{i+1}/{num_scenarios}] Generating scenario...", end=" ")
            
            scenario = self.generate_scenario()
            
            if not scenario:
                print("❌ Failed to generate")
                continue
            
            result = self.test_scenario(scenario)
            successful += 1
            
            if verbose:
                status = "✅" if result.is_correct else f"❌ [{result.severity.upper()}]"
                print(f"{status}")
                print(f"   📝 {scenario.complaint_ar[:60]}...")
                print(f"   Expected: L{scenario.expected_level} ({scenario.expected_category})")
                print(f"   Actual:   L{result.actual_level} ({result.actual_category})")
                
                if result.suggested_keywords:
                    print(f"   💡 Keywords to add: {', '.join(result.suggested_keywords)}")
        
        # Calculate summary
        summary = self._generate_summary(successful)
        
        # Save learned keywords
        if self.new_keywords_learned:
            self._save_learned_keywords()
        
        # Save session log
        self._save_session_log(summary)
        
        return summary
    
    def _generate_summary(self, total: int) -> Dict:
        """Generate session summary"""
        
        correct = sum(1 for r in self.results if r.is_correct)
        critical = sum(1 for r in self.results if r.severity == "critical")
        major = sum(1 for r in self.results if r.severity == "major")
        minor = sum(1 for r in self.results if r.severity == "minor")
        
        # Count new keywords
        total_new_keywords = sum(len(kws) for kws in self.new_keywords_learned.values())
        
        summary = {
            "total_scenarios": total,
            "successful_tests": len(self.results),
            "correct": correct,
            "accuracy": round(correct / len(self.results) * 100, 1) if self.results else 0,
            "critical_misses": critical,
            "major_misses": major,
            "minor_misses": minor,
            "new_keywords_learned": total_new_keywords,
            "api_calls": self.api_calls,
            "timestamp": datetime.now().isoformat()
        }
        
        print("\n" + "=" * 70)
        print("📊 SESSION SUMMARY")
        print("=" * 70)
        print(f"   Scenarios Tested: {len(self.results)}")
        print(f"   Accuracy:         {summary['accuracy']}%")
        print(f"   Critical Misses:  {critical} 🚨")
        print(f"   Major Misses:     {major} ⚠️")
        print(f"   Minor Misses:     {minor} ℹ️")
        print(f"   New Keywords:     {total_new_keywords} 💡")
        print(f"   API Calls:        {self.api_calls}")
        print("=" * 70)
        
        if self.new_keywords_learned:
            print("\n💡 KEYWORDS LEARNED THIS SESSION:")
            for category, keywords in self.new_keywords_learned.items():
                unique_kws = list(set(keywords))[:5]
                print(f"   {category}: {', '.join(unique_kws)}")
        
        return summary
    
    def _save_learned_keywords(self):
        """Save newly learned keywords"""
        
        for category, new_kws in self.new_keywords_learned.items():
            if category not in self.learned_keywords:
                self.learned_keywords[category] = []
            
            # Add unique keywords
            for kw in new_kws:
                if kw and kw not in self.learned_keywords[category]:
                    self.learned_keywords[category].append(kw)
        
        save_learned_keywords(self.learned_keywords)
        print(f"\n💾 Learned keywords saved to: {LEARNED_KEYWORDS_FILE}")
    
    def _save_session_log(self, summary: Dict):
        """Save session log"""
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = os.path.join(self.log_dir, f"ai_session_{timestamp}.json")
        
        log_data = {
            "summary": summary,
            "new_keywords": self.new_keywords_learned,
            "misclassifications": [
                {
                    "scenario_id": r.scenario.scenario_id,
                    "complaint_ar": r.scenario.complaint_ar,
                    "expected_level": r.scenario.expected_level,
                    "expected_category": r.scenario.expected_category,
                    "actual_level": r.actual_level,
                    "actual_category": r.actual_category,
                    "severity": r.severity,
                    "suggested_keywords": r.suggested_keywords
                }
                for r in self.misclassifications
            ]
        }
        
        with open(log_file, 'w', encoding='utf-8') as f:
            json.dump(log_data, f, ensure_ascii=False, indent=2)
        
        print(f"📁 Session log: {log_file}")
    
    def continuous_learning(self, iterations: int = 5, scenarios_per_iteration: int = 10):
        """Run continuous learning sessions"""
        
        print("\n" + "🔄" * 35)
        print("🎓 CONTINUOUS LEARNING MODE")
        print(f"   Iterations: {iterations} | Scenarios each: {scenarios_per_iteration}")
        print("🔄" * 35)
        
        all_summaries = []
        
        for i in range(iterations):
            print(f"\n{'='*70}")
            print(f"📚 ITERATION {i+1}/{iterations}")
            print(f"{'='*70}")
            
            summary = self.run_teaching_session(scenarios_per_iteration, verbose=True)
            all_summaries.append(summary)
            
            # Wait between iterations to respect rate limits
            if i < iterations - 1:
                print(f"\n⏳ Waiting 60s before next iteration...")
                time.sleep(60)
        
        # Final summary
        print("\n" + "=" * 70)
        print("📊 FINAL LEARNING SUMMARY")
        print("=" * 70)
        
        total_scenarios = sum(s["successful_tests"] for s in all_summaries)
        total_correct = sum(s["correct"] for s in all_summaries)
        total_keywords = sum(s["new_keywords_learned"] for s in all_summaries)
        
        print(f"   Total Scenarios: {total_scenarios}")
        print(f"   Overall Accuracy: {round(total_correct/total_scenarios*100, 1) if total_scenarios else 0}%")
        print(f"   Total Keywords Learned: {total_keywords}")
        
        print("\n   Accuracy Trend:")
        for i, s in enumerate(all_summaries):
            bar = "█" * int(s["accuracy"] / 5)
            print(f"   Iteration {i+1}: {bar} {s['accuracy']}%")
        
        print("=" * 70)
        
        # Show all learned keywords
        if self.learned_keywords:
            print("\n📚 ALL LEARNED KEYWORDS:")
            for category, keywords in sorted(self.learned_keywords.items()):
                if keywords:
                    print(f"   {category}: {', '.join(keywords[:10])}")
    
    def export_keywords_for_integration(self) -> str:
        """
        Export learned keywords in a format ready to copy into deterministic_triage.py
        """
        if not self.learned_keywords:
            return "No keywords learned yet."
        
        output = []
        output.append("# Keywords learned by AI Teaching Agent")
        output.append("# Add these to the appropriate category in _fallback_keyword_match()\n")
        
        for category, keywords in sorted(self.learned_keywords.items()):
            if keywords:
                unique_kws = list(set(keywords))
                formatted = ', '.join(f'"{kw}"' for kw in unique_kws)
                output.append(f'# {category}:')
                output.append(f'# Add: [{formatted}]')
                output.append("")
        
        result = "\n".join(output)
        
        # Also save to file
        export_file = os.path.join(self.log_dir, "keywords_to_add.txt")
        with open(export_file, 'w', encoding='utf-8') as f:
            f.write(result)
        
        print(f"📁 Keywords exported to: {export_file}")
        return result


# =============================================================================
# MAIN
# =============================================================================

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="AI Teaching Agent for SAFE-Triage")
    parser.add_argument("--scenarios", "-n", type=int, default=10,
                       help="Number of scenarios per session (default: 10)")
    parser.add_argument("--continuous", "-c", action="store_true",
                       help="Run continuous learning mode")
    parser.add_argument("--iterations", "-i", type=int, default=3,
                       help="Iterations for continuous mode (default: 3)")
    parser.add_argument("--delay", "-d", type=float, default=2.0,
                       help="Delay between API calls in seconds (default: 2.0)")
    parser.add_argument("--export", "-e", action="store_true",
                       help="Export learned keywords")
    
    args = parser.parse_args()
    
    agent = AITeachingAgent(rate_limit_delay=args.delay)
    
    if args.export:
        print(agent.export_keywords_for_integration())
    elif args.continuous:
        agent.continuous_learning(
            iterations=args.iterations,
            scenarios_per_iteration=args.scenarios
        )
    else:
        agent.run_teaching_session(num_scenarios=args.scenarios)
