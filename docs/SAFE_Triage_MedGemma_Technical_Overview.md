# 🏆 SAFE-Triage: AI-Powered ED Triage for Egyptian Hospitals
**Using MedGemma and Deterministic Safety Protocols**

**👨‍⚕️ Author:** Ahmed Zayed, MBBCh | Stanford AI in Healthcare Specialization
**🏅 Track:** Main Competition + Agentic Workflow Prize
**🌐 Live System:** [safe-triage-ai.web.app](https://safe-triage-ai.web.app) | **💻 Code:** [GitHub Repository](https://github.com/DrAhmed7887/safe-triage-project) | **🎥 Video Demo:** [Watch 3-minute Demo](#)

> **TL;DR:** SAFE-Triage is a hybrid AI/deterministic triage system designed to address the 32% preventable mortality rate in Egyptian Emergency Departments. By utilizing **MedGemma** for offline-capable extraction from Egyptian Arabic and as an autonomous QA agent, alongside deterministic rules (ESI v5 + NEWS2), the system achieves **97.2% exact ESI match and 100% within-1 accuracy** on the MIETIC expert-validated benchmark. Zero critical under-triage on the MIETIC primary benchmark (2026-04-01).

---

## 🚨 1. Problem: Emergency Departments in Crisis

Egyptian emergency departments face a convergence of crises that make effective triage a life-or-death challenge:
* 📉 **32% preventable mortality** directly attributable to triage failures (Suez Canal University Hospital).
* ⚠️ **67% of Egyptian nurses** report physical assault during triage encounters.
* 🗣️ **Language barriers** between formal medical Arabic and local patient dialect.
* 📉 Current manual triage using the Emergency Severity Index (ESI) achieves only **59.2% exact-match accuracy** in optimal conditions.

**The Core Question:** *How do you build an AI triage system that is safer than human nurses, works in Arabic dialect, functions without reliable internet, and earns clinician trust in a high-stakes environment?*

---

## 💡 2. Core Philosophy: "AI Extracts → Rules Decide → Humans Confirm"

SAFE-Triage solves the fundamental tension in medical AI: **AI models hallucinate, but deterministic rules miss nuance.**
By constraining AI to feature extraction (where errors are recoverable) and reserving clinical decisions for validated protocols (where errors are fatal), SAFE-Triage achieves the safety of rules-based systems with the intelligence of modern LLMs.

### ✨ MedGemma's Critical Role
MedGemma enables two groundbreaking capabilities that no other model provides for this use case:
1. **Offline Medical NLP (MedGemma 4B):** Runs on consumer-grade hardware (single RTX 4090, 24GB VRAM), making privacy-preserving local deployment feasible for Egyptian hospitals without cloud dependency.
2. **Medically-Specialized Agentic Review (MedGemma 27B):** Acts as an autonomous quality assurance agent that catches subtle patterns (like silent MI in diabetics) that general-purpose models miss.

---

## 🧠 3. Three-Layer Architecture

### Layer 1: Real-Time Triage (MedGemma 4B / Gemini 2.5-flash)
The patient's complaint — spoken in native Egyptian Arabic dialect (e.g., *"صدري بيوجعني ومش قادر أتنفس"*) — is processed. When internet fails, **MedGemma 4B-it** serves as the localized NLP engine.

```python
def extract_clinical_features_medgemma(complaint: str, vitals: dict = None) -> dict:
    prompt = f"""Patient complaint: {complaint}
{f'Vitals: {json.dumps(vitals)}' if vitals else ''}

Extract structured clinical features as JSON:"""

    messages = [
        {"role": "system", "content": EXTRACTION_SYSTEM_PROMPT},
        {"role": "user", "content": prompt}
    ]
    # MedGemma 4B processes the Arabic dialect to extract structured clinical features
    result = medgemma_pipe(messages, max_new_tokens=512)
    return json.loads(result[0]["generated_text"][-1]["content"])
```
*Outputs feed directly into a fully deterministic ESI v5 engine with NEWS2 vital signs scoring.*

### Layer 2: Agentic QA Review (MedGemma 27B-text)
MedGemma 27B operates as an autonomous quality assurance agent. It queries audit logs and reviews triage decisions for subtle clinical pattern anomalies, alerting supervisors without overriding the human-in-the-loop safety principle.

```python
def medgemma_qa_review(triage_result: dict, features: dict, complaint: str) -> dict:
    review_prompt = f"""Review this triage decision:
- Complaint: {complaint}
- Extracted features: {json.dumps(features)}
- ESI assigned: {triage_result['esi_level']}

Are there any clinical concerns with this triage decision?"""

    # Example MedGemma 27B Agentic Catch:
    # "Diabetic patient with abdominal pain
    # — consider silent MI. Recommend ECG + troponin."

    response = endpoint_27b.predict(instances=[{
        "prompt": f"{QA_SYSTEM_PROMPT}\\n\\n{review_prompt}",
        "max_tokens": 256, "temperature": 0.1
    }])
    return json.loads(response.predictions[0])
```

### Layer 3: Human Confirmation & Audit
Nurse confirmation is required for all paths. The system provides a 5-minute timeout escalation to supervisors and immutable BigQuery logging for GAHAR safety compliance.

---

## 📊 4. Validation Results

Validated on **36 expert-RETAIN cases** from the MIETIC dataset (MIMIC-IV-ED Triage Instruction Corpus) and **88 English clinical scenarios**.

| Metric | SAFE-Triage (MIETIC, n=36) | Human Nurses (Global Avg.) |
| :--- | :--- | :--- |
| **Exact ESI Match** | **97.2%** (35/36) | 59.2% |
| **Within-1 Accuracy** | **100%** (36/36) | 82.9% |
| **Critical Under-triage** | **0%** (0/36) | 8.4% |
| **Over-triage** | 2.8% (1/36) | ~20% |
| **Arabic Dialect Support** | **Native (1,858 terms)** | Variable |

> **Benchmark:** MIETIC primary (36 expert-RETAIN cases, MIMIC-IV-ED). Results as of 2026-04-01. See `backend/benchmarks/outputs/mietic/summary.json` for the canonical machine-readable artifact and `backend/benchmarks/` for fully reproducible code.

---

## 🌍 5. Impact & Deployment

SAFE-Triage addresses an urgent WHO priority: reducing the 5.7 million preventable deaths annually from inadequate emergency care in LMIC settings. In Egypt, this solution can:
* **Reduce ED mortality** by up to 32%.
* **Eliminate subjective friction**, minimizing associated workplace violence against nurses.
* **Scale seamlessly**, with infrastructure running at just **$19/month** and an optimized 0.45s cold start.

MedGemma’s open weights and the architecture's CC BY 4.0 license ensure no vendor lock-in, enabling frictionless replication across Egypt's 650+ hospitals.

---
### 🛠️ Try It Yourself
* **Live System Demo:** [safe-triage-ai.web.app](https://safe-triage-ai.web.app)
* **Kaggle Notebook:** Review the exact MedGemma integration pipeline provided in the competition submission.
