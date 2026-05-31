# SAFE-Triage Data Availability

Snapshot date: 2026-05-31

## MIETIC

The primary retrospective benchmark uses the expert-validated subset of the MIMIC-IV-Ext Triage Instruction Corpus (MIETIC), derived from MIMIC-IV-ED and available through PhysioNet credentialed access.

Repository artifacts:

- `backend/benchmarks/outputs/mietic/summary.json`
- `backend/benchmarks/outputs/mietic/predictions.csv`
- `backend/benchmarks/outputs/mietic/report.md`

Locked public claims:

- 35/36 exact ESI agreement = 97.2% (95% Wilson CI 85.8% to 99.5%).
- 36/36 within-one agreement = 100.0% (95% Wilson CI 90.4% to 100.0%).
- 0/36 critical under-triage = 0.0% (95% Wilson CI 0.0% to 9.6%).

## MIETIC Arabic Mirror

The Arabic mirror is a translated version of the same 36 MIETIC cases. It is useful for translated-case parity, but it is not an Arabic-native emergency department corpus.

Repository artifacts:

- `backend/benchmarks/outputs/mietic_ar/summary.json`
- `backend/benchmarks/outputs/mietic_ar/predictions.csv`
- `backend/benchmarks/outputs/mietic_ar/report.md`
- `backend/benchmarks/outputs/mietic_ar/comparison.md`

Locked public claims:

- 35/36 exact ESI agreement = 97.2% (95% Wilson CI 85.8% to 99.5%).
- 36/36 within-one agreement = 100.0% (95% Wilson CI 90.4% to 100.0%).
- 0/36 critical under-triage = 0.0% (95% Wilson CI 0.0% to 9.6%).

## KTAS

The KTAS dataset is used only as a cross-protocol stress test. KTAS and ESI have different acuity boundaries, so exact agreement must not be framed as native ESI validation.

Repository artifacts:

- `backend/benchmarks/outputs/ktas/summary.json`
- `backend/benchmarks/outputs/ktas/predictions.csv`
- `backend/benchmarks/outputs/ktas/report.md`

Locked public claims:

- 477/1,262 exact agreement = 37.8% (95% Wilson CI 35.2% to 40.5%).
- 1,030/1,262 within-one agreement = 81.6% (95% Wilson CI 79.4% to 83.7%).
- 16/1,262 critical under-triage = 1.3% (95% Wilson CI 0.8% to 2.0%).
- 708/1,262 over-triage = 56.1% (95% Wilson CI 53.3% to 58.8%).

## Reproducibility Script

Confidence intervals are produced by:

```bash
python3 scripts/wilson_ci.py
```

The script has no third-party dependencies.
