# SAFE-Triage · Phase 1 Hospital Lite — Demo Runbook

> **Decision support only — clinician must confirm.**
> **أداة دعم قرار فقط — يجب على الطبيب التأكيد.**
>
> Phase-1 is a **pilot / shadow-mode** clinical decision-support prototype. It is **not** an approved, certified, or validated clinical device. Do **not** use it as a primary triage system for live patient care.

This is the practical "how do I run it for a demo tomorrow" doc. The deeper architecture notes live in `HOSPITAL_LITE.md` (architecture), `HOSPITAL_LITE_TESTING.md` (testing flow), `docs/implementation-notes.md` (running build log), and `docs/implementation-notes/safe-triage-phase1-hospital-lite.md` (this pass's audit).

---

## 1. What this app is

A demo-ready bilingual (EN / AR + Egyptian dialect) emergency-triage decision-support app. The clinician enters chief complaint + vitals, the deterministic ESI v5 / NEWS2 engine suggests a triage level, and the clinician confirms or overrides with a reason. Three runtimes from the same source:

1. **Web app / PWA** — open in any modern browser, installable to home-screen on iOS / Android.
2. **Local offline-first demo** — no backend, no Firebase, no AI calls.
3. **Capacitor iOS wrapper** — open `frontend/ios/App/App.xcworkspace` in Xcode and Run.

**Golden Rule:** *AI Extracts → Rules Decide → Humans Confirm.* The deterministic engine is always in the decision path. Demo presets fill the form; they never write a final ESI level.

## 2. Prerequisites

- Node ≥ 20 (we built and tested on Node 22).
- npm (bundled with Node).
- For iOS: Xcode 15+ on macOS, plus CocoaPods (`sudo gem install cocoapods` if missing).
- Python 3.9+ is only needed if you want to run the canonical engine as a backend (Phase-2 / parity test runs). Hospital Lite demo mode does **not** need Python or any backend.

## 3. Run as a web app (one terminal)

```bash
# First time only
cp frontend/.env.hospital_lite frontend/.env.local
npm --prefix frontend install

# Every time
npm --prefix frontend run dev -- --host
```

Open `http://localhost:5173`. You should see:

- The **SAFE-Triage · Hospital Lite** header with a "Decision support only — clinician must confirm" sub-label.
- A clinician sign-in card (name + role) — **local only**, no remote identity. Press *Continue*.
- The **New case** form with a *Demo presets · sample cases, not real patients* row at the top.

### Use the demo presets

Tap any of the five presets. The form fills with synthetic vitals + complaint. Press **Suggest triage**. The deterministic engine produces an ESI level. Then you have to **Confirm** or **Override** (override demands a free-text reason).

Expected (offline JS engine, validated against the canonical Python engine — zero drift across 18 parity fixtures):

| Preset | Expected ESI |
|---|---|
| Chest pain · ?MI | ESI 2 (cardiac chest-pain category) |
| SOB · low SpO₂ | ESI 1 (SpO₂ < 90 hypoxia floor) |
| Fever in child | ESI 1–2 (pediatric tachycardia + fever) |
| Minor wound · low risk | ESI 4 |
| Confused elderly | ESI 2 (altered mental status + sepsis signals) |

## 4. Build a production bundle

```bash
npm --prefix frontend run build
```

Output lands in `frontend/dist/`. This is what the Capacitor iOS shell embeds.

## 5. Run on iOS via Capacitor + Xcode

`frontend/ios/` is already generated and committed (see commits `353d70a` and `f1e00f0`). Do **not** run `cap add ios` again — it would regenerate the Xcode project and you'd lose the existing wiring.

```bash
# After any code change:
npm --prefix frontend run ios:sync   # = vite build + cap sync ios

# Open the Xcode workspace:
npm --prefix frontend run ios:open
```

In Xcode:

1. Select the `App` scheme.
2. Choose a simulator (iPhone 15 / iPad Pro work well) or a connected device.
3. Press **Run** (⌘R).

If Xcode asks about signing, set a development team in *Signing & Capabilities*. The current bundle identifier is `app.safetriage.hospitallite`; you can change it in Xcode if your Apple Developer account expects a different one.

Permissions: the app currently asks for **no** mic / camera / location — Info.plist has no usage-description strings. Don't add fake permission strings to "look professional"; Apple App Review will reject the binary.

## 6. Demo mode characteristics — what's offline

| Behaviour | Status |
|---|---|
| Deterministic ESI v5 / NEWS2 engine | runs in the browser (`frontend/src/lib/triageEngineOfflineFallback.js`) |
| Patient queue, audit trail, clinician profile | persisted in `localStorage` only |
| Sign-in | local-only, no Firebase / no remote identity |
| AI extraction | **not used** in this mode — deterministic only |
| Backend call (`POST /triage`) | attempted first; on any failure (network down, 5xx, timeout) the UI silently falls back to the JS engine and shows an amber *"Offline fallback · clinician must verify"* banner |
| Service worker (`/sw.js`) | registered on production builds only (not in `npm run dev`) |
| PWA install | iOS *Share → Add to Home Screen* / Android *Install app* both work after a production build is served over HTTPS |

To force offline-fallback mode for a demo: open DevTools → Network → Offline, then submit a triage.

## 7. What is NOT production-ready

Be explicit with reviewers and hospital stakeholders about these limits:

1. **Not a certified medical device.** No CE mark, no FDA clearance, no GAHAR sign-off as a device. This is decision support in pilot / shadow mode.
2. **No real patient data should be entered.** The localStorage queue is unencrypted and survives until the user clears site data.
3. **No supervisor PIN gate** on downgrade overrides. Any signed-in user can downgrade with a reason. A real PIN gate is a Phase-2 item.
4. **No audit trail leaves the device** in Hospital Lite mode. Connecting to a backend / cloud audit store is a deliberately separate, later step.
5. **JS fallback engine's Arabic detection is a subset of the canonical Python engine's.** For demos that need full Arabic + Egyptian dialect coverage, run the backend (`SAFE_TRIAGE_MODE=hospital_lite python -m uvicorn main:app --app-dir backend --port 8000`) and the frontend will use it.
6. **No remote logging.** No Crashlytics, no Sentry, nothing phones home. Logs stay in the browser console.
7. **Single-language switch is per-device** (localStorage). Different iPad → different default.

## 8. Verifying it before a demo

Run before any demo where someone you care about is watching:

```bash
# Frontend build must be green
npm --prefix frontend run build

# JS fallback engine smoke (13 named safety floors)
node frontend/src/lib/triageEngineOfflineFallback.smoke.mjs

# Cross-engine parity (only if Python 3.9+ is installed)
python3 tests/parity/run_python_engine.py
node tests/parity/run_js_engine.mjs --compare
```

The last command must say `All parity checks passed (tolerance=0).` — if it doesn't, the JS engine has drifted from the canonical engine and you should stop and investigate before showing the app.

## 9. Known risks / TODOs

1. **Bundle identifier drift** — `app.safetriage.hospitallite` is the current identifier. Decide on the public-facing one (likely `app.zayedmd.safetriage`) before any TestFlight push.
2. **Supervisor downgrade gate** — currently a TODO. See `docs/implementation-notes/safe-triage-phase1-hospital-lite.md` §7.
3. **Pediatric NEWS2** — NEWS2 is adult-only; the engine uses age-banded HR / RR. Mention this if a reviewer asks.
4. **Service-worker stale cache** — if you ship a new build and the iPad / iPhone still shows the old one, *Settings → Safari → Clear History and Website Data* (Safari) or *Delete App and reinstall* (Capacitor IPA).
5. **iPad split-keyboard on the number fields** — vitals fields use `inputMode="decimal"`. Tested in simulator; verify on a real iPad before the demo.
6. **No screenshot-blur of "patient" data** in the printable handoff. Use only demo presets when demoing in front of an audience.

## 10. Emergency overrides during a demo

- **Reset everything:** DevTools console → `localStorage.clear()` → reload.
- **Force RTL:** click the AR pill in the top-right header.
- **Force offline engine:** DevTools → Network → Offline → submit. The amber banner should appear.
- **Force online engine:** Run the backend in another terminal:
  ```bash
  export $(grep -v '^#' backend/.env.hospital_lite | xargs)
  python3 -m uvicorn main:app --app-dir backend --reload --port 8000
  ```

## 11. What this runbook does not cover

- Production deployment to Cloud Run / Firebase Hosting (deliberately out of scope for the Phase-1 demo; see `docs/devops/safe-triage-cicd-action-plan.md`).
- Anything involving real PHI / MIMIC-IV data — that goes through the benchmarking pipeline, not Hospital Lite.
- App Store / TestFlight submission — needs a signed Apple Developer account and a chosen bundle identifier; out of scope here.
