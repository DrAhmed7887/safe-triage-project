# SAFE-Triage Project

## Overview
AI-first emergency department triage decision support system for Egyptian hospitals.
AUC AI & Business capstone thesis. Uses hybrid deterministic + AI architecture.

**Golden Rule:** "AI Extracts -> Rules Decide -> Humans Confirm"

## Architecture
- **Layer 1:** AI Extraction (Gemini 2.5-flash) - chief complaint -> fixed symptom category
- **Layer 2:** Deterministic Rules (ESI v5 + NEWS2) - category + vitals -> ESI level
- **Layer 3:** Human Confirmation - physician dashboard review
- **Async:** MedGemma QA batch review

## Key Differentiator
**Arabic/Egyptian dialect support** - 1,858 Arabic medical keywords including Egyptian colloquial variants. No other MIMIC-IV triage system handles Arabic. This is the unique angle for both the competition and paper publication.

## Tech Stack
- **Backend:** FastAPI + Python (Google Cloud Run)
- **Frontend:** React + Vite (Firebase Hosting)
- **AI Models:** Gemini 2.5-flash (Vertex AI), MedGemma 2B (QA), EgyBERT (Arabic NLP)
- **Data:** BigQuery (prod), SQLite (offline), MIMIC-IV-ED (benchmarking)
- **Terminology:** 6,370 SNOMED-CT concepts, ICD-10 mapping

## Key Files
- `backend/logic/triage_engine_v2.py` - Main hybrid triage engine (NEWS2 + ESI v5)
- `backend/logic/esi_v5_engine.py` - ESI v5 protocol with safety floors
- `backend/ai_service.py` - Gemini integration
- `backend/main.py` - FastAPI API endpoints
- `backend/benchmarks/mietic_benchmark.py` - Primary gold-standard benchmark (36 RETAIN cases)
- `backend/tests/mimic_replay_benchmark.py` - Large-scale MIMIC-IV replay benchmark

## MIMIC-IV Data (`mimic-iv-ed-2.2/ed/`)
- `triage.csv.gz` - 418K labeled triage cases (chief complaint + vitals + ESI acuity)
- `edstays.csv.gz` - Demographics (gender, race, arrival_transport, disposition)
- `vitalsign.csv.gz` - Serial vital signs (HR, RR, SpO2, BP, Temp, pain)
- `diagnosis.csv.gz` - ICD codes
- `medrecon.csv.gz` - Medication reconciliation
- `pyxis.csv.gz` - Dispensing records (DO NOT USE - failed in prior attempt)

## Benchmarking
- **MIETIC (primary):** 36 expert-validated cases. Target: 0% critical under-triage.
- **MIMIC replay (secondary):** 7K balanced sample. Stress test, not primary validation.
- **English scenarios:** 88 hand-crafted regression tests.

## Important Rules
- **Safety first:** 0% critical under-triage is non-negotiable. Over-triage is acceptable.
- **Do NOT tune safety floor rules** to reduce over-triage - too risky.
- **Do NOT use pyxis.csv** for resource estimation - tried before and failed.
- **Always frame as bilingual** (Arabic + English with Egyptian dialect) in any paper/pitch.
- Temperatures in MIMIC are Fahrenheit. Convert to Celsius for the engine.

## Competition Strategy
1. Join real demographics from edstays.csv (age derivable from subject_id linkage, gender available)
2. Use serial vitals from vitalsign.csv (worst/most abnormal)
3. ML ensemble layer (XGBoost/LightGBM + rule engine + MedGemma)
4. Outcome validation against ICU admission/mortality for paper
5. Emphasize Arabic dialect NLP as unique contribution

## Compliance
GAHAR (Egyptian Hospital Accreditation), ESI v5 (AHRQ), NEWS2 (RCP), SNOMED-CT, ICD-10, CITI Program ethics certification.
