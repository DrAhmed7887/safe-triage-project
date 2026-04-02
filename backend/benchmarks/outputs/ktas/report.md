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
- **Timestamp**: 20260401T233334Z

## Summary Metrics

| Metric | Value |
|--------|-------|
| Total cases | 1262 |
| Exact ESI match | 477 (37.8%) |
| Within-one-level | 1042 (82.6%) |
| Under-triage (all) | 136 (10.8%) |
| Over-triage (all) | 649 (51.4%) |
| **Critical under-triage** | **37 (2.9%)** |

> SAFETY GATE: **FAILED** (37 critical under-triage cases)

## Per-Class Recall

| ESI Level | Recall | Correct / Total |
|-----------|--------|-----------------|
| ESI 1 | 26.9% | 7 / 26 |
| ESI 2 | 78.5% | 172 / 219 |
| ESI 3 | 41.3% | 201 / 487 |
| ESI 4 | 21.3% | 97 / 455 |
| ESI 5 | 0.0% | 0 / 75 |

## Confusion Matrix

Rows = Actual ESI, Columns = Predicted ESI

| | Pred 1 | Pred 2 | Pred 3 | Pred 4 | Pred 5 |
|---|---|---|---|---|---|
| **Actual 1** | 7 | 19 | 0 | 0 | 0 |
| **Actual 2** | 29 | 172 | 17 | 1 | 0 |
| **Actual 3** | 10 | 177 | 201 | 99 | 0 |
| **Actual 4** | 0 | 154 | 204 | 97 | 0 |
| **Actual 5** | 0 | 19 | 36 | 20 | 0 |

## Critical Under-Triage Cases

| Case ID | Actual | Predicted | Complaint |
|---------|--------|-----------|-----------|
| ktas_row_61 | ESI 2 | ESI 3 | abd pain |
| ktas_row_119 | ESI 2 | ESI 3 | headache |
| ktas_row_123 | ESI 1 | ESI 2 | dyspnea |
| ktas_row_132 | ESI 2 | ESI 3 | fever |
| ktas_row_152 | ESI 1 | ESI 2 | mental change |
| ktas_row_157 | ESI 1 | ESI 2 | Motor weakness |
| ktas_row_158 | ESI 2 | ESI 3 | fever |
| ktas_row_163 | ESI 1 | ESI 2 | melena |
| ktas_row_166 | ESI 1 | ESI 2 | dyspnea |
| ktas_row_169 | ESI 2 | ESI 3 | Amnesia |
| ktas_row_217 | ESI 1 | ESI 2 | mental change |
| ktas_row_382 | ESI 2 | ESI 3 | dyspnea |
| ktas_row_407 | ESI 2 | ESI 3 | dyspnea |
| ktas_row_409 | ESI 2 | ESI 3 | general weakness |
| ktas_row_500 | ESI 2 | ESI 3 | dizziness |
| ktas_row_694 | ESI 2 | ESI 4 | upper back pain |
| ktas_row_707 | ESI 1 | ESI 2 | abd pain |
| ktas_row_713 | ESI 2 | ESI 3 | epigastric pain |
| ktas_row_757 | ESI 2 | ESI 3 | upper back pain |
| ktas_row_806 | ESI 1 | ESI 2 | mental change |
| ktas_row_822 | ESI 1 | ESI 2 | mental change |
| ktas_row_889 | ESI 1 | ESI 2 | seizure |
| ktas_row_980 | ESI 2 | ESI 3 | Abnormality, Visual Acuity |
| ktas_row_1008 | ESI 1 | ESI 2 | post-CPR state |
| ktas_row_1010 | ESI 2 | ESI 3 | vomiting |
| ktas_row_1011 | ESI 1 | ESI 2 | post-CPR state |
| ktas_row_1014 | ESI 2 | ESI 3 | dizziness |
| ktas_row_1041 | ESI 1 | ESI 2 | arrest |
| ktas_row_1075 | ESI 1 | ESI 2 | mental change |
| ktas_row_1080 | ESI 1 | ESI 2 | altered mental change |
| ktas_row_1090 | ESI 2 | ESI 3 | general weakness |
| ktas_row_1097 | ESI 2 | ESI 3 | DZ - Dizziness |
| ktas_row_1134 | ESI 1 | ESI 2 | mental change |
| ktas_row_1145 | ESI 1 | ESI 2 | post-CPR state |
| ktas_row_1173 | ESI 1 | ESI 2 | acute dyspnea |
| ktas_row_1187 | ESI 2 | ESI 3 | ?? ??? |
| ktas_row_1194 | ESI 1 | ESI 2 | mental change |
