# MIETIC Arabic Mirror Benchmark Report

## Dataset
- **Source**: Arabic MIETIC mirror fixture
- **Subset**: Expert-validated RETAIN cases with physician-filled Arabic vignette
- **Total fixture cases**: 36
- **Runnable Arabic cases**: 36
- **Acuity distribution**: {1: 14, 2: 11, 3: 5, 4: 4, 5: 2}
- **Cases with missing vitals**: 11
- **Timestamp**: 20260404T211129Z

## Summary Metrics

| Metric | Value |
|--------|-------|
| Total cases | 36 |
| Exact ESI match | 35 (97.2%) |
| Within-one-level | 36 (100.0%) |
| Under-triage (all) | 0 (0.0%) |
| Over-triage (all) | 1 (2.8%) |
| **Critical under-triage** | **0 (0.0%)** |

> SAFETY GATE: PASSED (zero critical under-triage)

## Per-Class Recall

| ESI Level | Recall | Correct / Total |
|-----------|--------|-----------------|
| ESI 1 | 100.0% | 14 / 14 |
| ESI 2 | 100.0% | 11 / 11 |
| ESI 3 | 80.0% | 4 / 5 |
| ESI 4 | 100.0% | 4 / 4 |
| ESI 5 | 100.0% | 2 / 2 |

## Confusion Matrix

Rows = Actual ESI, Columns = Predicted ESI

| | Pred 1 | Pred 2 | Pred 3 | Pred 4 | Pred 5 |
|---|---|---|---|---|---|
| **Actual 1** | 14 | 0 | 0 | 0 | 0 |
| **Actual 2** | 0 | 11 | 0 | 0 | 0 |
| **Actual 3** | 0 | 1 | 4 | 0 | 0 |
| **Actual 4** | 0 | 0 | 0 | 4 | 0 |
| **Actual 5** | 0 | 0 | 0 | 0 | 2 |
