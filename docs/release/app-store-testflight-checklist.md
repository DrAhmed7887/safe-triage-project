# SAFE-Triage Lite — TestFlight / App Store Submission Checklist

**Owner:** Dr. Ahmed Zayed
**Status:** Draft. Not submitted. No App Store Connect record created.
**Last updated:** 2026-05-19

> **Decision support only — clinician must confirm.**
> SAFE-Triage Lite is a Phase-1 educational / decision-support prototype. It is not a certified medical device. Apple App Review will be sensitive to clinical wording; this checklist treats that as a primary risk.

This is the operational checklist. Every item below has to either be ticked or explicitly waived before TestFlight build #1 goes to Apple. Anything marked **manual** must be done by Ahmed — Claude cannot perform these from here.

---

## 1. Apple Developer Program (manual)

| Item | Status | Notes |
|---|---|---|
| Active Apple Developer Program membership ($99/yr) | ☐ | Required for any TestFlight / App Store upload. |
| Two-factor authentication on the Apple ID | ☐ | Required to sign in to App Store Connect from Xcode. |
| Developer agreement + paid-apps agreement signed | ☐ | App Store Connect → Agreements, Tax, and Banking. Even free apps need the Free Apps Agreement. |
| Team role: Account Holder or Admin | ☐ | Needed to create the App Record and submit. |

**Blocker until done:** TestFlight upload will be impossible without these.

## 2. App Store Connect — App Record (manual)

| Item | Status | Notes |
|---|---|---|
| Create new iOS app record | ☐ | App Store Connect → My Apps → "+". |
| Bundle ID: decision needed (see §3) | ☐ | Cannot be changed after first build is uploaded. |
| App name: **SAFE-Triage Lite** | ☐ | 30-char max. Reserved at app-record creation. |
| Primary language: **English (U.S.)** | ☐ | We can add Arabic localisation later. |
| SKU: e.g. `SAFETRIAGE-LITE-001` | ☐ | Free-text, internal. |
| User access: Limited Access | ☐ | Defer until Ahmed has co-collaborators. |

## 3. Bundle Identifier

Current Capacitor config (`frontend/capacitor.config.ts`): `app.safetriage.hospitallite`.

Decision needed before App Record creation:

| Option | Pro | Con |
|---|---|---|
| `app.safetriage.hospitallite` (keep current) | No code changes. iOS project state stable. | Brand reads as a generic side-project. |
| `app.zayedmd.safetriage` | Aligns with the zayedmd brand the user already owns (github.com/DrAhmed7887/zayedmd). | One-time Xcode rename + cap sync. |
| `com.zayedmd.safetriage` | `com.` is the historically dominant prefix. | Same rename cost. |

**Recommendation:** `app.zayedmd.safetriage` once the App Store Connect record is created. Do **not** rename in-place after the first TestFlight upload — Apple ties the bundle ID to the SKU for app analytics and you cannot change it. If you want to rename, do so before the first upload.

**Steps if renaming (manual, in Xcode):**

1. Open `frontend/ios/App/App.xcworkspace`.
2. Select the `App` target → *General* tab → set *Bundle Identifier*.
3. Also update `frontend/capacitor.config.ts` → `appId` so future `cap sync` doesn't overwrite the Xcode project.
4. Re-run `npm --prefix frontend run ios:sync`.
5. Sign in *Signing & Capabilities* and confirm Xcode resolves provisioning.

## 4. Signing & Capabilities (manual)

| Item | Status | Notes |
|---|---|---|
| Development team selected in Xcode | ☐ | *Signing & Capabilities* → *Team*. |
| "Automatically manage signing" enabled | ☐ | OK for a single-developer flow. |
| Provisioning profile generated | ☐ | Auto with the above. |
| Push Notifications capability | ☐ | **Do NOT add this.** Hospital Lite has no FCM. |
| Background Modes | ☐ | **Do NOT add.** No background work. |
| HealthKit | ☐ | **Do NOT add.** Triggers extra App Review scrutiny and we don't use it. |
| App Transport Security: default | ☐ | Hospital Lite ships bundled assets, no network needed. |

## 5. Version / Build numbers

| Field | Initial value | Notes |
|---|---|---|
| Marketing Version (`CFBundleShortVersionString`) | `0.1.0` | Three-digit semver. Bump on every public release. |
| Build Number (`CFBundleVersion`) | `1` | Must be monotonically increasing on TestFlight. |
| Strategy | `1`, `2`, `3`, … per TestFlight build | Bump even for trivial fixes once a build is uploaded. |

Both live in `frontend/ios/App/App/Info.plist` (`$(MARKETING_VERSION)` / `$(CURRENT_PROJECT_VERSION)` placeholders) or directly in the Xcode target's *General* tab. They are **not** in source today; set them in Xcode for build #1.

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

- **6.7" iPhone** (iPhone 15 Pro Max / 16 Pro Max): 1290 × 2796 — **at least 3, up to 10**.
- **6.5" iPhone** (iPhone 14 Plus / 11 Pro Max): 1284 × 2778 or 1242 × 2688 — optional but recommended.
- **iPad 12.9"** (Pro 6th gen): 2048 × 2732 — required if you say the app supports iPad.

Suggested screenshots (synthetic content only):

1. ClinicianGate (sign-in screen) — shows decision-support badge + synthetic-demo banner.
2. Form with a demo preset loaded (Chest pain · ?MI) — shows complaint + vitals.
3. SuggestedTriage card showing ESI 2 with the safety-floor strip.
4. Confirmation flow with override-with-reason open.
5. Handoff record + queue.
6. Arabic-mode form (RTL).

**Do NOT** use real patient names or identifiers in any screenshot. **Do NOT** use clinical photos.

## 9. TestFlight — internal testing (manual)

1. In Xcode, **Product → Archive**.
2. Open *Organizer* → select the archive → **Distribute App** → **App Store Connect**.
3. Wait for Apple to finish "Processing" (typically 10-30 min).
4. App Store Connect → *TestFlight* → *Internal Testing* → add Ahmed's Apple ID as a tester. Internal testers do not need Beta App Review.
5. Test on a real iPhone and a real iPad before any external invitation.

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
| Decide bundle ID (§3) | Ahmed | ☐ |
| Create App Record in App Store Connect | Ahmed | ☐ |
| Host privacy policy at a real URL | Ahmed | ☐ |
| Generate iOS screenshots (synthetic content) | Ahmed | ☐ |
| Set Marketing + Build version in Xcode | Ahmed | ☐ |
| Disable `webContentsDebuggingEnabled` for the release scheme — see §13 | Ahmed | ☐ |
| Archive + upload via Xcode | Ahmed | ☐ |
| Internal TestFlight smoke on real iPhone + iPad | Ahmed | ☐ |
| Submit for Beta App Review (for external testers) | Ahmed | ☐ |
| Submit for full App Review (when ready for App Store) | Ahmed | ☐ |

## 13. Pre-flight: `webContentsDebuggingEnabled`

`frontend/capacitor.config.ts` currently sets `webContentsDebuggingEnabled: true`. This is the right value for the simulator and a local iPhone connected to Xcode (you can inspect the WKWebView from Safari → Develop). **It must be `false` for any TestFlight or App Store build** — Apple has historically accepted it both ways, but it's a clear "release vs debug" signal and an easy reason to be questioned.

Two ways to fix at release time:

- **Manual:** flip the boolean to `false`, run `npm --prefix frontend run ios:sync`, archive.
- **Better (later):** add a `capacitor.config.release.ts` and a build-time switch. Not required for build #1.

Track this on the must-flip-before-submit list.

## 14. What this checklist does NOT cover

- Cloud deployment of the (separate) cloud-connected SAFE-Triage app — see `docs/devops/safe-triage-cicd-action-plan.md`.
- MIMIC-IV benchmarking / thesis work.
- GAHAR / CE / FDA regulatory pathway — Phase 1 is not a regulated device submission.
