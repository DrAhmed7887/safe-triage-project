# SAFE-Triage MIMIC Replay Metrics

Source summary: `backend/tests/benchmark_outputs/mimic_replay_hsil-clean-rerun_20260330_192956.summary.json`

## Core Metrics

| Metric | Value |
| --- | --- |
| Usable MIMIC-IV-ED rows | 418,084 |
| Unique complaint buckets | 20,065 |
| Sample selected | 1,000 |
| Valid predictions | 1,000 |
| Failed predictions | 0 |
| Exact-match accuracy | 28.40% |
| Within-one-level accuracy | 73.10% |
| Over-triage rate | 40.90% |
| Under-triage rate | 30.70% |
| Critical under-triage rate | 25.60% |
| Critical under-triage count | 256 |

## Sample Composition

| ESI Level | Target | Selected |
| --- | --- | --- |
| 1 | 200 | 200 |
| 2 | 200 | 200 |
| 3 | 200 | 200 |
| 4 | 200 | 200 |
| 5 | 200 | 200 |

## Top Complaint Buckets In Sample

| Complaint bucket | Count |
| --- | --- |
| `abd pain` | 38 |
| `dyspnea` | 32 |
| `chest pain` | 29 |
| `fall` | 29 |
| `suture removal` | 26 |
| `back pain` | 23 |
| `mvc` | 19 |
| `altered mental status` | 19 |
| `med refill` | 19 |
| `dizziness` | 14 |
| `headache` | 13 |
| `n v` | 11 |
| `etoh` | 11 |
| `dental pain` | 10 |
| `sore throat` | 9 |

## Top Miss Buckets

| Complaint bucket | Count |
| --- | --- |
| `abd pain` | 31 |
| `suture removal` | 26 |
| `fall` | 25 |
| `med refill` | 19 |
| `dyspnea` | 18 |
| `back pain` | 18 |
| `altered mental status` | 17 |
| `mvc` | 13 |
| `headache` | 12 |
| `dental pain` | 10 |
| `dizziness` | 9 |
| `chest pain` | 9 |
| `wound eval` | 9 |
| `l foot pain` | 8 |
| `lower back pain` | 8 |

## Notes

- Replay used complaint text and triage vitals from MIMIC-IV-ED.
- Age/gender were neutral placeholders because the local ED extract does not include demographics.
- This is suitable for retrospective replay benchmarking, not for claiming prospective clinical validation.

## Artifacts

- Sample CSV: `/Users/ahmedzayed/Projects/safe-triage-project/backend/tests/benchmark_outputs/mimic_replay_hsil-clean-rerun_20260330_192956.sample.csv`
- Predictions CSV: `/Users/ahmedzayed/Projects/safe-triage-project/backend/tests/benchmark_outputs/mimic_replay_hsil-clean-rerun_20260330_192956.predictions.csv`

## Slide-Safe One-Liner

`Retrospective replay on 1000 stratified MIMIC-IV-ED triage cases yielded 73.10% within-one-level accuracy, with 256 critical under-triage cases in this run.`
