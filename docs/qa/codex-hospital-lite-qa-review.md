# SAFE-Triage Hospital Lite QA Review

Date: 2026-05-19  
Reviewer: Codex, independent QA reviewer and clinical product design critic  
Scope: Phase 1 Hospital Lite app only. No deployment, cloud resource creation, IAM changes, secrets, clinical-threshold changes, or test removal.

## 1. Executive Verdict

**Ready with caveats for a controlled synthetic demo.**

Hospital Lite builds, the offline deterministic fallback works, the five demo presets run through triage, and the UI clearly forces clinician confirmation before a case enters the queue. It is credible for thesis defense / hackathon / mentor demos using synthetic cases.

It is **not ready for real patient data, clinical pilot use, or TestFlight distribution** without privacy hardening, lint/CI cleanup, an explicit Hospital Lite build script, iOS release hardening, and clearer in-app disclaimers around offline fallback and pediatric NEWS2.

Clinical product principle status: **AI does not appear to override or downgrade the deterministic rules in Hospital Lite.** The tested path was deterministic JS fallback because the local backend could not be started in this environment.

## 2. Build And Test Results

| Check | Result | Notes |
|---|---:|---|
| `npm --prefix frontend run build` | Pass | Built Hospital Lite using current `frontend/.env.local`. Vite warned that one chunk is >500 kB after minification. |
| `node frontend/src/lib/triageEngineOfflineFallback.smoke.mjs` | Pass | 13/13 passed. |
| `python3 tests/parity/run_python_engine.py` | Pass | Wrote `tests/parity/python_results.json`; canonical fixture outputs completed. |
| `node tests/parity/run_js_engine.mjs --compare` | Pass | 19/19 parity checks passed with tolerance 0; no JS under-triage versus Python fixtures. |
| `npm --prefix frontend run lint` | Fail | 174 problems. Major cause: ESLint scans generated Capacitor assets under `frontend/ios/App/App/public`; also source lint errors remain. |
| Local backend connected-mode smoke | Not run | `python3 -m uvicorn ...` failed because the active Python lacks `uvicorn`. |
| Rendered browser QA | Pass with caveats | In-app browser loaded `http://127.0.0.1:5173/`, no console warnings/errors, no Vite overlay, presets worked in fallback mode. |

Browser flow tested:

1. Local clinician gate with `QA Reviewer`.
2. Demo preset click.
3. `Suggest triage`.
4. Review card with ESI, NEWS2, red flags/floors, engine source, clinician-confirm notice.
5. `Confirm this level`.
6. Queue entry and handoff audit.
7. Arabic toggle and mobile viewport at 390 x 844.

Preset outcomes observed in offline fallback:

| Preset | Observed result | Safety display |
|---|---:|---|
| Chest pain · ?MI | ESI 2 | NEWS2 5, cardiac chest pain, severe-pain floor. |
| SOB · low SpO2 | ESI 1 | NEWS2 6, severe hypoxia floor. |
| Fever in child | ESI 1 | NEWS2 10, abnormal RR/HR + fever/tachycardia floors. |
| Minor wound · low risk | ESI 4 | NEWS2 0, no red flags. |
| Confused elderly | ESI 2 | NEWS2 11, voice-only + fever/tachycardia floors. |

## 3. Clinical Safety Findings

Strong points:

- Presets only populate form fields; they do not write an ESI result directly. See `frontend/src/components/HospitalLite/LiteTriageForm.jsx` and `frontend/src/components/HospitalLite/DemoPresetsBar.jsx`.
- `getTriageSuggestion()` tries the backend first and falls back to `runOfflineFallbackTriage()` only after failure or `navigator.onLine === false`.
- Review and handoff screens visibly show engine source, ESI level, NEWS2, red flags/floors, and the clinician-confirmation notice.
- The audit trail records `engine_source` and fallback error kind.
- Parity fixture check passed: the JS fallback did not under-triage any tested critical case versus Python.

Safety caveats:

- The rendered fallback path labels the child fever case with plain `NEWS2`, even though NEWS2 is an adult early-warning score. The repo docs already acknowledge this, but the UI does not. A reviewer could reasonably call this misleading unless the UI says pediatric handling is an age-adjusted safety overlay, not pure NEWS2.
- The “Confused elderly” fallback result reached ESI 2 safely, but its category label was `Needs medical evaluation` because the fallback keyword set appears to miss `confusion` while matching `confused`. That is not an under-triage in the tested preset, but it looks clinically imprecise in a demo.
- In connected mode, backend response adaptation may show `NEWS2 = null` if the backend payload lacks exposed NEWS2 breakdown fields. I could not verify this path locally because `uvicorn` is not installed.
- External clinical references checked: AHRQ describes ESI as a five-level ED triage algorithm from 1 most urgent to 5 least urgent, and NHS/RCP material describes NEWS2 as a standardised early-warning system for acute illness, specifically for adults. Sources: [AHRQ ESI overview](https://www.ahrq.gov/patient-safety/settings/hospital/resource/about.html), [NHS England NEWS](https://www.england.nhs.uk/ourwork/clinical-policy/sepsis/nationalearlywarningscore/), [RCP NEWS2 adult/sepsis note](https://rcp.ac.uk/news-and-media/news-and-opinion/nhs-england-approves-use-of-national-early-warning-score-news-2-to-improve-detection-of-acutely-ill-patients/).

## 4. UI/UX Professionalism Findings

Strong points:

- The app feels substantially more clinical than a student prototype: compact form, restrained colors, queue rail, handoff record, audit trail, bilingual support, and visible decision-support language.
- The demo preset bar is useful and fast. It is clearly labelled as sample cases, not real patients.
- Confirmation/override flow is easy to understand; override requires a reason.
- The mobile Arabic form at 390 x 844 had no horizontal overflow and no obvious layout break.

Professionalism gaps:

- The UI still lacks a prominent “Phase 1 / shadow mode / no real patient data” banner. “Decision support only” is necessary but not enough for healthcare AI reviewers.
- Safety floors are present but visually buried inside the red-flags card. In a demo, the floor should be a first-class line: “Safety floor applied: severe hypoxia -> cannot be below ESI 1.”
- The offline banner is truthful after triage, but there is no startup backend status. A presenter may not know the first case is about to run fallback until after submission.
- The form accepts full patient name and stores it locally. For demos, the UI should actively discourage real PHI entry.
- The queue rail on mobile appears before the form in DOM order and can push the active workflow down after several entries. It remained usable, but a bottom/top tab pattern would feel more polished.

## 5. Mobile And iOS Findings

Strong points:

- `frontend/index.html` has viewport, PWA manifest, theme color, iOS home-screen metadata, and iOS icons.
- Capacitor config uses bundled `dist` assets and does not point to a dev server.
- Info.plist does not request camera, mic, or location permissions, which is good.

Readiness problems:

- I did not run Xcode/iOS because this QA pass was local web only.
- `frontend/ios/` is untracked in git status; generated public assets are ignored. This makes it unclear which iOS wrapper files Claude intends to commit.
- Resolved in the final release-candidate pass:
  `webContentsDebuggingEnabled` is now `false` for the release path.
- Bundle identifier `app.safetriage.hospitallite` should be finalized before TestFlight.
- There is no explicit release/privacy copy for localStorage PHI in the app itself.

## 6. Privacy And Security Findings

Strong points:

- Hospital Lite bypasses Firebase Auth at runtime when `VITE_APP_MODE=hospital_lite`.
- Queue/audit/clinician profile are local-only and bounded to 200 entries.
- No cloud deployment, IAM change, or resource creation was performed.

Risks:

- `frontend/public/firebase-messaging-sw.js` with Firebase project config is still shipped in public assets. Firebase web API keys are not secrets by themselves, but this undermines the “no Firebase in Hospital Lite” story and may alarm privacy reviewers.
- `frontend/.env.production` points at the Cloud Run API and Firebase project. A clean production build without `VITE_APP_MODE=hospital_lite` can produce the standard cloud-connected app, not Hospital Lite.
- LocalStorage is unencrypted and contains patient name, complaint, vitals, clinician name, and audit. This is not safe for real PHI on shared hospital devices.
- `Export JSON` downloads identifiable data with full audit. That is useful for demos, but risky around real patients unless the UI says synthetic/demo only.
- Backend defaults still include `SUPERVISOR_PIN=0000` in the Hospital Lite env preset. The current frontend does not use the PIN, but any future downgrade gate must not ship this default.

## 7. Exact Bugs Found

1. **Frontend lint fails.** `npm --prefix frontend run lint` reports 174 problems. The biggest issue is linting generated `frontend/ios/App/App/public/assets/*.js`; `frontend/eslint.config.js` ignores only `dist`.
2. **Connected backend cannot be launched from this environment.** `python3 -m uvicorn main:app --app-dir backend --port 8000` fails with `No module named uvicorn`.
3. **Confused elderly preset category is imprecise in JS fallback.** The preset still lands on ESI 2, but the category is `unclear_needs_evaluation` / “Needs medical evaluation” instead of altered mental status. Likely keyword gap: `confusion` is not in the fallback AMS keyword list.
4. **Pediatric preset displays plain NEWS2.** The four-year-old preset shows `NEWS2 = 10 (HIGH)` without an adult-score caveat.
5. **Hospital Lite build mode is fragile.** The successful build depends on current `frontend/.env.local`; there is no package script that guarantees Hospital Lite mode.
6. **Firebase messaging worker ships with Hospital Lite public assets.** It is not registered in the tested Hospital Lite runtime, but the file is visible and still targets `/dashboard`.
7. **Source lint issues exist outside generated assets.** Examples include empty catches in `hospitalLite.js` / `i18n.js`, unused `input` in `triageClient.js`, duplicate `else if` in `triageEngineOfflineFallback.js`, and existing React hooks lint errors in standard-mode components.

## 8. Recommended Fixes Ranked

### Must Fix Before Demo

- Add a dedicated `build:hospital-lite` script that sets `VITE_APP_MODE=hospital_lite`, and update demo docs to use it.
- Add an in-app demo/shadow-mode warning: “Synthetic demo only. Do not enter real patient identifiers.”
- Remove or conditionally exclude `firebase-messaging-sw.js` from Hospital Lite builds, or document why it is present and prove it is never registered.
- Fix the confused-elderly fallback keyword/category gap without changing clinical thresholds.
- Fix ESLint config so generated Capacitor public assets are ignored; then decide whether source lint is blocking CI.

### Should Fix Before Demo

- Add a startup backend status chip: “Backend engine connected” / “Browser fallback mode” before the first triage submit.
- Make safety floors visually first-class on the review card and handoff.
- Add a pediatric caveat for NEWS2 display or rename pediatric output as “Physiology safety score” when age < 16.
- Add a one-tap “Clear local demo data” control for presenters.
- Disable Capacitor web debugging for release/TestFlight builds.
- Add a short privacy line near `Patient name`: optional, local-only, avoid real PHI in demo mode.

### Nice To Have Later

- Code split standard-mode pages out of Hospital Lite bundle.
- Add Playwright/e2e tests for all five presets and the confirm/override flows.
- Add a backend `/api/mode` preflight in the Hospital Lite shell.
- Add iPad portrait/landscape screenshots to the runbook.
- Add a real supervisor downgrade gate after an identity story exists.

## 9. Specific Interface Improvement Recommendations

- Review card top stack should be: ESI badge, category, “Safety floor applied” strip, engine source, clinician-confirmation notice.
- Replace raw red-flag tokens like `abnormal_hr` with human labels and Arabic equivalents.
- Show “Suggested by rules” and “Final after clinician confirmation” as separate states.
- Make the offline fallback banner shorter but stronger: “Backend unavailable. Browser rules fallback. Confirm conservatively.”
- On the handoff, show “System suggested Lx -> Clinician confirmed Lx” even when not overridden.
- Add a compact mode for iPad landscape so queue + form + result are readable without large scrolling.
- Keep the preset row, but add a tiny “Load only, does not decide” helper tooltip or sublabel.

## 10. Files Claude Should Edit Next

- `frontend/package.json`
- `frontend/eslint.config.js`
- `frontend/src/lib/triageEngineOfflineFallback.js`
- `frontend/src/components/HospitalLite/DemoPresetsBar.jsx`
- `frontend/src/components/HospitalLite/SuggestedTriage.jsx`
- `frontend/src/components/HospitalLite/HandoffRecord.jsx`
- `frontend/src/components/HospitalLite/LiteTriageForm.jsx`
- `frontend/src/components/HospitalLite/HospitalShell.jsx`
- `frontend/src/lib/i18n.js`
- `frontend/src/lib/triageClient.js`
- `frontend/public/firebase-messaging-sw.js`
- `frontend/capacitor.config.ts`
- `docs/demo/safe-triage-phase1-hospital-lite-runbook.md`
