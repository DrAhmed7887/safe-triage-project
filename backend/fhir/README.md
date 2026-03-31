# FHIR Interoperability Module

**Owner:** Amany Moussa (@amanymoussa)

## What is this?

This module converts SAFE-Triage output into [HL7 FHIR R4](https://hl7.org/fhir/R4/) resources so Egyptian hospitals can exchange triage data with any FHIR-compatible Electronic Medical Record (EMR) system.

This is critical for **GAHAR compliance** (Egyptian Hospital Accreditation) and interoperability with national health information exchanges.

## Your Task

Build a Python module (`mapper.py`) that takes a SAFE-Triage result (see `sample_triage_output.json`) and converts it into valid FHIR R4 resources.

### FHIR Resources to Implement

You need to generate **4 FHIR resources** from each triage result:

#### 1. `Patient` Resource
Maps from: `patient.patient_id`, `patient.patient_name`, `patient.age`, `patient.gender`

```json
{
  "resourceType": "Patient",
  "id": "MRN-2024-00147",
  "name": [{"use": "official", "text": "Mohamed Ahmed"}],
  "gender": "male",
  "birthDate": "1968-01-01"
}
```

Reference: https://hl7.org/fhir/R4/patient.html

#### 2. `Encounter` Resource
Maps from: `result.level`, `result.color_code`, `metadata.timestamp`

```json
{
  "resourceType": "Encounter",
  "id": "enc-MRN-2024-00147",
  "status": "triaged",
  "class": {"code": "EMER", "display": "Emergency"},
  "priority": {"coding": [{"system": "http://hl7.org/fhir/v3/ActPriority", "code": "EM"}]},
  "subject": {"reference": "Patient/MRN-2024-00147"},
  "period": {"start": "2026-03-31T14:30:00Z"},
  "reasonCode": [{"text": "Severe chest pain with shortness of breath"}]
}
```

Reference: https://hl7.org/fhir/R4/encounter.html

#### 3. `Observation` Resources (Vitals)
Maps from: `input.vitals` — one Observation per vital sign using LOINC codes

| Vital | LOINC Code | Unit |
|-------|-----------|------|
| Heart Rate | 8867-4 | /min |
| Respiratory Rate | 9279-1 | /min |
| SpO2 | 2708-6 | % |
| Temperature | 8310-5 | Cel |
| Systolic BP | 8480-6 | mm[Hg] |
| Diastolic BP | 8462-4 | mm[Hg] |
| Pain Score | 72514-3 | {score} |
| GCS | 9269-2 | {score} |

```json
{
  "resourceType": "Observation",
  "status": "final",
  "code": {"coding": [{"system": "http://loinc.org", "code": "8867-4", "display": "Heart rate"}]},
  "subject": {"reference": "Patient/MRN-2024-00147"},
  "valueQuantity": {"value": 112, "unit": "/min", "system": "http://unitsofmeasure.org"}
}
```

Reference: https://hl7.org/fhir/R4/observation.html

#### 4. `Condition` Resource
Maps from: `result.icd10_code`, `result.icd10_description`, `input.chief_complaint_text`

```json
{
  "resourceType": "Condition",
  "subject": {"reference": "Patient/MRN-2024-00147"},
  "code": {
    "coding": [{"system": "http://hl7.org/fhir/sid/icd-10", "code": "I21.9", "display": "Acute myocardial infarction, unspecified"}],
    "text": "ألم شديد في الصدر مع ضيق في التنفس"
  },
  "clinicalStatus": {"coding": [{"code": "active"}]}
}
```

Reference: https://hl7.org/fhir/R4/condition.html

---

## File Structure

```
backend/fhir/
├── __init__.py                  # Module init (done)
├── README.md                    # This file (done)
├── sample_triage_output.json    # Single example input (done)
├── sample_cases.json            # 5 test cases, ESI 1-5 (done)
├── mapper.py                    # YOUR CODE: conversion logic
├── fhir_bundle.py               # YOUR CODE: Bundle wrapper
└── test_fhir.py                 # YOUR CODE: pytest tests
```

## How to Test

```bash
cd backend
pip install pytest
python -m pytest fhir/test_fhir.py -v
```

Test with the 5 sample cases in `sample_cases.json` (one per ESI level 1-5).

## Requirements

- Python 3.10+
- No external FHIR libraries needed — just build plain JSON dicts
- Output must be valid FHIR R4 JSON
- Include Arabic text in `text` fields where available

## DO NOT

- Do NOT import anything from `backend/logic/`
- Do NOT import anything from `backend/ai_service.py`
- Do NOT modify any files outside of `backend/fhir/`
- Do NOT add dependencies to `requirements.txt` without asking Ahmed first
