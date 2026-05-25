# SAFE-Triage Lite — TestFlight / App Store Submission Checklist

**Owner:** Dr. Ahmed Zayed
**Status:** Build uploaded to App Store Connect. Not submitted for App Review.
**Last updated:** 2026-05-25

> **Decision support only — clinician must confirm.**
> SAFE-Triage Lite is a Phase-1 educational / decision-support prototype. It is not a certified medical device. Apple App Review will be sensitive to clinical wording; this checklist treats that as a primary risk.

This is the operational checklist. Build `1.0 (3)` has been uploaded and Apple
reports it as `VALID`. Anything marked **manual** must still be completed by
Ahmed in App Store Connect before external TestFlight or App Review.

---

## 1. Apple Developer Program (manual)

| Item | Status | Notes |
|---|---|---|
| Active Apple Developer Program membership ($99/yr) | Done | Required for TestFlight / App Store upload. |
| Two-factor authentication on the Apple ID | Done | Required to sign in to App Store Connect from Xcode. |
| Developer agreement + paid-apps agreement signed | Verify | App Store Connect → Agreements, Tax, and Banking. Even free apps need the Free Apps Agreement. |
| Team role: Account Holder or Admin | Done | API key role reported as Admin. |

**Current status:** command-line upload is working.

## Final submission blockers

These items remain manual blockers before Ahmed can submit for external
TestFlight or full App Review. Codex uploaded the build but did not submit it
for review.

- Hosted privacy policy URL.
- Final iPhone and iPad screenshots in App Store Connect.
- Age-rating questionnaire.
- App Privacy nutrition label.
- Export compliance answers, if App Store Connect asks for them.
- Build selection for TestFlight internal testing.
- External TestFlight review, if using external testers.
- Final App Store metadata completion and human review approval.

## 2. App Store Connect — App Record (manual)

| Item | Status | Notes |
|---|---|---|
| Create new iOS app record | Done | App Store Connect app ID `6771520904`. |
| Bundle ID: `app.safetriage.hospitallite` | Done | Cannot be changed after the uploaded builds. |
| App name: **SAFE-Triage Lite** | Done | 30-char max. Reserved at app-record creation. |
| Primary language: **English (U.S.)** | Done | Add Arabic localisation later if needed. |
| SKU: `SAFE-TRIAGE-LITE-IOS` | Done | Free-text, internal. |
| User access: Limited Access | ☐ | Defer until Ahmed has co-collaborators. |

## 3. Bundle Identifier

Current Capacitor config (`frontend/capacitor.config.ts`): `app.safetriage.hospitallite`.

Final Bundle ID:

```text
app.safetriage.hospitallite
```

Do not rename it for this App Store Connect record. Apple ties uploaded builds
to the Bundle ID.

## 4. Signing & Capabilities (manual)

| Item | Status | Notes |
|---|---|---|
| Development team selected for archive | Done | Command-line archive used team `6F22G47URV`. |
| Signing style | Done | Manual App Store signing used for the uploaded archive. |
| Provisioning profile generated | Done | `SAFE-Triage Lite App Store` installed locally. |
| Push Notifications capability | ☐ | **Do NOT add this.** Hospital Lite has no FCM. |
| Background Modes | ☐ | **Do NOT add.** No background work. |
| HealthKit | ☐ | **Do NOT add.** Triggers extra App Review scrutiny and we don't use it. |
| App Transport Security: default | ☐ | Hospital Lite ships bundled assets, no network needed. |

## 5. Version / Build numbers

| Field | Initial value | Notes |
|---|---|---|
| Marketing Version (`CFBundleShortVersionString`) | `1.0` | Current uploaded marketing version. |
| Latest uploaded Build Number (`CFBundleVersion`) | `3` | Build `3` is `VALID` in App Store Connect. |
| Strategy | `1`, `2`, `3`, … per TestFlight build | Bump even for trivial fixes once a build is uploaded. |

Both live in `frontend/ios/App/App/Info.plist` (`$(MARKETING_VERSION)` /
`$(CURRENT_PROJECT_VERSION)` placeholders) and the Xcode target build settings.
The current valid candidate is build `1.0 (3)`.

## 6. Privacy

| Item | Status | Notes |
|---|---|---|
| Privacy policy URL — **required for App Store submission** | ☐ | Draft at `docs/release/privacy-policy-draft.md`. Host at https://zayedmd.com/safe-triage/privacy or similar before submitting. |
| Privacy Manifest (`PrivacyInfo.xcprivacy`) | ☐ | Apple now requires this for many APIs. Hospital Lite uses none of the flagged APIs (no UserDefaults beyond Capacitor defaults, no file timestamp, no system boot time, no disk space). Default Capacitor template should be fine. |
| App Privacy nutrition label | ☐ | See `docs/release/app-store-metadata-draft.md` §App Privacy. |
| `NSUserTrackingUsageDescription` | ☐ | **Not needed.** No tracking. |
| Mic / camera / location / Bluetooth usage strings | ☐ | **None needed.** None of those APIs used. Confirm by re-inspecting `Info.plist`. |

## 7. Age rating

| Item | Decision | Notes |
|---|---|---|
| Apple age rating (computed) | 17+ (medical/health/clinical) | Triggered by *Medical/Treatment Information* — yes (occasional). |
| "Made for Kids" | No | |
| Restricted Web Access | No | |

Be cautious: choosing "Frequent/Intense Medical/Treatment Information" will inflate the rating, but understating clinical content risks App Review rejection. *Occasional* is the honest setting for a demo / decision-support prototype that doesn't render real patient charts.

## 8. Screenshot requirements

Minimum required:

- **6.9" iPhone** (iPhone 14 Pro Max through newer Max/Plus models): accepted portrait sizes include 1260 × 2736, 1290 × 2796, and 1320 × 2868 — **at least 3, up to 10**.
- **6.5" iPhone** (iPhone 14 Plus / 11 Pro Max): 1284 × 2778 or 1242 × 2688 — optional but recommended.
- **13" iPad**: accepted portrait sizes include 2064 × 2752 and 2048 × 2732 — required if the app supports iPad.

Prepared screenshot assets:

- `docs/release/app-store-screenshots/iphone-6.9/`
- `docs/release/app-store-screenshots/ipad-13/`

Suggested screenshots (synthetic content only):

1. ClinicianGate (sign-in screen) — shows decision-support badge + synthetic-demo banner.
2. Form with a demo preset loaded (Chest pain · ?MI) — shows complaint + vitals.
3. SuggestedTriage card showing ESI 2 with the safety-floor strip.
4. Confirmation flow with override-with-reason open.
5. Handoff record + queue.
6. Arabic-mode form (RTL).

**Do NOT** use real patient names or identifiers in any screenshot. **Do NOT** use clinical photos.

## 9. TestFlight — internal testing (manual)

1. App Store Connect → *TestFlight* → select build `1.0 (3)`.
2. Add Ahmed's Apple ID as an internal tester. Internal testers do not need
   Beta App Review.
3. Install from the TestFlight app on a real iPhone and a real iPad.
4. Run the SOB / low SpO2 preset and the Fever in child preset.
5. Confirm the no-real-PHI warning, safety-floor strip, pediatric NEWS2 caveat,
   and clinician confirmation flow before any external invitation.

## 10. TestFlight — external testing (manual)

External testing requires **Beta App Review** by Apple — usually 24-48 hours.

| Item | Status | Notes |
|---|---|---|
| Test information / "What to test" notes | ☐ | Draft at `docs/release/app-store-metadata-draft.md` §TestFlight Notes. |
| Beta App Description | ☐ | Same source. |
| Email for tester feedback | ☐ | Use a real address you check. |
| Marketing URL (optional) | ☐ | Can be a placeholder. |

External testers can give feedback for **up to 90 days**, then the build expires.

## 11. App Review — clinical wording risk

Apple's App Review Guidelines, especially §1.4 (Physical Harm) and §5.1 (Privacy), are stricter for anything medical. Practical guardrails:

- **Do not say "AI doctor", "diagnose", "treat", "replace clinician".** Even casually.
- **Do not imply real-time emergency routing.** This app does not call ambulances.
- **Do not advertise the app for actual ED use.** Frame as educational / demo / decision-support prototype.
- **Have the in-app banner clearly visible at all times** (already implemented in `HospitalShell.jsx`).
- **Provide the App Review team with demo presets**. Reviewers can't type real Arabic complaints; the presets let them validate the flow.

If App Review rejects, the most likely reasons are:

1. *"Medical app needs evidence of regulatory approval."* Counter: this is a synthetic-demo / decision-support prototype, no medical claims made.
2. *"Cannot enter the app without an account."* Counter: ClinicianGate is local-only, no account; it accepts any name.
3. *"Insufficient functionality."* Counter: full triage flow runs in the demo with the five presets.

## 12. Final manual steps before submission

| Step | Owner | Done |
|---|---|---|
| Confirm selected build is `1.0 (3)` (`VALID`) | Ahmed | ☐ |
| Host privacy policy at a real URL | Ahmed | ☐ |
| Review prepared iPhone/iPad screenshots and replace with signed-device captures if needed | Ahmed | ☐ |
| Complete App Privacy nutrition labels and age rating | Ahmed | ☐ |
| Answer export-compliance questions for build `1.0 (3)` | Ahmed | ☐ |
| Complete metadata and reviewer notes using the cautious draft | Ahmed | ☐ |
| Internal TestFlight smoke on real iPhone + iPad | Ahmed | ☐ |
| Submit for Beta App Review (for external testers) | Ahmed | ☐ |
| Submit for full App Review (when ready for App Store) | Ahmed | ☐ |

## 13. Pre-flight: `webContentsDebuggingEnabled`

`frontend/capacitor.config.ts` currently sets `webContentsDebuggingEnabled: false`. Keep it false for TestFlight and App Store builds. Flip it temporarily only when debugging a local simulator or connected iPhone from Safari → Develop, then restore `false` before archiving.

If debugging is needed before release:

- **Temporary debug:** set the value to `true`, run `npm --prefix frontend run ios:sync`, inspect the device, then restore `false`.
- **Release:** run `npm --prefix frontend run ios:sync:hospital-lite` after restoring `false`, then archive.

Track this as a confirmation item before every archive.

## 14. What this checklist does NOT cover

- Cloud deployment of the (separate) cloud-connected SAFE-Triage app — see `docs/devops/safe-triage-cicd-action-plan.md`.
- MIMIC-IV benchmarking / thesis work.
- GAHAR / CE / FDA regulatory pathway — Phase 1 is not a regulated device submission.
