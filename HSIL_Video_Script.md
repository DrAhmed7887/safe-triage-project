# SAFE-Triage — Harvard HSIL Hackathon Video Script
**Duration:** 2 minutes (~320 words at natural pace)
**Speaker:** Dr. Ahmed Zayed — Lead Developer & System Architect

---

## [0:00–0:20] INTRODUCTION

Hello. My name is Dr. Ahmed Zayed — physician and Clinical AI Specialist at DoctorIQ. On behalf of our team, thank you for the opportunity to present at this hackathon.

We are the Avengers — a team of six clinicians from the American University in Cairo: two dentists, a public health specialist, a gynecologist, a pharmacist, and a physician. We come from different specialties — but we all share one thing: we have all been to an Egyptian emergency department, as doctors and as patients. And we have all seen what happens when triage fails.

---

## [0:20–0:40] THE PROBLEM

In Egypt, **32% of ED deaths are preventable** — directly attributable to triage failures. There is no standardized triage protocol in most Egyptian hospitals. Nurses work in overcrowded rooms, dealing with patients speaking colloquial Arabic, with no decision support — and **86% of ED staff report experiencing workplace violence** during triage encounters.

This is the problem we decided to solve.

---

## [0:40–1:10] THE SOLUTION

SAFE-Triage is a research-stage, hybrid AI triage decision-support system built specifically for this environment. The golden rule is simple: **AI extracts. Rules decide. Humans confirm.**

Our AI — powered by Gemini and MedGemma — understands native Egyptian Arabic dialect, with 1,858 colloquial medical keywords. But it never decides how sick someone is. That decision belongs entirely to deterministic clinical protocols: ESI v5 and NEWS2, encoded directly from international guidelines. A clinician confirms every single case. No exceptions.

And when the internet goes down — which happens regularly in Egyptian hospitals — the system switches to a fully offline mode. No internet does not mean no triage.

---

## [1:10–1:35] LIVE DEMO

Let me show you how simple it is. *(screen recording)*

You enter the patient's name, their chief complaint — in Arabic or English — and their vitals, just like a standard NEWS2 assessment. Within **17 seconds**, the system returns an ESI level, ICD-10 code, recommended resources, and action text — bilingual, in English and Arabic. The physician receives an instant push alert to confirm.

No training required. The interface was designed so any nurse can use it on day one.

---

## [1:35–1:50] VALIDATION

We validated against the **MIETIC expert-validated benchmark** — 36 expert-reviewed cases from MIMIC-IV-ED. The system achieved **35/36 exact ESI agreement** (97.2%; 95% Wilson CI 85.8%-99.5%), **36/36 within-one-level agreement** (100.0%; 95% Wilson CI 90.4%-100.0%), and **0/36 critical under-triage** (95% Wilson CI 0.0%-9.6%) on the frozen benchmark run. No ESI 1 or 2 patient was assigned ESI 3, 4, or 5. Every case is logged to BigQuery, audit-ready for GAHAR hospital accreditation.

---

## [1:50–2:00] CLOSE

SAFE-Triage is live right now at safe-triage-ai.web.app. Egypt has over 650 hospitals and a preventable mortality crisis. This is our answer — built by clinicians, for clinicians.

Thank you.

---

### Production Notes

| Cue | Visual Suggestion |
|-----|-------------------|
| 0:00–0:20 | Dr. Ahmed on camera, team photos on screen |
| 0:20–0:40 | ED statistics on screen, Egyptian hospital footage |
| 0:40–1:10 | Architecture diagram: AI → Rules → Human |
| 1:10–1:35 | Live screen recording of the triage form + result |
| 1:35–1:50 | Validation metrics table, dataset names |
| 1:50–2:00 | Live URL on screen, team photo |

**Word count:** ~320 words (fits 2:00 at moderate speaking pace)
**Tone:** Confident, personal, clinical — let the team story and the numbers do the work.
