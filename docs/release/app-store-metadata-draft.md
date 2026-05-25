# SAFE-Triage Lite — App Store Metadata Draft

**Status:** Draft. Not submitted. Wording deliberately cautious for App Review.
**Last updated:** 2026-05-20

> Apple App Review for medical-adjacent apps is strict. Every line below has been written to avoid: (a) unsupported clinical claims, (b) implication of regulatory approval, (c) any suggestion that this app replaces clinical judgement. **Do not edit these strings to sound more confident before review** — they are tuned to pass §1.4.1 and §5.1 of the App Review Guidelines.

---

## App name (max 30 characters)

```
SAFE-Triage Lite
```

(16 characters — well within limit.)

## Subtitle (max 30 characters)

Two cautious options. Pick one before submitting:

```
Clinical triage demo
```

```
Triage decision support
```

(`Clinical triage demo` is safer; `Triage decision support` matches the in-app copy. Both fit.)

## Promotional Text (max 170 characters)

```
A bilingual (English / Arabic) educational demo of an emergency-triage decision-support prototype. Decision support only — clinicians must confirm every case.
```

## Short Description / Keywords field (max 100 characters of comma-separated)

```
triage,demo,clinical,decision support,ESI,NEWS2,Arabic,emergency,education,physician,prototype
```

(89 characters.)

## Full description (max 4000 characters; current draft is ~1,400 chars)

```
SAFE-Triage Lite is an educational, synthetic-demo prototype of an emergency-department triage
decision-support workflow. It is bilingual (English / Arabic) and runs fully offline on iPhone
and iPad, with no patient data sent to any server.

This app is intended for clinicians, healthcare students, hackathon judges, thesis reviewers,
and hospital leadership who want to inspect how an AI-assisted, rules-first triage workflow
behaves. It is not a medical device. It does not diagnose, treat, or replace clinical
judgement. Every suggested triage level must be confirmed by a qualified clinician before any
clinical action is taken.

How the prototype works:
- The clinician (any signed-in user, local only) enters a synthetic chief complaint and a set
  of vital signs.
- A deterministic engine — based on the Emergency Severity Index (ESI v5) and the National
  Early Warning Score 2 (NEWS2, validated for adults) — suggests a triage level from 1 (most
  acute) to 5 (least acute).
- The clinician must confirm the suggestion or override it with a written reason.
- Safety floors prevent silent under-triage of high-risk presentations.

Five synthetic demo cases are included so reviewers can see the full flow without typing
clinical text:
- Chest pain with sweating (possible MI)
- Shortness of breath with low oxygen saturation
- Fever in a child
- Minor wound, low-risk
- Confused elderly patient

This app does not:
- Diagnose disease.
- Replace a triage nurse, doctor, or any clinician.
- Constitute a regulated medical device.
- Process or transmit real protected health information (PHI).
- Use camera, microphone, location, or any push notifications.

For real patient care, follow your hospital's accredited triage protocol and local clinical
governance.
```

## Keywords field (max 100 characters, comma-separated, no spaces around commas)

Apple's "Keywords" field is separate from description text and *very* size-constrained. Use:

```
triage,ESI,NEWS2,decision,support,clinical,Arabic,emergency,demo,education,physician
```

(85 characters.)

## What's New in This Version (release notes)

Build #1 (TestFlight internal only):

```
First TestFlight build of SAFE-Triage Lite — a bilingual (English / Arabic) educational demo
of an emergency-triage decision-support workflow. Includes five synthetic demo cases, an
offline deterministic ESI v5 / NEWS2 engine, and a clinician-confirmation step on every
suggested triage level. No real patient data is collected or transmitted.
```

## Marketing URL (optional)

Placeholder until a landing page is hosted:

```
https://zayedmd.com/safe-triage
```

(The site must exist before App Store submission if this URL is used. TestFlight
does not require a marketing URL.)

## Support URL (required for App Store, optional for TestFlight)

```
https://github.com/DrAhmed7887/safe-triage-project-github/issues
```

(Public issue tracker is acceptable. For App Store, an email-based support page is usually
expected; a hosted page on zayedmd.com is better.)

## Privacy Policy URL (required for App Store submission)

Published app-specific policy URL:

```
https://github.com/DrAhmed7887/safe-triage-project/blob/codex/safe-triage-lite-release-candidate/docs/release/privacy-policy.md
```

## App Review Information — Notes for Reviewer

This is the most important free-text field for a medical-adjacent app.

```
Hello App Review,

SAFE-Triage Lite is a synthetic-demo educational prototype for emergency-triage decision
support. It is not a medical device, does not diagnose patients, and does not handle real
protected health information (PHI). The Hospital Lite build runs locally on the device; no
cloud network requests are required and none of the included flows transmit data to the
developer. If a developer runs the optional localhost backend during a local demo, that
backend is a loopback development endpoint, not a cloud service.

How to test the full flow without entering any clinical text:

1. On the sign-in screen, type any name (e.g. "App Review") and tap Continue.
   - This is a local-only sign-in. There is no account system and no remote authentication.
2. On the new-case screen, tap any of the five "Demo presets" buttons across the top.
   This pre-fills the form with synthetic patient data.
3. Tap "Suggest triage" at the bottom.
4. The next screen shows the suggested ESI level (1-5) and a NEWS2 score from the
   deterministic engine. A clearly visible "Decision support only — clinician must confirm"
   notice appears, and if a clinical safety floor was triggered, a red "Safety floor applied"
   strip is shown.
5. Tap "Confirm this level" to record the suggestion, or "Override" to enter a new level
   plus a free-text reason.
6. The handoff screen confirms the recorded case and offers a print/export option.

Optional: tap "AR" in the top-right to switch the entire interface to Arabic (right-to-left).

The app deliberately:
- Asks for NO permissions (no camera, microphone, location, contacts, notifications).
- Performs NO tracking, analytics, advertising, or third-party SDK calls.
- Stores any test data in the device's local storage only. The user can clear it by
  uninstalling the app or clearing the app's local website data.

If you require credentials for any reason, no credentials exist. The app has no accounts.

Thank you.
```

## App Review — demo account

```
Account not required. The app has no account system. Sign in is a local-only name field.
```

## App Review — contact

(Manual — Ahmed's email.)

## App Privacy — nutrition-label draft

Apple's data-collection questionnaire. Answers below for the **synthetic-demo / Hospital
Lite** build only.

| Category | Collected? | If yes, used for |
|---|---|---|
| Contact info (name, email, phone, address) | **No** | — |
| Health & Fitness | **No** (synthetic only) | — |
| Financial info | **No** | — |
| Location | **No** | — |
| Sensitive info (race, sexual orientation, etc.) | **No** | — |
| Contacts | **No** | — |
| User content (photos, videos, audio) | **No** | — |
| Browsing history | **No** | — |
| Search history | **No** | — |
| Identifiers (User ID, Device ID) | **No** | — |
| Purchases | **No** | — |
| Usage data | **No** | — |
| Diagnostics | **No** | — |
| Other data | **No** | — |

Special note for App Review: anything a clinician types into the form is stored *only* in the
device's local storage. It is not collected by the developer, transmitted, or linked to any
identifier outside the device. The in-app banner explicitly tells users not to enter real
patient data.

## TestFlight — "What to Test" notes

```
This build is a synthetic-demo emergency-triage decision-support prototype.

Please test:
1. The five demo presets (top of the form on the new-case screen).
2. Both English and Arabic interface modes — switch using the "AR" / "EN" toggle in the
   header.
3. Confirm and Override flows — Override requires a written reason.
4. Printable handoff record at the end of a case.
5. iPhone and iPad layouts.

Please do NOT enter any real patient names, identifiers, or other protected health
information. The app is for synthetic demonstration only.

Known limitations:
- The triage engine is intended for adults; paediatric cases show a NEWS2 caveat banner.
- This is a Phase-1 prototype and is not validated for live clinical use.

Feedback: please send screenshots + steps-to-reproduce to the contact email.
```

## Category

- **Primary category:** Medical
- **Secondary category:** Education

(`Medical` triggers App Review scrutiny but is the honest categorisation. `Education` is the
secondary because of the demo / training framing.)

## Age rating

- **Apple computed:** 17+ (occasional Medical/Treatment Information).
- See `docs/release/app-store-testflight-checklist.md` §7 for the answers to give Apple's
  age-rating questionnaire.

## Pricing

- **Free**, no in-app purchases.

## Availability

- Recommend launching in **Egypt** and **United States** for build #1.
- Add Germany / Spain / UK later when bilingual EN/AR demo content is reviewed by Arabic
  speakers in those markets.
