# SAFE-Triage — 3-Minute Video Pitch Script (v2)

**Speaker:** Dr. Ahmed Zayed, MBBCh — Lead Developer & System Architect
**Format:** 3-minute video submission — MedGemma Impact Challenge
**Tone:** Clinical authority + technical showcase
**Approx. word count:** ~480 words (~3 min at natural pace)

---

## [0:00–0:25] THE PROBLEM — Open with clinical stakes

Thank you to the MedGemma Impact Challenge committee for shortlisting our project.

In Egyptian emergency departments, there is no standardized triage. A patient having a silent MI can sit in a waiting room for hours — triaged by a nurse who has never been trained on ESI, in a department seeing 300 patients a day, with no early warning score, no structured protocol, and no safety net.

Published data tells us what that costs. In one Egyptian ED study, implementing structured triage cut mortality by 32% and reduced length of stay from 184 minutes to 51. The gap between no triage and structured triage is, quite literally, the gap between life and death.

## [0:25–0:55] THE SOLUTION — Architecture in one sentence, then expand

SAFE-Triage is a research-stage hybrid AI decision-support system built on Google Cloud, designed for this exact problem. Our architecture follows one rule: **AI extracts. Rules decide. Humans confirm.**

Here is how it works. The patient speaks — in colloquial Egyptian Arabic or English. Gemini 2.5-flash on Vertex AI processes the complaint, extracting symptoms and mapping them to over 6,370 SNOMED-CT concepts using a custom database of 1,858 Egyptian Arabic medical keywords. This is not Modern Standard Arabic — this is the language patients actually speak.

But the AI never decides how sick the patient is. That decision is made by deterministic clinical protocols — ESI version 5 and NEWS2 — hard-coded from the official handbooks. A patient with a NEWS2 of 7 gets escalated. A patient describing sudden-onset weakness triggers a stroke pathway. These are rules, not predictions. The AI cannot override them.

Every case is then confirmed by a clinician through real-time physician alerts with FCM push notifications and a web dashboard on Firebase Hosting.

## [0:55–1:30] GOOGLE CLOUD ARCHITECTURE — The full stack

The entire system runs natively on Google Cloud. The backend is a FastAPI application deployed on Cloud Run in us-central1. The frontend is hosted on Firebase. Every triage decision — 19 structured columns per case — is logged to BigQuery for audit, quality assurance, and GAHAR Egyptian hospital accreditation compliance.

MedGemma was evaluated as a development-stage clinical quality assurance layer. In offline testing, it reviewed completed triage decisions and flagged high-risk atypical presentations for human attention. It does not set final acuity and is not the current final triage authority.

## [1:30–2:10] VALIDATION — Hard numbers

We validated SAFE-Triage against the MIETIC benchmark — the expert-validated triage instruction corpus built on MIMIC-IV-ED. On 36 expert-reviewed cases: 35/36 exact ESI agreement (97.2%; 95% Wilson CI 85.8%-99.5%), 36/36 within one level (100.0%; 95% Wilson CI 90.4%-100.0%), and — critically — 0/36 critical under-triage (95% Wilson CI 0.0%-9.6%). No ESI 1 or 2 patient was assigned ESI 3, 4, or 5. The system was further stress-tested against Egyptian Arabic mirror cases to confirm translated-case parity; Arabic-native ED validation remains future work.

Over-triage was 2.8% (1/36). That is deliberate. In emergency medicine, over-triage is the safe direction. We would rather bring a patient in too fast than too slow.

## [2:10–2:40] RESILIENCE AND CONSTRAINTS — Built for the real world

This system was designed for Egyptian infrastructure. When internet connectivity fails — and it does — SAFE-Triage activates an offline fallback engine running on 1,858 locally stored Arabic medical keywords. No internet does not mean no triage.

All patient data is stored and processed within Google Cloud with HIPAA-compliant infrastructure. The system aligns with GAHAR accreditation standards and produces a complete audit trail for every patient encounter.

## [2:40–3:00] CLOSE — Team and call to action

SAFE-Triage was built by the Avengers — a multidisciplinary team from the American University in Cairo, spanning medicine, pharmacy, dentistry, gynecology, and public health. The public research demonstration is live at safe-triage-ai.web.app on Google Cloud Run.

We built SAFE-Triage because Egyptian patients deserve the same triage safety net that exists in Boston or London. MedGemma and Google Cloud made that possible.

Thank you.

---

## Production Notes

- **Total duration:** ~3:00
- **Live demo insert point:** Consider a 15–20 second screen recording overlay at [1:30] showing a real Arabic complaint being triaged, with ESI result and BigQuery log entry
- **Slide/B-roll cues:** Architecture diagram at [0:25], Google Cloud logo stack at [0:55], MIETIC results table at [1:30], live dashboard at [2:40]
