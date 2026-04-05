# SAFE-Triage: A Hybrid Deterministic-AI Triage System with Arabic Dialect Support

## 1. Clinical Problem Statement

Emergency department (ED) triage errors kill patients. Under-triage -- assigning a critically ill patient a lower acuity than warranted -- delays life-saving interventions and is associated with increased mortality (Farrohknia et al., 2011). Studies report under-triage rates of 5--15% across high-volume EDs, with the highest rates occurring in settings that lack structured decision support (Hinson et al., 2019).

The problem is compounded in low- and middle-income countries. Egyptian public hospitals handle triage through unstructured physician assessment without standardized scoring. The Egyptian Ministry of Health issued ED triage guidelines in 2019, but adoption remains inconsistent. Meanwhile, existing AI triage systems -- trained almost exclusively on English-language data from US or European institutions -- cannot process Arabic chief complaints, let alone the Egyptian colloquial dialect used by patients at the bedside.

SAFE-Triage addresses both problems: it provides a structured, auditable triage decision support system built on validated clinical protocols, and it is the first MIMIC-IV-benchmarked triage system to support Arabic input, including Egyptian dialect.

## 2. Methodology

### Architecture: "AI Extracts, Rules Decide, Humans Confirm"

SAFE-Triage uses a three-layer hybrid architecture where AI is deliberately constrained to a classification role. The system never allows a language model to assign an acuity level directly.

**Layer 1 -- AI Feature Extraction.** The patient's chief complaint (Arabic or English) is processed by Gemini 2.5-Flash (primary) or Gemma 4 E4B-IT (open-weight backup) via Vertex AI. The model performs two constrained tasks: (a) map the free-text complaint to one of 38 predefined symptom categories (e.g., `chest_pain_cardiac`, `respiratory_distress`, `minor_trauma`), and (b) extract structured features including SNOMED-CT codes, body system, severity, onset, red flags, and expected ED resource needs. The model output is schema-validated; any field outside the allowed vocabulary is rejected.

**Layer 2 -- Deterministic Rules.** Two validated clinical scoring systems run independently:

- **NEWS2** (Royal College of Physicians, 2017): Calculates an early warning score from seven vital sign parameters (HR, RR, SpO2, SBP, temperature, consciousness, supplemental O2). The score maps to clinical risk levels (Low / Low-Medium / Medium / High).
- **ESI v5** (AHRQ): A two-stage decision algorithm. Stage 1 checks for immediate life threats and high-risk presentations. Stage 2 estimates expected resource consumption to differentiate ESI-3 through ESI-5.

The final ESI level is the *more urgent* of the complaint-derived level and the NEWS2-derived level, after applying age-based modifiers (pediatric < 3 years, elderly >= 65 years) and safety floor rules.

**Layer 3 -- Human Confirmation.** A physician dashboard presents the recommended ESI level alongside the full decision audit trail: complaint category, NEWS2 parameter scores, safety floors triggered, and any alerts for missing vitals. The physician can accept or override. Deterministic rules always take precedence over AI output.

**Async Quality Assurance.** MedGemma 4B-IT (Vertex AI Model Garden) runs batch review on completed triage cases, flagging potential under-triage for retrospective audit.

### Safety Floors

The system enforces hard safety constraints that cannot be overridden by the AI layer:

- Life-threatening conditions (cardiac arrest, respiratory arrest, anaphylaxis, status epilepticus, and 20+ others defined by SNOMED code sets) are locked to ESI-1.
- High-risk presentations (chest pain with cardiac features, stroke FAST-positive, active hemorrhage) cannot be triaged below ESI-2.
- Low AI confidence (< 0.70) triggers automatic escalation by one level.
- Incomplete vitals (>= 4 missing parameters) cap the minimum triage at ESI-3 to prevent false reassurance.
- Over-triage is explicitly preferred over under-triage throughout the rule set.

### Terminology and Coding

The system maps complaints to 6,370 SNOMED-CT concepts with ICD-10 cross-references, supporting GAHAR (Egyptian Hospital Accreditation Program) compliance requirements.

## 3. Arabic and Egyptian Dialect NLP

This is SAFE-Triage's primary differentiator. No other MIMIC-IV triage system handles Arabic input.

The system maintains a curated lexicon of **1,858 Arabic medical keywords** spanning three registers:

1. **Modern Standard Arabic (MSA)** medical terminology -- formal terms used in Egyptian medical education (e.g., "ضيق تنفس" for dyspnea, "سكتة دماغية" for stroke).
2. **Egyptian colloquial dialect** -- how patients actually describe symptoms at ED triage. Examples: "بيلف عليه" (dizziness, lit. "spinning on him"), "وجع في صدره" (chest pain), "مش قادر اتكلم" (cannot speak), "وشه مايل" (facial droop, lit. "his face is tilted"), "سخونية" (fever, colloquial).
3. **Hybrid clinical shorthand** -- terms used by Egyptian nurses during documentation that blend Arabic and transliterated English.

The keyword set is integrated at two levels. First, the deterministic engine uses pre-compiled regex patterns with Arabic-aware normalization (hamza flattening, alef-maqsura normalization) and Arabic negation stripping (handling constructs like "بينفي" / "مفيش" / "مش عنده"). Second, the AI extraction prompt includes bilingual category descriptions so the language model can map Egyptian dialect input to the correct standardized category.

Critical safety signals -- stroke (FAST criteria), chest pain, altered consciousness, hemorrhage -- have dedicated Arabic keyword sets to ensure they trigger safety floor rules regardless of whether the AI extraction succeeds. For example, the stroke signal set includes 20+ Egyptian dialect variants covering facial droop, speech difficulty, and lateralized weakness as patients would naturally describe them.

## 4. Results

SAFE-Triage was evaluated on four independent benchmarks:

### MIETIC (Primary Validation)
36 expert-validated RETAIN cases spanning all five ESI acuity levels (14 ESI-1, 11 ESI-2, 5 ESI-3, 4 ESI-4, 2 ESI-5).

| Metric | Value |
|--------|-------|
| Exact match | 97.2% (35/36) |
| Within-one accuracy | 100% (36/36) |
| Critical under-triage | **0%** (0 cases) |
| Over-triage | 2.8% (1 case, ESI-3 triaged as ESI-2) |
| ESI-1 recall | 100% (14/14) |
| ESI-2 recall | 100% (11/11) |

The single non-exact case was an ESI-3 over-triaged to ESI-2 -- the safe direction.

### MIETIC Arabic Mirror
The same 36 cases translated to Egyptian colloquial Arabic, using natural ED patient speech rather than formal MSA.

| Metric | Value |
|--------|-------|
| Exact match | 97.2% (35/36) |
| Critical under-triage | **0%** |
| Over-triage | 2.8% (1 case) |

Arabic performance is identical to English, confirming that the dialect keyword layer and bilingual AI extraction produce equivalent triage decisions.

### KTAS External (Korean Triage and Acuity Scale)
1,262 patients from two Korean hospitals with expert-consensus KTAS labels.

| Metric | Value |
|--------|-------|
| Exact match | 36.8% |
| Within-one accuracy | 81.5% |
| Critical under-triage | 1.4% (17 cases) |
| Over-triage | 54.1% |

The low exact match reflects a systematic over-triage bias -- by design, SAFE-Triage's safety floors escalate aggressively. Of the 17 critical under-triage cases, most involved ambiguous chief complaints ("abd pain", "headache", "fever") where the KTAS expert panel assigned ESI-2 based on clinical context not available in the structured data. No KTAS-1 cases were missed entirely (all received ESI-1 or ESI-2).

### NHAMCS (National Hospital Ambulatory Medical Care Survey)
10,495 US CDC cases. Current results: approximately 40% exact match, 7.9% critical under-triage. This dataset is the most challenging due to sparse vitals, unstructured chief complaints, and a different triage philosophy (US nurse-assigned ESI vs. our deterministic protocol). NHAMCS performance is an active area of improvement.

## 5. Key Design Decisions

**Deterministic rules override AI.** The AI layer cannot downgrade a triage level that the rule engine has assigned. If NEWS2 scores place a patient at HIGH risk (score >= 7 or any single parameter = 3), the patient receives at minimum ESI-2 regardless of what the AI classifies the complaint as. This is a deliberate design choice: false-positive escalations are recoverable; false-negative de-escalations may not be.

**Constrained AI output space.** The AI can only output one of 38 predefined symptom categories. It cannot generate free-text triage reasoning or acuity levels. This follows the principle that "classification tasks with defined output categories are more reliable and auditable than open-ended generation tasks in clinical settings" (Rajkomar et al., NEJM 2019).

**Conservative fallback.** When AI confidence is low or extraction fails entirely, the system falls back to keyword matching. When keyword matching is inconclusive, the default category is `unclear_needs_evaluation` (ESI-3), which prevents undertriage of genuinely ambiguous cases.

**Budget-aware deployment.** The system is designed for Egyptian public hospital economics. Gemma 4 E4B-IT (open-weight, deployable on a single L4 GPU) provides the privacy-sensitive and cost-effective option. Gemini 2.5-Flash serves as the low-latency primary. A budget guard module enforces a hard stop at $950 of cloud spend and auto-undeploys all Vertex AI endpoints at threshold.

## 6. Limitations

**NHAMCS under-triage.** At 7.9% critical under-triage, NHAMCS performance does not yet meet our target. The dataset's unstructured complaints and missing vitals expose the limits of keyword-based fallback when AI extraction is unavailable.

**Single-source training bias.** The MIETIC and MIETIC-AR benchmarks, while expert-validated, contain only 36 cases. Larger prospective validation in Egyptian EDs is needed.

**Arabic lexicon is hand-curated.** The 1,858 keywords were compiled by domain experts, not learned from data. Coverage gaps are possible for regional dialect variants outside Cairo/Alexandria. A data-driven expansion from transcribed ED encounters would strengthen the lexicon.

**Cross-scale mapping.** KTAS and ESI are different triage scales. Our KTAS benchmark maps KTAS levels to ESI equivalents, which introduces alignment noise. The high over-triage rate on KTAS partially reflects this mapping rather than true clinical error.

**No prospective clinical validation.** All benchmarks are retrospective. A prospective study comparing SAFE-Triage recommendations against attending physician decisions in a live Egyptian ED is the necessary next step.

## 7. Impact and Reproducibility

**Open-weight models.** The backup extraction model (Gemma 4 E4B-IT) and the QA model (MedGemma 4B-IT) are open-weight and deployable on commodity hardware. This matters for Egyptian hospitals that cannot send patient data to external APIs for regulatory or cost reasons.

**Deployable in resource-constrained settings.** The system runs on Google Cloud Run (backend) and Firebase Hosting (frontend). The deterministic engine requires no GPU and can run offline with keyword-only classification. AI extraction is additive, not required.

**Full audit trail.** Every triage decision records the complete decision path: AI category, NEWS2 parameter scores, safety floors triggered, and confidence level. This supports the GAHAR accreditation requirement for documented triage rationale.

**Code availability.** The complete system -- deterministic engine, AI service, benchmarks, Arabic keyword sets, and deployment scripts -- is available on GitHub.

**Tech stack.** FastAPI + React frontend. Google Cloud Run for backend. Vertex AI for model serving. BigQuery for production data. 6,370 SNOMED-CT concepts with ICD-10 mapping. Benchmarked across 4 datasets totaling 11,829 cases.

---

*SAFE-Triage is a capstone thesis project at the American University in Cairo, AI & Business program. The system is designed as clinical decision support and does not replace physician judgment.*
