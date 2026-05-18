# Triage engine parity tests

SAFE-Triage has two deterministic triage engines:

- **Canonical** — Python, lives in `backend/logic/deterministic_triage.py`,
  validated against MIETIC / MIETIC-Arabic / KTAS / NHAMCS. This is the
  source of truth and what the production `/triage` endpoint uses.
- **Offline fallback** — JS, lives in
  `frontend/src/lib/triageEngineOfflineFallback.js`, used by the browser
  only when the backend is unreachable (offline iPad, network blip).

The fallback **is not** benchmark-validated and **is not** a competing
implementation. It is a degraded-mode safety net.

To prevent silent drift between the two engines on safety-critical
cases, a small parity harness shares a fixture file between them.

## Parity rule

For every case in `tests/parity/critical_cases.json`:

> The JS fallback may produce a more acute level than the Python engine
> (over-triage is acceptable), but it must **never** produce a less
> acute level (under-triage is a parity failure).

Numerically, ESI 1 is the most acute and ESI 5 is the least acute, so:

```
js_level <= python_level + tolerance        (tolerance = 0 by default)
```

Each fixture may also declare `expected_max_level` — the highest
numerical level that case may show under either engine. This is the
absolute safety floor a chest-pain case must respect.

## How to run

```bash
# Python regression suite for Arabic chest-pain variants.
python -m pytest backend/tests/test_arabic_chest_pain.py -v

# Run the canonical engine over the shared fixtures (writes
# tests/parity/python_results.json + prints a per-case table).
python tests/parity/run_python_engine.py

# Run the JS fallback over the same fixtures and compare under-triage
# parity against the Python output (exits non-zero on parity failure).
node tests/parity/run_js_engine.mjs --compare

# JS-only smoke test for the offline engine.
node frontend/src/lib/triageEngineOfflineFallback.smoke.mjs
```

CI also runs these commands automatically on every PR that touches the
engine, the fallback, the fixtures, or this workflow — see
`.github/workflows/triage-parity.yml`.

## Safety rationale for chest-pain cases

Chest pain in an Egyptian ED triage app must over-triage by default.
Both engines route the following Arabic phrasings to a cardiac L2
pathway (either `chest_pain_cardiac` or `silent_mi`, both clinically
equivalent at the safety-floor level):

- _ألم في الصدر_ / _ألم شديد في الصدر_ / _ألم حاد في الصدر_
- _وجع في الصدر_
- _ضغط في الصدر_ / _ضغط على الصدر_
- _ضيق في الصدر_ / _ضيقة في الصدر_
- _حرقان في الصدر_
- Possessive variants: _في صدري_ / _في صدره_ / _في صدرها_
- Word-order variants where the pain-word and chest-word are not adjacent

The `silent_mi` category is in `_ESI2_MANDATORY_CATEGORIES` so that the
severity-ceiling guardrail cannot demote it below L2 — atypical ACS by
definition lacks the overt instability signals the ceiling looks for.
