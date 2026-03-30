# MIETIC Benchmark Report

## Dataset
- **Source**: MIMIC-IV-ED Triage Instruction Corpus (MIETIC)
- **Subset**: Expert-validated RETAIN cases
- **Total cases**: 36
- **Acuity distribution**: {1: 14, 2: 11, 3: 5, 4: 4, 5: 2}
- **Cases with missing vitals**: 11
- **Timestamp**: 20260330T232325Z

## Summary Metrics

| Metric | Value |
|--------|-------|
| Total cases | 36 |
| Exact ESI match | 26 (72.2%) |
| Within-one-level | 35 (97.2%) |
| Under-triage (all) | 1 (2.8%) |
| Over-triage (all) | 9 (25.0%) |
| **Critical under-triage** | **0 (0.0%)** |

> SAFETY GATE: PASSED (zero critical under-triage)

## Per-Class Recall

| ESI Level | Recall | Correct / Total |
|-----------|--------|-----------------|
| ESI 1 | 100.0% | 14 / 14 |
| ESI 2 | 81.8% | 9 / 11 |
| ESI 3 | 0.0% | 0 / 5 |
| ESI 4 | 75.0% | 3 / 4 |
| ESI 5 | 0.0% | 0 / 2 |

## Confusion Matrix

Rows = Actual ESI, Columns = Predicted ESI

| | Pred 1 | Pred 2 | Pred 3 | Pred 4 | Pred 5 |
|---|---|---|---|---|---|
| **Actual 1** | 14 | 0 | 0 | 0 | 0 |
| **Actual 2** | 2 | 9 | 0 | 0 | 0 |
| **Actual 3** | 0 | 4 | 0 | 1 | 0 |
| **Actual 4** | 0 | 1 | 0 | 3 | 0 |
| **Actual 5** | 0 | 0 | 0 | 2 | 0 |
