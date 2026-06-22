# SAFE-Triage · Hospital Lite — Morning Testing Runbook

This document is the practical companion to `HOSPITAL_LITE.md`. The
architecture doc explains *why* Hospital Lite is built the way it is; this
doc explains *how to actually run it tomorrow morning* and verify it
behaves correctly before any real-world testing.

> **Decision support only — clinician must confirm.**
> **أداة دعم قرار فقط — يجب على الطبيب التأكيد.**

Hospital Lite is **Phase-1 / pilot / shadow-mode** clinical decision
support. It is **not** an approved, certified, or validated clinical
device. Do not use it as a primary triage system for live patient care.

---

## 1. Boot the environment (Codespaces or local Linux)

All commands assume the repo root `/workspaces/safe-triage-project`.

### 1a. Connected mode — the real architecture (recommended)

Two terminals.

**Terminal A — canonical Python engine on port 8000:**

```bash
export $(grep -v '^#' backend/.env.hospital_lite | xargs)
python -m uvicorn main:app --app-dir backend --reload --port 8000
```

You should see `🏥 Hospital Lite mode — skipping AI/UMLS warmup, MedGemma, FCM.`
in the log. Confirm the mode endpoint:

```bash
curl -s http://localhost:8000/api/mode
# → {"mode":"hospital_lite","hospital_lite":true,"decision_support_only":true,...}
```

**Terminal B — Vite dev server on port 5173:**

```bash
cp frontend/.env.hospital_lite frontend/.env.local
npm --prefix frontend install      # first time only
npm --prefix frontend run dev -- --host
```

Open `http://localhost:5173` in a desktop browser, or
`http://<codespace-host>:5173` from the iPad on the same network.
On the iPad, after the page loads tap *Share → Add to Home Screen* — the
viewport meta tags in `frontend/index.html` give it the standalone iOS
look.

### 1b. Offline-fallback mode — for demoing the degraded path

Bring up only Terminal B. Leave the backend stopped (or stop it after
boot). The first triage submission will time out against `/triage` and
the UI switches to the JS fallback. The amber **"Offline fallback —
clinician must verify"** banner must appear before the clinician
confirms.

---

## 2. Smoke / regression suite — run before any demo

```bash
# Python regression (Arabic chest-pain pin)
python -m pytest backend/tests/test_arabic_chest_pain.py -v

# Canonical engine over shared parity fixtures
python tests/parity/run_python_engine.py

# JS fallback smoke (12 cases)
node frontend/src/lib/triageEngineOfflineFallback.smoke.mjs

# JS-vs-Python parity (no under-triage allowed)
node tests/parity/run_js_engine.mjs --compare

# Frontend production build
VITE_APP_MODE=hospital_lite npm --prefix frontend run build
```

All five must finish green. CI runs the same set on every PR touching
the engine, the fallback, the fixtures, or this workflow — see
`.github/workflows/triage-parity.yml`.

---

## 3. Manual QA checklist — eight minutes end-to-end

Run through every box below before showing the app to anyone clinical.

### 3.1 Boot & first paint
- [ ] Hospital Lite shell loads at `/` — no Firebase sign-in, no auth
      redirect. (App.jsx branches on `IS_HOSPITAL_LITE`.)
- [ ] Tab title reads **"SAFE-Triage · Hospital Lite"**.
- [ ] Footer / banner shows **"Decision support only — clinician must
      confirm."** somewhere on screen.
- [ ] EN/AR language toggle works. Switching to AR flips the layout to
      RTL and keeps that choice across reloads.

### 3.2 Clinician gate
- [ ] First load shows the `ClinicianGate`; entering a name + role
      stores a local clinician profile and advances to the workflow.
- [ ] Signing out returns to the gate.

### 3.3 Triage entry form
- [ ] Patient ID "Generate" button produces a deterministic
      `HL-YYYYMMDD-####` identifier.
- [ ] Chief-complaint placeholder reads the Arabic example
      *ألم شديد في الصدر منذ ٣٠ دقيقة* when language is AR.
- [ ] Submitting without a chief complaint or age shows an inline
      bilingual error and does **not** advance.
- [ ] Submitting a valid case shows a brief loading state and then the
      `SuggestedTriage` review screen.

### 3.4 Engine source surfacing
- [ ] **Connected mode:** the green badge **"Online · backend engine"**
      appears on the suggestion card.
- [ ] **Offline mode:** the amber banner **"Offline fallback —
      clinician must verify"** appears with a short error hint
      (`timeout`, `network`, `offline`, `http_error`).
- [ ] Both modes show the **"Decision support only — clinician must
      confirm."** notice on the review card.

### 3.5 Confirmation / override flow
- [ ] **Confirm** writes a queue entry with `action: "confirmed"`,
      `final_level === suggested_level`, and a two-row audit
      (`suggested` + `confirmed`).
- [ ] **Override** is rejected unless a free-text reason is entered
      (the Save button is disabled while the textarea is empty).
- [ ] Overriding records `action: "overridden"`, the new level, and
      the reason string.
- [ ] The first audit row records `engine_source` (and the second
      records the clinician's name + role).

### 3.6 Queue & handoff
- [ ] New cases appear at the **top** of the side rail; the rail is
      capped at 200 entries (oldest dropped first).
- [ ] Tapping a queue entry re-opens the handoff for that case.
- [ ] The handoff card shows: final level, suggested level (if
      different), engine source, audit chain, and full vitals.
- [ ] **Print handoff** opens a browser print dialog with a clean
      single-page layout.
- [ ] **Export JSON** downloads `triage-<patient_id>.json` containing
      the full record including the audit trail.

### 3.7 Persistence
- [ ] Reload the page: queue and clinician profile survive (localStorage
      keys `safeTriage.hl.queue` and `safeTriage.hl.clinician`).
- [ ] Switching to the offline path mid-shift: previously-submitted
      cases are still in the queue rail.

### 3.8 iPad / iOS Safari sanity (only if iPad available)
- [ ] Page renders without zoom or content shift in landscape and
      portrait.
- [ ] After *Add to Home Screen*, launching from the home icon hides
      the Safari chrome (status bar style: default).
- [ ] Both EN and AR layouts read top-to-bottom without overflow on a
      ~10–11" iPad.

---

## 4. Demo cases — what to type, what to expect

Each case in the table below is a one-shot demo. Submit the chief
complaint with the listed vitals, then walk through the confirm/override
flow. **Connected** means the backend Python engine is running; the
result column is what the Python engine returns. **Offline** means the
JS fallback. Parity-rule: offline level ≤ connected level (offline may
over-triage, must never under-triage).

| # | Chief complaint                                | Age | Vitals (HR / RR / SBP / SpO₂ / T)  | Connected (Python)                | Offline (JS)              | Notes |
|---|------------------------------------------------|-----|-------------------------------------|-----------------------------------|---------------------------|-------|
| 1 | `severe chest pain for 30 minutes`             |  56 | 95 / 18 / 138 / 96 / 37.0          | **L2** `chest_pain_cardiac`       | **L2**                    | English cardiac pathway |
| 2 | `ألم شديد في الصدر منذ ساعة`                   |  55 | 95 / 18 / 140 / 96 / 37.0          | **L2** `chest_pain_cardiac`       | **L2**                    | Arabic with modifier — the bug PR #17 fixed |
| 3 | `وجع في صدري`                                  |  56 | 94 / 18 / 138 / 97 / 37.0          | **L2** `chest_pain_cardiac`       | **L2**                    | Egyptian possessive — Codex P1 fix |
| 4 | `حرقان في الصدر`                               |  60 | 92 / 18 / 138 / 97 / 37.0          | **L2** `silent_mi`                | **L2** `chest_pain_cardiac` | Atypical ACS protected from ceiling-demote |
| 5 | `cardiac arrest, no pulse`                     |  60 | 0 / 0 / 0 / 60 / 35                | **L1** `cardiac_arrest`           | **L1**                    | Resuscitation floor |
| 6 | `found unresponsive at home`                   |  78 | 110 / 22 / 100 / 92 / 36.5         | **L1** `unconscious`              | **L1**                    | AVPU=U |
| 7 | `feels dizzy and weak`                         |  40 | 95 / 22 / 110 / **85** / 37        | **L1** (SpO₂ floor)               | **L1**                    | Severe hypoxia floor |
| 8 | `feels weak`                                   |  65 | 105 / 20 / **85** / 96 / 37        | **L2** (hypotension floor)        | **L2**                    | Adult hypotension floor |
| 9 | `vaginal bleeding` (pregnant)                  |  28 | 110 / 20 / 100 / 97 / 37           | **L2** `obstetric_emergency`      | **L2**                    | Pregnancy red-flag |
| 10| `fever and vomiting`                           |   2 | 170 / 32 / 90 / 96 / **39.5**      | **L1** (peds extreme NEWS2)       | **L1**                    | Toddler ≥2 score-3 params |
| 11| `mild fever, runny nose`                       |  25 | 80 / 16 / 120 / 99 / 37.8          | **L4** `uri_symptoms` / `fever_simple` | **L4**               | True low-acuity sanity check |
| 12| `here for medication refill, feels well`       |  55 | 78 / 14 / 124 / 98 / 36.8          | **L5** `chronic_refill`           | **L5**                    | Non-urgent, demonstrates we don't over-triage |

For every case verify the seven UI invariants in §3.4–§3.6 hold:
suggested level shown, engine-source surfaced, decision-support notice
visible, confirm or override-with-reason writes a queue entry, audit
trail records `engine_source`, handoff opens, export JSON works.

Cases 4, 7, 8, 10 also exercise safety floors — the floors panel on the
review card should list the floor that triggered.

---

## 5. Known limitations (read before showing this to a clinician)

- **Phase-1 pilot only.** Not regulatory-approved. Not a clinical
  device. No GAHAR / Egyptian MoH sign-off in this branch.
- **Single-station, local-only state.** Queue and audit live in
  `localStorage`. There is no shared backend queue, no sync between
  iPads, no central audit log. Phase 2.
- **JS fallback vocabulary is smaller than Python's.** The canonical
  engine has 1,858 Arabic medical keywords plus full Egyptian-colloquial
  coverage. The fallback hand-codes only the safety-critical Arabic
  chest-pain phrasings and a handful of common categories. Anything
  unusual on the fallback path should be treated as "best-effort" and
  the clinician should override conservatively.
- **No backend-mode self-check on boot.** The frontend doesn't yet
  ping `/api/mode` at startup; it learns about backend availability
  only when a triage submission either succeeds or fails. The first
  triage call effectively probes the backend.
- **No AI in this mode by design.** Hospital Lite intentionally
  disables Gemini, MedGemma, Vertex endpoints, BigQuery exporters,
  Firebase Cloud Messaging, push alerts, UMLS/RAG warmup, and the
  model warmup paths in `backend/main.py`. The research/demo app is
  unchanged on the `dashboard` routes.
- **iPad PWA is "add to home screen" only.** No service worker, no
  background sync, no offline queue replay. Closing Safari while
  offline keeps the data in `localStorage` but does not retry against
  the backend later.

---

## 6. Safety notes

- The deterministic engine *suggests*; the clinician *decides*. The
  override flow exists exactly so the clinician can disagree with the
  engine — please do, when clinically appropriate.
- Chest pain in this app is intentionally over-triaged in both engines
  (any pain word × any chest word → L2 cardiac pathway). Under-triage
  on chest pain is treated as a failure; over-triage is not.
- The app is not for patient self-diagnosis, not for treatment or
  prescribing advice, and not a replacement for ESI v5 / NEWS2 /
  GAHAR-required clinical judgment.
- If you see the amber **"Offline fallback"** banner, the suggestion
  did **not** come from the validated canonical engine — confirm with
  caution and prefer over-triage.

---

## 7. After the demo — what to do next

- File any clinician feedback against PR #17 or a new issue.
- If everything looks good, the next branch picks up *Phase 2* work:
  shared backend queue, service-worker offline replay, multi-station
  audit, optional re-introduction of the silent-shadow AI path with
  clinician-blinded compare. **None of that is in this PR.**

