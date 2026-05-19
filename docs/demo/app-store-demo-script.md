# SAFE-Triage Lite — Demo Script

**Audience:** App Review reviewers, hospital leadership, hackathon judges, thesis defense panel.
**Tone:** Professional. Cautious. Honest about prototype status.
**Last updated:** 2026-05-20

> **Decision support only — clinician must confirm.**

This script gives you exact words and exact taps for two demo lengths and one Apple App Review walkthrough. Use the synthetic presets — never use real patient data, even in private rehearsal.

---

## 0. Pre-flight (before any audience sees the screen)

- Phone or iPad fully charged.
- Build version + build number noted from Xcode (record in the demo log).
- Language set to English (you can toggle to Arabic during the demo).
- App opened to the sign-in screen. **Local storage cleared** (uninstall + reinstall, or *Settings → SAFE-Triage Lite → Storage → Delete*).
- Wifi and cellular **off** for the offline-mode portion of the demo. Re-enable only if asked to demonstrate connected mode.

---

## 1. The three-minute reviewer walkthrough (App Review / hackathon judge)

### Opening sentence (10 seconds)

> "SAFE-Triage Lite is a Phase-1 educational decision-support prototype. The AI extracts the chief complaint, deterministic clinical rules decide the triage level, and a human clinician confirms every case. The app is bilingual English-Arabic. Everything runs offline. There is no real patient data here."

### Step 1 — Sign in (20 seconds)

- Tap the **Clinician name** field, type *Demo Reviewer*, tap **Continue**.
- *Pause.* Point at the amber strip under the header.
- Say:
  > "Notice the synthetic-demo banner. The app refuses to ever look like a production hospital system."

### Step 2 — Load a preset (30 seconds)

- Scroll to the top of the form. Tap **Chest pain · ?MI**.
- The form fills.
- Say:
  > "This is a synthetic case — a 58-year-old male, crushing central chest pain, vitals on the threshold. I didn't type any of this. It's a fixture. Real patient information must never be entered."

### Step 3 — Run the engine (30 seconds)

- Tap **Suggest triage**.
- ESI 2 card appears (or ESI 1 depending on the safety floor).
- Point at the **Safety floor applied** red strip if present.
- Point at the **Decision support only** amber strip.
- Point at the **Engine source** chip.
- Say:
  > "The deterministic engine just produced ESI two. A safety floor has been applied for the cardiac chest pain pattern. The engine source — bottom-right — tells me whether this came from the Python canonical engine or the in-browser offline fallback. Right now, this device is offline, so we are on the in-browser engine. The clinician must now confirm."

### Step 4 — Confirm / override (40 seconds)

- Tap **Confirm this level** for two seconds.
- *Do not* press it yet.
- Tap **Override** instead.
- Show the 1–5 buttons and the required-reason field.
- Say:
  > "If a clinician disagrees with the engine, they can override — but only with a written reason. The engine never silently changes acuity. Downgrades are auditable."
- Tap **Cancel**, then tap **Confirm this level**.

### Step 5 — Handoff (20 seconds)

- Show the handoff record with the audit trail.
- Say:
  > "Every step is in the audit trail — engine suggestion, who confirmed, when. The handoff can be printed or exported as JSON for a paper-based ED."

### Step 6 — Arabic (15 seconds)

- Tap the **AR** chip in the top-right.
- Show the form flipping to RTL.
- Say:
  > "The app is bilingual. Arabic and English. The same deterministic engine produces the same result regardless of interface language."

### Step 7 — Close (15 seconds)

- Say:
  > "Three things to keep in mind: this is a prototype, not a medical device; no real patient data should be entered; and the deterministic rules — not the AI — are the source of truth."

**Total: ~3 minutes 0 seconds. Stop here.**

---

## 2. The five-minute hospital-leadership walkthrough

Same first six steps as above, then:

### Step 7 — Offline robustness (45 seconds)

- *(Already offline.)*
- Tap **New case**.
- Tap **SOB · low SpO₂** preset.
- Tap **Suggest triage**.
- Show the result.
- Say:
  > "Notice this is still working with no network. Egyptian EDs have unreliable connectivity. A triage station cannot drop to 'ask the doctor' just because the WiFi blinked. The deterministic engine runs on the device. When the connected backend is reachable, the app uses the canonical Python engine — validated against MIETIC, KTAS, and NHAMCS — and shows that explicitly in the engine-source chip."

### Step 8 — A pediatric case (30 seconds)

- Tap **New case**.
- Tap **Fever in child** preset.
- Tap **Suggest triage**.
- Point at the **Pediatric NEWS2 caveat** chip.
- Say:
  > "NEWS2 is validated for adults. The app says so when it suggests a triage for a child. The engine uses age-banded vital thresholds for paediatric safety, but the displayed NEWS2 number is for adult clinicians to read in context. We will not pretend a paediatric early-warning score exists when there isn't an internationally agreed one."

### Step 9 — Low-acuity case (30 seconds)

- Tap **New case**.
- Tap **Minor wound · low risk** preset.
- Tap **Suggest triage**.
- Show ESI 4 / 5 with no safety floor and no red flags.
- Say:
  > "The engine doesn't over-triage. A clean low-acuity case lands at ESI 4 with no false alarm. Over-triage costs a hospital money; under-triage costs a patient. The deterministic engine is asymmetric on purpose — it will over-triage before it under-triages."

### Step 10 — Q&A and stop (rest of the time)

Be ready for these questions:

1. *"Is this validated?"* — The deterministic engine is benchmarked against MIETIC, MIETIC-Arabic, KTAS, NHAMCS. The Hospital Lite build is a prototype demonstrating the workflow; clinical pilot validation is a separate step that requires institutional sign-off.
2. *"Where does the patient data go?"* — In Hospital Lite mode, nowhere. The local storage on the device is the only persistence. No cloud, no Firebase, no analytics.
3. *"Can a clinician downgrade the AI's suggestion?"* — Yes, with a required written reason, captured in the audit trail.
4. *"Does the AI ever override the rules?"* — No. Rules decide. AI extracts only. Humans confirm.
5. *"What stops a junior clinician from accepting every suggestion?"* — Nothing technical, today. That is a governance question for the deploying hospital. The audit trail at least makes accept-everything behaviour visible to a supervisor.

---

## 3. App Review (Apple) walkthrough

Apple's reviewer has a copy of the script in `docs/release/app-store-metadata-draft.md` §"App Review — Notes for Reviewer". Highlights to emphasise on a screen recording:

- The amber synthetic-demo / no-real-PHI strip is **always visible**.
- The Engine source chip is **always visible**.
- The "Decision support only" amber pill is **always visible** on the review card.
- Every preset is **labelled as a synthetic sample case**.
- The "Override" path **requires a free-text reason** — the *Save* button is disabled until the reason is typed.
- The app **asks for no permissions**.

If the reviewer pushes on clinical claims, the answer is:

> "The app is a synthetic-demo / educational prototype. It does not diagnose, it does not treat, and it does not transmit data to any cloud service or developer server. The clinical wording inside the app is intentionally cautious. The supporting paper is in submission to AIiH 2026 and EuSEM 2026; this app is a teaching tool, not the regulatory submission."

---

## 4. What never to say in any demo

- "AI doctor."
- "Triages patients automatically."
- "Replaces the triage nurse."
- "Validated for clinical use."
- "Approved medical device."
- "FDA-cleared" / "CE-marked" / "GAHAR-certified" — none of these are true.
- "Diagnoses chest pain" — the app classifies the chief complaint, it doesn't diagnose.
- "Real patients" — never reference real patients in a public demo.
- Naming any actual hospital that hasn't agreed to be named.

If you slip and a stakeholder pushes back, say:

> "Let me correct that. The app is a decision-support prototype. The deterministic rules suggest a triage level. The clinician confirms or overrides every case. It is not a medical device."

---

## 5. Stop condition

End the demo as soon as you've completed the script for the audience. Do not improvise new clinical claims. Do not show new presets that haven't been rehearsed. Do not show the connected-mode Python engine unless you have already booted it on the same machine before the demo started.

If the audience asks for a hands-on session, hand the device over and let them tap **New case** and try a preset themselves. Stay nearby in case they have questions.
