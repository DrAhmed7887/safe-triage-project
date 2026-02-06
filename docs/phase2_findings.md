# Phase 2 Findings - SAFE-Triage

Date: 2026-02-05

## 1) Cold Start Performance

**Measurement method**
- `curl` against Cloud Run `/health` endpoint.
- First request after idle vs. immediate second request.

**Observed**
- Cold start: **~17.4s** (`/health`, first request)
- Warm: **~0.30s** (`/health`, subsequent requests)

**Interpretation**
- Cold start is above the 5s target.
- Likely dominated by Python imports, Vertex AI init, and UMLS cache access.

**Recommendation (Ahmed approval)**
- Option B: add startup warmup in `main.py` to pre-initialize AI + UMLS cache.
- Option A: set `min-instances=1` for demos if needed.
- Option C: connection pool for SQLite if warmup not sufficient.

---

## 2) Voice Input (Transcribe) Diagnosis

**Live test**
```
POST /transcribe
Response: 500 "Gemini API not configured"
```

**Root causes**
1. `GEMINI_API_KEY` is not set in Cloud Run.
2. `google-genai` package is not installed in the backend container.

**Fix implemented (placeholder)**
- Added optional Speech-to-Text fallback (Google Cloud Speech API).
- New env flag: `USE_VERTEX_SPEECH=true` to enable.
- Added dependency: `google-cloud-speech`.

**Requires Ahmed decision**
- Enable Speech-to-Text API and grant service account permissions.
- Decide whether to keep Gemini multimodal for audio or switch fully to Speech-to-Text.

---

## 3) Human Confirmation Backend (Placeholder)

- `/confirm-triage/request` to register pending confirmation.
- `/pending-confirmations` to list pending confirmations (in-memory placeholder).
- `/confirm-triage` to finalize and log to BigQuery.

**Placeholders**
- Supervisor PIN: `SUPERVISOR_PIN` (default `0000`)
- Timeout: `CONFIRMATION_TIMEOUT_SECONDS` (default `300`)
- Downgrade role: `DOWNGRADE_ROLE` (default `supervisor`)

---

## 4) HuggingFace Cleanup

- Tests now set `DISABLE_RAG=true` before imports to avoid HuggingFace downloads.
- `rag/retriever.py` now respects `DISABLE_RAG` values `true|1|yes`.

---

## Notes
- DNS resolution to the primary Cloud Run URL was intermittent for POST during testing. GET `/health` worked reliably. Measurements were taken from `/health`.
