"""
SAFE-Triage AI Teaching Agent v2.0
===================================

An AI-powered teaching agent that uses Gemini to:
1. Generate realistic clinical scenarios
2. Test them against the deterministic triage engine
3. Identify misclassifications
4. AUTOMATICALLY update the keyword database to improve accuracy

This creates a continuous learning loop where the AI teaches the 
deterministic system by discovering and fixing gaps in keyword coverage.

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

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from logic.deterministic_triage import DeterministicTriageEngine, SYMPTOM_CATEGORIES
from logic.keyword_database import KeywordDatabase, get_keyword_database

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
    timestamp: str
    keywords_added: List[str]  # Keywords added to fix this


class GeminiTeachingAgent:
    """
    AI Teaching Agent that uses Gemini to continuously improve
    the deterministic triage system.
    
    The agent:
    1. Generates realistic Arabic clinical scenarios
    2. Tests them against the keyword-based classifier
    3. When misclassifications occur, extracts key phrases
    4. Adds those phrases to the keyword database
    5. Verifies the fix works
    """
    
    def __init__(self, log_dir: str = None):
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY not found in environment")
        
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-2.5-flash')
        
        # Triage engine (will be recreated after keyword updates)
        self.engine = DeterministicTriageEngine()
        
        # Keyword database
        self.keyword_db = get_keyword_database()
        
        # Setup logging directory
        if log_dir is None:
            log_dir = os.path.join(os.path.dirname(__file__), "teaching_logs")
        self.log_dir = log_dir
        os.makedirs(log_dir, exist_ok=True)
        
        # Track results
        self.results: List[TestResult] = []
        self.misclassifications: List[TestResult] = []
        self.keywords_added: List[Dict] = []
        
        # Scenario counter
        self.scenario_count = 0
        
        # Rate limiting for Gemini API
        self.last_api_call = 0
        self.min_delay = 1.0  # Minimum 1 second between calls
    
    def _rate_limit(self):
        """Ensure we don't exceed API rate limits"""
        elapsed = time.time() - self.last_api_call
        if elapsed < self.min_delay:
            time.sleep(self.min_delay - elapsed)
        self.last_api_call = time.time()
    
    def _call_gemini(self, prompt: str, max_retries: int = 3) -> Optional[str]:
        """Call Gemini API with retry logic"""
        for attempt in range(max_retries):
            try:
                self._rate_limit()
                response = self.model.generate_content(prompt)
                return response.text.strip()
            except Exception as e:
                error_msg = str(e)
                if "429" in error_msg or "quota" in error_msg.lower():
                    wait_time = (attempt + 1) * 10  # Progressive backoff
                    print(f"   Rate limited. Waiting {wait_time}s...")
                    time.sleep(wait_time)
                else:
                    print(f"   API Error: {e}")
                    return None
        return None
    
    def generate_scenario(self, target_level: int = None, dialect: str = None) -> Optional[ClinicalScenario]:
        """Generate a realistic clinical scenario using Gemini"""
        
        if target_level is None:
            # Weight towards critical levels to find important gaps
            target_level = random.choices([1, 2, 3, 4, 5], weights=[20, 30, 25, 15, 10])[0]
        
        if dialect is None:
            dialect = random.choice(["egyptian", "egyptian", "levantine", "gulf", "msa"])
        
        # Get categories for this level
        level_categories = [
            (cat_id, cat) for cat_id, cat in SYMPTOM_CATEGORIES.items() 
            if cat.esi_level == target_level
        ]
        
        if not level_categories:
            level_categories = [("unclear", SYMPTOM_CATEGORIES["unclear"])]
        
        target_category_id, target_category = random.choice(level_categories)
        
        dialect_instructions = {
            "egyptian": "استخدم اللهجة المصرية العامية الحقيقية (مثل: عندي، بيوجعني، مش عارف، حاسس، جامد، خالص)",
            "levantine": "استخدم اللهجة الشامية (مثل: عندي، بيوجعني، ما بقدر، حاسس، كتير)",  
            "gulf": "استخدم اللهجة الخليجية (مثل: عندي، يوجعني، ما أقدر، حاس، وايد)",
            "msa": "استخدم اللغة العربية الفصحى"
        }
        
        prompt = f"""أنت طبيب طوارئ مصري خبير. أنشئ سيناريو مريض واقعي جداً للتدريب.

المطلوب: سيناريو مستوى {target_level} (ESI)
الفئة المستهدفة: {target_category.name_ar} ({target_category.name_en})
الفئة بالإنجليزية: {target_category_id}

{dialect_instructions[dialect]}

مهم جداً:
1. اجعل الشكوى واقعية جداً كما يقولها مريض حقيقي في الشارع
2. استخدم تعبيرات عامية متنوعة ومختلفة
3. لا تذكر اسم المرض أو التشخيص
4. أضف تفاصيل واقعية (المدة، الشدة، أعراض مصاحبة)

أجب بصيغة JSON فقط بدون أي نص إضافي:
{{
    "complaint_ar": "الشكوى بالعربية العامية",
    "complaint_en": "English translation",
    "age": 45,
    "gender": "male أو female",
    "vitals": {{
        "hr": 90,
        "rr": 18,
        "spo2": 98,
        "sbp": 120,
        "temp": 37.0,
        "gcs": 15,
        "pain_score": 5
    }},
    "clinical_reasoning": "سبب التصنيف بإختصار",
    "key_phrases": ["عبارة مفتاحية 1", "عبارة مفتاحية 2"]
}}"""

        response = self._call_gemini(prompt)
        
        if not response:
            return None
        
        try:
            # Extract JSON from response
            if "```json" in response:
                response = response.split("```json")[1].split("```")[0]
            elif "```" in response:
                response = response.split("```")[1].split("```")[0]
            
            data = json.loads(response)
            
            self.scenario_count += 1
            
            return ClinicalScenario(
                scenario_id=f"AI-{datetime.now().strftime('%Y%m%d%H%M%S')}-{self.scenario_count:04d}",
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
            print(f"   Error parsing scenario: {e}")
            return None
    
    def test_scenario(self, scenario: ClinicalScenario) -> TestResult:
        """Test a scenario against the deterministic engine"""
        
        patient_data = {
            "age": scenario.age,
            "gender": scenario.gender,
            "chief_complaint_text": scenario.complaint_ar,
            "vitals": scenario.vitals
        }
        
        result = self.engine.triage(patient_data)
        
        # Check if level matches
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
        
        # Extra critical if under-triaged emergency
        if scenario.expected_level <= 2 and result.final_level > scenario.expected_level:
            severity = "critical"
        
        test_result = TestResult(
            scenario=scenario,
            actual_level=result.final_level,
            actual_category=result.category,
            decision_path=result.decision_path,
            is_correct=is_correct,
            severity=severity,
            timestamp=datetime.now().isoformat(),
            keywords_added=[]
        )
        
        self.results.append(test_result)
        
        if not is_correct:
            self.misclassifications.append(test_result)
        
        return test_result
    
    def extract_keywords_from_misclassification(self, result: TestResult) -> List[str]:
        """Use Gemini to extract key phrases that should trigger correct classification"""
        
        scenario = result.scenario
        
        prompt = f"""أنت خبير في تصنيف شكاوى الطوارئ.

الشكوى: "{scenario.complaint_ar}"
التصنيف الصحيح: {scenario.expected_category} (مستوى {scenario.expected_level})
التصنيف الخاطئ: {result.actual_category} (مستوى {result.actual_level})

استخرج الكلمات والعبارات المفتاحية من الشكوى التي يجب أن تؤدي للتصنيف الصحيح.

أجب بـ JSON فقط:
{{
    "keywords": ["كلمة1", "كلمة2", "عبارة مهمة"]
}}"""

        response = self._call_gemini(prompt)
        
        if not response:
            # Fallback: use key_phrases from scenario
            return scenario.key_phrases
        
        try:
            if "```json" in response:
                response = response.split("```json")[1].split("```")[0]
            elif "```" in response:
                response = response.split("```")[1].split("```")[0]
            
            data = json.loads(response)
            keywords = data.get("keywords", [])
            
            # Also add key phrases from scenario
            keywords.extend(scenario.key_phrases)
            
            # Remove duplicates
            return list(set(keywords))
            
        except:
            return scenario.key_phrases
    
    def fix_misclassification(self, result: TestResult) -> List[str]:
        """
        Attempt to fix a misclassification by adding keywords to the database.
        Returns list of keywords that were added.
        """
        # Extract keywords
        keywords = self.extract_keywords_from_misclassification(result)
        
        if not keywords:
            return []
        
        added = []
        category = result.scenario.expected_category
        
        for kw in keywords:
            # Clean the keyword
            kw = kw.strip()
            if len(kw) < 2:
                continue
            
            # Try to add it
            if self.keyword_db.add_keyword(category, kw, source="ai"):
                added.append(kw)
                print(f"      ➕ Added keyword: '{kw}' → {category}")
        
        if added:
            # Record the addition
            self.keywords_added.append({
                "scenario_id": result.scenario.scenario_id,
                "category": category,
                "keywords": added,
                "timestamp": datetime.now().isoformat()
            })
            
            result.keywords_added = added
        
        return added
    
    def verify_fix(self, result: TestResult) -> bool:
        """Verify that the fix worked by re-testing the scenario"""
        
        # Recreate engine to pick up new keywords
        # Note: In production, the engine should dynamically load from keyword_db
        
        # For now, test with direct keyword search
        search_result = self.keyword_db.search_keyword(result.scenario.complaint_ar)
        
        if search_result:
            found_category, found_level = search_result
            return found_category == result.scenario.expected_category
        
        return False
    
    def run_teaching_session(self, num_scenarios: int = 20, auto_fix: bool = True) -> Dict:
        """
        Run a teaching session.
        
        Args:
            num_scenarios: Number of scenarios to generate and test
            auto_fix: Automatically add keywords to fix misclassifications
        """
        print("=" * 70)
        print("🎓 SAFE-Triage AI Teaching Agent v2.0")
        print(f"   Generating and testing {num_scenarios} clinical scenarios")
        print(f"   Auto-fix mode: {'ON' if auto_fix else 'OFF'}")
        print("=" * 70)
        
        session_start = datetime.now()
        self.results = []
        self.misclassifications = []
        self.keywords_added = []
        
        successful_scenarios = 0
        
        for i in range(num_scenarios):
            print(f"\n[{i+1}/{num_scenarios}] Generating scenario...", end=" ")
            
            # Generate scenario
            scenario = self.generate_scenario()
            
            if scenario is None:
                print("❌ Failed to generate")
                continue
            
            successful_scenarios += 1
            
            # Test it
            result = self.test_scenario(scenario)
            
            # Display result
            if result.is_correct:
                print(f"✅ PASS")
            else:
                print(f"❌ [{result.severity.upper()}]")
                print(f"      Complaint: {scenario.complaint_ar}")
                print(f"      Expected: Level {scenario.expected_level} ({scenario.expected_category})")
                print(f"      Actual:   Level {result.actual_level} ({result.actual_category})")
                
                # Auto-fix if enabled
                if auto_fix and result.severity in ["critical", "major"]:
                    print(f"      🔧 Attempting to fix...")
                    added = self.fix_misclassification(result)
                    if added:
                        # Verify
                        if self.verify_fix(result):
                            print(f"      ✅ Fix verified!")
                        else:
                            print(f"      ⚠️ Fix may need manual review")
        
        # Calculate statistics
        total = len(self.results)
        correct = sum(1 for r in self.results if r.is_correct)
        critical_misses = sum(1 for r in self.results if r.severity == "critical")
        major_misses = sum(1 for r in self.results if r.severity == "major")
        minor_misses = sum(1 for r in self.results if r.severity == "minor")
        total_keywords_added = sum(len(k["keywords"]) for k in self.keywords_added)
        
        summary = {
            "session_id": session_start.strftime("%Y%m%d_%H%M%S"),
            "total_scenarios": total,
            "successful_generations": successful_scenarios,
            "correct": correct,
            "accuracy": round(correct / total * 100, 1) if total > 0 else 0,
            "critical_misses": critical_misses,
            "major_misses": major_misses,
            "minor_misses": minor_misses,
            "keywords_added": total_keywords_added,
            "duration_seconds": (datetime.now() - session_start).total_seconds()
        }
        
        print("\n" + "=" * 70)
        print("📊 SESSION SUMMARY")
        print("=" * 70)
        print(f"   Scenarios Generated: {successful_scenarios}/{num_scenarios}")
        print(f"   Total Tested:        {total}")
        print(f"   Correct:             {correct} ({summary['accuracy']}%)")
        print(f"   Critical Misses:     {critical_misses} 🚨")
        print(f"   Major Misses:        {major_misses} ⚠️")
        print(f"   Minor Misses:        {minor_misses} ℹ️")
        print(f"   Keywords Added:      {total_keywords_added} 📝")
        print(f"   Duration:            {summary['duration_seconds']:.1f}s")
        print("=" * 70)
        
        # Save session log
        self._save_session_log(summary)
        
        return summary
    
    def _save_session_log(self, summary: Dict):
        """Save session results to log file"""
        timestamp = summary["session_id"]
        log_file = os.path.join(self.log_dir, f"ai_session_{timestamp}.json")
        
        log_data = {
            "summary": summary,
            "results": [
                {
                    "scenario_id": r.scenario.scenario_id,
                    "complaint_ar": r.scenario.complaint_ar,
                    "complaint_en": r.scenario.complaint_en,
                    "expected_level": r.scenario.expected_level,
                    "expected_category": r.scenario.expected_category,
                    "actual_level": r.actual_level,
                    "actual_category": r.actual_category,
                    "is_correct": r.is_correct,
                    "severity": r.severity,
                    "keywords_added": r.keywords_added
                }
                for r in self.results
            ],
            "keywords_added": self.keywords_added,
            "database_stats": self.keyword_db.get_stats()
        }
        
        with open(log_file, 'w', encoding='utf-8') as f:
            json.dump(log_data, f, ensure_ascii=False, indent=2)
        
        print(f"\n📁 Session log: {log_file}")
    
    def continuous_learning(self, 
                           iterations: int = 5, 
                           scenarios_per_iteration: int = 10,
                           target_accuracy: float = 90.0):
        """
        Run continuous learning until target accuracy is reached.
        
        Args:
            iterations: Maximum number of iterations
            scenarios_per_iteration: Scenarios to test per iteration
            target_accuracy: Stop when this accuracy is reached
        """
        print("\n" + "🔄" * 35)
        print("🎓 CONTINUOUS LEARNING MODE")
        print(f"   Target Accuracy: {target_accuracy}%")
        print("🔄" * 35)
        
        all_summaries = []
        
        for i in range(iterations):
            print(f"\n{'='*70}")
            print(f"📚 ITERATION {i+1}/{iterations}")
            print(f"{'='*70}")
            
            summary = self.run_teaching_session(
                num_scenarios=scenarios_per_iteration,
                auto_fix=True
            )
            all_summaries.append(summary)
            
            # Check if target reached
            if summary["accuracy"] >= target_accuracy:
                print(f"\n🎉 TARGET ACCURACY REACHED: {summary['accuracy']}%")
                break
            
            # Show progress
            print(f"\n📈 Progress: {summary['accuracy']}% → Target: {target_accuracy}%")
        
        # Final summary
        print("\n" + "=" * 70)
        print("📊 FINAL LEARNING SUMMARY")
        print("=" * 70)
        
        total_scenarios = sum(s["total_scenarios"] for s in all_summaries)
        total_correct = sum(s["correct"] for s in all_summaries)
        total_keywords = sum(s["keywords_added"] for s in all_summaries)
        
        print(f"   Total Iterations:        {len(all_summaries)}")
        print(f"   Total Scenarios Tested:  {total_scenarios}")
        print(f"   Overall Accuracy:        {round(total_correct/total_scenarios*100, 1) if total_scenarios > 0 else 0}%")
        print(f"   Total Keywords Added:    {total_keywords}")
        
        # Show accuracy trend
        print("\n   📈 Accuracy Trend:")
        for i, s in enumerate(all_summaries):
            bar = "█" * int(s["accuracy"] / 5)
            print(f"   Iteration {i+1}: {bar} {s['accuracy']}% (+{s['keywords_added']} keywords)")
        
        # Database stats
        print("\n   📚 Keyword Database Stats:")
        stats = self.keyword_db.get_stats()
        print(f"   Total Keywords: {stats['total_keywords']}")
        print(f"   Updates Count:  {stats['updates_count']}")
        
        print("=" * 70)
        
        return all_summaries


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description="SAFE-Triage AI Teaching Agent")
    parser.add_argument("--scenarios", "-n", type=int, default=10,
                       help="Number of scenarios per session (default: 10)")
    parser.add_argument("--continuous", "-c", action="store_true",
                       help="Run continuous learning mode")
    parser.add_argument("--iterations", "-i", type=int, default=5,
                       help="Number of iterations for continuous mode (default: 5)")
    parser.add_argument("--target", "-t", type=float, default=90.0,
                       help="Target accuracy for continuous mode (default: 90)")
    parser.add_argument("--no-fix", action="store_true",
                       help="Disable auto-fix mode")
    
    args = parser.parse_args()
    
    try:
        agent = GeminiTeachingAgent()
        
        if args.continuous:
            agent.continuous_learning(
                iterations=args.iterations,
                scenarios_per_iteration=args.scenarios,
                target_accuracy=args.target
            )
        else:
            agent.run_teaching_session(
                num_scenarios=args.scenarios,
                auto_fix=not args.no_fix
            )
    
    except ValueError as e:
        print(f"❌ Error: {e}")
        print("   Make sure GEMINI_API_KEY is set in your .env file")
        sys.exit(1)


if __name__ == "__main__":
    main()
