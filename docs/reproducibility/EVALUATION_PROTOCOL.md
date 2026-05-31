# SAFE-Triage Evaluation Protocol

Snapshot date: 2026-05-31
Benchmark freeze: 20260408T223413Z

## Objective

Evaluate SAFE-Triage as a research-stage clinical decision-support prototype for ESI-oriented emergency triage, with emphasis on critical under-triage avoidance and honest uncertainty reporting.

## Datasets

| Dataset | Role | N | Notes |
|---|---|---:|---|
| MIETIC English expert-validated subset | Primary target-protocol benchmark | 36 | Expert-validated ESI cases from MIETIC |
| MIETIC Arabic mirror | Translated bilingual parity benchmark | 36 | Translation of the same 36 MIETIC cases; not Arabic-native ED data |
| KTAS external dataset | Cross-protocol stress test | 1,262 | KTAS and ESI are non-equivalent protocols |
| KTAS hard-case subset | Targeted model-review characterization | 17 | Critical/borderline KTAS cases |

## Endpoints

Primary endpoint:

- Critical under-triage: reference ESI 1 or 2 assigned by SAFE-Triage to ESI 3, 4, or 5.

Secondary endpoints:

- Exact ESI agreement.
- Within-one-level agreement.
- Over-triage / safe-direction disagreement.
- Hard-case resolution or flagging for Gemma/MedGemma review layers.

## Statistical Reporting

All proportions must be reported as count/denominator, point estimate, and 95% Wilson score confidence interval.

The Wilson interval is reproduced by:

```bash
python3 scripts/wilson_ci.py
```

## Locked Results

| Metric | Count | Point estimate | 95% Wilson CI |
|---|---:|---:|---:|
| MIETIC English exact agreement | 35/36 | 97.2% | 85.8% to 99.5% |
| MIETIC English within-one | 36/36 | 100.0% | 90.4% to 100.0% |
| MIETIC English critical under-triage | 0/36 | 0.0% | 0.0% to 9.6% |
| MIETIC Arabic exact agreement | 35/36 | 97.2% | 85.8% to 99.5% |
| MIETIC Arabic within-one | 36/36 | 100.0% | 90.4% to 100.0% |
| MIETIC Arabic critical under-triage | 0/36 | 0.0% | 0.0% to 9.6% |
| KTAS exact agreement | 477/1,262 | 37.8% | 35.2% to 40.5% |
| KTAS within-one | 1,030/1,262 | 81.6% | 79.4% to 83.7% |
| KTAS critical under-triage | 16/1,262 | 1.3% | 0.8% to 2.0% |
| KTAS over-triage | 708/1,262 | 56.1% | 53.3% to 58.8% |
| Gemma 4 hard-case resolution | 6/17 | 35.3% | 17.3% to 58.7% |
| MedGemma hard-case flagging | 12/17 | 70.6% | 46.9% to 86.7% |

## Framing Constraints

- Say "exact ESI agreement," not generic "accuracy," unless the metric is explicitly defined.
- Say "critical under-triage on MIETIC was 0/36," not "never under-triages."
- Say "KTAS cross-protocol stress test," not "KTAS validation."
- Say "research-stage prototype" or "public research demonstration," not "clinically deployed."
- Say "clinician confirms every decision," not "autonomous triage."
