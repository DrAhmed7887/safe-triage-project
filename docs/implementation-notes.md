# SAFE-Triage Hospital Lite — Implementation Notes

Running audit trail for non-obvious decisions taken while building Hospital
Lite mode. Aimed at: hospital stakeholders, the thesis committee, future
maintainers, and code reviewers (incl. automated reviewers like Codex). Tiny
mechanical edits are out of scope; this file is for things where the *why*
matters and would not be obvious from the diff alone.

Entries are append-only and reverse-chronological inside each section, so the
latest thinking is at the top. When a previous decision is overturned, leave
the original entry and add a follow-up rather than rewriting history.

---

## 1. Architecture decisions

### 1.1 Two triage engines (Python canonical + JS offline fallback) — 2026-05

**Decision.** Hospital Lite ships with two engines:

- **Canonical:** `backend/logic/deterministic_triage.py` (and
  `triage_engine_v2.py`, `esi_v5_engine.py`). This is what every benchmark
  (MIETIC, MIETIC-Arabic, KTAS, NHAMCS) validates and what the thesis claims
  performance against. Always wins when reachable.
- **Fallback:** `frontend/src/lib/triageEngineOfflineFallback.js`. A
  *partial* re-implementation of the safety-critical subset of the canonical
  engine, used only when `POST /triage` fails (offline iPad, network blip,
  backend unhealthy).

**Why.** Egyptian ED iPads can lose connectivity mid-shift. We refuse to
let a network outage drop the triage station to "ask the doctor"; that would
either delay care or push clinicians into ad-hoc gut-feel triage. A
deterministic JS fallback keeps the queue moving in degraded mode.

**Constraint we accept.** Maintaining two engines is a parity hazard. The
JS fallback is allowed to *over-triage* relative to Python (i.e. produce a
*more* acute ESI level) but **must never under-triage**. Under-triage is a
parity failure and a CI gate failure.

**How parity is enforced.**
- Shared fixtures: `tests/parity/critical_cases.json`.
- Python runner: `tests/parity/run_python_engine.py` →
  `python_results.json`.
- JS runner: `node tests/parity/run_js_engine.mjs --compare`. Fails the
  build if any case has `js_level > python_level` (numerically — lower ESI
  is more acute).
- Tolerance is `0` (strict).
- Smoke tests: `frontend/src/lib/triageEngineOfflineFallback.smoke.mjs`
  exercises individual safety floors with named assertions
  (`floors: ['hypotension']`, `floors: ['sepsis_fever_tachycardia']`, etc.)
  so a regression names the broken floor, not just the wrong level.

**Operational rule for the UI.** Suggestions carry
`engine_source: 'offline_js_fallback'` and the UI must display an explicit
"offline fallback" warning to the clinician when this source is set. The
fallback never claims to be the canonical engine.

### 1.2 "AI Extracts → Rules Decide → Humans Confirm" — golden rule

The JS fallback intentionally has **no AI**. It is the *Rules* layer running
in degraded mode (`ai_used: false` is asserted in smoke tests). When the
backend is unreachable we lose the AI extraction step, so the JS fallback
falls back to keyword classification of the chief complaint. This is a
deliberate downgrade — we'd rather have a deterministic, auditable L3 than a
hallucinated L2.

---

## 2. Clinical safety assumptions

### 2.1 Over-triage is acceptable; under-triage is not — project-wide

This is the single most important rule and it drives every parity decision.
- Target: 0% critical under-triage. Non-negotiable.
- Over-triage is treated as a workflow cost, not a safety issue.
- We do **not** tune safety floor rules downward to reduce over-triage. The
  CLAUDE.md project memory makes this explicit and the team has agreed.

### 2.2 Fever + tachycardia sepsis floor in the JS fallback — 2026-05

**Codex P1 on PR #17** identified a Python ↔ JS under-triage gap:
- Complaint: `fever and chills`, HR 105, Temp 38.2.
- Python: ESI 2 via `deterministic_triage.py` "Fever + tachycardia
  (sepsis pathway)" block.
- JS pre-fix: ESI 3 (category `fever_with_symptoms` at L3, NEWS2 total 2 /
  LOW, no floor triggered).

**Fix.** Added a `sepsis_fever_tachycardia` floor in
`applyCriticalSafetyFloors`. Smallest safe mirror of the Python pathway:

```
(complaintHasFever ∈ {fever, سخونية, سخونة, حمى}  OR  temp ≥ 38.0)
  AND  HR > 100
⇒ cap level at ESI 2
```

**Notes.**
- The Python engine *also* has a "Significant fever alone (≥ 38.5)" floor
  in the same block. The Codex repro does not need it (Temp 38.2), and the
  PR is scoped narrowly to parity for this one P1. If a future Codex finding
  surfaces an under-triage case driven by the ≥ 38.5 standalone path, mirror
  it then. Don't pre-emptively port the whole block.
- We deliberately use `>` (not `≥`) for HR per the Python source, so
  HR == 100 alone does not trigger the floor. Matches Python exactly.
- Floor name (`sepsis_fever_tachycardia`) is asserted in the parity smoke
  test so a regression is named, not silent.

### 2.3 Arabic chest-pain pair-match in the JS fallback — 2026-05 (PR #17)

**Why this exists.** Real Egyptian-dialect chest-pain complaints don't use
the textbook "ألم في الصدر" form. They use possessive ("ألم في صدري"),
colloquial ("وجع في صدره", "ضيق في صدرها"), and mixed
hamza-bearing-alif variants (أ / إ / آ vs ا). The canonical Python engine
already normalised these via hamza-collapse + a pain⊕chest set product. The
JS fallback didn't, so it under-triaged real Egyptian complaints to
`unclear_needs_evaluation` (L3) while Python correctly produced L2.

**Mirror.** Ported the minimal subset: hamza-alif normalisation (أ / إ / آ
→ ا) + `_AR_PAIN_TERMS × _AR_CHEST_TERMS` co-occurrence pair-check at the
`chest_pain_cardiac` slot, ordered *after* the L1 keyword rules so a true
L1 complaint (e.g. cardiac arrest) still wins when both signals coexist.

---

## 3. Backend Python vs JS fallback — porting rules

When porting a Python safety pathway to the JS fallback, follow these in
order:

1. **Port only what's needed to close the observed gap.** Don't port the
   whole Python block "while you're there." Parity is enforced case-by-case
   via fixtures; speculative ports add maintenance burden without test
   coverage.
2. **Match Python comparison operators exactly** (`>` vs `≥`, `<` vs `≤`).
   Off-by-one boundaries are how silent under-triage sneaks in.
3. **Add the repro case to `tests/parity/critical_cases.json`** with a
   tight `expected_max_level`. The fixture is the contract.
4. **Name the floor.** Each floor gets a stable `name:` string and is
   asserted by name in `triageEngineOfflineFallback.smoke.mjs`. Future
   regressions then report the *floor* that broke, not just a wrong level.
5. **Bilingual reason strings.** Every floor records EN + AR reasons so the
   audit trail is reviewable by Arabic-speaking clinicians.
6. **Leave AI out of the fallback.** The JS engine is the *Rules* layer in
   degraded mode. Don't add even a heuristic ML model.

---

## 4. Arabic / English triage edge cases

Logged here for clinical reviewers. The full set is in
`backend/logic/deterministic_triage.py`; this section flags cases that
required *non-obvious* engineering.

- **Hamza-bearing alif** (أ / إ / آ) is collapsed to ا before
  pair-matching. Without this, `ألم في صدري` (textbook) and `الم في صدري`
  (informal typing) classify differently. Both Python and JS now normalise.
- **Possessive chest forms** (`صدري` / `صدره` / `صدرها`) — the JS
  fallback used to only recognise definite-article phrases (`في الصدر`).
  Fixed in PR #17.
- **"حرارة" (heat / fever)** — *deliberately* not in the JS fever
  trigger list. Python removed it from its substring check because it
  false-positives on Arabic *normal-temperature* reports like
  `"وحرارة 37.4 مئوية"` ("...and a temperature of 37.4 Celsius"). The
  structured `temp ≥ 38.0` check catches real fevers via the vitals path
  without the false-positive risk.

---

## 5. Why specific files were changed

### Hospital Lite scaffolding branch hygiene — 2026-05

PR #17 is explicitly scoped to Arabic chest-pain parity + JS-fallback
safety floors. The wider Hospital Lite UI scaffolding lives on a separate
branch (`hospital-lite-scaffolding`) and is **not** included in PR #17.
The Codex review and the thesis-defense story both depend on this branch
staying narrow; widening it would force a rereview of unrelated UI code.

### `frontend/src/lib/triageEngineOfflineFallback.js`

- Added Arabic pain⊕chest pair-check (PR #17 main fix).
- Added `sepsis_fever_tachycardia` floor in `applyCriticalSafetyFloors`
  (PR #17 Codex P1 follow-up, commit `b66bbc5`).
- Kept the file's degraded-mode disclaimer header intact; it tells anyone
  reading this file first that it is **not** the canonical engine. Do not
  weaken this banner.

### `tests/parity/critical_cases.json`

- Source of truth for parity. Every Codex-found gap gets a fixture here so
  CI gates against the same regression in future.
- `expected_max_level` is the absolute cap. Cases without it are allowed
  to drift up/down — used for cases where the clinical answer is genuinely
  ambiguous (e.g. mild fever, normal vitals).

### `frontend/src/lib/triageEngineOfflineFallback.smoke.mjs`

- Mirrors each new floor with a *named* assertion. Parity fixture catches
  level drift; smoke test catches floor-name drift. Both matter.

---

## 6. Tests run and failures fixed

### 2026-05, PR #17 Codex P1 (sepsis floor, commit `b66bbc5`)

Run before commit:
- `python tests/parity/run_python_engine.py` → 19/19 respect
  `expected_max_level`.
- `node tests/parity/run_js_engine.mjs --compare` → 19/19 Δ=0.
- `node frontend/src/lib/triageEngineOfflineFallback.smoke.mjs` →
  13/13 passed.
- `python -m pytest backend/tests/test_arabic_chest_pain.py
  backend/tests/test_guardrails.py
  backend/tests/test_arabic_reasoning_and_export.py` → 108/108 passed.
- `VITE_APP_MODE=hospital_lite npx vite build` → clean.

No failures encountered during this fix. The pre-fix JS run reproduced the
Codex L3 under-triage, the post-fix run produced L2.

### Earlier in PR #17 (commit `dfc5b0a`, possessive Arabic chest forms)

Failure that the fix resolved:
- Pre-fix: `node tests/parity/run_js_engine.mjs --compare` failed on
  `ألم في صدري`, `وجع في صدره`, `ضيق في صدرها` (Python L2, JS L3).
- Post-fix: all 18 parity cases Δ=0.

---

## 7. Unresolved risks before hospital testing

### High priority

- **AI extraction provider drift.** Gemini 2.5-flash on Vertex AI is the
  live primary, Gemma 4 E4B-IT is shadow/backup. We do not yet have a
  documented runbook for what happens if both providers degrade
  simultaneously (e.g. a Vertex region outage). Today the system falls
  through to the JS keyword classifier, which is a *much* coarser
  classifier than the AI extraction. This is safe (over-triages, never
  under-triages) but the UI does not currently surface "AI degraded —
  using keyword classifier" clearly enough for clinicians.
- **Budget guard interaction with parity tests.** `budget_guard.py` is set
  to auto-undeploy all Vertex AI endpoints at $950. If this trips mid-day
  during hospital testing, the system goes into JS-fallback mode for every
  request. We need a hospital-side dashboard tile that surfaces this state
  unambiguously. Today the only signal is `engine_source` in the response.
- **MIETIC Arabic coverage.** MIETIC-Arabic is 36 mirror cases. Hospital
  pilot complaints will not be drawn from this distribution. We expect to
  find new dialect edge cases in week 1 of the pilot and need a feedback
  loop (Codex-style review on every unique missed case) ready to go.

### Medium priority

- The Codex P1 fix only mirrors Python's fever+tachycardia pathway. Python
  also has:
  - "Significant fever alone (≥ 38.5)" → ESI 2.
  - "Symptomatic tachycardia (HR ≥ 110 + weakness/dizziness/syncope)" →
    ESI 2.
  - "Elderly (≥ 65) + fever + borderline hypotension (SBP ≤ 100)" → ESI 2.
  These have not been observed to cause Python↔JS divergence in our
  fixtures *yet*, but a Codex re-review may surface them. Mirror on
  evidence, not pre-emptively, per the porting rules in §3.
- **NHAMCS exact-match accuracy is 40%.** Critical under-triage on that
  dataset is 7.9%. This is much worse than MIETIC and KTAS. We have not
  decided yet whether to address this pre-pilot or treat NHAMCS as an
  out-of-distribution stress test. Decision needed before defense.
- **Pediatric coverage in JS fallback.** The pediatric modifier in the JS
  fallback escalates for `age < 5` with NEWS2 risk. Python uses `age < 3`
  for the equivalent pediatric block (`triage_engine_v2.py`). This
  divergence is deliberate (JS over-triages in this band, which is safe),
  but it should be revisited if the pilot includes pediatric ED data.

### Low priority

- The `decision_path` string in the JS fallback uses unicode arrows
  (`→`). Some legacy hospital systems we haven't tested against may not
  render these in audit-log exports. Worth a smoke check before pilot, not
  a blocker.

---

## 8. Conventions for future entries

- Date entries `YYYY-MM` and reference commits / PRs by short hash and
  number (`commit b66bbc5`, `PR #17`).
- For each new safety floor: state the trigger condition exactly, the
  level cap, the fixture that exercises it, and the floor name asserted in
  the smoke test.
- If a decision is later overturned, do *not* rewrite the earlier entry;
  append a follow-up with the new reasoning.
- This file is the audit trail. CLAUDE.md is for behaviour rules. PR
  descriptions are for *what changed*. This file is for *why*.
