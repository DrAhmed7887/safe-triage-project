# Changelog

## 2026-02-08 - Critical Safety Improvements

### Added
- Backend chief-complaint validator in `backend/ai_service.py` (`ComplaintValidator`).
- Mandatory vital-sign validator with life-threatening bypass in `backend/logic/deterministic_triage.py` (`VitalSignsValidator`).
- NEWS2+ glucose logic and glucose red-flag checks in `backend/logic/deterministic_triage.py`.
- Strict ESI-5 eligibility gate in `backend/logic/deterministic_triage.py` (`ESI5Criteria`).
- Frontend unusual-vitals confirmation modal in `frontend/src/components/ConfirmationDialog.jsx`.
- Frontend glucose input and styling in `frontend/src/components/TriageForm.jsx` and `frontend/src/styles/vitals.css`.
- Edge-case test dataset in `safe-triage-testing/test_data/edge_cases.json`.

### Changed
- `/triage` and `/ai-triage` now enforce complaint and vital-sign validation before triage scoring in `backend/main.py`.
- AI endpoint now surfaces low-confidence clarification behavior and explicit validation responses instead of silent fallback.
- Test payload mapper now sends `blood_glucose` in `safe-triage-testing/run_batch_test.py`.
- Test-case generator supports `--include-edge-cases` in `safe-triage-testing/generate_test_cases.py`.

### Safety Impact
- Rejects nonsense inputs instead of assigning default ESI.
- Blocks incomplete vital-sign submissions unless life-threatening bypass applies.
- Raises urgency for severe glucose abnormalities.
- Reduces non-urgent over-triage via stricter ESI-5 decision logic.
