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

SAFE-Triage is a **production-deployed, hybrid AI system** that follows one golden rule:

> ### 🧠 AI Extracts → 📏 Rules Decide → 👨‍⚕️ Humans Confirm

| Layer | Role | Technology |
|-------|------|------------|
| **AI Extraction** | Understands patient complaints in Arabic dialect & English | Gemini 2.5-flash + MedGemma on Vertex AI |
| **Deterministic Rules** | Makes all safety-critical triage decisions | ESI v5 + NEWS2 (pre-encoded from official handbooks) |
| **Human Confirmation** | Clinician reviews and confirms every case | Real-time physician alerts + web dashboard |

**AI never decides how sick someone is.** It only extracts and classifies symptoms. Clinical protocols make the decisions. A human confirms every case.

---

## MedGemma Integration

SAFE-Triage integrates **MedGemma 4B-IT**, Google's open medical foundation model, deployed natively on **Vertex AI Model Garden** as a clinical quality assurance layer:

- **Vertex AI Deployment** — MedGemma runs on a dedicated Vertex AI endpoint (L4 GPU, scale-to-zero) within the same `safe-triage-ai` Google Cloud project. No third-party API dependencies.
- **Batch QA Review** — MedGemma performs asynchronous hourly review of triage decisions, flagging cases where AI extraction may have missed atypical presentations
- **Silent Killer Detection** — Catches high-risk cases with misleading mild symptoms (e.g., diabetic patient with "mild heartburn" → atypical MI → escalated to ESI 2)
- **QA Dashboard** — Dedicated monitoring dashboard at `/medgemma/dashboard` showing severity breakdown, pattern trends, daily flag volume, and recent flagged cases. Backed by BigQuery analytics views.
- **Arabic Medical NLP** — Combined with Gemini 2.5-flash, provides robust bilingual understanding of Egyptian dialect medical complaints
- **Disaster Protocol Activation** — Triggers mass casualty protocols when unusual case volume patterns are detected

The system was submitted to the **MedGemma Impact Challenge on Kaggle** (February 2026) for both the Main Track and Novel Task Prize categories, positioning Arabic dialect emergency triage as a genuinely novel application.

---

## Validated Performance

| Metric | SAFE-Triage (MIETIC, n=36) | Human Nurses | Industry Standard |
|--------|---------------------------|--------------|-------------------|
| **Exact ESI Accuracy** | **97.2%** (35/36) | 61.3% | ~72% |
| **Within-1 Accuracy** | **100%** (36/36) | 82.9% | ~85% |
| **Critical Under-triage** | **0.0%** (0/36) | 5-15% | <5% (ACS-COT) |
| **Over-triage** | 2.8% (1/36) | ~20% | ~30% |

*Validated on 36 expert-reviewed MIETIC cases (MIMIC-IV-ED Triage Instruction Corpus).
Zero critical under-triage. 97.2% exact ESI match. 100% within-one-level.
See `backend/benchmarks/` for fully reproducible benchmark code.*

---

## Key Features

**🇪🇬 Arabic Dialect Support** — 1,858 Egyptian Arabic medical keywords, not just Modern Standard Arabic. Understands colloquial complaints like "قلبي بيوجعني" and "حاسس إني هموت".

**🔒 Safety-First Architecture** — Zero critical under-triage achieved on the MIETIC benchmark. Over-triage is always safer than under-triage. Deterministic safety floors (vital-sign escalation, life-threat text detection) enforce patient safety that AI cannot override.

**🧬 MedGemma QA Layer** — Google's medical foundation model reviews triage decisions asynchronously, catching atypical presentations and silent killers that pattern matching alone would miss.

**📴 Offline Mode** — When internet fails (common in Egyptian hospitals), the system falls back to a local keyword engine with 1,858 terms. No internet ≠ no triage.

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
| **Terminology** | 1,858 Arabic keywords, 6,370 SNOMED-CT concepts |

---

## Clinical Validation Datasets

| Dataset | Source | Cases | Purpose |
|---------|--------|-------|---------|
| MIMIC-IV-ED | MIT/PhysioNet | 425,000+ | Large-scale ED visit validation |
| MIETIC (RETAIN subset) | Expert panel | 36 | Primary validation benchmark (36 expert-reviewed cases from MIMIC-IV-ED Triage Instruction Corpus) |
| Korean KTAS | External | — | Cross-cultural generalizability |
| Custom Arabic | Internal | 156+ | Egyptian dialect stress testing |

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
