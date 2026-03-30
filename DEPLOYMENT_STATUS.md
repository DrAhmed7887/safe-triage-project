# DEPLOYMENT STATUS
**Date:** 2026-03-30
**Backend:** `safe-triage-00176-nkv` (`us-central1`)
**Backend URL:** `https://safe-triage-459364571026.us-central1.run.app`  
**Frontend URL:** `https://safe-triage-ai.web.app`  
**Notice:** `According to GAHAR Standards | وفقاً لمعايير الجهار`

## Cloud Run Topology
```text
safe-triage-ai
├── safe-triage (us-central1)
│   ├── role: canonical production backend
│   ├── revision: safe-triage-00176-nkv
│   ├── url: https://safe-triage-eciux5h4aq-uc.a.run.app
│   └── status: ready
├── safe-triage (me-west1)
│   ├── role: legacy backend snapshot
│   ├── revision: safe-triage-00031-6qn
│   ├── url: https://safe-triage-eciux5h4aq-zf.a.run.app
│   └── status: ready but stale
├── safe-triage (...-ew.a.run.app)
│   ├── role: extra legacy/test service with same name
│   └── status: do not use for routine validation or release checks
├── safe-triage-api
└── safe-triage-frontend
```

## Release Rule
- Treat `safe-triage` in `us-central1` as the only production deploy target.
- Treat the other same-name Cloud Run services as legacy/test artifacts until they are intentionally retired.
- Use the GitHub workflow in `.github/workflows/cloud-run-deploy.yml` to validate the production target before release.

## Working Features
- [x] AI triage endpoint stable (`/ai-triage`)
- [x] Stroke classification guardrails (English + Arabic acute neuro patterns)
- [x] Category-specific action text routing
- [x] Resource label keyword matching + bilingual labels
- [x] FCM push alert service with SendGrid email fallback (no n8n dependency)
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

## Runtime Config Reference
- Core deploy env in GitHub Actions: `PYTHONUNBUFFERED`, `GEMINI_API_KEY`, `PROJECT_ID`, `FIREBASE_PROJECT_ID`, `ALERT_FRONTEND_URL`
- Defaults exist in code for many operational settings, including `SUPERVISOR_PIN`, `CONFIRMATION_TIMEOUT_SECONDS`, `DOWNGRADE_ROLE`, `DATASET_ID`, `TRIAGE_TABLE`, `BQ_LOCATION`, `VERTEX_REGION`, `ALERT_FCM_TOPIC`, and `ALERT_RECIPIENT_NAME`
- Optional integrations only need extra config when the feature is enabled:
  - `UMLS_API_KEY`
  - `USE_VERTEX_SPEECH`
  - `SENDGRID_API_KEY`
  - `ALERT_EMAIL_TO`
  - `ALERT_EMAIL_RECIPIENTS`
  - `ALERT_EMAIL_FROM`
  - `DR7_API_KEY`
  - `QA_FLAGS_TABLE`
  - `QA_REVIEWS_TABLE`
  - `QA_MODEL`
  - `QA_MAX_CASES`

## Final Status
- Canonical production backend is healthy in `us-central1` and serving traffic.
- Repo docs and workflow are now the primary release source of truth for HSIL demo prep.
