# MIETIC Arabic Mirror Benchmark Report

## Dataset
- **Source**: Arabic MIETIC mirror fixture
- **Subset**: Expert-validated RETAIN cases with physician-filled Arabic vignette
- **Total fixture cases**: 36
- **Runnable Arabic cases**: 36
- **Acuity distribution**: {1: 14, 2: 11, 3: 5, 4: 4, 5: 2}
- **Cases with missing vitals**: 11
- **Timestamp**: 20260401T210012Z

## Summary Metrics

| Metric | Value |
|--------|-------|
| Total cases | 36 |
| Exact ESI match | 19 (52.8%) |
| Within-one-level | 33 (91.7%) |
| Under-triage (all) | 11 (30.6%) |
| Over-triage (all) | 6 (16.7%) |
| **Critical under-triage** | **11 (30.6%)** |

> SAFETY GATE: **FAILED** (11 critical under-triage cases)

## Per-Class Recall

| ESI Level | Recall | Correct / Total |
|-----------|--------|-----------------|
| ESI 1 | 42.9% | 6 / 14 |
| ESI 2 | 72.7% | 8 / 11 |
| ESI 3 | 80.0% | 4 / 5 |
| ESI 4 | 0.0% | 0 / 4 |
| ESI 5 | 50.0% | 1 / 2 |

## Confusion Matrix

Rows = Actual ESI, Columns = Predicted ESI

| | Pred 1 | Pred 2 | Pred 3 | Pred 4 | Pred 5 |
|---|---|---|---|---|---|
| **Actual 1** | 6 | 7 | 1 | 0 | 0 |
| **Actual 2** | 0 | 8 | 2 | 1 | 0 |
| **Actual 3** | 0 | 1 | 4 | 0 | 0 |
| **Actual 4** | 0 | 0 | 4 | 0 | 0 |
| **Actual 5** | 0 | 0 | 1 | 0 | 1 |

## Critical Under-Triage Cases

| Case ID | Actual | Predicted | Complaint |
|---------|--------|-----------|-----------|
| stay_30000679 | ESI 2 | ESI 3 | ABDOMINAL PAIN |
| stay_30017342 | ESI 1 | ESI 2 | Overdose |
| stay_30055056 | ESI 1 | ESI 2 | Found down |
| stay_30115077 | ESI 2 | ESI 4 | Chest pain |
| stay_30116118 | ESI 1 | ESI 2 | ALTERED LEVEL OF CONSCIOUSNESS |
| stay_30125793 | ESI 1 | ESI 2 | Cardiac arrest |
| stay_30132519 | ESI 1 | ESI 3 | MVC, Transfer |
| stay_30134741 | ESI 2 | ESI 3 | L Leg injury, Transfer |
| stay_30179684 | ESI 1 | ESI 2 | Unresponsive, Respiratory distress |
| stay_31731173 | ESI 1 | ESI 2 | Chest pain |
| stay_32622318 | ESI 1 | ESI 2 | SEPSIS |
