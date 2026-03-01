# Phase 4 Deployment Validation

Date: 2026-02-05
Revision: safe-triage-00014-gjm
Service URL: https://safe-triage-459364571026.us-central1.run.app

## 1) Cold Start Check
- `/health` response time: **~0.42s** (min-instances=1 enabled)
- Target: <1s ✅

Command:
```
curl -s -o /dev/null -w "code:%{http_code} time:%{time_total}\n" https://safe-triage-459364571026.us-central1.run.app/health
```

## 2) Voice Input
- `/transcribe` with silent WAV succeeded (Speech-to-Text ar-EG)
- Response: `{"success":true,"transcription":""}`

Command:
```
curl -X POST "https://safe-triage-459364571026.us-central1.run.app/transcribe" \
  -F "audio=@backend/tests/sample_silence.wav" \
  -F "language=ar-EG"
```

## 3) Human Confirmation
- `/confirm-triage` succeeded with defaults
- Response: `{"status":"confirmed"}`

Command:
```
curl -X POST "https://safe-triage-459364571026.us-central1.run.app/confirm-triage" \
  -H "Content-Type: application/json" \
  -d '{"patient_id":"TEST","recommended_esi":2,"confirmed_esi":2,"clinician_id":"nurse_test","action":"confirmed"}'
```

## 4) UMLS RAG (Validated)
- Successful `/ai-triage` response with:
  - ESI level: 2
  - SNOMED: 225566008
  - ICD-10: I20

Command:
```
curl -X POST "https://safe-triage-459364571026.us-central1.run.app/ai-triage" \
  -H "Content-Type: application/json" \
  -d '{"patient_id":"TEST","age":58,"gender":"male","chief_complaint_text":"chest pain radiating to arm","vitals":{"hr":95,"sbp":140,"dbp":90,"rr":18,"temp":37,"spo2":97},"consciousness":"A"}'
```

## 5) Local Test Suite
- `test_triage_scenarios.py`: **50/50 passed**
- `test_english_scenarios.py`: **88 total, 58 passed, 30 over-triage (no critical under-triage)**
- `test_triage_v2.py`: **3/6 groups passed** (AI disabled offline)

## 6) Deterministic /triage Smoke Test
- Successful `/triage` request requires the same core schema as `/ai-triage`:
  - `chief_complaint_text`
  - complete `vitals` (`hr`, `sbp`, `dbp`, `rr`, `temp`, `spo2`)
- A payload with only `complaint` will fail request validation.

Command:
```
curl -X POST "https://safe-triage-eciux5h4aq-uc.a.run.app/triage" \
  -H "Content-Type: application/json" \
  -d '{"patient_id":"TEST-TRIAGE","age":40,"gender":"male","chief_complaint_text":"severe headache","vitals":{"hr":88,"sbp":130,"dbp":82,"rr":18,"temp":37,"spo2":98},"consciousness":"A"}'
```

Artifacts:
- `backend/tests/results.txt`
- `backend/tests/results_english.txt`
- `backend/tests/results_triage_v2.txt`
