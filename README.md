# 🏥 SAFE-Triage: Smart AI-First Emergency Triage

### AI-Powered Emergency Department Decision Support — Built for Egyptian Hospitals

[![Live System](https://img.shields.io/badge/🔴_Live-safe--triage--ai.web.app-brightgreen)](https://safe-triage-ai.web.app)
[![Cloud Run](https://img.shields.io/badge/Backend-Google_Cloud_Run-4285F4?logo=googlecloud)](https://safe-triage-eciux5h4aq-uc.a.run.app)
[![ESI v5](https://img.shields.io/badge/Protocol-ESI_v5_+_NEWS2-red)](https://www.ahrq.gov/patient-safety/settings/emergency-dept/esi.html)
[![MedGemma](https://img.shields.io/badge/AI-MedGemma_+_Gemini_2.5--flash-blue?logo=google)](https://ai.google.dev/gemma/docs/medgemma)
[![License](https://img.shields.io/badge/License-Proprietary-orange)]()

---

## The Problem

Egyptian emergency departments face a convergence of crises:

- **86%** of ED staff experience workplace violence ([WHO Eastern Mediterranean, 2023](https://www.emro.who.int))
- **32%** preventable mortality linked to triage failures in LMICs
- **No standardized triage** in most Egyptian hospitals
- Language barriers for international patients and tourists
- Unreliable internet infrastructure

**The result:** Critical patients wait. Lives are lost. Nurses burn out.

---

## The Solution

SAFE-Triage is a **research-stage, hybrid AI decision-support system** that follows one golden rule:

> ### 🧠 AI Extracts → 📏 Rules Decide → 👨‍⚕️ Humans Confirm

| Layer | Role | Technology |
|-------|------|------------|
| **AI Extraction** | Understands patient complaints in Arabic dialect & English | Gemini 2.5-flash + structured keyword/rules fallback |
| **Deterministic Rules** | Makes all safety-critical triage decisions | ESI v5 + NEWS2 (pre-encoded from official handbooks) |
| **Human Confirmation** | Clinician reviews and confirms every case | Real-time physician alerts + web dashboard |

**AI never decides how sick someone is.** It only extracts and classifies symptoms. Clinical protocols make the decisions. A human confirms every case.

---

## MedGemma Integration

SAFE-Triage has evaluated **MedGemma 4B-IT**, Google's open medical foundation model, as a clinical quality assurance layer during development:

- **Development QA Review** — MedGemma was tested as an asynchronous reviewer that flags cases where extraction or deterministic rules may need human attention.
- **Hard-case flagging** — In an offline KTAS hard-case review, MedGemma flagged 12/17 critical or borderline cases (70.6%; 95% Wilson CI 46.9% to 86.7%).
- **Current status** — MedGemma is not the final triage authority and should be described as a development-stage QA component unless a current deployment check confirms otherwise.
- **Arabic Medical NLP** — Combined with Gemini 2.5-flash, provides robust bilingual understanding of Egyptian dialect medical complaints

The system was submitted to the **MedGemma Impact Challenge on Kaggle** (February 2026) for both the Main Track and Novel Task Prize categories, positioning Arabic dialect emergency triage as a genuinely novel application.

---

## Validated Performance

### Primary Benchmark — MIETIC (n=36, expert-validated)

| Metric | SAFE-Triage | 95% Wilson CI | Framing |
|--------|-------------|----------------|---------|
| **Exact ESI agreement** | **35/36 = 97.2%** | 85.8% to 99.5% | Small expert-validated MIETIC subset |
| **Within-one agreement** | **36/36 = 100.0%** | 90.4% to 100.0% | Agreement within one ESI level |
| **Critical under-triage** | **0/36 = 0.0%** | 0.0% to 9.6% | Primary safety endpoint |
| **Over-triage** | 1/36 = 2.8% | 0.5% to 14.2% | Safe-direction discordance |

The Arabic mirror benchmark produced the same locked result: 35/36 exact ESI agreement, 36/36 within-one agreement, 0/36 critical under-triage, and 1/36 safe-direction over-triage. The mirror is a translation of the English MIETIC cases, not an Arabic-native ED corpus.

### External Benchmark — KTAS (n=1,262, cross-protocol stress test)

| Metric | SAFE-Triage | 95% Wilson CI | Framing |
|--------|-------------|----------------|---------|
| Exact agreement | 477/1,262 = 37.8% | 35.2% to 40.5% | Expected to be low because KTAS and ESI are non-equivalent protocols |
| Within-one agreement | 1,030/1,262 = 81.6% | 79.4% to 83.7% | Robustness signal, not native ESI validation |
| Critical under-triage | 16/1,262 = 1.3% | 0.8% to 2.0% | Non-zero limitation under protocol mismatch |
| Over-triage | 708/1,262 = 56.1% | 53.3% to 58.8% | Predominantly safe-direction disagreement |

KTAS is a Korean Triage and Acuity Scale dataset. These results must be framed as cross-protocol stress testing, not as SAFE-Triage accuracy on its home ESI protocol.

See `backend/benchmarks/` for benchmark code and `scripts/wilson_ci.py` for the confidence-interval calculation.

---

## Key Features

**🇪🇬 Arabic Dialect Support** — 2,101 Egyptian Arabic medical keywords, not just Modern Standard Arabic. Understands colloquial complaints like "قلبي بيوجعني" and "حاسس إني هموت".

**🔒 Safety-First Architecture** — Zero critical under-triage achieved on the MIETIC benchmark. Over-triage is always safer than under-triage. Deterministic safety floors (vital-sign escalation, life-threat text detection) enforce patient safety that AI cannot override.

**🧬 MedGemma QA Layer** — Google's medical foundation model reviews triage decisions asynchronously, catching atypical presentations and silent killers that pattern matching alone would miss.

**📴 Offline Mode** — When internet fails (common in Egyptian hospitals), the system falls back to a local keyword engine with 2,101 terms. No internet ≠ no triage.

**🌍 Bilingual Output** — Every triage result includes English and Arabic descriptions, actions, and time estimates. Serves both local patients and international tourists.

**📊 Full Audit Trail** — Every case logged to BigQuery (19 columns) for quality assurance, GAHAR compliance, and research.

**⚡ Real-Time Physician Alerts** — Critical cases (ESI 1-2) trigger instant notifications to on-call physicians for immediate confirmation.

---

## Architecture

```
Patient Complaint (Arabic/English)
         │
         ▼
┌─────────────────────────┐
│  Gemini 2.5-flash        │  ← AI: Extract symptoms, map to SNOMED-CT
│  (Vertex AI)             │     6,370 concepts, structured JSON output
└──────────┬──────────────┘
           │
           ▼
┌─────────────────────────┐
│  Deterministic Engine    │  ← Rules: ESI v5 Decision Points A→D
│  ESI v5 + NEWS2          │     NEWS2 vital signs scoring
│  (Local SQLite)          │     Red-flag pattern matching
└──────────┬──────────────┘
           │
           ▼
┌─────────────────────────┐
│  Human Confirmation      │  ← Clinician: Review, confirm, override
│  Physician Alerts +      │     Every case. No exceptions.
│  Web Dashboard           │
└──────────┬──────────────┘
           │
           ▼
┌─────────────────────────┐
│  MedGemma QA Layer       │  ← Async: Batch review, silent killer
│  (Quality Assurance)     │     detection, disaster protocol triggers
└──────────┬──────────────┘
           │
           ▼
┌─────────────────────────┐
│  BigQuery Audit Log      │  ← 19 columns per case
│  + Analytics             │     GAHAR compliance ready
└─────────────────────────┘
```

---

## Tech Stack

| Component | Technology |
|-----------|-----------|
| **AI/NLP** | Gemini 2.5-flash (Vertex AI) + MedGemma 4B-IT (Vertex AI Model Garden) |
| **Backend** | Python, FastAPI |
| **Frontend** | React, Vite |
| **Hosting** | Google Cloud Run (backend), Firebase Hosting (frontend) |
| **Database** | BigQuery (audit logs), SQLite (rules engine) |
| **Medical Standards** | ESI v5, NEWS2, SNOMED-CT, ICD-10 |
| **Alerts** | Real-time physician notification system |
| **Terminology** | 2,101 Arabic keywords, 6,370 SNOMED-CT concepts |

---

## Clinical Validation Datasets

| Dataset | Source | Cases | Purpose |
|---------|--------|-------|---------|
| MIMIC-IV-ED | MIT/PhysioNet | 425,000+ | Large-scale ED visit validation |
| MIETIC (RETAIN subset) | Expert panel | 36 | Primary benchmark - 35/36 exact, 36/36 within-one, 0/36 critical under-triage |
| MIETIC Arabic mirror | Internal | 36 | Translated mirror benchmark - same locked metrics as English |
| Korean KTAS | External | 1,262 | Cross-protocol stress test - 477/1,262 exact, 1,030/1,262 within-one, 16/1,262 critical under-triage |
| NHAMCS (CDC) | US CDC | 10,495 | Large low-context stress test |

---

## Repository Structure

```
safe-triage-project/
├── backend/                  # FastAPI backend + triage engine
│   ├── triage_engine_v2.py   # Deterministic ESI v5 + NEWS2 engine
│   ├── main.py               # API endpoints
│   ├── keywords_db.py        # 1,858 Arabic medical keywords
│   └── Dockerfile            # Cloud Run deployment
├── frontend/                 # React + Vite frontend
│   ├── src/
│   └── dist/                 # Built assets (Firebase Hosting)
├── docs/                     # Documentation
│   ├── SAFE_Triage_Complete_Project_History.md
│   ├── SAFE_Triage_Defense_Script_BILINGUAL.md
│   ├── SAFE_Triage_Safety_Plan.pdf
│   └── SAFE_Triage_Technical_Report.pdf
├── validation/               # Test suites and validation scripts
├── .gitignore
├── CONTRIBUTING.md           # Team collaboration guide
├── TEAM.md                   # Team members & Harvard application
└── README.md                 # This file
```

---

## Quick Start

```bash
# Clone the repository
git clone https://github.com/DrAhmed7887/safe-triage-project.git
cd safe-triage-project

# Backend
cd backend
pip install -r requirements.txt
uvicorn main:app --reload

# Frontend
cd frontend
npm install
npm run dev
```

---

## Live Demo

🔗 **Try it now:** [safe-triage-ai.web.app](https://safe-triage-ai.web.app)

🎥 **Video Demo:** [youtu.be/RRQ0_RTsDrI](https://youtu.be/RRQ0_RTsDrI)

## Deployment

- Pushes to `main` automatically deploy the backend to Cloud Run and the frontend to Firebase Hosting.
- GitHub is the source of truth; make edits locally, commit them, and push to keep the cloud copies in sync.

---

## Publications & Competitions

| Venue | Status | Date |
|-------|--------|------|
| MedGemma Impact Challenge (Kaggle) | ✅ Submitted (Main Track + Novel Task) | Feb 2026 |
| AMIA Clinical Informatics Conference | ✅ Submitted | Feb 2026 |
| Harvard HSIL Hackathon | 🔜 Preparing | 2026 |
| JAMIA Manuscript | 🔜 In preparation | 2026 |

---

## Team

**Avengers Team (Group 1)** — The American University in Cairo, School of Business

*Capstone thesis project for the AUC AI & Business program.*

See [TEAM.md](TEAM.md) for the full team roster and Harvard application details.

**Ahmed Zayed, MBBCh** — Lead Developer & System Architect
- GitHub: [@DrAhmed7887](https://github.com/DrAhmed7887)

---

## Compliance & Standards

- **GAHAR** (Egyptian Hospital Accreditation) — ACT.03, ICD.08/09, NSR alignment
- **ESI v5** — Emergency Severity Index, 5th Edition (AHRQ)
- **NEWS2** — National Early Warning Score 2 (Royal College of Physicians)
- **SNOMED-CT** — Systematized Nomenclature of Medicine
- **ICD-10** — International Classification of Diseases
- **CITI Program** — Research ethics training completed
- **PhysioNet** — Credentialed data access (NLM-10000064943)

---

## According to GAHAR Standards | وفقاً لمعايير الجهار

---

## License

Proprietary — The American University in Cairo (2026)
