# SAFE Engine vs Korean Nurse — KTAS External Validation

## Dataset
- **Source**: Kaggle (ilkeryildiz/emergency-service-triage-application)
- **Design**: Cross-sectional retrospective, two Korean EDs
- **Gold standard**: KTAS_expert (3 triage experts consensus)
- **Total cases**: 1262
- **KTAS distribution**: {1: 26, 2: 219, 3: 487, 4: 455, 5: 75}
- **Timestamp**: 20260401T194249Z

## Head-to-Head Comparison

| Metric | SAFE Engine | Korean Nurse | Winner |
|--------|-----------|------------|--------|
| Exact match | 43.7% | 85.5% | Nurse |
| Within-one-level | 91.4% | 98.6% | Nurse |
| Under-triage | 12.4% | 10.4% | Nurse |
| Over-triage | 43.9% | 4.1% | Nurse |
| Critical under-triage | 3.9% | 3.6% | Tie |

## Per-Class Recall

| KTAS Level | SAFE Engine | Korean Nurse | Winner |
|------------|-----------|------------|--------|
| KTAS 1 | 26.9% | 57.7% | Nurse |
| KTAS 2 | 73.1% | 83.1% | Nurse |
| KTAS 3 | 47.2% | 82.1% | Nurse |
| KTAS 4 | 33.8% | 92.1% | Nurse |
| KTAS 5 | 0.0% | 84.0% | Nurse |

## SAFE Engine Confusion Matrix

Rows = Actual KTAS, Columns = Predicted ESI

| | Pred 1 | Pred 2 | Pred 3 | Pred 4 | Pred 5 |
|---|---|---|---|---|---|
| **KTAS 1** | 7 | 15 | 3 | 1 | 0 |
| **KTAS 2** | 29 | 160 | 24 | 6 | 0 |
| **KTAS 3** | 10 | 139 | 230 | 108 | 0 |
| **KTAS 4** | 0 | 36 | 265 | 154 | 0 |
| **KTAS 5** | 0 | 8 | 45 | 22 | 0 |

## Korean Nurse Confusion Matrix

Rows = Actual KTAS expert, Columns = Nurse KTAS_RN

| | Pred 1 | Pred 2 | Pred 3 | Pred 4 | Pred 5 |
|---|---|---|---|---|---|
| **KTAS 1** | 15 | 11 | 0 | 0 | 0 |
| **KTAS 2** | 3 | 182 | 27 | 6 | 1 |
| **KTAS 3** | 0 | 16 | 400 | 63 | 8 |
| **KTAS 4** | 0 | 3 | 18 | 419 | 15 |
| **KTAS 5** | 0 | 0 | 0 | 12 | 63 |
