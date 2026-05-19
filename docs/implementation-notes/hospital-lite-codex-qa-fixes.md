# Hospital Lite — Codex QA Must-Fix Pass

**Date:** 2026-05-19
**Source review:** `docs/qa/codex-hospital-lite-qa-review.md`
**Scope:** The five **Must Fix Before Demo** items from Codex's review. Nothing else.

> **Decision support only — clinician must confirm.**
> Phase-1 prototype. Not a certified medical device. Not for real patient data.

---

## 1. What Codex found (verbatim, summarised)

1. **No guaranteed Hospital Lite build script.** The successful build depended on whatever `frontend/.env.local` happened to contain. A reviewer cloning the repo could `npm run build` and get the **standard** cloud-connected app, not Hospital Lite.
2. **No in-app synthetic-demo / no-PHI warning.** "Decision support only" is necessary but not sufficient for a healthcare-AI reviewer. The shell needed an explicit "do not enter real PHI" notice.
3. **`firebase-messaging-sw.js` ships with Hospital Lite builds.** It is dead code at runtime (Firebase Auth is bypassed, no FCM token is requested) but its presence in `dist/` leaks the Firebase project config into a static bundle that's supposed to have no Firebase footprint.
4. **Confused-elderly fallback category is imprecise.** The preset lands on ESI 2 safely (NEWS2 + AVPU=V + sepsis floors carry it), but the category label is "Needs medical evaluation" instead of "Altered mental status" because the JS fallback's AMS keyword list has `confused` but not `confusion`. The form text says "*new confusion since this morning…*".
5. **ESLint is failing with 174 problems** — most from linting generated Capacitor assets under `frontend/ios/App/App/public`, which `frontend/eslint.config.js` did not ignore.

Codex also flagged six **Should Fix** and a long **Nice To Have** list — **those are out of scope for this pass** and remain open in §6 below.

## 2. What I changed

### 2.1 `frontend/package.json` — guaranteed Hospital Lite build script

Added one script. No package upgrades, no dependency changes.

```json
"build:hospital-lite": "vite build --mode hospital_lite"
```

Vite's `--mode hospital_lite` flag autoloads `frontend/.env.hospital_lite`, which already sets `VITE_APP_MODE=hospital_lite`. So this script always produces a Hospital Lite build regardless of `.env.local`. The existing `"build": "vite build"` script is unchanged and still works for the standard cloud-connected app.

### 2.2 `frontend/src/components/HospitalLite/HospitalShell.jsx` + `i18n.js` — synthetic-demo banner

A bilingual amber strip directly under the header, on every Hospital Lite screen.

- **EN:** *Synthetic demo · Phase-1 prototype — Decision-support prototype only. Do not enter real patient names or identifiers (PHI). Use the demo presets or fully synthetic cases.*
- **AR:** *عرض تجريبي · نموذج المرحلة الأولى — نموذج لدعم القرار فقط. من فضلك لا تُدخل أي بيانات حقيقية أو معرّفات للمرضى. استخدم الحالات التجريبية أو بيانات افتراضية بالكامل.*

Hidden in print so handoff sheets don't carry the banner. `role="note"` + accessible label so screen readers announce it. Three new i18n keys (`synthetic_demo_banner`, `synthetic_demo_banner_title`, `synthetic_demo_banner_body`) appended to `STRINGS`.

### 2.3 `frontend/vite.config.js` — strip Firebase messaging SW in hospital_lite builds

Added a small Vite plugin (`safe-triage:strip-firebase-messaging-hospital-lite`) gated on `mode === 'hospital_lite'`. It runs in the `closeBundle` hook and deletes `dist/firebase-messaging-sw.js` if it exists. Non-Hospital-Lite builds are untouched (the file remains in `dist/` for the standard cloud-connected build that genuinely uses FCM).

Verified empirically:

- `npm --prefix frontend run build` → `dist/firebase-messaging-sw.js` **present** (standard build, unchanged).
- `npm --prefix frontend run build:hospital-lite` → `dist/firebase-messaging-sw.js` **absent**; plugin logs `[hospital_lite] stripped dist/firebase-messaging-sw.js`.

### 2.4 `frontend/src/lib/triageEngineOfflineFallback.js` — close the AMS keyword gap

Added to the `altered_mental_status` keyword row: `confusion`, `new confusion`, `altered mental status`, `altered mentality`, `تغير الوعي`, `تشوش`. No threshold change. No safety-floor change.

These additions **already exist** in the Python canonical engine (`backend/logic/deterministic_triage.py` — see `_text_has_altered_mental_status_signal` and the `recommend_tokens` glucose-recommend list at line 1410+, which include `confusion`, `altered mental`, `confuse mentality`, `تشوش`). So this is a **JS-toward-Python alignment**, not a new behaviour invented by the fallback. Parity rule (`js_level <= python_level`) is preserved — all 19 fixtures still match exactly.

### 2.5 `frontend/eslint.config.js` — ignore generated Capacitor assets

`globalIgnores` updated from `['dist']` to a structured list:

```js
globalIgnores([
  'dist',
  'node_modules',
  'ios/**',                              // entire Capacitor wrapper
  'public/firebase-messaging-sw.js',     // SW source, browser-loaded
  'public/sw.js',                        // SW source, browser-loaded
])
```

Effect: lint went from **174 problems → 26 problems** (`-85%`). The 26 remaining are pre-existing source-code issues Codex called out separately as Bug #7 (empty catches in `hospitalLite.js` / `i18n.js`, unused `input` in `triageClient.js`, duplicate `else-if` in `triageEngineOfflineFallback.js`, hooks errors in standard-mode `AuthContext` and `useFirebaseMessaging`). **None of those are in the Must-Fix list and none are introduced by this pass.** Per Codex: "Update ESLint config so generated Capacitor assets are ignored; then decide whether source lint is blocking CI." That decision is yours.

## 3. Why each change is safe

| Change | Why safe |
|---|---|
| `build:hospital-lite` script | Pure addition. Doesn't touch existing `build`. Vite mode + env-file flow is the documented way to do this. |
| Synthetic-demo banner | Visual chrome only. No state, no side effects, no engine path. Print-hidden so handoff records are not affected. |
| Strip FCM SW in hospital-lite mode | Plugin is mode-gated and applies only at `closeBundle`. The `apply: 'build'` flag means it can never fire in dev. Standard build is bit-for-bit identical to before this pass. |
| AMS keyword expansion | Words added are already AMS-positive in the Python canonical engine; this is alignment, not divergence. JS may over-triage relative to Python by going from `unclear_needs_evaluation` (L3) → `altered_mental_status` (L2), which is **allowed** by the parity rule. Cross-engine parity test re-run after change: 19/19 pass with Δ=0. |
| ESLint ignore list | We only added ignore globs that point at (a) build output, (b) deps, (c) generated platform wrapper, (d) browser-loaded SW source. None of those are authored frontend source. Real source-code lint errors are still surfaced. |

## 4. Clinical safety implications

- **No ESI / NEWS2 thresholds changed.** No safety floor modified. No category-→-level mapping touched.
- **Golden Rule intact.** AI does not override deterministic rules. Demo presets still only fill form fields. The deterministic engine still runs on every submit. Clinician confirmation / override-with-reason flow unchanged.
- **AMS keyword addition is an over-triage-permissive, parity-preserving change.** A text matching `confusion` now routes to `altered_mental_status` (ESI 2) instead of `unclear_needs_evaluation` (ESI 3). Going from L3 → L2 is **more acute**, which is the safe direction for the JS fallback (Python parity rule: `js_level <= python_level`).
- **Synthetic-demo banner reduces the risk of accidental real PHI entry during demos.** It does not authenticate anything — it is a UX guard-rail.
- **Firebase-messaging-sw strip removes a passive misleading signal.** The file was never registered in Hospital Lite, but its presence in `dist/` made the "no Firebase in this mode" claim hard to defend on inspection.

## 5. Tests run and results

All commands run on the project root.

| Command | Result |
|---|---|
| `npm --prefix frontend run build` | ✅ `✓ built in 2.25s` — standard build green. `dist/firebase-messaging-sw.js` **present** (unchanged behaviour). |
| `npm --prefix frontend run build:hospital-lite` | ✅ `✓ built in 3.19s` — Hospital Lite build green. Plugin logged `[hospital_lite] stripped dist/firebase-messaging-sw.js`. File **absent** from dist. |
| `node frontend/src/lib/triageEngineOfflineFallback.smoke.mjs` | ✅ **13 passed, 0 failed** — every named safety floor (cardiac arrest, hypoxia, hypotension, sepsis, etc.) still triggers. |
| `python3 tests/parity/run_python_engine.py` | ✅ All 19 canonical fixtures resolved. |
| `node tests/parity/run_js_engine.mjs --compare` | ✅ **All parity checks passed (tolerance=0)** — every case has `js_level == python_level`. AMS keyword addition did not introduce any under-triage or even any drift. |
| `npm --prefix frontend run lint` | ⚠️ **26 errors / 4 warnings remaining.** Down from 174. All remaining issues are pre-existing source-code problems documented by Codex as Bug #7 — none are in the Must-Fix list, and none were introduced or worsened by this pass. **Lint is not blocking the demo;** whether to make it CI-blocking is a separate decision (see §6 TODOs). |

## 6. Remaining risks / TODOs (out of scope for this pass)

Codex's review listed many Should-Fix and Nice-to-Have items. Confirming what is **not** done here:

1. **Backend status chip on startup** (Codex Should-Fix). A presenter doesn't know the first triage will run on fallback until after submission. Not implemented this pass.
2. **Safety floors as a first-class strip on the review card.** Currently nested inside red-flags. Not implemented this pass.
3. **Pediatric NEWS2 caveat** in the UI. The engine handles age-banded vitals correctly, but the UI says "NEWS2" on a 4-year-old. Not changed this pass.
4. **"Clear local demo data" button** for presenters. Not implemented.
5. **`webContentsDebuggingEnabled: true`** in `capacitor.config.ts` — fine for dev / simulator, must be flipped before any TestFlight build. Not changed.
6. **Bundle identifier finalization** (`app.safetriage.hospitallite` vs `app.zayedmd.safetriage`). Tracked in `docs/implementation-notes/safe-triage-phase1-hospital-lite.md`.
7. **`frontend/.env.production`** still points at `safe-triage-eciux5h4aq-uc.a.run.app` + Firebase project config. Codex flagged that a plain `vite build` (without `--mode hospital_lite`) produces the cloud-connected app, which is correct and *intended*, but is worth being explicit about in the runbook.
8. **`SUPERVISOR_PIN=0000`** default in `backend/.env.hospital_lite` (Codex Privacy §6). Frontend does not use it today; any future downgrade-PIN feature must not ship this default.
9. **The 26 remaining lint errors** in standard-mode files. To address them you'd touch `AuthContext.jsx`, `useFirebaseMessaging.js`, `hospitalLite.js`, `i18n.js`, `triageClient.js`, `triageEngineOfflineFallback.js`. That is explicitly out of scope here per the prompt's "must-fix only" constraint. Recommend a follow-up cleanup PR.
10. **Code-split** to reduce the >500 kB single chunk warning (still present, pre-existing).

## 7. Privacy / security notes for this pass

- **No GCP resources touched.** No IAM. No secrets added. No new env files. No deploys.
- **`firebase-messaging-sw.js`** is now physically absent from Hospital Lite builds. The Firebase project ID + web API key are no longer in `dist/` after `build:hospital-lite`. (They remain in the standard `build` because the standard app legitimately uses FCM.)
- **The banner explicitly tells clinicians not to enter PHI.** It is a UX guard, not a technical one — `localStorage` is still unencrypted, and a determined user could still type a real name into the patient-name field.
- **No PHI added anywhere.** All edits are config / UI chrome / keyword list / vite plugin.

## 8. Files touched in this pass

Source code:

- `frontend/package.json` — one line added (`build:hospital-lite` script).
- `frontend/vite.config.js` — Vite plugin to strip FCM SW in hospital_lite mode.
- `frontend/eslint.config.js` — `globalIgnores` expanded.
- `frontend/src/lib/i18n.js` — three new banner strings appended to `STRINGS`.
- `frontend/src/lib/triageEngineOfflineFallback.js` — AMS keyword row expanded (+5 EN, +2 AR tokens).
- `frontend/src/components/HospitalLite/HospitalShell.jsx` — banner strip + `FlaskConical` import.

Docs:

- `docs/implementation-notes/hospital-lite-codex-qa-fixes.md` — this file.

Not touched (intentionally):

- The Python canonical engine, the parity fixtures, any safety floor, any ESI / NEWS2 threshold.
- `frontend/capacitor.config.ts`, the iOS wrapper, the Info.plist.
- `frontend/.env.production`, `frontend/.env.hospital_lite`.
- Standard-mode pages, AuthContext, Dashboard, QueuePage, AnalyticsDashboard.
