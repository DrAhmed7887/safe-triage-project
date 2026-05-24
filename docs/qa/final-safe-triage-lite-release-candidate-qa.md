# Final SAFE-Triage Lite release-candidate QA

**Date:** 2026-05-20 (Africa/Cairo)  
**Engineer:** Codex  
**Branch:** `codex/safe-triage-lite-release-candidate`  
**Repo:** `/Volumes/Extreme SSD/safe-triage-project-github`

## 1. Executive verdict

SAFE-Triage Lite is ready as a local Hospital Lite release candidate for
synthetic demos, thesis defense, hackathon review, and iOS handoff into Xcode.

It can be built as a Hospital Lite production bundle, synced into Capacitor iOS,
and prepared for TestFlight/App Store work. It is not ready for App Store
submission until Ahmed completes the Apple manual blockers listed below.

The clinical safety posture held: deterministic rules remain authoritative,
the JS fallback did not under-triage relative to the Python parity fixtures, and
clinician confirmation is still required before a case enters the handoff queue.

## 2. What was tested

Codex inspected and tested:

- Workspace guard, branch, status, and recent release commits.
- Frontend package scripts.
- Hospital Lite route and entry point.
- Hospital Lite UI components.
- Offline JS fallback engine.
- Python/JS parity harness.
- Capacitor config and iOS wrapper.
- Hospital Lite production bundle contents.
- iOS `public/` bundle contents after `ios:sync:hospital-lite`.
- Release docs, privacy policy draft, metadata draft, and demo script.
- Five synthetic demo presets in rendered browser QA.

## 3. Build results

| Check | Result | Notes |
|---|---:|---|
| `npm --prefix frontend install` | Pass | No package changes. npm reports 11 existing audit findings. |
| `npm --prefix frontend run build` | Pass | Production build compiles. |
| `npm --prefix frontend run build:hospital-lite` | Pass | Hospital Lite build strips FCM worker and unused standard-app assets. |
| `node frontend/src/lib/triageEngineOfflineFallback.smoke.mjs` | Pass | 13/13 safety smoke cases. |
| `python3 tests/parity/run_python_engine.py` | Pass | 19 canonical fixture outputs written. |
| `node tests/parity/run_js_engine.mjs --compare` | Pass | 19/19 parity checks; tolerance 0; no JS under-triage. |
| `npm --prefix frontend run lint` | Fails | 9 remaining standard-app issues; no Hospital Lite blockers. |
| `npm --prefix frontend run ios:sync:hospital-lite` | Pass | Hospital Lite bundle copied into `frontend/ios/App/App/public/`. |
| `xcodebuild -downloadPlatform iOS -buildVersion 26.5 -architectureVariant arm64` | Pass | iOS 26.5 platform/runtime installed locally. |
| `xcodebuild ... CODE_SIGNING_ALLOWED=NO` | Pass | Unsigned native iOS Release compile passed. |
| `xcodebuild ... -allowProvisioningUpdates ... archive` | Blocked | Xcode reported `No Account for Team "7R65LRGNHT"` and no provisioning profile for `app.safetriage.hospitallite`. |

### Lint classification

| Bucket | Result |
|---|---|
| A. Hospital Lite blocking | None found. |
| B. iOS/TestFlight blocking | None found. |
| C. Standard cloud app only | `AuthContext.jsx`, `useFirebaseMessaging.js`, `NotificationBell.jsx`, `TriageConfirmation.jsx`, `TriageForm.jsx`, `TriageStatsWidget.jsx`. |
| D. Safe cleanup fixed | Unused parameters/catches and a render-created skeleton component. |

The remaining lint errors are React hook-rule and Fast Refresh issues in the
standard cloud app. They need a separate standard-app refactor and were not
broad-refactored during this Hospital Lite release pass.

## 4. Clinical safety results

Rendered browser QA was run against the local Hospital Lite app at
`http://127.0.0.1:5173/`.

| Preset | Result | Required clinical surfaces |
|---|---:|---|
| Chest pain / possible MI | ESI 2, NEWS2 5 medium | Red flags, safety floor, clinician confirmation. |
| Shortness of breath + low SpO2 | ESI 1, NEWS2 6 high | Red flags, safety floor, clinician confirmation. |
| Fever in child | ESI 1, NEWS2 10 high | Red flags, safety floor, pediatric NEWS2 caveat, clinician confirmation. |
| Minor wound | ESI 4, NEWS2 0 low | No false safety floor; clinician confirmation still required. |
| Confused elderly patient | ESI 2, NEWS2 11 high | Red flags, safety floor, clinician confirmation. |

For each preset:

- The preset filled form fields only.
- No result appeared before pressing **Suggest triage**.
- The deterministic engine decided the ESI result.
- NEWS2 appeared.
- Red flags appeared when expected.
- Safety-floor strip appeared when expected.
- The pediatric NEWS2 caveat appeared for the child case only.
- **Confirm this level** and **Override** remained visible.
- No autonomous diagnosis wording appeared.
- The no-real-PHI warning remained visible.
- Browser console warnings/errors were empty.

## 5. Privacy and security results

Hospital Lite privacy checks passed after a bundle hardening fix:

- `dist/firebase-messaging-sw.js` is absent after `build:hospital-lite`.
- `frontend/ios/App/App/public/firebase-messaging-sw.js` is absent after
  `ios:sync:hospital-lite`.
- Firebase strings, Firebase project identifiers, and the FCM worker path are
  absent from the Hospital Lite `dist/` bundle and iOS `public/` bundle.
- No push-notification UI or remote patient workflow appears in Hospital Lite.
- Demo presets are synthetic.
- The sticky banner warns not to enter real patient names or identifiers.
- Local queue, clinician profile, language preference, and audit records use
  local storage only.
- No analytics, ads, tracking SDKs, or new third-party SDKs were added.
- `Info.plist` has no camera, microphone, location, tracking, Bluetooth, or
  notification usage strings.

The Hospital Lite bundle still contains `http://localhost:8000` because the app
tries an optional local developer backend before falling back to the browser
engine. Release docs now describe this as a loopback-only developer path, not a
cloud service.

## 6. iOS and Capacitor results

| Check | Result |
|---|---:|
| Capacitor app name | `SAFE-Triage` |
| Capacitor app ID | `app.safetriage.hospitallite` |
| `webDir` | `dist` |
| Hospital Lite bundle synced to iOS | Pass |
| Firebase messaging worker in iOS public folder | Absent |
| Unnecessary permission strings | None found |
| Xcode version/build placeholders | `MARKETING_VERSION = 1.0`, `CURRENT_PROJECT_VERSION = 1` in project settings |
| Xcode open | Not run; opening GUI was left as Ahmed's manual step |

`frontend/capacitor.config.ts` now has `webContentsDebuggingEnabled: false` for
the release path. Flip it temporarily only for local Safari WKWebView debugging,
then restore `false` before archiving.

## 7. App Store/TestFlight readiness

Release docs were reviewed and updated:

- `docs/release/app-store-testflight-checklist.md`
- `docs/release/app-store-metadata-draft.md`
- `docs/release/privacy-policy-draft.md`
- `docs/demo/app-store-demo-script.md`

The wording stays cautious:

- No claim that the app is validated for clinical use.
- No approved-medical-device wording.
- No autonomous diagnosis claim.
- No clinician-replacement claim.
- Synthetic demo only.
- No real patient data.
- Decision support only; clinician confirmation required.
- Privacy policy now reflects the optional localhost backend path and the
  stripped Firebase/Auth Hospital Lite bundle.

## 8. Remaining blockers

Ahmed must complete these manually before TestFlight/App Store submission:

- Apple Developer Program membership and agreements.
- App Store Connect app record.
- Final bundle ID alignment.
- Xcode signing team and provisioning.
- Xcode account/team access for `7R65LRGNHT`.
- Hosted privacy policy URL.
- Synthetic screenshots for required iPhone/iPad sizes are prepared in
  `docs/release/app-store-screenshots/`; Ahmed can replace them with
  signed-device captures if needed.
- Age-rating questionnaire.
- App Privacy nutrition label.
- Export compliance answers if App Store Connect asks.
- Confirm `webContentsDebuggingEnabled: false`.
- Xcode archive, validation, upload, and TestFlight review.

Standard cloud-app cleanup remains separate:

- Refactor remaining React hook lint issues in Auth, Firebase messaging,
  notification history, old triage confirmation timer, and standard triage form
  effects.
- Review npm audit findings before any broader cloud-connected release.

## 9. Manual steps for Ahmed

1. Run `npm --prefix frontend run ios:open`.
2. In Xcode, choose the final bundle ID before creating the App Store Connect
   record.
3. Select the Apple developer team under **Signing & Capabilities**.
4. Decide whether to keep `SAFE-Triage` display name or set
   `SAFE-Triage Lite`.
5. Confirm `webContentsDebuggingEnabled: false` for the release archive path.
6. Archive with **Product → Archive**.
7. Upload only after the hosted privacy policy URL, screenshots, age rating,
   privacy label, and App Review notes are ready.

## 10. Exact final commands

Run these from `/Volumes/Extreme SSD/safe-triage-project-github`:

```bash
npm --prefix frontend install
npm --prefix frontend run build:hospital-lite
node frontend/src/lib/triageEngineOfflineFallback.smoke.mjs
python3 tests/parity/run_python_engine.py
node tests/parity/run_js_engine.mjs --compare
npm --prefix frontend run ios:sync:hospital-lite
npm --prefix frontend run ios:open
```

Lint is useful but currently expected to fail on standard-app issues:

```bash
npm --prefix frontend run lint
```
