# SAFE-Triage Project

## Overview
AI-first emergency department triage decision support system for Egyptian hospitals.
AUC AI & Business capstone thesis. Uses hybrid deterministic + AI architecture.

**Golden Rule:** "AI Extracts -> Rules Decide -> Humans Confirm"

## Architecture
- **Layer 1:** AI Extraction - chief complaint -> fixed symptom category
  - **Live primary:** Gemini 2.5-flash (fast, ~1-2s, uses $1K GenAI App Builder credit)
  - **Shadow/backup:** Gemma 4 E4B-IT (open-weight story for privacy-sensitive hospitals, Vertex AI endpoint)
- **Layer 2:** Deterministic Rules (ESI v5 + NEWS2) - category + vitals -> ESI level
- **Layer 3:** Human Confirmation - physician dashboard review
- **Async:** MedGemma 4B-IT QA batch review (Vertex AI Model Garden) — 27B doesn't fit on 1x L4 (23.5GB weights leaves no KV cache)
- **Final authority:** Deterministic SAFE-Triage rules always win

## Key Differentiator
**Arabic/Egyptian dialect support** - 1,858 Arabic medical keywords including Egyptian colloquial variants. No other MIMIC-IV triage system handles Arabic. This is the unique angle for both the competition and paper publication.

## Budget Allocation
- **$1,000 GenAI App Builder credit** (exp 2027-02): Vertex AI model endpoints — Gemini 2.5-flash API, Gemma 4 26B A4B GPU, MedGemma 27B GPU
- **$105 free trial** (exp 2026-05-05, use first): Infrastructure — Cloud Run, Firebase Hosting, BigQuery, Cloud Storage, misc GCP

## Tech Stack
- **Backend:** FastAPI + Python (Google Cloud Run)
- **Frontend:** React + Vite (Firebase Hosting)
- **AI Models:** Gemma 4 27B-IT (extraction, Vertex AI), Gemini 2.5-flash (fallback), MedGemma 4B-IT (QA, Vertex AI), EgyBERT (Arabic NLP)
- **Data:** BigQuery (prod), SQLite (offline), MIMIC-IV-ED (benchmarking)
- **Terminology:** 6,370 SNOMED-CT concepts, ICD-10 mapping
- **Budget:** $1,000 GenAI App Builder credit + $105 free trial. Hard stop at $950 via budget_guard.py.

## Key Files
- `backend/logic/triage_engine_v2.py` - Main hybrid triage engine (NEWS2 + ESI v5)
- `backend/logic/esi_v5_engine.py` - ESI v5 protocol with safety floors
- `backend/ai_service.py` - AI extraction (Gemma 4 primary → Gemini fallback, via Vertex AI)
- `backend/gemma4_client.py` - Gemma 4 Vertex AI endpoint client
- `backend/main.py` - FastAPI API endpoints
- `backend/benchmarks/mietic_benchmark.py` - Primary gold-standard benchmark (36 RETAIN cases)
- `backend/benchmarks/nhamcs_benchmark.py` - NHAMCS 10K CDC benchmark
- `backend/tests/mimic_replay_benchmark.py` - Large-scale MIMIC-IV replay benchmark
- `backend/deploy_gemma4_vertex.py` - Deploy Gemma 4 on Vertex AI Model Garden
- `backend/deploy_medgemma_vertex.py` - Deploy MedGemma on Vertex AI Model Garden
- `backend/budget_guard.py` - Hard stop at $950, auto-undeploys all endpoints

## MIMIC-IV Data (`mimic-iv-ed-2.2/ed/`)
- `triage.csv.gz` - 418K labeled triage cases (chief complaint + vitals + ESI acuity)
- `edstays.csv.gz` - Demographics (gender, race, arrival_transport, disposition)
- `vitalsign.csv.gz` - Serial vital signs (HR, RR, SpO2, BP, Temp, pain)
- `diagnosis.csv.gz` - ICD codes
- `medrecon.csv.gz` - Medication reconciliation
- `pyxis.csv.gz` - Dispensing records (DO NOT USE - failed in prior attempt)

## Benchmarking
- **MIETIC (primary):** 36 expert-validated cases. Current: 35/36 exact = 97.2% (95% Wilson CI 85.8%-99.5%), 36/36 within-one, 0/36 critical under-triage (95% Wilson CI 0.0%-9.6%).
- **MIETIC Arabic:** 36 translated mirror cases in Egyptian dialect. Current: 35/36 exact = 97.2%, 36/36 within-one, 0/36 critical under-triage; same CI bounds as English.
- **KTAS (external):** 1,262 Korean ED cases, cross-protocol stress test. Current: 477/1,262 exact = 37.8%, 1,030/1,262 within-one = 81.6%, 16/1,262 critical under-triage = 1.3% (95% Wilson CI 0.8%-2.0%).
- **NHAMCS:** 10,495 US CDC cases. Current: 40% exact, 7.9% crit under-triage (needs work).
- **MIMIC replay (secondary):** 7K balanced sample. Stress test, not primary validation.
- **English scenarios:** 88 hand-crafted regression tests.

## Important Rules
- **Safety first:** 0% critical under-triage is non-negotiable. Over-triage is acceptable.
- **Do NOT tune safety floor rules** to reduce over-triage - too risky.
- **Do NOT use pyxis.csv** for resource estimation - tried before and failed.
- **Do NOT use GEMINI_API_KEY** — all AI goes through Vertex AI (ai_service.py). Legacy google.generativeai SDK removed.
- **Always frame as bilingual** (Arabic + English with Egyptian dialect) in any paper/pitch.
- Temperatures in MIMIC are Fahrenheit. Convert to Celsius for the engine.
- **Budget guard:** $950 hard stop. Run `python budget_guard.py --status` to check. Auto-undeploys all Vertex AI endpoints at threshold.

## Competition Strategy
1. Join real demographics from edstays.csv (age derivable from subject_id linkage, gender available)
2. Use serial vitals from vitalsign.csv (worst/most abnormal)
3. ML ensemble layer (XGBoost/LightGBM + rule engine + MedGemma)
4. Outcome validation against ICU admission/mortality for paper
5. Emphasize Arabic dialect NLP as unique contribution

## Compliance
GAHAR (Egyptian Hospital Accreditation), ESI v5 (AHRQ), NEWS2 (RCP), SNOMED-CT, ICD-10, CITI Program ethics certification.
