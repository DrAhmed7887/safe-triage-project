# SAFE-Triage · Hospital Lite (Phase 1)

A simplified, offline-capable triage desk experience that reuses the
existing SAFE-Triage clinical design language and — crucially — the
**existing canonical Python deterministic engine** as the source of
truth. The browser keeps a small JS fallback engine for the case when the
network is down, but it never silently replaces the canonical engine.

## Principle

> **Decision support only — clinician must confirm.**
>
> **أداة دعم قرار فقط — يجب على الطبيب التأكيد.**

The deterministic engine *suggests* a triage level. The clinician must
either confirm or override with a free-text reason. AI is **not** in the
decision path in this mode.

## Architecture: one canonical engine, one fallback

```
[ Hospital Lite browser ]
            │
            ▼
   POST /triage  ───────────► [ Python canonical engine ]
            │                  backend/logic/triage_engine_v2.py
            │                  validated by MIETIC, KTAS, NHAMCS
            │                  → engine_source: "python_engine"
            │
            ✗ network / 5xx / timeout
            │
            ▼
   runOfflineFallbackTriage()
   frontend/src/lib/triageEngineOfflineFallback.js
   best-effort JS port — NOT benchmark-validated
   → engine_source: "offline_js_fallback"
   → UI shows orange "offline fallback" banner
```

- **Connected mode:** the canonical Python engine decides. The UI shows
  a green chip *"Online · backend engine"*.
- **Offline / degraded mode:** the JS fallback decides. The UI shows an
  amber banner *"Offline fallback — clinician must verify"*. The same
  warning appears on the queue rail and on the printed handoff record.
- **Audit trail:** the `suggested` event records `engine_source` and, if
  the fallback was used, the `fallback_error.kind` (e.g. `timeout`,
  `network`, `http_error`, `offline`). The handoff record and the JSON
  export include the full audit chain.

The JS engine is **never** the primary decision path. It is a
degraded-mode safety net.

## Parity harness

A small JSON fixture is run through both engines so the fallback cannot
silently drift away from the canonical engine on critical cases.

```bash
# 1. Run canonical engine
python tests/parity/run_python_engine.py
#    → writes tests/parity/python_results.json

# 2. Run JS fallback + compare
node tests/parity/run_js_engine.mjs --compare
```

The parity rule is asymmetric on purpose: JS may over-triage (be more
acute than Python), but **never** under-triage. Per ESI v5, level 1 is
the most acute and level 5 is the least acute, so the assertion is:

```
js_level <= python_level + tolerance     (tolerance=0 by default)
```

If a future change makes JS less acute than Python on any fixture case,
the harness exits with code 1 and the offending case is printed.

### What the harness already caught

Writing this harness immediately surfaced two real issues:

1. **JS keyword brittleness on Arabic word-order** — the fallback's
   keyword list missed _"ألم شديد في الصدر"_ because the modifier
   _شديد_ sat between the head words. Fixed by adding more
   Egyptian-colloquial variants (_ألم شديد في الصدر_, _ضغط في الصدر_,
   _ضيق في الصدر_, _في الصدر_). The Python engine's keyword DB (1,858
   entries) is much richer; the JS fallback always will be poorer at
   Arabic and the docs say so.
2. **Pediatric extreme-NEWS2 under-triage** — for a toddler with HR 170,
   RR 32, T 39.5 °C, JS originally returned L2 while Python returned
   L1. Added a pediatric modifier in the JS fallback: when age < 5 and
   NEWS2 risk is HIGH with ≥2 score-3 parameters, escalate to L1.

This is exactly what the parity harness exists for.

## Files

- `frontend/src/lib/triageClient.js` — calls `/triage` first, falls
  back to JS on failure, normalizes both shapes for the UI
- `frontend/src/lib/triageEngineOfflineFallback.js` — **fallback only**
- `frontend/src/lib/triageEngineOfflineFallback.smoke.mjs` — 12-case
  node smoke test for the fallback alone
- `frontend/src/lib/hospitalLite.js` — local clinician profile, queue, audit
- `frontend/src/lib/i18n.js` — bilingual strings + RTL persistence
- `frontend/src/components/HospitalLite/EngineSourceBadge.jsx` —
  green/amber chip + banner indicating which engine was used
- `frontend/src/components/HospitalLite/*` — UI components (form,
  result, queue rail, handoff)
- `frontend/src/pages/HospitalLite/HospitalLitePage.jsx` — page that
  orchestrates ENTRY → REVIEW → HANDOFF and records `engine_source`
  in the audit trail
- `frontend/src/App.jsx` — branches on `VITE_APP_MODE`
- `frontend/.env.hospital_lite` / `backend/.env.hospital_lite` —
  env presets
- `backend/main.py` — `SAFE_TRIAGE_MODE=hospital_lite` startup gate +
  `/api/mode` endpoint
- `tests/parity/critical_cases.json` — shared fixture
- `tests/parity/run_python_engine.py` — canonical-engine runner
- `tests/parity/run_js_engine.mjs` — fallback runner + parity compare

## Run it locally

### Frontend + backend (connected mode — recommended)

```bash
# Backend (Python canonical engine, all AI/QA disabled in hospital_lite)
export $(grep -v '^#' backend/.env.hospital_lite | xargs)
python -m uvicorn main:app --app-dir backend --reload --port 8000
# Confirm:  curl http://localhost:8000/api/mode

# Frontend
cp frontend/.env.hospital_lite frontend/.env.local
npm --prefix frontend install
npm --prefix frontend run dev -- --host
```

Open `http://<your-ip>:5173` from an iPad on the same Wi-Fi and add to
home screen. The form will round-trip through `/triage` for every
submission.

### Install on iPhone / iPad (PWA — recommended for hackathon demo)

The frontend ships as an installable Progressive Web App. Once
installed it launches full-screen with the SAFE-Triage icon — looks
and feels like a native app.

1. Deploy or `npm run preview` and open the URL in **Safari** on
   iOS (Safari is required for install; Chrome on iOS proxies to the
   same WebKit but its "Add to Home Screen" is degraded).
2. Tap the share icon → **Add to Home Screen** → **Add**.
3. The teal SAFE-Triage icon appears on the home screen. Tapping it
   launches the app in standalone mode (no Safari chrome).

What the PWA gives you:

- **Standalone launch** — no browser UI; honest "feels like an app"
  experience for hackathon judges.
- **Offline shell** — the service worker (`public/sw.js`) caches the
  app shell and hashed JS bundle on first online launch. After that
  the deterministic JS engine runs entirely on-device; flight mode
  and dead Wi-Fi don't break the demo.
- **iOS theme colour** — status bar matches the teal brand.
- **Branded icon** — `public/app-icon.svg` is the source of truth;
  PNG variants for every iOS device size live in
  `public/icons/pwa/` and are regenerated by
  `node frontend/scripts/generate-pwa-icons.mjs`.

### Frontend only (offline fallback path for demoing the degraded mode)

Stop the backend, submit a case in the browser. The amber "Offline
fallback" banner appears and `engine_source: offline_js_fallback` is
recorded in the audit trail. This is the same path the iPad would take
on a flaky Wi-Fi.

## What the backend mode flag does

When `SAFE_TRIAGE_MODE=hospital_lite` the FastAPI startup hook skips:

- AI service / UMLS RAG warmup
- MedGemma hourly QA job preload
- FCM device registration warmup
- BigQuery exporters
- Push alerts to external systems

Deterministic `/triage` and `/confirm-triage` continue to work normally.

## Smoke test

```
$ node frontend/src/lib/triageEngineOfflineFallback.smoke.mjs
... 12 passed, 0 failed (12 total)

$ python tests/parity/run_python_engine.py
$ node tests/parity/run_js_engine.mjs --compare
... All parity checks passed (tolerance=0).
```

## Known issues the parity harness surfaced (canonical engine)

- **Arabic chest pain was being dropped to L4 by the Python engine.** —
  **fixed in this PR.** For phrasings like _"ألم شديد في الصدر منذ
  ساعة"_, _"ضغط في الصدر"_, _"ضيق في الصدر"_, the canonical engine
  used to return L4 with category `severe_pain` because every Arabic
  chest-pain token assumed the pain-word and the chest-word were
  adjacent. A modifier between them (_شديد_, _حاد_) caused the chest
  pathway to miss, and the complaint fell through to the generic
  severe-pain match. Fix: in `backend/logic/deterministic_triage.py`
  (`AISymptomClassifier._fallback_keyword_match`) the
  `chest_discomfort_tokens` list was extended *and* a small
  pain⊕chest co-occurrence check was added so any Arabic pain-word
  (_ألم / وجع / حرقان / ضغط / ضيق / نغزة_) together with any Arabic
  chest-word (_في الصدر / بالصدر / على الصدر / صدري_) routes to
  `chest_pain_cardiac` regardless of word order. Pinned by
  `backend/tests/test_arabic_chest_pain.py` (21 cases) and by the
  five additional Arabic chest-pain rows in the parity fixture.

## What's intentionally out of scope for Phase 1

- Multi-user shared queue with backend persistence (Phase 2).
- Background-sync queue replay. Phase 1 ships a service worker that
  caches the app shell so the PWA boots offline, but per-request
  triages still take the offline JS fallback rather than queuing for
  later replay against the canonical backend.
- Authentication via Firebase — replaced by a local clinician profile
  in localStorage. Sufficient for a single-station pilot; not yet
  hospital-IT ready.
