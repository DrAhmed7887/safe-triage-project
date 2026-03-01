# SAFE-Triage API Documentation

## Overview
SAFE-Triage provides clinical decision support for emergency department triage using a hybrid AI + deterministic rules approach.

Base URL (Cloud Run):
- https://safe-triage-eciux5h4aq-uc.a.run.app

## Endpoints

### POST /ai-triage
**Description:** AI-assisted triage assessment (Gemini + UMLS + deterministic ESI rules).

**Request**
```json
{
  "patient_id": "string",
  "age": 58,
  "gender": "male",
  "chief_complaint_text": "chest pain radiating to arm",
  "vitals": {
    "hr": 95,
    "sbp": 140,
    "dbp": 90,
    "rr": 18,
    "temp": 37,
    "spo2": 97
  },
  "consciousness": "A",
  "comorbidities": ["diabetes"]
}
```

**Response (example)**
```json
{
  "level": 2,
  "ai_data": {
    "snomed_code": "225566008",
    "category": "chest_pain_cardiac",
    "icd10_coding": {"primary_code": "I20.9"}
  },
  "red_flags": [],
  "reasoning": ["..."],
  "icd10_coding": {"primary_code": "I20.9"}
}
```

### POST /triage
**Description:** Deterministic triage (no AI).

**Request**
```json
{
  "patient_id": "string",
  "age": 40,
  "gender": "male",
  "chief_complaint_text": "severe headache",
  "vitals": {
    "hr": 88,
    "sbp": 130,
    "dbp": 82,
    "rr": 18,
    "temp": 37,
    "spo2": 98
  },
  "consciousness": "A"
}
```

**cURL smoke test**
```bash
curl -X POST "https://safe-triage-eciux5h4aq-uc.a.run.app/triage" \
  -H "Content-Type: application/json" \
  -d '{"patient_id":"TEST-TRIAGE","age":40,"gender":"male","chief_complaint_text":"severe headache","vitals":{"hr":88,"sbp":130,"dbp":82,"rr":18,"temp":37,"spo2":98},"consciousness":"A"}'
```

**Validation note:** `/triage` requires `chief_complaint_text` and a complete `vitals` object. A payload with only `complaint` will fail schema validation.

### POST /confirm-triage
**Description:** Record human confirmation/override of triage decision.

**Request**
```json
{
  "patient_id": "string",
  "recommended_esi": 2,
  "confirmed_esi": 2,
  "clinician_id": "nurse_01",
  "clinician_role": "nurse",
  "action": "confirmed",
  "override_reason": null,
  "supervisor_pin": null
}
```

### POST /confirm-triage/request
**Description:** Register pending confirmation (for timeout/queue).

### GET /pending-confirmations
**Description:** List pending confirmations.

### POST /transcribe
**Description:** Speech-to-text (ar-EG) using Google Speech-to-Text.

**Multipart Form**
- `audio`: audio file (webm/ogg/wav)
- `language`: `ar-EG` (default)

### GET /health
**Description:** Health check.

## Error Codes
- `400`: validation error
- `401`: invalid supervisor PIN
- `403`: unauthorized downgrade
- `500`: internal error
