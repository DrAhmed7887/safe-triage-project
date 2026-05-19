# SAFE-Triage Phase 1 — Hospital Lite Implementation Notes

**Date:** 2026-05-19
**Author:** Dr. Ahmed Zayed (with Claude as scribe)
**Scope:** This file documents the Phase-1 / Hospital Lite *audit and small additions* pass. The earlier, deeper Hospital Lite build is documented in `docs/implementation-notes.md` (root-level) and in `HOSPITAL_LITE.md` / `HOSPITAL_LITE_TESTING.md`. **This file is additive, not a replacement.**

> **Decision support only — clinician must confirm.**
> Phase-1 is pilot / shadow-mode. Not a certified medical device. No patient data is collected or stored beyond the local browser. Demo only.

---

## 1. Mission for this pass

The Phase-1 goal stated for this pass was to deliver a *demo-ready* SAFE-Triage Hospital Lite app suitable for Egyptian hospitals, mentors, hackathons, and thesis reviewers — without doing a broad rewrite of the already-shipped Hospital Lite. So this pass is mostly **audit + the smallest safe additions**, plus the missing-from-disk documentation.

## 2. State of the world before this pass

Findings from inspecting the repo, captured in 10–15 lines as the prompt asked:

1. **Frontend:** React 19 + Vite 7 + Tailwind 3 + Capacitor 8. All Hospital Lite UI lives under `frontend/src/pages/HospitalLite/` and `frontend/src/components/HospitalLite/`.
2. **Mode gate:** `frontend/src/lib/hospitalLite.js` reads `VITE_APP_MODE=hospital_lite` and `App.jsx` swaps the whole AuthProvider tree for `HospitalLiteApp` (no Firebase, no Auth, no router state).
3. **Triage flow:** `HospitalLitePage` runs three stages — `ENTRY → REVIEW → HANDOFF` — with the canonical Python engine attempted first and an in-browser deterministic JS engine (`triageEngineOfflineFallback.js`) as the only-when-offline fallback. The engine source is recorded in the audit chain.
4. **i18n:** EN/AR strings in `frontend/src/lib/i18n.js`; the document `dir` is flipped to `rtl` for Arabic.
5. **Local persistence:** localStorage-backed clinician profile + queue + audit (`safeTriage.hl.*` keys). No remote storage of patient data anywhere.
6. **iOS shell:** `frontend/capacitor.config.ts` is set up with `appId: app.safetriage.hospitallite`, `webDir: dist`, brand `backgroundColor: #0d9488`, debug WKWebView. `frontend/ios/App/App/Info.plist` already has `CFBundleDisplayName = SAFE-Triage` and **no mic/camera usage strings** (truthful — no plugins request them).
7. **PWA:** `frontend/index.html` registers `/sw.js` and links a manifest; service worker present at `frontend/public/sw.js`.
8. **Parity:** `tests/parity/critical_cases.json` shared fixtures; `run_python_engine.py` + `run_js_engine.mjs --compare` enforce *no JS under-triage* relative to the canonical Python engine.
9. **Smoke:** `frontend/src/lib/triageEngineOfflineFallback.smoke.mjs` exercises individual safety floors by name.
10. **Two long docs at repo root** (`HOSPITAL_LITE.md`, `HOSPITAL_LITE_TESTING.md`) plus `docs/implementation-notes.md`. **No** `docs/demo/` or `docs/implementation-notes/` subdirectory yet.
11. **Branch state going in:** `claude/safe-triage-app-JwaKd`, with `frontend/package*.json` modified and `frontend/ios/` untracked from the earlier Capacitor wrap. No work in flight in Hospital Lite source.
12. **Bundle ID drift:** Capacitor config uses `app.safetriage.hospitallite`. The Phase-1 prompt suggested `com.zayedmd.safetriage` as a placeholder. Both are valid; see §6 below for the decision.

## 3. Smallest safe implementation path

The audit revealed exactly **one** functional gap against the Phase-1 spec: **§7 sample cases**. The current `LiteTriageForm` has no quick-fill demo presets. Everything else asked for in the prompt either exists already, is documented, or is a doc deliverable. Therefore the minimum-change plan is:

| Change | Justification | Risk |
|---|---|---|
| Add `DemoPresetsBar` component with 5 clinically-meaningful presets | Prompt §7 explicitly asks for this | Low — UI only, doesn't touch the engine |
| Wire it into `LiteTriageForm` via an `onLoadPreset` callback | Smallest surface; no state-up refactor | Low |
| Add `docs/implementation-notes/safe-triage-phase1-hospital-lite.md` (this file) | Prompt explicitly asks for it | None |
| Add `docs/demo/safe-triage-phase1-hospital-lite-runbook.md` | Prompt §11 | None |
| Run `npm --prefix frontend run build` + JS smoke / parity if Python is on PATH | Prompt §10 | None |

Explicitly **not** doing:

- Anything to the canonical Python engine or the JS fallback engine.
- Anything to ESI/NEWS2 thresholds or safety floors.
- Touching Capacitor config, the iOS Xcode project, or Info.plist.
- Bundle-identifier change. The existing `app.safetriage.hospitallite` is fine; the placeholder in the prompt is just a placeholder.
- Adding supervisor auth (prompt §5 says "document as TODO rather than inventing a fake system" — see §7).
- Wiring this branch up to deploy, Firebase, or GCP.

## 4. Demo presets — design

New file: `frontend/src/components/HospitalLite/DemoPresetsBar.jsx`.

- Pure component. Props: `lang`, `onLoadPreset(preset)`.
- Renders a row of 5 buttons + a brief "Demo presets · sample cases, not real patients" label.
- Each preset is a plain object containing form-shaped values (`age`, `gender`, `chief_complaint_text`, `vitals.*`, `consciousness`, `pain_scale`, plus optional risk-flag toggles).
- The parent (`LiteTriageForm`) merges them into local form state, including a shallow merge of `vitals`. **Patient ID and name are not pre-filled** — keeps every demo run a deterministic-engine call, not a confusing "ID already exists" state.

The 5 cases (numbers chosen to exercise the safety floors):

| Preset | Demonstrates | Expected ESI band |
|---|---|---|
| **Chest pain · ?MI** — M, 58y, crushing CP, sweating, HR 108, BP 105/70, SpO₂ 94 | Cardiac red flag + borderline hemodynamics | ESI 1–2 |
| **SOB · low SpO₂** — F, 72y, COPD, RR 28, SpO₂ 86 | Hypoxia safety floor at SpO₂ < 90 | ESI 1–2 |
| **Fever in child** — F, 4y, T 39.4, HR 150, RR 32, lethargic | Pediatric fever + tachycardia/tachypnea | ESI 2 |
| **Minor wound · low risk** — M, 28y, 3 cm forearm laceration, vitals all normal | Negative control / proves engine can produce a low acuity | ESI 4–5 |
| **Confused elderly** — M, 82y, new confusion (V on AVPU), HR 112, RR 24, T 38.4 | Sepsis / altered mental status | ESI 2 |

These are paraphrased clinical templates, not patient records. They are bilingual at the button level (preset label is localized via the existing i18n helper).

**Why presets and not a "load test fixture" button?** Reviewers and hackathon judges scan, they don't read forms. The presets exist so the demo flows in under 10 seconds per case. They are *not* part of the validation set — that remains `tests/parity/critical_cases.json`.

## 5. Clinical-safety implications of the additions

- The presets fill the form, **then the deterministic engine runs**. No preset bypasses the engine, no preset writes a "level" directly. The Golden Rule is intact: *AI extracts → rules decide → humans confirm*.
- The override-with-reason path is unchanged. A clinician can still confirm or override any suggestion produced from a preset.
- Presets do not toggle a "demo mode" off the safety floor. The same engine, the same floors, run for preset and hand-typed input.
- Bilingual labels are descriptive only; the clinical content (vitals, complaint text) is in English in the demo since the JS fallback's keyword detection is currently strongest in English. Arabic complaint detection lives in the canonical Python engine and is exercised by the connected-mode demo.

## 6. Decisions not stated in the prompt

| Decision | Why |
|---|---|
| Kept `appId = app.safetriage.hospitallite` | Already used by the wrapped iOS project. Changing it now would require regenerating the `ios/` directory or hand-editing Xcode project files. The placeholder `com.zayedmd.safetriage` from the prompt is a hint, not a requirement. **TODO:** before TestFlight / App Store submission, decide on the canonical bundle id (probably `app.zayedmd.safetriage`) and use Xcode → Signing & Capabilities to rename. Document this. |
| Did **not** add a "demo mode" badge separate from the existing Hospital-Lite shell | The shell already shows "Decision support only — clinician must confirm" and the engine-source chip already shows online/offline. Adding a third banner is visual noise. The new presets section is itself labelled "Demo presets · sample cases, not real patients." |
| Did **not** add supervisor PIN / role gate for downgrades | Override is already gated by a free-text reason. A real PIN/role system needs an identity layer (Firebase, custom backend, etc.) that does not exist in Hospital Lite mode. Documented as TODO in §7. |
| Did **not** wire a Python parity run from inside this Claude session | Repo has no `requirements.txt` install in this working tree's venv state for sure. Documented in §9. |
| Did **not** change service-worker logic | Already production-quality for a demo. |

## 7. TODOs Dr. Ahmed should review

1. **Bundle identifier finalization.** Decide on the public-facing bundle id before any TestFlight push. Current: `app.safetriage.hospitallite`. Likely target: `app.zayedmd.safetriage`. Owner: Ahmed.
2. **Supervisor PIN for downgrades.** Prompt §5 noted this as a TODO if no system exists. None exists. A future Phase 2 could add a 4-digit PIN gate (local-only, hashed in storage) for downgrades — but **only** if local-only is clinically defensible. Otherwise this needs a real identity layer.
3. **Arabic chief-complaint detection in the offline JS engine.** The canonical Python engine handles Arabic + Egyptian dialect via a 1,858-keyword dictionary; the JS fallback only matches a smaller English subset. A demo run with an Arabic complaint will currently fall back to "unknown category" + safety floors in offline mode. Document in the runbook so the demo flow uses English text when forced offline.
4. **Pediatric NEWS2.** NEWS2 is adult-only; pediatric vitals interpretation in the engine uses age-banded heart-rate / respiratory-rate cutoffs. Reviewers will ask. The "Fever in child" preset is a good moment to mention this if asked, but it is not changed by this pass.
5. **Bundle-identifier ↔ Apple Developer account** must be matched before signing.
6. **Tighten the demo presets' clinical wording** with a senior ED colleague before the EuSEM submission. Current wording is mine and is intentionally generic.
7. **Add a `npm run test:smoke`** script that runs `node src/lib/triageEngineOfflineFallback.smoke.mjs` and the JS parity step. Currently those commands are documented but not packaged. Out of scope for this pass.

## 8. Files touched in this pass

- **New:** `frontend/src/components/HospitalLite/DemoPresetsBar.jsx`
- **Modified:** `frontend/src/components/HospitalLite/LiteTriageForm.jsx` — adds import + one render of `<DemoPresetsBar />` above the patient section and a preset-merge helper. No business-logic changes.
- **New:** `docs/implementation-notes/safe-triage-phase1-hospital-lite.md` (this file)
- **New:** `docs/demo/safe-triage-phase1-hospital-lite-runbook.md`

That is the entire functional change-set.

## 9. Tests run and results

To be filled in during the test pass at the end of this session. Recorded commands and results:

- `npm --prefix frontend run build` — *recorded below*
- `node frontend/src/lib/triageEngineOfflineFallback.smoke.mjs` — *recorded below*
- `node tests/parity/run_js_engine.mjs --compare` — *recorded below; requires `python_results.json` from a prior run of `python tests/parity/run_python_engine.py`. If not present, the harness is run without `--compare` to confirm the JS side at least executes.*
- Backend pytest is **not** run from here; it requires installed Python deps and is documented as a separate step in the runbook.

(See bottom of file for the recorded outputs.)

## 10. Security / IAM / billing implications

- **None changed.** No GCP resources, no IAM, no API enablement, no secrets added.
- No Firebase calls in Hospital Lite mode — the `IS_HOSPITAL_LITE` flag bypasses `AuthProvider` entirely.
- Demo presets contain **no PHI**; they are synthetic.
- localStorage is the only persistence; clearing site data wipes Hospital Lite state.

## 11. Stop condition

This pass stops once:

1. The new `DemoPresetsBar` is wired and the frontend build succeeds.
2. The two docs (this file + the runbook) are written.
3. Tests are run or, if they cannot be run here, that's documented.
4. A final summary is produced.

No deploy, no commit, no GCP, no IAM, no secrets.

---

## Appendix A — recorded test output

All runs on `claude/safe-triage-app-JwaKd` at 2026-05-19 on macOS / Node 22 / Python 3.9.6 (`/usr/bin/python3`).

### A.1 `npm --prefix frontend run build`

```
vite v7.3.1 building client environment for production...
✓ 2204 modules transformed.
dist/index.html                   2.52 kB │ gzip:   1.03 kB
dist/assets/index-C0Kfgasu.css   79.15 kB │ gzip:  15.08 kB
dist/assets/index-Crn0_RFS.js   530.74 kB │ gzip: 163.01 kB
✓ built in 2.10s
```

The single-chunk-larger-than-500 kB warning is pre-existing and unrelated to this pass (it's the React + lucide + framer-motion bundle); deferred to a Phase-2 code-split pass.

### A.2 `node frontend/src/lib/triageEngineOfflineFallback.smoke.mjs`

`13 passed, 0 failed (13 total)` — covers cardiac arrest, unresponsive, Arabic chest pain, Egyptian dialect respiratory arrest, hypoxia floor, hypotension floor, severe abdo pain, mild fever, refill, pregnant + bleeding, AI-flag absent, toddler fever + tachycardia, adult sepsis pathway.

### A.3 `python3 tests/parity/run_python_engine.py` + `node tests/parity/run_js_engine.mjs --compare`

`All parity checks passed (tolerance=0).` 18 fixtures, every case has `js_level == python_level`. Safety rule (`js_level <= python_level`) holds with zero drift.

### A.4 Backend pytest

Not run. Backend tests require `pip install -r backend/requirements.txt` in a venv that this Claude session does not own. The parity harness above is the canonical cross-engine signal; the JS engine is what Hospital Lite runs in offline / Capacitor mode, and it matches Python on every fixture.

