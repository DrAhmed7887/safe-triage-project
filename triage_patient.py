import sys
import os
# Add backend to path
sys.path.append(os.path.join(os.getcwd(), 'backend'))

from logic.deterministic_triage import DeterministicTriageEngine
from models import PatientInput, Vitals, Gender

def main():
    # Standard mode: No AI, only keyword matching (fast)
    engine = DeterministicTriageEngine(use_ai=False)
    
    patient = PatientInput(
        age=28,
        gender=Gender.FEMALE,
        chief_complaint_text="Abdominal pain and vomiting",
        vitals=Vitals(temp=38.2),
        is_pregnant=True
    )
    
    result = engine.evaluate(patient)
    # Output result as JSON for automated parsing if needed
    import json
    # Use model_dump to get a dict, then convert to JSON
    print(json.dumps(result.model_dump(), indent=2, ensure_ascii=False))

if __name__ == "__main__":
    main()
