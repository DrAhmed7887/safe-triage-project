# Arabic Dialect Findings

This file is the intake funnel for Arabic phrase discovery and parity work.

## Current state

Current keyword snapshot from code:
- total Arabic keyword entries: `2,101`
- base entries: `1,541`
- net-new expansion entries: `560`
- code source: `backend/arabic_keywords_v2.py`

Historical counts already present elsewhere in the repo:
- `1,453` in `docs/SAFE_Triage_Academic_Documentation.md`
- `1,858` in `README.md` and pitch-facing docs
- `2,101` in the current code snapshot

Action:
- standardize one thesis-facing number before final submission
- when using a number in slides or paper text, cite the snapshot source explicitly

## Source artifacts for Arabic work

- keyword registry: `backend/arabic_keywords_v2.py`
- keyword generation helper: `backend/tools/generate_arabic_keywords.py`
- benchmark repair prompt: `docs/prompts/arabic-dialect-expansion.md`
- Arabic MIETIC mirror benchmark: `backend/benchmarks/outputs/mietic_ar/summary.json`
- KTAS Arabic benchmark: `backend/benchmarks/outputs/ktas_arabic/arabic_summary.json`

## High-priority phrase clusters from KTAS Arabic critical under-triage

These are the best current intake candidates because they recur in actual benchmark misses.

| Count | Arabic phrase | Likely intent | Target bucket |
| --- | --- | --- | --- |
| 7 | `نهجان / كرشة نفس` | dyspnea / respiratory distress | `A1` |
| 3 | `دوخة` | dizziness or presyncope, often under-contextualized | `A1` or `C1` |
| 3 | `حالة بعد إنعاش قلبي` | post-resuscitation / very high acuity | `S1` or `A1` |
| 2 | `وجع في البطن` | abdominal pain | `A1` |
| 2 | `تقل في جنبي اليمين` | right flank or RUQ pain | `A1` |
| 2 | `سخونية` | fever, often too generic without context | `C1` |
| 2 | `ضيقة في الصدر كله` | diffuse chest discomfort | `A2` |
| 2 | `نزيف مهبلي` | vaginal bleeding | `A1` |
| 2 | `همدان وتعب عام` | fatigue / weakness / possible AMS proxy | `A1` or `P1` |
| 2 | `ضعف في الجنب الشمال` | unilateral weakness | `A1` |
| 2 | `وجع أعلى الظهر` | upper back pain, possible atypical ACS overlap | `A1` or `C1` |
| 2 | `أغمى عليا` | syncope | `A2` |

## Arabic-versus-English parity drift

Current KTAS Arabic artifact:
- parity-difference count: `50`
- source: `backend/benchmarks/outputs/ktas_arabic/arabic_summary.json`

Representative parity drift examples:
- `مع وجع أو ضيقة في الصدر` -> Arabic ESI `4`, English ESI `2`
- `أغمى عليا` -> Arabic ESI `3`, English ESI `2`
- `ضعف حركي في الجنب اليمين` -> Arabic ESI `3`, English ESI `2`
- `وجع حاد في فم المعدة` -> Arabic ESI `4`, English ESI `3`
- `نهجان / كرشة نفس` -> Arabic ESI `3`, English ESI `2`

Interpretation:
- some Arabic phrases are still too colloquial to map cleanly into the existing English-oriented complaint buckets
- some misses are true coverage gaps
- some are evidence that English rules are also too weak, but the Arabic version falls farther behind

## Findings already captured elsewhere and worth preserving

From `docs/prompts/arabic-dialect-expansion.md`:
- Arabic negation matters, especially patterns like `بينفي`, `مفيش`, `من غير`, `مش عنده`, `مش عندها`
- abdominal pain phrases such as `وجع أسفل البطن` should not be lost to generic assessment buckets
- open-fracture phrases should be aligned with English logic rather than over-escalated inconsistently

## Working rules for new Arabic additions

- prefer Egyptian colloquial phrasing over MSA when the goal is patient-speech coverage
- add the phrase only after identifying the intended category and safety consequence
- if a phrase implies denial, do not add it blindly as a positive keyword
- when possible, capture both patient speech and family speech variants
- any addition that changes high-acuity behavior should trigger MIETIC, MIETIC Arabic, and KTAS rechecks

## Intake template

Use this format when adding a new finding:

### Phrase
- Arabic text:
- Literal English gloss:
- Dialect region or style:
- Dataset or case id:
- Expected category:
- Predicted category:
- Failure bucket:
- Candidate fix:
- Safety gates to rerun:
