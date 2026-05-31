# Arabic Egyptian Dialect Expansion — Fix 4 Remaining MIETIC Mismatches

## Goal
Make the Arabic MIETIC benchmark produce IDENTICAL ESI levels to the English benchmark for all 36 cases. Currently 32/36 match. 4 remain.

## How to Run the Benchmark
```bash
cd /Users/ahmedzayed/Projects/safe-triage-project/backend
.venv/bin/python -u -c "
import sys, os
os.environ['DISABLE_RAG'] = 'true'
sys.path.insert(0, '.')
from benchmarks.mietic_arabic_benchmark import load_arabic_fixture, merge_arabic_cases, run_arabic_predictions
from benchmarks.mietic_loader import load_mietic_validated
from benchmarks.mietic_benchmark import build_patient_input
from benchmarks.metrics import compute_metrics
from logic.deterministic_triage import DeterministicTriageEngine

fixture_meta, fixture_cases = load_arabic_fixture('benchmarks/mietic_arabic_fixture.json')
english_cases = sorted(load_mietic_validated(retain_only=True), key=lambda c: c.stay_id)
ar_cases, _ = merge_arabic_cases(english_cases, fixture_cases)
engine = DeterministicTriageEngine()

for en_case, ar_case in zip(english_cases, ar_cases):
    en_p = build_patient_input(en_case)
    en_r = engine.evaluate(en_p)
    en_esi = int(getattr(en_r.level, 'value', en_r.level))
    ar_p = build_patient_input(ar_case)
    ar_r = engine.evaluate(ar_p)
    ar_esi = int(getattr(ar_r.level, 'value', ar_r.level))
    if en_esi != ar_esi:
        print(f'MISMATCH stay_{en_case.stay_id}: actual={en_case.acuity} EN={en_esi} AR={ar_esi}')
        print(f'  EN: {en_r.reasoning_en[:3]}')
        print(f'  AR: {ar_r.reasoning_en[:3]}')
"
```

## Also Run Regression Checks After Every Fix
```bash
# English MIETIC (must stay 35/36 exact = 97.2%, 0/36 critical under-triage; report Wilson CIs)
.venv/bin/python -m benchmarks.mietic_benchmark 2>&1 | grep -E "Exact|Critical|SAFETY"

# KTAS External (must stay 0% ESI-1 missed)
.venv/bin/python -m benchmarks.ktas_benchmark --data-path ../data/ktas/data.csv 2>&1 | grep -E "Exact|Critical"
```

## The 4 Remaining Mismatches

### Mismatch 1: stay_30010910 — Rectal Abscess (EN=3, AR=2)
**Problem**: Arabic text contains "بينفي أي سخونية" (denies any fever) but "سخونية" substring matches as a fever keyword, triggering "High Fever + Toxic Appearance" → ESI 2.
**Root cause**: The keyword DB and INSTABILITY_SIGNALS contain "سخونية" as a fever signal. But this patient DENIES fever. Need Arabic negation detection.
**Arabic text**: "...بس بينفي أي سخونية، رعشة، إفرازات، إسهال، أو دم في البراز..."
**Fix approach**: Add Arabic negation phrases to skip fever when preceded by "بينفي" (denies), "مفيش" (no), "من غير" (without). Check:
- `INSTABILITY_SIGNALS` in `deterministic_triage.py` — "سخونية" was recently added
- `keywords_db.json` — "سخونية" is in `fever_with_symptoms`
- The dynamic keyword DB search at line ~2556 runs BEFORE negation checks
**Key negation patterns in Egyptian Arabic**:
- "بينفي" = denies
- "بتنفي" = she denies
- "مفيش" = there is no
- "من غير" = without
- "مش عنده/عندها" = doesn't have

### Mismatch 2: stay_30030554 — Wrist Pain (EN=4, AR=3)
**Problem**: Both EN and AR get category "Mild-Moderate Pain" but AR gets ESI 3 while EN gets ESI 4. AR reasoning shows "Severe pain" modifier pushing it up.
**Root cause**: The pain score from the English case vitals (which are shared between EN/AR) may differ in how it's processed. OR the Arabic text "وبتوصفه 8 من 10" (describing pain as 8/10) triggers a severe pain path that the English short complaint "R Wrist pain" doesn't.
**Arabic text**: "...وجع في رسغ إيديها اليمين، وبتوصفه 8 من 10..."
**Fix approach**: Check if the Arabic full-text path extracts a different pain score vs the English short-complaint path. The `build_patient_input` in `mietic_benchmark.py` uses `case.pain` for pain score — both EN and AR share the same vitals, so the issue is likely the text-based pain detection override. Check the pain extraction logic.

### Mismatch 3: stay_30047441 — Lower Abdominal Pain (EN=3, AR=4)
**Problem**: EN gets "Moderate Abdominal Pain" category (ESI 3, multiple resources). AR gets "Requires Clinical Assessment" (generic, ESI 4, one resource).
**Root cause**: English complaint "Lower abdominal pain" matches the abdominal pain keywords. Arabic "وجع أسفل البطن" doesn't match.
**Arabic text**: "...بتشتكي من وجع أسفل البطن شدته 7 من 10..."
**Fix approach**: Add "وجع أسفل البطن", "وجع في البطن", "ألم في البطن", "وجع بطن" to abdominal pain Arabic keywords. Check:
- `level3_keywords` in `deterministic_triage.py` — look for abdominal pain categories
- `keyword_database.py` — check `abdominal_pain_moderate` keywords
- `keywords_db.json` — check abdominal pain level 3 keywords
- `ABDOMINAL_SIGNALS` in `esi_v5_engine.py`

### Mismatch 4: stay_30134741 — Open Fracture (EN=2, AR=1)
**Problem**: EN gets "Fracture with Deformity" (ESI 2). AR gets "Severe Trauma" (ESI 1) due to "كسر مفتوح" (open fracture) being in LIFE_THREAT_SIGNALS.
**Root cause**: "كسر مفتوح" was added to LIFE_THREAT_SIGNALS (ESI 1 path) but in the English path, "open fracture" is only in DEFINITIVE_ESI2_SIGNALS (ESI 2 path).
**Arabic text**: "...كسر مفتوح في القصبة والشظية..."
**Fix approach**: Remove "كسر مفتوح" from LIFE_THREAT_SIGNALS. It should only be in INSTABILITY_SIGNALS and DEFINITIVE_ESI2_SIGNALS (ESI 2 path), matching the English behavior. Check line ~480 in `deterministic_triage.py`.

## Key Files to Edit
1. `backend/logic/deterministic_triage.py` — main engine (LIFE_THREAT_SIGNALS, INSTABILITY_SIGNALS, level3_keywords, pain logic)
2. `backend/logic/keywords_db.json` — dynamic keyword database
3. `backend/logic/keyword_database.py` — default keyword definitions
4. `backend/logic/esi_v5_engine.py` — signal sets (secondary)

## Rules
- Do NOT break English MIETIC (must stay 35/36 exact = 97.2% and 0/36 critical under-triage; report Wilson CIs from `scripts/wilson_ci.py`)
- Do NOT break KTAS External (must stay 0% ESI-1 missed)
- Only ADD Arabic keywords or fix Arabic-specific issues — don't change English logic
- Test after EVERY change: run the benchmark script above
- Egyptian colloquial Arabic (عامية مصرية), NOT Modern Standard Arabic

## Use Gemini CLI for Arabic Keyword Research
Run `gemini` in the terminal to get Egyptian Arabic medical synonyms:
```
gemini "List all Egyptian colloquial Arabic ways to say 'abdominal pain' in an ED setting. Include: وجع بطن، ألم في البطن, and any slang/dialect variants. Format as a Python list."
```
```
gemini "In Egyptian Arabic medical speech, what are the negation patterns for denying symptoms? E.g. 'بينفي سخونية' means 'denies fever'. List all patterns with examples."
```
