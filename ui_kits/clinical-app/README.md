# Clinical app UI kit

Recreation of the in-product clinician dashboard from `frontend/src/pages/Dashboard.jsx`.
The other surface to the SAFE-Triage product — slate, teal, ESI gradients, fully bilingual.

## Run it

`index.html` loads sibling `.jsx` files with `<script type="text/babel" src="…">`,
which most browsers block on `file://`. Serve over HTTP:

```bash
# from the repo root
python3 -m http.server 8080 --directory ui_kits
# then open http://localhost:8080/clinical-app/
```

Click "Override" in the triage result panel to jump back to the sign-in screen
and see that surface. Click "Sign in with Google" to return to the dashboard —
the SignIn flow is a state-flag toggle, not real auth.

## Components

| File | What it is |
|---|---|
| `SignIn.jsx` | Animated `-45deg` gradient (slate / teal / indigo / slate) + 3 blurred orbs + glass card. The most "designed" surface in the app. |
| `AppHeader.jsx` | Sticky 64px header. Logo + bilingual tabs + bell + user avatar with role line. |
| `SectionCard.jsx` | The canonical clinical-form container — white, 12px radius, **left accent border** (4px) in one of {teal, blue, amber, rose, purple, emerald}, header strip with bilingual title. |
| `QueuePanel.jsx` | Active-case rail. ESI-color gradient badge, bilingual complaint, pulse animation on ESI 1 critical rows. |
| `TriageForm.jsx` | Patient meta (`Field`, `Segmented`, comorbidity chips), bilingual chief-complaint textarea, vitals grid with NEWS2 auto-score and out-of-range flagging. |
| `TriageResult.jsx` | The ESI result hero — full-width gradient block, 96px level number, bilingual ESI name, confidence meter, audit chips, confirm/override action bar, GAHAR strip footer. |
| `WorkupCard.jsx` | Recommended workup list with STAT/timed badges, AI differential diagnoses with ICD-10 + SNOMED-CT chips and confidence bars, "Ask Patient" bilingual prompts. |

## Visual rules followed

- **Type**: Inter for English UI, Cairo for Arabic, IBM Plex Mono for codes (ICD-10, SNOMED-CT, vital-sign values).
- **ESI gradients** are load-bearing. Used in the QueuePanel ESI badges and the TriageResult hero. Never substituted.
- **Bilingual everywhere**: every label, button, status uses ` | ` separator + Cairo Arabic.
- **Status emoji** restricted to leading anchor: 🚨 ⚠️ ✅ 🔴 🏥 📋 🧪 🛡.
- **GAHAR** strip always present at the bottom of clinical results.
- **Left-accent border** allowed *only* on `SectionCard` — the one place left-accent borders are sanctioned in the system.

## What's intentionally not here

- The MedGemma analytics dashboard (`pages/MedGemmaDashboard.jsx`) — too deep for this kit.
- The `EducationalChat` in-form companion — separate component, not part of the core flow.
- Real Google OAuth — `SignIn` calls `onSignIn()` to flip a state flag.
- Real backend calls. Confirm/override mutate local React state only.

## Repo-local adaptations vs. the upstream design

- `index.html` references `../colors_and_type.css` (one level up, in `ui_kits/`)
  rather than `../../colors_and_type.css` from the original design archive — the
  CSS is shared across kits in this repo at `ui_kits/colors_and_type.css`.
- The 3-column dashboard grid uses a CSS class with `@media` breakpoints so it
  collapses cleanly on tablet (≤1180px) and mobile (≤760px) viewports.
- Reduced-motion preference disables the SignIn gradient + orb animations.
- The decorative SignIn orbs are `pointer-events: none` so they cannot trap clicks.
