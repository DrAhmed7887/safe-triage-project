"""
Test monitor integration by simulating HL7 v2.x JSON payloads.
"""

from datetime import datetime
import os
import requests

API_URL = os.getenv("SAFE_TRIAGE_API_URL", "https://safe-triage-459364571026.us-central1.run.app")


def now_iso() -> str:
    return datetime.utcnow().isoformat()


def print_section(title: str) -> None:
    print("\n" + "=" * 80)
    print(title)
    print("=" * 80)


def main() -> None:
    test_data = {
        "patient_id": "29501012345678",
        "encounter_id": "ED-2026-02-07-001",
        "monitor_type": "Philips IntelliVue MX450",
        "observations": [
            {"loinc_code": "8867-4", "value": 95, "unit": "/min", "timestamp": now_iso(), "device_id": "IntelliVue-MX450-003", "bed_number": "ED-Bed-3"},
            {"loinc_code": "8480-6", "value": 135, "unit": "mmHg", "timestamp": now_iso(), "device_id": "IntelliVue-MX450-003", "bed_number": "ED-Bed-3"},
            {"loinc_code": "8462-4", "value": 85, "unit": "mmHg", "timestamp": now_iso(), "device_id": "IntelliVue-MX450-003", "bed_number": "ED-Bed-3"},
            {"loinc_code": "9279-1", "value": 16, "unit": "/min", "timestamp": now_iso(), "device_id": "IntelliVue-MX450-003", "bed_number": "ED-Bed-3"},
            {"loinc_code": "2708-6", "value": 98, "unit": "%", "timestamp": now_iso(), "device_id": "IntelliVue-MX450-003", "bed_number": "ED-Bed-3"},
            {"loinc_code": "8310-5", "value": 37.0, "unit": "Cel", "timestamp": now_iso(), "device_id": "IntelliVue-MX450-003", "bed_number": "ED-Bed-3"},
        ],
    }

    print_section("TEST 1: Ingest monitor vitals")
    response = requests.post(f"{API_URL}/monitor/vitals/ingest", json=test_data, timeout=30)
    print(response.status_code, response.json())

    print_section("TEST 2: Retrieve cached vitals")
    response = requests.get(f"{API_URL}/monitor/vitals/{test_data['patient_id']}", timeout=30)
    print(response.status_code, response.json())

    print_section("TEST 3: Ingest critical vitals (NEWS2 >= 7)")
    critical_data = {
        **test_data,
        "patient_id": "29501012345679",
        "observations": [
            {"loinc_code": "8867-4", "value": 140, "unit": "/min", "timestamp": now_iso(), "device_id": "IntelliVue-MX450-003", "bed_number": "ED-Bed-5"},
            {"loinc_code": "8480-6", "value": 80, "unit": "mmHg", "timestamp": now_iso(), "device_id": "IntelliVue-MX450-003", "bed_number": "ED-Bed-5"},
            {"loinc_code": "8462-4", "value": 50, "unit": "mmHg", "timestamp": now_iso(), "device_id": "IntelliVue-MX450-003", "bed_number": "ED-Bed-5"},
            {"loinc_code": "9279-1", "value": 28, "unit": "/min", "timestamp": now_iso(), "device_id": "IntelliVue-MX450-003", "bed_number": "ED-Bed-5"},
            {"loinc_code": "2708-6", "value": 88, "unit": "%", "timestamp": now_iso(), "device_id": "IntelliVue-MX450-003", "bed_number": "ED-Bed-5"},
            {"loinc_code": "8310-5", "value": 39.5, "unit": "Cel", "timestamp": now_iso(), "device_id": "IntelliVue-MX450-003", "bed_number": "ED-Bed-5"},
        ],
    }
    response = requests.post(f"{API_URL}/monitor/vitals/ingest", json=critical_data, timeout=30)
    print(response.status_code, response.json())
    print("Check push/email delivery for the critical alert.")


if __name__ == "__main__":
    main()
