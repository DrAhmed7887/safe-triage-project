# SAFE-Triage System Card

Snapshot date: 2026-05-31
Benchmark freeze: 20260408T223413Z
Status: research-stage clinical decision-support prototype; not prospectively validated; not autonomous diagnosis.

## Intended Use

SAFE-Triage is intended as clinician-facing emergency triage decision support for Arabic/English patient complaints in resource-constrained emergency departments. The system recommends an ESI acuity level for clinician confirmation. It must not be used as an autonomous triage decision-maker.

## Architecture

| Layer | Role | Authority |
|---|---|---|
| AI extraction | Maps Arabic/English complaints to structured clinical features | No final acuity authority |
| Deterministic rules | Encodes ESI v5 and NEWS2 safety floors | Final software acuity recommendation |
| Human confirmation | Clinician accepts or overrides the recommendation | Required before clinical use |
| QA review | MedGemma/Gemma-style review of atypical or borderline cases | Flags only; no acuity authority |

Core rule: AI may escalate acuity through extracted red flags, but it cannot lower acuity below the deterministic safety floor.

## Locked Benchmark Results

| Benchmark | Metric | Count | Point estimate | 95% Wilson CI |
|---|---|---:|---:|---:|
| MIETIC English | Exact ESI agreement | 35/36 | 97.2% | 85.8% to 99.5% |
| MIETIC English | Within-one agreement | 36/36 | 100.0% | 90.4% to 100.0% |
| MIETIC English | Critical under-triage | 0/36 | 0.0% | 0.0% to 9.6% |
| MIETIC English | Over-triage | 1/36 | 2.8% | 0.5% to 14.2% |
| MIETIC Arabic mirror | Exact ESI agreement | 35/36 | 97.2% | 85.8% to 99.5% |
| MIETIC Arabic mirror | Within-one agreement | 36/36 | 100.0% | 90.4% to 100.0% |
| MIETIC Arabic mirror | Critical under-triage | 0/36 | 0.0% | 0.0% to 9.6% |
| KTAS cross-protocol | Exact agreement | 477/1,262 | 37.8% | 35.2% to 40.5% |
| KTAS cross-protocol | Within-one agreement | 1,030/1,262 | 81.6% | 79.4% to 83.7% |
| KTAS cross-protocol | Critical under-triage | 16/1,262 | 1.3% | 0.8% to 2.0% |
| KTAS cross-protocol | Over-triage | 708/1,262 | 56.1% | 53.3% to 58.8% |
| KTAS hard cases | Gemma 4 resolution | 6/17 | 35.3% | 17.3% to 58.7% |
| KTAS hard cases | MedGemma flagging | 12/17 | 70.6% | 46.9% to 86.7% |

## Known Limitations

- MIETIC has only 36 expert-validated cases; confidence intervals are wide.
- The Arabic mirror is translated from the English MIETIC set, not an Arabic-native ED corpus.
- KTAS is a cross-protocol stress test; low exact agreement is expected and should not be framed as native ESI performance.
- The system has not been prospectively validated in a live emergency department.
- MedGemma hard-case results are offline/development results and should not be framed as current clinical deployment unless independently reverified.

## Reproduction

Run:

```bash
python3 scripts/wilson_ci.py
```

Benchmark artifacts are under `backend/benchmarks/outputs/`.
