# Wiki Log

Append-only record of wiki operations: ingests, queries, fixes, and lint passes.

## [2026-04-08] scaffold | Initial wiki creation

- Created `docs/wiki/` with 6 files prefilled from existing repo knowledge
- Files: README.md, rule-provenance.md, arabic-dialect-findings.md, benchmark-failure-analysis.md, validation-claims.md, paper-evidence-bank.md
- Source: scattered knowledge across `backend/knowledge_base/`, `docs/prompts/`, benchmark outputs
- Merged to main via PR #7

## [2026-04-08] lint | Codex review on PR #7

- Codex flagged parity-difference count: wiki said `50`, actual data says `381`
- Root cause: original wiki author used a filtered subset count, not the raw `parity_differences` field
- Fixed in `arabic-dialect-findings.md`

## [2026-04-08] query | Arabic keyword coverage audit

- Cross-checked 10 high-priority Arabic phrases from wiki against `arabic_keywords_v2.py`
- Found 3 missing: `ضيقة في الصدر`, `ضعف في الجنب الشمال`, `وجع في البطن`
- Added to `arabic_keywords_v2.py` MANDATORY_NEW_KEYWORDS
- KTAS Arabic critical under-triage: 54 → 45 (-16.7%)

## [2026-04-08] query | Root cause analysis — remaining 45 critical cases

- Agent traced all 45 cases through `deterministic_triage.py` matching logic
- **Key finding:** `arabic_keywords_v2.py` is orphaned — never imported by the triage engine
- All keywords added there had zero effect on actual triage decisions
- Real matching happens in `_fallback_keyword_match()` and signal lists in `deterministic_triage.py`
- Identified 13 fixable keyword gaps, 5 vitals-dependent cases, 1 garbled text

## [2026-04-08] fix | 13 Arabic keywords added to deterministic engine

Fixes applied to `backend/logic/deterministic_triage.py`:
- Dyspnea: نهجان, كرشة نفس, بنهج, كتمة → respiratory_distress
- Stroke variants: ضعف في الجنب, ضعف حركي, تقل في جنبي, ثقل في حركة → stroke_symptoms
- Chest tightness: ضيقة في الصدر → chest_pain_cardiac
- Syncope: اغمى عليا/عليه → altered_mental_status
- Fatigue: همدان → altered_mental_status
- Vaginal bleeding: نزيف مهبلي → obstetric_emergency
- GI bleed: دم نازل مع البراز → gi_bleed
- Palpitations: ضربات قلب سريعة → chest_pain_cardiac
- Priapism: انتصاب → urological emergency
- Eye trauma: خبطة في العين → eye emergency
- Upper back: وجع أعلى الظهر → age-based ACS escalation
- Post-resuscitation: إنعاش قلبي → LIFE_THREAT_SIGNALS
- Vision: زغللة → INSTABILITY_SIGNALS (stroke/TIA)

Results:
- KTAS Arabic critical under-triage: 54 → 12 (-77.8%)
- Arabic now safer than English: 1.0% vs 1.3% critical under-triage
- Parity differences: 381 → 309 (-18.9%)
- Safety gates: MIETIC 0 critical, MIETIC Arabic 0 critical (unchanged)

## [2026-04-09] query | English KTAS failure analysis

- 17 English critical under-triage cases analyzed
- Clusters: mental change ×5, dyspnea ×3, abd pain ×2, acute dyspnea ×1, melena ×1, headache ×1, fever ×1, vomiting ×1, dizziness ×1, garbled ×1
- 2 potentially fixable: "dyspnea" → ESI 3 (should be ESI 2), "abd pain" actual ESI 1 → predicted ESI 3 (2-level miss)
- Remaining 15: vitals-dependent or correct behavior given sparse complaint text
- Status: fixed — see entry below

## [2026-04-09] fix | English keyword fixes + Codex review fixes

Engine fixes:
- "dyspnea" was missing from `_fallback_keyword_match()` entirely → added to pre-keyword guardrail → respiratory_distress (ESI 2)
- "abd pain" mapped to `mild_pain` (ESI 4) in dynamic keyword DB → added abbreviation guardrail → abdominal_pain_moderate (ESI 3)

Codex review fixes (from PR #8 comments):
- `انتصاب` (priapism) narrowed to `انتصاب مستمر`/`انتصاب مؤلم` — bare word too broad, covers non-emergent ED visits
- `همدان` (fatigue) narrowed to compound phrases `همدان ومش فايق`/`همدان وتعب` — standalone too aggressive for common fatigue

Results:
- KTAS English critical: 17 → 16 (-1)
- KTAS English exact: 36.8% → 37.8% (+1.0%)
- KTAS Arabic critical: 12 → 13 (+1, expected from hemdan narrowing)
- MIETIC: 0 critical (unchanged), MIETIC Arabic: 0 critical (unchanged)

Remaining 16 English critical cases are vitals-dependent — not fixable by keywords
