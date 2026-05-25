# SAFE-Triage Lite App Store Connect handoff

Date: May 25, 2026
Owner: Ahmed
Status: Build `1.0 (4)` is selected for version `1.0`. Do not submit for
App Review in this release-control pass.

## Candidate

This is the App Store Connect release-candidate record for the offline Hospital
Lite binary.

- App: `SAFE-Triage Lite`
- App Store Connect:
  <https://appstoreconnect.apple.com/apps/6771520904/appstore>
- TestFlight:
  <https://appstoreconnect.apple.com/apps/6771520904/testflight/ios>
- Privacy policy:
  <https://github.com/DrAhmed7887/safe-triage-project/blob/codex/safe-triage-lite-release-candidate/docs/release/privacy-policy.md>
- Bundle ID: `app.safetriage.hospitallite`
- Current App Store candidate: `1.0 (4)`, `VALID`, `APP_STORE_ELIGIBLE`
- Prior internal-only baseline: `1.0 (3)`, `VALID`, `INTERNAL_ONLY`
- Apple team/profile: `6F22G47URV` / `SAFE-Triage Lite App Store`

Build `1.0 (4)` was required because Apple rejects build `1.0 (3)` for the App
Store version relationship: it was exported for internal TestFlight only.

## Completed preparation

The following App Store Connect preparation was completed without submitting
for review:

- [x] Entered cautious subtitle, promotional text, description, keywords,
  support URL, privacy-policy URL, categories, and copyright.
- [x] Uploaded five 6.9-inch iPhone screenshots and five 13-inch iPad
  screenshots; Apple reports all ten assets as complete.
- [x] Completed the age-rating declaration honestly as health/wellness content
  with frequent or intense medical/treatment information; Apple computes 17+.
- [x] Answered export compliance for build `1.0 (4)` as not using nonexempt
  encryption.
- [x] Added build `1.0 (4)` to the internal TestFlight group with Ahmed as an
  internal tester.
- [x] Selected build `1.0 (4)` for App Store version `1.0`.

## Manual Apple steps remaining

Ahmed must complete these user-account or device-dependent steps:

1. In the App Store Connect web interface, complete **App Privacy** for this
   Hospital Lite binary as no data collected by the developer and no tracking.
2. Before any later review submission, provide and verify App Review contact
   details and reviewer notes.
3. Install build `1.0 (4)` through internal TestFlight on a real iPhone and a
   real iPad, and run the synthetic-preset smoke tests.
4. Stop before **Beta App Review** or **App Review** unless Ahmed separately
   decides to proceed.

## What not to claim

Do not claim validated clinical use, diagnosis, autonomous triage,
medical-device approval or certification, or replacement of a clinician.
Describe this build only as a bilingual English/Arabic synthetic-demo
decision-support prototype that requires clinician confirmation.

## Screenshots checklist

The screenshot submission is complete and uses synthetic content only:

- [x] Five prepared 6.9-inch iPhone images (`1320 x 2868`) uploaded.
- [x] Five prepared 13-inch iPad images (`2064 x 2752`) uploaded.
- [x] Sets include the no-real-PHI clinician gate, demo presets, safety-floor
  result, pediatric caveat, and Arabic interface.
- [x] No real names, MRNs, identifiers, contact details, or clinical photos
  are shown.

## Privacy checklist

The public policy and binary checks are complete; the public-facing Apple
questionnaire still requires Ahmed's authenticated web confirmation.

- [x] Published the app-specific privacy policy at the public HTTPS repository
  URL above and entered that URL in App Store Connect.
- [x] Confirmed the archived Hospital Lite bundle has no Firebase messaging
  worker and no Firebase or messaging runtime strings.
- [x] Confirmed the policy describes local-only synthetic demo storage and
  tells users not to enter real patient data.
- [ ] In **App Privacy**, save the declarations: no developer-collected data
  and no tracking.

## Export-compliance checklist

The export answer is recorded for the current candidate:

- [x] Confirmed build `1.0 (4)` uses no custom or separately implemented
  nonexempt encryption.
- [x] Recorded `usesNonExemptEncryption = false` for build `1.0 (4)`.

## Rollback

Build `1.0 (4)` is the current valid App Store candidate. Build `1.0 (3)`
remains valid for internal TestFlight only and cannot be selected for the App
Store version. Leave build `1.0 (4)` unsubmitted while correcting any remaining
App Privacy or device-testing issue; do not return to build `1.0 (3)` for an
App Store release.
