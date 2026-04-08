# Rule Provenance

This file explains why the highest-impact SAFE-Triage rules exist.

Use this file when:
- writing the methods or discussion section of the thesis
- defending a rule to reviewers or judges
- deciding whether a benchmark miss should change a rule, a keyword list, or only a prompt

## Core architecture rules

| Rule or design choice | Why it exists | Evidence or rationale | Primary source files |
| --- | --- | --- | --- |
| AI extracts, rules decide, humans confirm | Keeps the safety-critical decision path deterministic and auditable | central design principle across thesis, validation report, and backend entrypoint | `backend/main.py`, `backend/logic/deterministic_triage.py`, `backend/logic/esi_v5_engine.py`, `docs/VALIDATION_REPORT.md` |
| Educational RAG is read-only | Retrieval can support explanation, not decision authority | avoids non-reproducible runtime behavior in a safety-critical workflow | `backend/educational_chat.py`, `backend/logic/deterministic_triage.py` |
| RAG context in triage result is citation-only | lets the UI show supporting protocol context without changing ESI assignment | preserves determinism while still surfacing references | `backend/logic/deterministic_triage.py` |

## Safety floors

| Safety floor | Why it exists | Notes | Primary source files |
| --- | --- | --- | --- |
| NEWS2 `>= 7` or any single parameter `= 3` -> minimum ESI 1 | captures physiological instability even when the complaint text is vague | should not be relaxed to improve benchmark exact match | `backend/knowledge_base/safe_triage_clinical_rules.txt`, `backend/knowledge_base/news2_scoring_guide.txt`, `backend/logic/deterministic_triage.py` |
| NEWS2 `>= 5` -> minimum ESI 2 | protects against under-triage in decompensating patients | key thesis safety argument | same as above |
| Chest pain any presentation -> minimum ESI 2 | prevents low-acuity assignment for potential ACS presentations | especially important for atypical ACS and sparse-text benchmarks | `backend/knowledge_base/safe_triage_clinical_rules.txt`, `backend/logic/deterministic_triage.py` |
| Stroke FAST positive -> ESI 1 or 2 | avoids missing time-sensitive stroke patterns | relevant to English and Arabic complaint variants | `backend/knowledge_base/safe_triage_clinical_rules.txt`, `backend/logic/esi_v5_engine.py`, `backend/logic/deterministic_triage.py` |
| Neonate fever -> minimum ESI 2 | pediatric sepsis safety floor | thesis-safe clinical modifier | `backend/knowledge_base/safe_triage_clinical_rules.txt`, `backend/logic/deterministic_triage.py` |
| Immunocompromised patient with fever -> minimum ESI 2 | sepsis and occult infection risk | should remain escalation-only | same as above |

## Context rules

| Context rule | Why it exists | Evidence signal | Primary source files |
| --- | --- | --- | --- |
| Silent MI in diabetics | catches atypical cardiac presentations with GI-like complaints | called out repeatedly in project docs and MedGemma material as a differentiator | `backend/knowledge_base/safe_triage_clinical_rules.txt`, `backend/logic/deterministic_triage.py`, `docs/VALIDATION_REPORT.md` |
| Atypical ACS in women | prevents under-triage in non-classic cardiac complaints | relevant to symptom-only and benchmark-lite cases | `backend/knowledge_base/safe_triage_clinical_rules.txt`, `backend/logic/deterministic_triage.py` |
| Sepsis screening escalation | captures high-risk infectious cases hidden behind common complaints | ties physiology and complaint context together | same as above |
| Ectopic pregnancy detection | protects reproductive-age abdominal pain cases | justified as a high-risk context rule, not a free-text diagnosis | same as above |

## Decision rubric for future changes

When a failure appears, ask this before changing a rule:

1. Is the miss due to unrecognized wording?
   Then prefer `keywords`, `arabic dialect intake`, or `AI extraction prompt` changes.

2. Is the miss due to sparse or ambiguous benchmark context?
   Then classify it as `D1` or `C1` before changing deterministic logic.

3. Is the miss a true safety problem with clear clinical rationale?
   Then a rule or safety floor change may be justified.

4. Would the fix lower acuity anywhere?
   If yes, treat it as high-risk and require stronger evidence.

## Current provenance gaps to close

- several public docs still describe ESI as `v4`, while active code and recent docs emphasize `v5`; standardize the wording before submission
- Arabic keyword count is inconsistent across repo snapshots: `1,453` in the academic draft, `1,858` in README and pitch material, `2,101` in current code
- `docs/VALIDATION_REPORT.md` contains a strong safety-summary line that should be checked carefully against NHAMCS wording before reusing it verbatim in the paper
