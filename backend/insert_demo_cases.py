#!/usr/bin/env python3
"""
Insert demo cases into SAFE-Triage via the live API.
Includes a "Silent MI" trap case that MedGemma should flag.
"""

import requests
import json
import time

BASE_URL = "https://safe-triage-459364571026.us-central1.run.app"

# Demo cases — mix of normal + trap cases
DEMO_CASES = [
    {
        "name": "🎯 TRAP: Silent MI in Diabetic (MedGemma should catch this!)",
        "payload": {
            "patient_id": "900001",
            "chief_complaint_text": "حرقان في المعدة خفيف من الصبح",
            "age": 58,
            "gender": "male",
            "vitals": {
                "hr": 88,
                "sbp": 138,
                "dbp": 85,
                "rr": 16,
                "spo2": 98,
                "temp": 37.0,
                "consciousness": "alert"
            }
        }
    },
    {
        "name": "✅ Normal: Mild headache",
        "payload": {
            "patient_id": "900002",
            "chief_complaint_text": "عندي صداع خفيف من امبارح",
            "age": 32,
            "gender": "female",
            "vitals": {
                "hr": 72,
                "sbp": 120,
                "dbp": 78,
                "rr": 14,
                "spo2": 99,
                "temp": 36.8,
                "consciousness": "alert"
            }
        }
    },
    {
        "name": "🎯 TRAP: Elderly with 'dizziness' (possible stroke)",
        "payload": {
            "patient_id": "900003",
            "chief_complaint_text": "دوخة وتنميل في ايدي الشمال",
            "age": 72,
            "gender": "male",
            "vitals": {
                "hr": 92,
                "sbp": 175,
                "dbp": 95,
                "rr": 18,
                "spo2": 96,
                "temp": 37.1,
                "consciousness": "alert"
            }
        }
    },
    {
        "name": "✅ Normal: Sore throat",
        "payload": {
            "patient_id": "900004",
            "chief_complaint_text": "زوري بيوجعني من 3 ايام",
            "age": 25,
            "gender": "female",
            "vitals": {
                "hr": 78,
                "sbp": 115,
                "dbp": 72,
                "rr": 15,
                "spo2": 99,
                "temp": 37.8,
                "consciousness": "alert"
            }
        }
    },
    {
        "name": "🎯 TRAP: Young female with back pain (possible ectopic)",
        "payload": {
            "patient_id": "900005",
            "chief_complaint_text": "ألم في بطني من تحت ناحية الشمال ووجع في ضهري",
            "age": 28,
            "gender": "female",
            "vitals": {
                "hr": 105,
                "sbp": 100,
                "dbp": 65,
                "rr": 20,
                "spo2": 98,
                "temp": 37.2,
                "consciousness": "alert"
            }
        }
    },
]


def send_triage(case):
    """Send a triage request to the live API."""
    print(f"\n{'='*60}")
    print(f"Sending: {case['name']}")
    print(f"Patient: {case['payload']['patient_id']}")
    print(f"Complaint: {case['payload']['chief_complaint_text']}")

    try:
        resp = requests.post(
            f"{BASE_URL}/triage",
            json=case["payload"],
            timeout=30,
        )

        if resp.status_code == 200:
            data = resp.json()
            esi = data.get("esi_level") or data.get("final_esi") or data.get("esi")
            news2 = data.get("news2_score") or data.get("news2", {}).get("total_score")
            confidence = data.get("ai_confidence")
            print(f"✅ ESI: {esi} | NEWS2: {news2} | Confidence: {confidence}")
            return data
        else:
            print(f"❌ HTTP {resp.status_code}: {resp.text[:200]}")
            return None
    except Exception as e:
        print(f"❌ Error: {e}")
        return None


def main():
    print("🏥 SAFE-Triage Demo Case Insertion")
    print(f"Target: {BASE_URL}")
    print(f"Cases: {len(DEMO_CASES)}")

    # Test connectivity
    try:
        r = requests.get(f"{BASE_URL}/health", timeout=10)
        print(f"\n🟢 Backend is UP (status: {r.status_code})")
    except:
        print(f"\n🔴 Backend is DOWN — cannot proceed")
        return

    results = []
    for case in DEMO_CASES:
        result = send_triage(case)
        results.append(result)
        time.sleep(2)  # Don't hammer the API

    print(f"\n{'='*60}")
    print("📊 SUMMARY")
    print(f"{'='*60}")

    success = sum(1 for r in results if r)
    print(f"Sent: {len(DEMO_CASES)} | Success: {success} | Failed: {len(DEMO_CASES) - success}")

    print(f"\n📸 Next steps:")
    print(f"1. Go to https://dr7.ai/dashboard and add $2 credits")
    print(f"2. Then run: curl -X POST {BASE_URL}/medgemma/hourly-review")
    print(f"3. Screenshot the response — MedGemma should flag DEMO-MI-001!")
    print(f"4. Check BigQuery: SELECT * FROM safe_triage_audit.medgemma_flagged_cases")


if __name__ == "__main__":
    main()
