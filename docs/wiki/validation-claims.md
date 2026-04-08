# Validation Claims

This file defines which claims are safe to use in the thesis, slides, demos, and judge conversations.

## Safe claims to use

- SAFE-Triage follows the architecture: `AI Extracts -> Rules Decide -> Humans Confirm`.
- The deterministic rules engine is the final authority for live triage decisions.
- MIETIC primary benchmark performance is `35/36 exact`, `36/36 within-one`, and `0 critical under-triage`.
- The Arabic MIETIC mirror currently matches the same safety profile: `35/36 exact`, `36/36 within-one`, and `0 critical under-triage`.
- The system has a meaningful Arabic dialect differentiation story because the project explicitly targets Egyptian colloquial complaint language, not only formal Arabic.
- KTAS can be presented as an external generalizability benchmark, with clear caveats that it is a cross-protocol comparison.
- NHAMCS can be presented as a large-scale stress test with sparse complaint labels and cross-system mismatch, not as the primary validation basis.

## Claims that need careful wording

- Arabic keyword count
  Use only with a snapshot reference. Current code says `2,101`. Older docs say `1,858` or `1,453`.

- "Arabic parity"
  Safe for MIETIC mirror results. Not safe as a blanket statement across all datasets because KTAS Arabic still shows meaningful drift.

- "External validation"
  Safe if phrased as "external signal" or "cross-national stress test". Avoid implying KTAS is directly equivalent to ESI.

- "Safer than nurses"
  Only use when the exact comparator, dataset, and scope are explicit. Do not generalize beyond the benchmark used.

## Claims to avoid or rewrite before submission

- Avoid any wording that implies the AI model itself decides acuity.
- Avoid any global claim that all benchmarks had `0` missed ESI-1 cases unless the dataset scope is explicitly limited.
- Avoid mixing ESI `v4` and `v5` in outward-facing materials without resolving which one the active system claims to implement.
- Avoid citing a single Arabic keyword count across all materials until the snapshot is standardized.

## Known wording drift to fix

### Arabic keyword count drift
- `docs/SAFE_Triage_Academic_Documentation.md` says `1,453`
- `README.md` says `1,858`
- `backend/arabic_keywords_v2.py` currently yields `2,101`

Recommended thesis wording:
- "The offline Arabic lexicon contained 2,101 keyword entries in the April 2026 code snapshot, including 560 net-new expansion terms over the 1,541-entry base registry."

### Benchmark safety-summary drift
`docs/VALIDATION_REPORT.md` has a strong summary section that should not be quoted blindly without checking its dataset scope against NHAMCS.

Recommended safe wording:
- "The project achieved zero critical under-triage on the primary expert-validated MIETIC benchmark and its Arabic mirror. External datasets are reported separately as stress tests and cross-protocol evaluations."

### Protocol-version drift
Some older materials still say ESI `v4`, while current architecture files and recent docs emphasize ESI `v5`.

Recommended action:
- standardize protocol wording across README, thesis draft, and slides before the final paper build

## Evidence pointers

- architecture and safety principle: `backend/main.py`, `backend/logic/deterministic_triage.py`, `backend/logic/esi_v5_engine.py`
- benchmark numbers: `backend/benchmarks/outputs/*/summary.json`
- validation narrative: `docs/VALIDATION_REPORT.md`
- thesis narrative draft: `docs/SAFE_Triage_Academic_Documentation.md`
