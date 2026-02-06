# DEPLOYMENT STATUS
**Date:** 2026-02-06  
**Backend:** `safe-triage-00060-prc` (`us-central1`)  
**Backend URL:** `https://safe-triage-459364571026.us-central1.run.app`  
**Frontend URL:** `https://safe-triage-ai.web.app`  
**Notice:** `According to GAHAR Standards | وفقاً لمعايير الجهار`

## Working Features
- [x] AI triage endpoint stable (`/ai-triage`)
- [x] Stroke classification guardrails (English + Arabic acute neuro patterns)
- [x] Category-specific action text routing
- [x] Resource label keyword matching + bilingual labels
- [x] Telegram direct alert service (no n8n dependency)
- [x] Confirmation flow endpoints (`/confirm-triage/request`, `/confirm-triage`)
- [x] BigQuery confirmation audit logging
- [x] `/health` reports AI/RAG/QA/BigQuery/alerts status
- [x] MedGemma endpoints (`/medgemma/status`, `/medgemma/review-now`)
- [x] Homepage redesign deployed with login CTA and new safety-staff section

## Critical Bugs Fixed
- [x] `send_critical_alert` mismatch resolved by using `send_alert_sync`
- [x] `/health` RAG check uses `umls_rag` correctly
- [x] `triage_confirmations` BigQuery table auto-create on startup
- [x] Confirmation/override API calls return success and clear pending queue
- [x] NEWS2 score persists to BigQuery (verified non-zero rows exist)
- [x] Sepsis/headache/minor wound category refinement in AI mapping
- [x] Sepsis action text now category-specific (`Acute care, IV access, labs`)
- [x] Chest pain ICD-10 fallback hardened (`I20.9`) when AI returns `R69`
- [x] MedGemma silent-MI miss fixed with deterministic QA rule

## Verification Snapshot
- Health: `healthy` with all components `ok`.
- Dashboard stats endpoint:
  - `total: 131`
  - `underTriage: 0`
  - `overrideRate: 0.0`
- Confirmation audit rows verified in BigQuery for:
  - `CONFIRM-1770388118` (confirmed)
  - `OVERRIDE-1770388118` (overridden with reason + supervisor)
- 10-case matrix: `10/10 PASS` (see `/Users/ahmedzayed/Downloads/safe-triage-project/TEST_RESULTS_OVERNIGHT.md`).
- MedGemma silent-MI test: `PASS` (see `/Users/ahmedzayed/Downloads/safe-triage-project/MEDGEMMA_TEST_RESULT.md`).

## Known Limitations
- `/reports/daily-summary` is token-protected and correctly returns `401` without Firebase ID token.
- Local generation of `SAMPLE_REPORT.pdf` was blocked in this environment because local Python lacks `reportlab`; production endpoint remains available with auth.
- Some non-specific presentations still map to `R69` by design (when complaint is clinically non-specific).

## Required Env Vars (Runtime)
- `UMLS_API_KEY`
- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHAT_ID`
- `ALERT_RECIPIENT_NAME`
- `SENDGRID_API_KEY` (optional, enables email alerts)
- `ALERT_EMAIL_TO` (required for SendGrid path)
- `ALERT_EMAIL_FROM` (optional, defaults to `ALERT_EMAIL_TO`)
- `SUPERVISOR_PIN`
- `CONFIRMATION_TIMEOUT_SECONDS`
- `DOWNGRADE_ROLE`
- `FIREBASE_PROJECT_ID`
- `PROJECT_ID`
- `DATASET_ID`
- `TRIAGE_TABLE`
- `QA_FLAGS_TABLE`
- `QA_REVIEWS_TABLE`
- `QA_MAX_CASES`
- `QA_MODEL`
- `BQ_LOCATION`
- `VERTEX_REGION`

## Final Status
- Overnight core mission items are complete and deployed on production.
- System is in a team-reviewable state with documented validation artifacts.
