# SAFE-Triage Safety Plan v2.4

## Scope
This update adds expert-validation safety controls for input quality, vital-sign completeness, glucose risk detection, and ESI-5 assignment strictness.

## Safety Controls Added

1. Input validation hard-stop
- Chief complaint now enforces minimum length, maximum length, letter presence, and rejects numbers-only/symbol-only entries.
- Low-information complaints are rejected with clarification guidance instead of being auto-triaged.

2. Mandatory vital signs
- Required fields: `hr`, `sbp`, `dbp`, `rr`, `spo2`, `temp`, `consciousness`.
- Missing required vitals now return validation errors.
- Life-threatening bypass exists for obvious ESI-1 presentations to avoid blocking resuscitation workflows.

3. NEWS2+ glucose support
- Added optional `blood_glucose` (mg/dL) with red-flag checks:
  - Severe hypoglycemia (`<54`) -> minimum ESI 2.
  - Diabetic hyperglycemia (`>250`) -> DKA concern, minimum ESI 2.
  - Extreme hyperglycemia (`>600`) -> HHS concern, minimum ESI 2.
- NEWS2+ combines base NEWS2 with glucose score contribution.

4. ESI-5 refinement
- ESI 5 now requires strict eligibility (age band, stable physiology, low pain, low-risk complaint profile, no high-risk modifiers).
- Non-eligible cases are automatically moved to ESI 4.

5. Low-confidence and unclear handling
- Very low-confidence or invalid complaint extraction now triggers clarification flow.
- Unrecognized complaints retain conservative handling and review flags; no silent downgrade to non-urgent flow.

## Validation Targets
- Invalid complaint rejection: 100%.
- Missing-vitals rejection: 100% (except ESI-1 bypass cases).
- Glucose red-flag detection: 100% for severe hypo/hyperglycemia scenarios.
- Reduced ESI-4 over-triage to ESI-5-appropriate cases while preserving zero critical under-triage.
