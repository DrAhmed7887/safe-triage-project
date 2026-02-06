# TEST RESULTS OVERNIGHT
**Date:** 2026-02-06  
**Environment:** Production Cloud Run (`safe-triage-00060-prc`)  
**Endpoint:** `https://safe-triage-459364571026.us-central1.run.app/ai-triage`  
**Notice:** `According to GAHAR Standards | وفقاً لمعايير الجهار`

## Summary
- Total cases: `10`
- Pass: `10`
- Fail: `0`

## Matrix
| Case | Expected Category | Actual Category | Expected ESI | Actual ESI | ICD-10 | Action Text | Resource Labels | PASS/FAIL |
|---|---|---|---|---|---|---|---|---|
| CASE-01 | chest_pain_cardiac | chest_pain_cardiac | 2 | 2 | I20 | ECG room, continuous monitoring | 12-Lead ECG; Troponin I/T, CK-MB, BNP; Chest X-ray (PA/Lateral) | PASS |
| CASE-02 | chest_pain_cardiac | chest_pain_cardiac | 2 | 2 | I20 | ECG room, continuous monitoring | 12-Lead ECG; Troponin I/T, CK-MB, BNP; CBC, CMP, Coagulation; Chest X-ray (PA/Lateral) | PASS |
| CASE-03 | respiratory_distress | respiratory_distress | 2 | 2 | R06.0 | Resuscitation area, oxygen | CBC, CMP, Coagulation; Chest X-ray (PA/Lateral); 12-Lead ECG; ABG; D-dimer | PASS |
| CASE-04 | stroke_symptoms | stroke_symptoms | 2 | 2 | I63.9 | Stroke bay, CT immediately | CT Scan (specify region); 12-Lead ECG; CBC, CMP, Coagulation; PT/INR; PTT; Troponin I/T, CK-MB, BNP; NIH Stroke Scale assessment | PASS |
| CASE-05 | stroke_symptoms | stroke_symptoms | 2 | 2 | I63.9 | Stroke bay, CT immediately | CT Scan (specify region); 12-Lead ECG; CBC, CMP, Coagulation | PASS |
| CASE-06 | abdominal_pain | abdominal_pain | 3-4 | 3 | R69 | Urgent care area |  | PASS |
| CASE-07 | trauma_fracture | trauma_fracture | 2-3 | 2 | S52.2 | Trauma bay, imaging | X-ray of Affected Limb; Pain Assessment (VAS Scale) | PASS |
| CASE-08 | sepsis_concern | sepsis_concern | 2 | 2 | R69 | Acute care, IV access, labs | CBC, CMP, Coagulation; Urinalysis; Chest X-ray (PA/Lateral); CT Scan (specify region) | PASS |
| CASE-09 | headache | headache_mild | 3-4 | 4 | R69 | Waiting area, routine | Neurovascular Examination; CBC, CMP, Coagulation | PASS |
| CASE-10 | minor_wound | minor_trauma | 4-5 | 4 | R69 | Waiting area, routine | wound examination; irrigation and cleaning; tetanus immunization status check | PASS |

## Notes
- Category normalization accepted aliases:
  - `headache_mild` accepted for expected `headache`
  - `minor_trauma` accepted for expected `minor_wound`
- Full raw JSON responses are stored under `/tmp/safe_matrix_final_post60/`.
