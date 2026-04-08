# Benchmark Failure Analysis

This file is the starting point for systematic error reduction.

## Current benchmark snapshot

| Dataset | Exact match | Within-one | Critical under-triage | Intended role |
| --- | --- | --- | --- | --- |
| MIETIC | `35/36` = `97.22%` | `36/36` = `100%` | `0` | primary expert-validated safety benchmark |
| MIETIC Arabic mirror | `35/36` = `97.22%` | `36/36` = `100%` | `0` | Arabic parity benchmark |
| KTAS external | `36.77%` | `81.46%` | `17` | external generalizability signal |
| KTAS Arabic | `36.45%` | `82.09%` | `12` | Arabic parity and phrase-coverage stress test |
| NHAMCS | `39.96%` | `83.74%` | `831` | large low-context stress test, not primary validation |

Primary source files:
- `backend/benchmarks/outputs/mietic/summary.json`
- `backend/benchmarks/outputs/mietic_ar/summary.json`
- `backend/benchmarks/outputs/ktas/summary.json`
- `backend/benchmarks/outputs/ktas_arabic/arabic_summary.json`
- `backend/benchmarks/outputs/nhamcs/summary.json`

## NHAMCS hotspots

Top recurring chief complaints among NHAMCS critical under-triage cases:

| Count | Complaint text |
| --- | --- |
| 40 | `Oth symptoms/problems relat to psycho` |
| 16 | `Shortness of breath` |
| 13 | `Abdominal pain, cramps, spasms, NOS` |
| 12 | `General psychiatric or psychological` |
| 8 | `Laceration/cut of upper extremity` |
| 5 | `Vomiting` |
| 5 | `Leg pain, ache, soreness, discomfort` |
| 5 | `Vertigo - dizziness` |
| 5 | `Side pain, flank pain` |
| 4 | `Functional psychoses` |
| 4 | `Behavioral disturbances` |
| 4 | `Chest pain` |

Critical under-triage pair counts:
- actual `2` -> predicted `3`: `479`
- actual `2` -> predicted `4`: `185`
- actual `1` -> predicted `2`: `72`
- actual `1` -> predicted `3`: `59`
- actual `1` -> predicted `4`: `36`

Working interpretation:
- NHAMCS is heavily dominated by sparse complaint labels and cross-system acuity differences
- the fastest wins are likely to come from complaint-cluster fixes rather than single-case tinkering
- psychiatric and respiratory clusters look especially important

## KTAS deterministic hotspots

Recurring critical under-triage complaints in the English KTAS benchmark:
- `dyspnea`
- `mental change`
- `abd pain`
- `headache`
- `fever`
- `melena`
- `dizziness`
- `vomiting`

These complaints suggest four recurring failure families:
- high-risk respiratory complaints that do not cross an escalation threshold
- altered mental status or stroke-adjacent phrasing that is still too weakly captured
- GI presentations that may hide bleed, sepsis, or atypical ACS
- generic symptom labels with insufficient context for exact ESI prediction

## KTAS Arabic hotspots

The Arabic benchmark is not only a translation stress test. It is a phrase-coverage audit.

Recurring Arabic critical under-triage clusters:
- `نهجان / كرشة نفس`
- `دوخة`
- `ضيقة في الصدر كله`
- `ضعف في الجنب الشمال`
- `أغمى عليا`
- `نزيف مهبلي`
- `همدان وتعب عام`

This strongly suggests that Arabic parity work should focus on:
- dyspnea wording
- unilateral weakness and stroke language
- chest discomfort variants
- syncope and presyncope phrasing
- fatigue or weakness phrases that may imply higher-risk contexts

## Root-cause buckets to use going forward

| Bucket | Meaning | Likely fix surface |
| --- | --- | --- |
| `A1` | Arabic phrase missing or weakly mapped | `arabic_keywords_v2.py`, `generate_arabic_keywords.py`, parity fixtures |
| `A2` | Arabic and English disagree for the same concept | keyword harmonization, parity audit, sometimes rule alignment |
| `P1` | AI extraction misclassification | `backend/ai_service.py` prompt or constrained few-shot examples |
| `R1` | resource estimation issue | resource estimator or category-to-workup mapping |
| `S1` | safety floor or escalation miss | deterministic rule or threshold review |
| `D1` | benchmark label mismatch or low-context artifact | document, do not overfit blindly |
| `C1` | complaint too ambiguous without more context | document as limitation or add context-sensitive rule if justified |

## Suggested next experiments

1. NHAMCS clustering pass
- group the top `100` critical under-triage cases into the taxonomy above
- stop after the first `5` root causes if they already explain most misses

2. KTAS Arabic parity pass
- target the top `10` recurring Arabic phrases from `arabic-dialect-findings.md`
- measure whether parity-difference count drops from `50`

3. Prompt-improvement pass
- create a small table of `P1` extraction misses with `got`, `should be`, and `why`
- use it to tune the constrained extraction prompt in `backend/ai_service.py`

## Guardrail

Do not optimize NHAMCS by weakening safety floors.

If a proposed fix lowers acuity in a way that improves exact match on NHAMCS, it should be treated as suspect until it passes MIETIC and KTAS safety checks.
