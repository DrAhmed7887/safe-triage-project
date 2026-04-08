# Paper Evidence Bank

This file maps thesis or slide claims to the best supporting artifacts already in the repo.

## Architecture claim

Claim:
- SAFE-Triage is a hybrid clinical decision support system where AI extracts structured complaint information, deterministic rules assign acuity, and clinicians confirm the final result.

Best evidence:
- `backend/main.py`
- `backend/logic/deterministic_triage.py`
- `backend/logic/esi_v5_engine.py`
- `docs/VALIDATION_REPORT.md`

## Safety claim

Claim:
- The system prioritizes avoiding critical under-triage over optimizing exact-match accuracy.

Best evidence:
- `backend/knowledge_base/safe_triage_clinical_rules.txt`
- `backend/knowledge_base/news2_scoring_guide.txt`
- `backend/benchmarks/outputs/mietic/summary.json`
- `backend/benchmarks/outputs/mietic_ar/summary.json`

## Arabic differentiator claim

Claim:
- SAFE-Triage explicitly supports Egyptian colloquial Arabic complaint language.

Best evidence:
- `backend/arabic_keywords_v2.py`
- `backend/tools/generate_arabic_keywords.py`
- `docs/prompts/arabic-dialect-expansion.md`
- `backend/benchmarks/outputs/mietic_ar/summary.json`
- `backend/benchmarks/outputs/ktas_arabic/arabic_summary.json`

Important caveat:
- standardize the keyword-count snapshot before using any numeric lexicon claim

## External-validation claim

Claim:
- The system was stress-tested beyond MIETIC using external datasets including KTAS and NHAMCS.

Best evidence:
- `backend/benchmarks/outputs/ktas/summary.json`
- `backend/benchmarks/outputs/ktas_arabic/arabic_summary.json`
- `backend/benchmarks/outputs/nhamcs/summary.json`
- `docs/VALIDATION_REPORT.md`

Recommended wording:
- KTAS is the stronger external story than NHAMCS because it is expert-labeled and clinically richer
- NHAMCS should be framed as a large sparse-label stress test

## Deployment and production-readiness claim

Claim:
- SAFE-Triage is deployed as a working web system with deterministic logic, analytics, and clinician review paths.

Best evidence:
- `README.md`
- `docs/thesis_defense/Deployment_Guide.md`
- `backend/main.py`
- `frontend/src/pages/Dashboard.jsx`
- `frontend/src/pages/MedGemmaDashboard.jsx`

## MedGemma or QA-layer claim

Claim:
- MedGemma operates as an asynchronous QA layer rather than live decision authority.

Best evidence:
- `docs/VALIDATION_REPORT.md`
- `README.md`
- `backend/medgemma_batch_qa.py`
- `backend/medgemma_hourly_job.py`

## Limitations section evidence

Use these as grounded limitations instead of generic AI caveats:
- Arabic parity outside MIETIC is incomplete: see `backend/benchmarks/outputs/ktas_arabic/arabic_summary.json`
- NHAMCS exact-match performance is modest and reflects sparse-label and cross-system mismatch: see `backend/benchmarks/outputs/nhamcs/summary.json`
- claim drift exists in current docs for keyword counts and protocol-version wording: see `docs/wiki/validation-claims.md`

## Figure and table candidates

Strong candidates for the thesis or defense deck:
- architecture figure from the README or validation report
- benchmark summary table using MIETIC, MIETIC Arabic, KTAS, and NHAMCS
- Arabic parity table using selected examples from `parity_diff_details` in `backend/benchmarks/outputs/ktas_arabic/arabic_summary.json`
- rule-provenance table showing safety floors and supporting clinical rationale

## Questions this evidence bank should answer quickly

- Why is the system safer than a pure-LLM triage design?
- Why is Arabic support a genuine contribution and not just translation?
- Why should reviewers trust the rules?
- Which benchmark is the primary basis for claims?
- Which numbers are current and which are stale?
