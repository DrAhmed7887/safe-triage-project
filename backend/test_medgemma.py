#!/usr/bin/env python3
"""
Test MedGemma QA review workflow.
Submits a silent MI test case, triggers /medgemma/review-now, and validates flag.
"""
import json
import sys
import requests

BASE_URL = "https://safe-triage-459364571026.us-central1.run.app"
GAHAR_NOTICE = "🏥 According to GAHAR Standards | وفقاً لمعايير الجهار"


def main() -> int:
    test_case = {
        "patient_id": "TEST-MEDGEMMA-001",
        "age": 58,
        "gender": "male",
        "chief_complaint_text": "عندي سوء هضم من الصبح",
        "vitals": {"hr": 88, "sbp": 135, "dbp": 85, "rr": 16, "temp": 37.0, "spo2": 98},
        "consciousness": "A",
        "comorbidities": ["diabetes", "hypertension"],
    }

    print("Submitting silent MI test case... | إرسال حالة اختبار الذبحة الصامتة...")
    triage_resp = requests.post(f"{BASE_URL}/ai-triage", json=test_case, timeout=30)
    triage_resp.raise_for_status()
    triage_data = triage_resp.json()
    print(json.dumps(triage_data, indent=2, ensure_ascii=False))

    print("\nTriggering MedGemma review... | تشغيل مراجعة MedGemma...")
    review_resp = requests.post(f"{BASE_URL}/medgemma/review-now", timeout=60)
    review_resp.raise_for_status()
    review_data = review_resp.json()

    print(json.dumps(review_data, indent=2, ensure_ascii=False))
    print(f"\n{GAHAR_NOTICE}\n")

    flagged = False
    for item in review_data.get("details", []):
        if item.get("patient_id") == "TEST-MEDGEMMA-001":
            flagged = True
            break

    if flagged:
        print("✅ PASS: MedGemma flagged the silent MI pattern | تم رصد النمط الخطر بنجاح")
        return 0

    print("❌ FAIL: MedGemma did not flag the silent MI case | لم يتم رصد النمط الخطر")
    return 1


if __name__ == "__main__":
    sys.exit(main())
