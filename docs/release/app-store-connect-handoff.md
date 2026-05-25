# SAFE-Triage Lite App Store Connect Handoff

Date: 2026-05-25
Owner: Ahmed
Status: Manual Apple steps remaining. Do not submit for App Review in this release-control pass.

## Candidate

- App: `SAFE-Triage Lite`
- App Store Connect: <https://appstoreconnect.apple.com/apps/6771520904/appstore>
- TestFlight build page: <https://appstoreconnect.apple.com/apps/6771520904/testflight/ios>
- Privacy policy URL: <https://github.com/DrAhmed7887/safe-triage-project/blob/codex/safe-triage-lite-release-candidate/docs/release/privacy-policy.md>
- Bundle ID: `app.safetriage.hospitallite`
- Version/build: `1.0 (3)`
- Apple team/profile used for upload: `6F22G47URV` / `SAFE-Triage Lite App Store`
- App Store Connect processing status: build `1.0 (3)` is `VALID`.

## Manual Apple Steps Remaining

1. In App Store Connect, select build `1.0 (3)` for the intended internal TestFlight release.
2. Confirm the published app-specific privacy policy URL remains publicly reachable.
3. Upload/review final iPhone and iPad screenshots listed below, using synthetic content only.
4. Complete App Privacy, age-rating, export-compliance, support/contact, metadata, and review-note fields.
5. Run internal TestFlight smoke testing on a real iPhone and iPad using only the synthetic presets.
6. Stop before Beta App Review or App Review submission unless Ahmed separately elects to proceed.

## What Not To Claim

Do not claim validated clinical use, diagnosis, autonomous triage, medical-device approval or certification, or replacement of a clinician. Describe this build only as a bilingual English/Arabic synthetic-demo decision-support prototype that requires clinician confirmation.

## Screenshots Checklist

- [ ] Upload the five prepared 6.9-inch iPhone images from `docs/release/app-store-screenshots/iphone-6.9/` (`1320 x 2868`).
- [ ] Upload the five prepared 13-inch iPad images from `docs/release/app-store-screenshots/ipad-13/` (`2064 x 2752`), because iPad is supported.
- [ ] Confirm screenshots show only synthetic cases and no names, MRNs, identifiers, contact details, or clinical photos.
- [ ] Confirm the set shows the no-real-PHI/clinician gate, demo presets, safety-floor result, pediatric caveat, and Arabic interface.

## Privacy Checklist

- [x] Publish the app-specific privacy policy at its public HTTPS repository URL.
- [ ] Declare no developer-collected data and no tracking for this Hospital Lite binary, subject to the final App Store Connect questionnaire.
- [ ] Confirm no push notifications, analytics, advertising, or Firebase runtime/messaging behavior is represented for Hospital Lite.
- [ ] Confirm text explains local-only synthetic demo storage and instructs users not to enter real patient data.
- [ ] Confirm no camera, microphone, location, contacts, Bluetooth, or tracking permission claims are added.

## Export Compliance Checklist

- [ ] Open build `1.0 (3)` in App Store Connect and answer any export-compliance prompt before tester availability.
- [ ] Confirm the app uses only Apple's platform-provided HTTPS/TLS behavior and contains no custom or separately implemented encryption before selecting the corresponding exempt/not-using-nonexempt-encryption answer.
- [ ] Record the completed export-compliance response in the App Store Connect build record; do not alter the binary for this administrative answer.

## Rollback

Build `1.0 (3)` is the current valid candidate. If any manual metadata, screenshot, privacy, or export-compliance issue prevents release, leave build `1.0 (3)` unsubmitted while correcting the App Store Connect materials. Do not revert to an older build or upload a new binary unless a real binary blocker is identified.
