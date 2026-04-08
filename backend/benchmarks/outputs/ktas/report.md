# KTAS External Benchmark Report

## Dataset
- **Source**: Kaggle: ilkeryildiz/emergency-service-triage-application
- **Design**: Cross-sectional retrospective, two Korean EDs (Oct 2016 - Sep 2017)
- **Gold standard**: KTAS_expert (3 triage experts consensus)
- **Engine mode**: Deterministic only (no Gemini/MedGemma)
- **Total cases**: 1262
- **KTAS distribution**: {1: 26, 2: 219, 3: 487, 4: 455, 5: 75}
- **Missing SpO2**: 692 (55%)
- **Missing pain score**: 553 (44%)
- **Timestamp**: 20260408T221730Z

## Summary Metrics

| Metric | Value |
|--------|-------|
| Total cases | 1262 |
| Exact ESI match | 464 (36.8%) |
| Within-one-level | 1028 (81.5%) |
| Under-triage (all) | 115 (9.1%) |
| Over-triage (all) | 683 (54.1%) |
| **Critical under-triage** | **17 (1.3%)** |

> SAFETY GATE: **FAILED** (17 critical under-triage cases)

## Per-Class Recall

| ESI Level | Recall | Correct / Total |
|-----------|--------|-----------------|
| ESI 1 | 61.5% | 16 / 26 |
| ESI 2 | 81.7% | 179 / 219 |
| ESI 3 | 35.1% | 171 / 487 |
| ESI 4 | 21.5% | 98 / 455 |
| ESI 5 | 0.0% | 0 / 75 |

## Confusion Matrix

Rows = Actual ESI, Columns = Predicted ESI

| | Pred 1 | Pred 2 | Pred 3 | Pred 4 | Pred 5 |
|---|---|---|---|---|---|
| **Actual 1** | 16 | 10 | 0 | 0 | 0 |
| **Actual 2** | 33 | 179 | 7 | 0 | 0 |
| **Actual 3** | 21 | 197 | 171 | 98 | 0 |
| **Actual 4** | 0 | 158 | 199 | 98 | 0 |
| **Actual 5** | 1 | 18 | 36 | 20 | 0 |

## Critical Under-Triage Cases

| Case ID | Actual | Predicted | Complaint |
|---------|--------|-----------|-----------|
| ktas_row_61 | ESI 2 | ESI 3 | abd pain |
| ktas_row_119 | ESI 2 | ESI 3 | headache |
| ktas_row_123 | ESI 1 | ESI 2 | dyspnea |
| ktas_row_158 | ESI 2 | ESI 3 | fever |
| ktas_row_163 | ESI 1 | ESI 2 | melena |
| ktas_row_166 | ESI 1 | ESI 2 | dyspnea |
| ktas_row_217 | ESI 1 | ESI 2 | mental change |
| ktas_row_382 | ESI 2 | ESI 3 | dyspnea |
| ktas_row_707 | ESI 1 | ESI 2 | abd pain |
| ktas_row_806 | ESI 1 | ESI 2 | mental change |
| ktas_row_1010 | ESI 2 | ESI 3 | vomiting |
| ktas_row_1014 | ESI 2 | ESI 3 | dizziness |
| ktas_row_1075 | ESI 1 | ESI 2 | mental change |
| ktas_row_1134 | ESI 1 | ESI 2 | mental change |
| ktas_row_1173 | ESI 1 | ESI 2 | acute dyspnea |
| ktas_row_1187 | ESI 2 | ESI 3 | ?? ??? |
| ktas_row_1194 | ESI 1 | ESI 2 | mental change |
