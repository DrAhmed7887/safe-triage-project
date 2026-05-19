# SAFE-Triage Lite — Privacy Policy (Draft)

**Effective date placeholder:** 2026-05-19
**Last updated:** 2026-05-19
**Owner:** Dr. Ahmed Zayed, MBBCh (zayedmd)

> Draft. Not yet hosted. Apple App Store requires this policy be reachable at a public URL **before** the app can be submitted for review. Recommended host: `https://zayedmd.com/safe-triage/privacy`. The wording here matches the SAFE-Triage Lite Hospital Lite build *as it ships today* — do not relax this language without re-inspecting the code.
>
> **Where this policy says "we", it means Dr. Ahmed Zayed as developer.**
> **Where it says "the app", it means the SAFE-Triage Lite iOS application distributed via TestFlight and (later) the App Store.**

This policy reflects the app's behaviour as verified in source code. Specifically, the
Hospital Lite build (the only build distributed via TestFlight / the App Store) bypasses
Firebase Authentication at runtime, ships no Firebase Cloud Messaging worker, and uses no
camera, microphone, location, contacts, advertising-identifier, or tracking APIs.

---

## 1. What the app is

SAFE-Triage Lite is a synthetic-demo educational prototype that illustrates a deterministic
emergency-triage decision-support workflow. The app is **not** a medical device, does not
provide a diagnosis, does not handle real patient information, and does not replace
clinical judgement. Every triage suggestion in the app must be confirmed by a qualified
clinician before any clinical action is taken.

## 2. What data the app collects from you

**The app does not collect, transmit, or share personal information.**

The Hospital Lite build of SAFE-Triage Lite asks for no permissions: no microphone, no
camera, no location, no contacts, no Bluetooth, no notifications, no advertising identifier,
no tracking permission.

Any text or numbers you type into the form (synthetic chief complaint, age, vital signs,
clinician name) are stored **only on your device**, using the local storage of the in-app
web view. This data:

- Never leaves your device under normal operation of the Hospital Lite build.
- Is not associated with an account or identifier outside your device.
- Is not used by us for analytics, profiling, or any other purpose.
- Is not sold, shared, or licensed to any third party.

We explicitly ask users, inside the app, **not** to enter real patient names or other
protected health information.

## 3. Local data: what is stored, where, and how to delete it

The app uses your device's WKWebView local storage to remember:

- The name you typed into the local "Clinician name" field on the sign-in screen.
- The synthetic patient cases you have triaged in the current session, plus the
  deterministic engine's suggestion and any clinician confirmation or override.
- Your interface language preference (English or Arabic).
- An internal patient counter so each demo case gets a unique local ID.

To delete this data:

- iOS: *Settings → SAFE-Triage Lite → Storage → Delete*, or uninstall the app.
- In the web version (if you use it): open your browser's storage panel and clear
  "site data" for the app's origin.

Reinstalling the app does not restore the data.

## 4. Network access

The Hospital Lite build does not require network access to function. The deterministic
ESI v5 / NEWS2 engine runs entirely on your device. The app does not attempt to call any
cloud service for triage decisions in this build.

If a future "connected" build is distributed, the network behaviour for that build will be
documented in this same policy and announced in the App Store "What's New" notes.

## 5. Cookies, analytics, tracking

**None.** The app does not use cookies, in-app analytics SDKs, advertising SDKs, or any
form of tracking. It does not integrate with Google Analytics, Firebase Analytics, Crashlytics,
Sentry, Mixpanel, Amplitude, or comparable tools.

## 6. Third-party SDKs

The app includes only the third-party code needed to render the user interface and to act as
a thin native wrapper around a web view:

- React, React Router, lucide-react, framer-motion, Tailwind CSS — UI rendering.
- Capacitor (`@capacitor/core`, `@capacitor/ios`, `@capacitor/app`,
  `@capacitor/status-bar`) — native shell.

None of these libraries phone home from the Hospital Lite build.

## 7. Children

This app is rated 17+ on the App Store because medical/clinical content is intrinsically
adult-directed. It is not designed for children and we do not knowingly collect any data
from anyone of any age (see §2).

## 8. Security

We rely on the device's own protections (App Sandbox, Data Protection class, lock-screen
authentication). Because the app intentionally does not collect or transmit data, there is no
server-side data to secure.

We recommend that users:

- Keep iOS up to date.
- Use a device passcode / Face ID / Touch ID.
- Treat any text typed into the demo form as if it were public — do not enter real PHI.

## 9. Your rights

Because the app does not collect, store on a server, or otherwise process your personal
information, GDPR / CCPA / PDPL "access" and "delete" rights are satisfied by deleting the
app's local storage on your device (see §3).

## 10. Disclosure to law enforcement

We hold no user data on any server we control. Local data on your device is yours, governed
by the device's own security model and any local law that applies to you.

## 11. Changes to this policy

If we change this policy in a way that materially affects users (for example, by introducing
analytics, by enabling cloud sync, or by collecting any new category of data), we will:

- Update the "Last updated" date above.
- Note the change in the App Store "What's New" text for the version that ships the change.
- For any change that introduces collection of personal data, request explicit consent
  inside the app before any new collection begins.

Prior versions of this policy will be retained in the project repository at
`docs/release/privacy-policy-draft.md` so users can see what changed.

## 12. Contact

For questions about this policy or the app:

- **Email:** [placeholder — Ahmed's support email]
- **GitHub issues:** https://github.com/DrAhmed7887/safe-triage-project-github/issues
- **Postal address:** [placeholder — required by some jurisdictions if Ahmed wants App Store distribution in those markets]

## 13. Legal review needed

This is a developer-drafted privacy policy that matches the app's current technical
behaviour. Before publishing, it should be reviewed by:

- A lawyer familiar with **App Store / TestFlight** requirements in the target markets
  (Egypt + US for build #1).
- A lawyer familiar with **medical-adjacent product** language, particularly any
  market where the user resides (Egypt's PDPL, EU GDPR if listed in EU, US state laws if
  listed in the US).
- Apple's **App Privacy nutrition label** wizard in App Store Connect — the answers in
  `docs/release/app-store-metadata-draft.md` §App Privacy must agree with this document.

Any contradiction between this policy and code behaviour is a defect — fix the code, not
this document. The policy is the contract.
