# SAFE-Triage Lite Launch-Now Checklist

Date: 2026-05-25
Branch: `codex/safe-triage-lite-release-candidate`
Build-control commit: `08dd16a`

## 0. Current App Store Connect Status

Updated: 2026-05-25.

- App Store Connect app record exists: `SAFE-Triage Lite`, SKU
  `SAFE-TRIAGE-LITE-IOS`.
- Bundle ID exists and matches the iOS archive:
  `app.safetriage.hospitallite`.
- The API key belongs to App Store Connect team `6F22G47URV`. The earlier
  local development team `7R65LRGNHT` could not sign the App Store archive
  because it did not own the matching distribution certificate/profile.
- Apple Distribution certificate created through the API:
  `Apple Distribution: Ahmed Zayed (6F22G47URV)`.
- App Store profile created and installed locally:
  `SAFE-Triage Lite App Store`
  (`495a3d4f-75f0-4237-b135-acc2c46e9266`).
- Build `1.0 (1)` uploaded successfully and reached App Store Connect
  processing.
- Build `1.0 (2)` uploaded successfully after the App Store-facing visual pass
  and offline-first Hospital Lite correction. Xcode reported:
  `Uploaded package is processing` and `Upload succeeded`.
- Build `1.0 (3)` was archived from the final branded Hospital Lite bundle and
  uploaded successfully after replacing the App Store icon with an opaque PNG.
  Xcode reported: `Uploaded package is processing`, `Upload succeeded`, and
  `** EXPORT SUCCEEDED **`.
- App Store Connect reports build `1.0 (3)` as `VALID` but `INTERNAL_ONLY`, so
  Apple rejects it for the App Store version relationship.
- Build `1.0 (4)` was required as a true release blocker correction. It was
  archived from the same Hospital Lite bundle with the App Store-eligible
  export configuration, uploaded successfully, and reports `VALID` and
  `APP_STORE_ELIGIBLE`.
- Build `1.0 (4)` is selected for App Store version `1.0` and is available in
  the internal TestFlight group.
- App Store Connect metadata, privacy-policy URL, categories, age rating,
  export compliance, and ten screenshots have been completed. App Privacy
  web confirmation and real-device smoke testing remain manual.
- App Store Connect API now shows two valid builds:
  - build `1` uploaded `2026-05-20T14:11:32-07:00`, state `VALID`
  - build `2` uploaded `2026-05-20T14:31:13-07:00`, state `VALID`
- App Store Connect API now shows build `3` as `VALID`, uploaded
  `2026-05-20T15:14:25-07:00`, `expired=false`.
- No App Review submission has been made.

## 1. Current Branch And Commit

- Repository: `/Users/ahmedzayed/Downloads/safe-triage-project-github`
- Branch: `codex/safe-triage-lite-release-candidate`
- Build-control commit: `08dd16a release: prepare App Store eligible build 4`

## 2. Commands Run

```bash
pwd
git branch --show-current
git status --short
git log --oneline -5

npm --prefix frontend install
npm --prefix frontend run build
npm --prefix frontend run build:hospital-lite
node frontend/src/lib/triageEngineOfflineFallback.smoke.mjs
python3 tests/parity/run_python_engine.py
node tests/parity/run_js_engine.mjs --compare
npm --prefix frontend run ios:sync:hospital-lite
npm --prefix frontend run lint

npm --prefix frontend run dev -- --host
npm --prefix frontend run ios:sync:hospital-lite
npm --prefix frontend run ios:open
xcodebuild -downloadPlatform iOS -buildVersion 26.5 -architectureVariant arm64
xcodebuild -project frontend/ios/App/App.xcodeproj -target App -configuration Release -sdk iphoneos26.5 build CODE_SIGNING_ALLOWED=NO
xcodebuild -project frontend/ios/App/App.xcodeproj -scheme App -configuration Release -sdk iphoneos26.5 -destination generic/platform=iOS -archivePath frontend/ios/build/SAFE-Triage-Lite.xcarchive archive DEVELOPMENT_TEAM=7R65LRGNHT
xcodebuild -project frontend/ios/App/App.xcodeproj -scheme App -configuration Release -sdk iphoneos26.5 -destination generic/platform=iOS -archivePath frontend/ios/build/SAFE-Triage-Lite.xcarchive archive DEVELOPMENT_TEAM="$APPLE_DEVELOPMENT_TEAM" -allowProvisioningUpdates -authenticationKeyPath "$ASC_KEY_PATH" -authenticationKeyID "$ASC_KEY_ID" -authenticationKeyIssuerID "$ASC_ISSUER_ID"
python3 frontend/scripts/generate-brand-assets.py
npm --prefix frontend run build:hospital-lite
npm --prefix frontend run ios:sync:hospital-lite
xcodebuild -project frontend/ios/App/App.xcodeproj -scheme App -configuration Release -sdk iphoneos26.5 -destination generic/platform=iOS -derivedDataPath frontend/ios/build/DerivedData -archivePath frontend/ios/build/SAFE-Triage-Lite-build3-opaque.xcarchive archive DEVELOPMENT_TEAM=6F22G47URV CODE_SIGN_STYLE=Manual PROVISIONING_PROFILE_SPECIFIER='SAFE-Triage Lite App Store' CODE_SIGN_IDENTITY='Apple Distribution' CURRENT_PROJECT_VERSION=3 MARKETING_VERSION=1.0
xcodebuild -exportArchive -archivePath frontend/ios/build/SAFE-Triage-Lite-build3-opaque.xcarchive -exportPath frontend/ios/build/export-build3-opaque -exportOptionsPlist frontend/ios/build/ExportOptions.testflight-upload.plist -authenticationKeyPath "$ASC_KEY_PATH" -authenticationKeyID "$ASC_KEY_ID" -authenticationKeyIssuerID "$ASC_ISSUER_ID"
```

Additional bundle checks were run with `find` and `rg` against `frontend/dist`,
`frontend/ios/App/App/public`, and the Hospital Lite source path.

## 3. Test Results

- Workspace guard: passed.
- `npm install`: passed; npm still reports existing audit findings (`5 moderate`, `6 high`).
- Standard Vite build: passed.
- `hospital_lite` production build: passed.
- Offline fallback smoke: passed, `13 passed, 0 failed`.
- Python canonical parity output: passed and regenerated `tests/parity/python_results.json` without tracked changes.
- JS parity compare: passed, `19/19`, tolerance `0`.
- Capacitor Hospital Lite sync: passed.
- Browser launch QA: passed at `http://localhost:5173/`.
- Browser console during launch QA: no warnings or errors.
- Lint: failed only in non-Hospital-Lite standard cloud/auth/notification code paths.
- iOS 26.5 platform install: passed.
- Unsigned native iOS Release compile: passed with `CODE_SIGNING_ALLOWED=NO`.
- Signed archive without provisioning updates: failed as expected because no
  provisioning profile existed locally.
- Signed archive with App Store Connect API key and provisioning updates:
  initially blocked by Xcode account/team provisioning. Xcode reported
  `No Account for Team "7R65LRGNHT"`. The release archive now signs with the
  App Store Connect team that owns the app record/profile: `6F22G47URV`.
- App Store Connect API environment file: created locally at
  `.env.apple-connect.local`; ignored by Git.
- App Store Connect private key: moved out of the repo to
  `~/.appstoreconnect/private_keys/AuthKey_C26JYVJZ24.p8` with `600`
  permissions.
- App Store Connect API authentication: passed. Read-only API checks returned
  `200 OK` for apps, Bundle IDs, certificates, profiles, and devices.
- App Store Connect app record lookup: passed for `SAFE-Triage Lite`
  (`app.safetriage.hospitallite`).
- Developer Bundle ID lookup: passed for `app.safetriage.hospitallite`.
- App Store upload: passed for build `1.0 (2)`; Apple reports build `2` as
  `VALID`.
- Final branded App Store upload: passed for build `1.0 (3)` from
  `frontend/ios/build/SAFE-Triage-Lite-build3-opaque.xcarchive`.
- First build `3` upload attempt failed with Apple validation code `90717`
  because the large App Icon contained an alpha channel. The icon generator was
  corrected to emit opaque RGB icons, assets were regenerated, and the second
  build `3` archive/upload succeeded.
- App Store eligibility check: build `1.0 (3)` is `INTERNAL_ONLY` and cannot be
  selected for an App Store version.
- Replacement App Store upload: passed for build `1.0 (4)` from
  `frontend/ios/build/SAFE-Triage-Lite-build4-appstore.xcarchive`.
- App Store Connect API verification: build `1.0 (4)` is `VALID`,
  `APP_STORE_ELIGIBLE`, has `usesNonExemptEncryption = false`, and is selected
  for version `1.0`.

Lint classification:

- Hospital Lite blocking: none found.
- iOS/TestFlight blocking: internal-only export of build `3` was resolved by
  the minimal App Store-eligible build `4` upload.
- Standard cloud app only: `NotificationBell.jsx`, `AuthContext.jsx`, `useFirebaseMessaging.js`.
- Safe cleanup backlog: `TriageConfirmation.jsx`, `TriageForm.jsx`, `TriageStatsWidget.jsx`.

## 4. Xcode Manual Steps

Xcode was opened successfully with:

```bash
npm --prefix frontend run ios:open
```

Ahmed should now:

1. Select the `App` target.
2. Open `Signing & Capabilities`.
3. Select the Apple Developer Team.
4. Confirm the Bundle Identifier matches the Apple Developer portal and App Store Connect app record.
5. Choose an iOS simulator or connected iPhone.
6. Press `Run`.
7. In the app, run the same checks:
   - SOB / low SpO2 preset shows ESI, NEWS2, red flags, and Safety floor applied.
   - Fever in child preset shows the pediatric NEWS2 caveat.
   - Clinician confirmation remains required.
   - No real patient data is entered.

## 5. Apple Developer Program Requirement

Physical-device signing, TestFlight upload, and App Store Connect submission require
an active Apple Developer Program membership and a signing team selected in Xcode.
This is the current hard manual blocker.

## 6. Bundle ID Decision

Current iOS Bundle Identifier:

```text
app.safetriage.hospitallite
```

This is professional and suitable for a Lite hospital demo, but Ahmed must create
or select the exact matching Bundle ID in the Apple Developer portal before
archiving. Avoid changing the Bundle ID after the App Store Connect app record is
created unless there is a clear reason.

## 7. App Store Connect App Record Steps

1. Create a new iOS app record in App Store Connect.
2. Use the final app name: `SAFE-Triage` or `SAFE-Triage Lite`.
3. Select the Bundle ID matching Xcode.
4. Add SKU, primary language, category, and availability.
5. Add hosted privacy policy URL.
6. Complete age rating.
7. Complete privacy nutrition labels.
8. Add screenshots for required device classes.
9. Upload build from Xcode Organizer.
10. Add internal TestFlight testers.
11. Do not submit for App Review until all manual review text and screenshots are final.

## 8. Privacy Policy URL Requirement

Apple requires a publicly reachable privacy policy URL. The app-specific policy at
`docs/release/privacy-policy.md` matches current Hospital Lite behavior and is
published through the public repository release branch for App Store Connect use.

## 9. Privacy Nutrition Label Answers

Based on the Hospital Lite build:

- Data collected by developer: none for the standalone Hospital Lite demo.
- Tracking: no.
- Third-party advertising: no.
- Analytics SDKs: no.
- Push notifications: no.
- Firebase runtime/messaging in Hospital Lite iOS bundle: no.
- Camera, microphone, location, contacts, Bluetooth permissions: none found.
- Local-only storage: clinician display name/role, synthetic queue entries, audit trail, and local patient counter in `localStorage`.
- Health data: synthetic demo vitals may be entered locally; real patient data is explicitly prohibited.
- Data linked to user: no server-side linkage in Hospital Lite.

Use conservative wording in App Store Connect. If Apple requires a data category
for locally entered demo health values, disclose it as not collected by the
developer and not used for tracking.

## 10. Screenshot Checklist

Screenshot assets have been prepared from the local Hospital Lite web build for
draft App Store Connect metadata. Before final submission, Ahmed can replace
them with screenshots from the signed iOS build if Apple Review asks for device
chrome or if any iOS-only layout issue appears.

- `docs/release/app-store-screenshots/iphone-6.9/`
- `docs/release/app-store-screenshots/ipad-13/`

The screenshots cover:

- Clinician gate / no-real-PHI banner.
- Empty patient form with demo presets visible.
- SOB / low SpO2 result with Safety floor applied.
- Fever in child result with pediatric NEWS2 caveat.
- Clinician confirmation controls.
- Optional Arabic UI screenshot if positioning the demo as bilingual.

Use only synthetic cases. Do not show names, identifiers, phone numbers, MRNs, or
real patient information.

## 11. Version And Build Number Recommendation

Current Xcode project values:

- `MARKETING_VERSION = 1.0`
- `CURRENT_PROJECT_VERSION = 4`

Current first TestFlight choice:

- Keep Marketing Version `1.0`.
- Use build `4` for the current App Store-eligible Hospital Lite binary.
- Increment `CURRENT_PROJECT_VERSION` for every future upload.

Make the version number consistent across Xcode, App Store Connect, and release docs.

## 12. TestFlight Internal Testing Steps

Build `1.0 (4)` is already uploaded, export compliance is recorded, and Ahmed
is assigned to the internal TestFlight group. Complete the remaining test
steps:

1. Install build `1.0 (4)` through TestFlight on a real iPhone and a real
   iPad.
2. Repeat the SOB / low SpO2 and Fever in child checks.
3. Record any iOS-only layout, safe-area, or storage issues before external
   testing.

## 13. App Review Caution Wording

Use cautious wording:

- "Clinical decision-support prototype"
- "Synthetic Hospital Lite demo"
- "Deterministic triage rules with clinician confirmation"
- "Not for real patient care without institutional validation and governance"
- "AI Extracts -> Rules Decide -> Humans Confirm"

Avoid claiming production clinical validation, diagnosis, autonomous triage, or medical
device approval.

## 14. What Ahmed Must Not Claim

- Not validated for clinical use.
- Not an approved medical device.
- Not a diagnosis system.
- Not a replacement for a clinician.
- Not cleared for real patient data.
- Not autonomous emergency triage.
- Not an App Store/App Review approved medical product until Apple review is complete.

## 15. Final Ready / Blocked Verdict

- Web local demo: ready.
- Hospital Lite production bundle: ready.
- Capacitor iOS sync: ready.
- Xcode open: ready.
- iOS 26.5 local Xcode platform/runtime: installed on this machine with `xcodebuild -downloadPlatform iOS -buildVersion 26.5 -architectureVariant arm64`.
- Unsigned native iOS Release compile: passed with `CODE_SIGNING_ALLOWED=NO`.
- Signed archive: ready and completed for build `1.0 (4)` using the installed
  Apple Distribution certificate and App Store profile for
  `app.safetriage.hospitallite`.
- iOS simulator run: ready for manual Xcode run after selecting a compatible simulator.
- Physical iPhone/iPad run: pending Ahmed's internal TestFlight install and
  synthetic-preset smoke test.
- TestFlight: build `1.0 (4)` is in the internal tester group; real-device
  smoke testing remains.
- App Store Review: blocked only by App Privacy web confirmation, review
  contact/reviewer-note confirmation, real-device smoke testing, and explicit
  human submission approval.

Launch should stop at App Store Connect manual action. Do not deploy cloud
resources and do not submit to App Review without explicit human approval.

## 16. App Store Connect API Follow-Up

Ahmed provided the App Store Connect identifiers for the SAFE-Triage key:

```text
ASC_KEY_ID=C26JYVJZ24
ASC_ISSUER_ID=14ce111d-36f7-4419-abda-22672f874c7b
ASC_KEY_NAME=safe-triage
ASC_ACCOUNT_NAME=Ahmed Zayed
ASC_KEY_PATH=$HOME/.appstoreconnect/private_keys/AuthKey_C26JYVJZ24.p8
APPLE_DEVELOPMENT_TEAM=7R65LRGNHT
```

These values are saved locally in `.env.apple-connect.local`. The file is
ignored by Git through `.env.*.local`, and the private key itself was moved out
of the repository root to:

```text
~/.appstoreconnect/private_keys/AuthKey_C26JYVJZ24.p8
```

The key file is intentionally not committed. `.gitignore` also blocks
`AuthKey_*.p8` and `*.p8` files so future App Store Connect private keys cannot
be staged accidentally.

Nonmatching key files are also present locally and were not used:

```text
~/.appstoreconnect/private_keys/AuthKey_9YS687W675.p8
~/.appstoreconnect/private_keys/AuthKey_2KBJBJA8GV.p8
~/private_keys/AuthKey_2KBJBJA8GV.p8
```

The current keychain now has both development and distribution identities:

```text
Apple Development: ahmedadel7887@gmail.com (7R65LRGNHT)
Apple Distribution: Ahmed Zayed (6F22G47URV)
```

The App Store archive used the installed distribution identity and the App Store
profile named `SAFE-Triage Lite App Store`, because that profile owns the final
Bundle ID and App Store Connect app record.

The signed archive attempt without provisioning updates reached this blocker:

```text
No profiles for 'app.safetriage.hospitallite' were found.
Automatic signing is disabled and unable to generate a profile.
To enable automatic signing, pass -allowProvisioningUpdates to xcodebuild.
```

Read-only App Store Connect API checks confirmed the key is valid and that the
app record exists:

```text
apps?filter[bundleId]=app.safetriage.hospitallite -> SAFE-Triage Lite, app id 6771520904
build 1 -> VALID
build 2 -> VALID
build 3 -> VALID, INTERNAL_ONLY
build 4 -> VALID, APP_STORE_ELIGIBLE, selected for version 1.0
```

To check status from the command line, load the local API environment:

```bash
source .env.apple-connect.local
```

Future archives should keep the Bundle ID fixed and increment the build number:

```bash
xcodebuild \
  -project frontend/ios/App/App.xcodeproj \
  -scheme App \
  -configuration Release \
  -sdk iphoneos26.5 \
  -destination generic/platform=iOS \
  -archivePath frontend/ios/build/SAFE-Triage-Lite-build4-appstore.xcarchive \
  archive \
  DEVELOPMENT_TEAM=6F22G47URV \
  CODE_SIGN_STYLE=Manual \
  PROVISIONING_PROFILE_SPECIFIER='SAFE-Triage Lite App Store' \
  CODE_SIGN_IDENTITY='Apple Distribution' \
  CURRENT_PROJECT_VERSION=4 \
  MARKETING_VERSION=1.0
```

Then upload with:

```bash
xcodebuild \
  -exportArchive \
  -archivePath frontend/ios/build/SAFE-Triage-Lite-build4-appstore.xcarchive \
  -exportPath frontend/ios/build/export-build4-appstore \
  -exportOptionsPlist frontend/ios/ExportOptions.appstore-upload.plist \
  -authenticationKeyPath "$ASC_KEY_PATH" \
  -authenticationKeyID "$ASC_KEY_ID" \
  -authenticationKeyIssuerID "$ASC_ISSUER_ID"
```

Do not submit the build for App Review until Ahmed manually completes App
Privacy, runs real-device smoke testing, confirms the review contact and notes,
and explicitly decides to submit.
