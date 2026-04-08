# SAFE-Triage Working Wiki

This folder is a lightweight knowledge hub for the SAFE-Triage thesis and development loop.

Purpose:
- consolidate benchmark findings, rule rationale, Arabic dialect discoveries, and thesis-safe claims in one place
- speed up the fix loop: benchmark failure -> categorize -> patch -> rerun safety gates
- keep high-signal context explicit and navigable without adding runtime complexity

Non-goals:
- this is not part of the runtime triage path
- this is not an automated agent-maintained system
- this does not replace git history

Source-of-truth hierarchy:
1. Runtime behavior lives in code under `backend/`
2. Benchmark truth lives in `backend/benchmarks/outputs/`
3. This wiki explains why the system behaves the way it does and what to fix next

Files in this folder:
- `rule-provenance.md` — why high-impact rules and safety floors exist
- `arabic-dialect-findings.md` — Arabic phrase coverage, parity gaps, and intake queue
- `benchmark-failure-analysis.md` — clustered benchmark failures and next-fix priorities
- `validation-claims.md` — thesis-safe claims, claim wording, and claims to avoid
- `paper-evidence-bank.md` — where to find evidence for paper sections, slides, and defense answers

Recommended failure taxonomy:
- `A1` Arabic phrase coverage gap
- `A2` Arabic parity drift versus English
- `P1` AI extraction prompt/classification miss
- `R1` resource estimation miss
- `S1` safety floor or escalation threshold miss
- `D1` dataset label mismatch or low-context benchmark artifact
- `C1` complaint ambiguity or missing context

Recommended update loop:
1. Reproduce the failure on a benchmark or scenario test.
2. Add one short note to the relevant wiki file using the taxonomy above.
3. Patch the smallest likely fix in rules, keywords, prompts, or tests.
4. Re-run the required safety gates.
5. If the fix changes a thesis-facing claim, update `validation-claims.md`.

Minimum safety gates after any triage logic change:
- MIETIC must remain at `35/36 exact`, `36/36 within-one`, `0 critical under-triage`
- MIETIC Arabic must preserve the same safety profile
- KTAS should not regress on ESI-1 recall or critical under-triage
- NHAMCS can be used for stress testing and clustering, but should not drive unsafe rule relaxation

Important note on claim drift:
- public-facing files in this repo currently mention multiple Arabic keyword counts: `1,453`, `1,858`, and the current code snapshot `2,101`
- before thesis submission, standardize one number and always tie it to a snapshot date and source file
