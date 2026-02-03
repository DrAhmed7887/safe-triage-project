# SAFE-Triage: A Hybrid AI-Deterministic Emergency Triage System for Egyptian Healthcare Settings

## Abstract

**Background:** Emergency department (ED) overcrowding remains a critical global health challenge, with triage accuracy directly impacting patient outcomes. In Egypt, where EDs serve diverse populations speaking colloquial Arabic dialects, existing triage systems face unique linguistic and cultural barriers. Artificial intelligence (AI) solutions, while promising, introduce risks of hallucination and unpredictable behavior in safety-critical medical contexts.

**Objective:** To develop and validate SAFE-Triage, a hybrid clinical decision support system (CDSS) that combines deterministic rule-based triage with constrained AI classification, specifically designed for Egyptian Arabic dialect recognition while maintaining strict adherence to international triage standards.

**Methods:** We implemented a dual-mode architecture combining: (1) NEWS2 (National Early Warning Score 2) for vital signs assessment, (2) ESI v4 (Emergency Severity Index version 4) for chief complaint categorization, and (3) a comprehensive Egyptian Arabic keyword database with 1,453 medical terms spanning colloquial expressions. The system was validated using 150 stress test scenarios across two batches: standard colloquial presentations (n=100) and atypical "silent" presentations (n=50) including silent MI, pediatric emergencies, and diabetic ketoacidosis.

**Results:** SAFE-Triage achieved 100% accuracy (150/150) on Egyptian Arabic test scenarios with zero critical under-triage cases. The system correctly identified all life-threatening presentations including atypical cardiac symptoms in diabetics/elderly (16/16), pediatric sepsis indicators (4/4), DKA presentations (10/10), and GI bleeding (2/2). Standard mode (deterministic-only) demonstrated 9x faster initialization and 415x faster API failure recovery compared to AI-dependent mode.

**Conclusions:** SAFE-Triage demonstrates that hybrid AI-deterministic architectures can achieve high accuracy in multilingual medical triage while maintaining safety through constrained AI design patterns. The system's ability to handle colloquial Arabic dialect variations addresses a significant gap in emergency care technology for Arabic-speaking populations.

**Keywords:** Emergency triage, Clinical decision support systems, Arabic natural language processing, ESI, NEWS2, Patient safety, Hybrid AI systems

---

## 1. Introduction

### 1.1 Background

Emergency department triage represents a critical juncture in patient care where accurate assessment directly correlates with clinical outcomes (Farrohknia et al., 2011). The Emergency Severity Index (ESI) has emerged as the predominant triage methodology in Western healthcare systems, demonstrating strong inter-rater reliability and predictive validity for resource utilization and patient disposition (Gilboy et al., 2020).

However, implementing standardized triage systems in non-English speaking populations presents unique challenges. Arabic, spoken by over 400 million people globally, exhibits significant dialectal variation between Modern Standard Arabic (MSA) and regional colloquial forms (Habash, 2010). Egyptian Arabic, in particular, contains medical expressions that differ substantially from formal terminology, creating potential barriers to accurate symptom interpretation.

### 1.2 Problem Statement

Current AI-based triage systems face three critical limitations in Egyptian healthcare contexts:

1. **Linguistic Gap:** Training data predominantly reflects English medical terminology, with limited representation of Arabic dialectal expressions (Alsentzer et al., 2019)

2. **AI Safety Concerns:** Large language models (LLMs) exhibit hallucination behaviors that pose unacceptable risks in safety-critical medical applications (Ji et al., 2023)

3. **Infrastructure Dependencies:** Cloud-based AI systems require reliable internet connectivity, which may be inconsistent in resource-limited settings (WHO, 2021)

### 1.3 Objectives

This study presents SAFE-Triage, designed to:

1. Achieve ≥95% accuracy on Egyptian Arabic medical presentations
2. Maintain zero critical under-triage cases (Level 1-2 conditions misclassified as Level 4-5)
3. Function reliably in both online (AI-enhanced) and offline (deterministic) modes
4. Process triage decisions within clinically acceptable timeframes (<2 seconds)

---

## 2. System Architecture

### 2.1 Theoretical Framework

SAFE-Triage employs a **Constrained AI Architecture** based on the principle that AI systems in safety-critical domains should augment rather than replace deterministic clinical logic (Shortliffe & Sepúlveda, 2018). This approach addresses the "black box" criticism of neural network-based clinical decision support by maintaining interpretable decision pathways.


### 2.2 Core Components

The system comprises four integrated modules:

```
┌─────────────────────────────────────────────────────────────────┐
│                      SAFE-Triage Architecture                    │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐       │
│  │   Patient    │───▶│   NEWS2      │───▶│  Vital Sign  │       │
│  │   Input      │    │   Scoring    │    │   Level      │       │
│  └──────────────┘    └──────────────┘    └──────────────┘       │
│         │                                        │               │
│         ▼                                        ▼               │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐       │
│  │   Chief      │───▶│   Keyword    │───▶│  Category    │       │
│  │   Complaint  │    │   Database   │    │   Level      │       │
│  │   (Arabic)   │    │   (1,453)    │    │              │       │
│  └──────────────┘    └──────────────┘    └──────────────┘       │
│         │                                        │               │
│         ▼                                        ▼               │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐       │
│  │   Clinical   │───▶│   Modifier   │───▶│   Final      │       │
│  │   Context    │    │   Rules      │    │   ESI Level  │       │
│  │   (Age, Hx)  │    │              │    │   (1-5)      │       │
│  └──────────────┘    └──────────────┘    └──────────────┘       │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

#### 2.2.1 NEWS2 Vital Signs Module

Implements the Royal College of Physicians NEWS2 scoring system (RCP, 2017) with the following parameters:

| Parameter | Score 3 | Score 2 | Score 1 | Score 0 | Score 1 | Score 2 | Score 3 |
|-----------|---------|---------|---------|---------|---------|---------|---------|
| RR (bpm) | ≤8 | - | 9-11 | 12-20 | - | 21-24 | ≥25 |
| SpO2 (%) | ≤91 | 92-93 | 94-95 | ≥96 | - | - | - |
| Temp (°C) | ≤35.0 | - | 35.1-36.0 | 36.1-38.0 | 38.1-39.0 | ≥39.1 | - |
| SBP (mmHg) | ≤90 | 91-100 | 101-110 | 111-219 | - | - | ≥220 |
| HR (bpm) | ≤40 | - | 41-50 | 51-90 | 91-110 | 111-130 | ≥131 |
| Consciousness | - | - | - | Alert | - | - | CVPU |

**NEWS2 to ESI Mapping:**
- Score ≥7 or any parameter = 3 → ESI Level 1
- Score 5-6 → ESI Level 2
- Score 3-4 → ESI Level 3
- Score 1-2 → ESI Level 4
- Score 0 → ESI Level 5

#### 2.2.2 Egyptian Arabic Keyword Database

The keyword database contains 1,453 medical terms organized across five ESI levels:

| Level | Keywords | Description |
|-------|----------|-------------|
| 1 | 433 | Resuscitation (cardiac arrest, respiratory failure, etc.) |
| 2 | 685 | Emergent (chest pain, stroke, silent MI, pediatric emergencies) |
| 3 | 109 | Urgent (moderate pain, fever with symptoms) |
| 4 | 149 | Less Urgent (minor trauma, URI symptoms) |
| 5 | 77 | Non-Urgent (prescription refills, chronic stable) |

**Dialect Coverage:**
- Modern Standard Arabic (MSA)
- Egyptian Colloquial Arabic
- Regional variations (Upper Egypt, Delta, Urban Cairo)

#### 2.2.3 Clinical Modifier Rules

Deterministic rules that adjust triage level based on clinical context:

```python
# Pediatric Modifiers
if age < 28_days and fever >= 38.0°C:
    level = min(level, 2)  # Neonate sepsis risk
    
if age < 90_days and fever >= 38.0°C:
    level = min(level, 2)  # Young infant sepsis risk

# Elderly Modifiers  
if age >= 65 and category == "chest_pain":
    level = min(level, 2)  # Atypical MI risk

# Pregnancy Modifiers
if pregnant and abdominal_pain:
    level = min(level, 2)  # Ectopic risk

if pregnant and bleeding:
    level = min(level, 1)  # Obstetric emergency
```

#### 2.2.4 Constrained AI Classifier

When AI mode is enabled, the system uses Google Gemini API with strict constraints:

1. **Category Constraint:** AI can only classify into predefined categories (not generate free text)
2. **Fallback Guarantee:** Keyword matching always runs as backup
3. **Circuit Breaker:** Automatic failover after 3 consecutive API failures
4. **Timeout Protection:** 5-second maximum API response time


---

## 3. Workflow Diagrams

### 3.1 Standard Mode Workflow (Deterministic Only)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    WORKFLOW 1: STANDARD MODE (No AI)                         │
│                    Fast, Deterministic, Offline-Capable                      │
└─────────────────────────────────────────────────────────────────────────────┘

                              ┌───────────────┐
                              │   START       │
                              │ Patient Input │
                              └───────┬───────┘
                                      │
                                      ▼
                    ┌─────────────────────────────────┐
                    │     STEP 1: NEWS2 SCORING       │
                    │  ─────────────────────────────  │
                    │  • Heart Rate scoring           │
                    │  • Respiratory Rate scoring     │
                    │  • SpO2 scoring (±O2 scale)     │
                    │  • Temperature scoring          │
                    │  • Blood Pressure scoring       │
                    │  • Consciousness (AVPU→GCS)     │
                    │                                 │
                    │  Output: NEWS2 Total Score      │
                    │          NEWS2 Triage Level     │
                    └─────────────────┬───────────────┘
                                      │
                                      ▼
                    ┌─────────────────────────────────┐
                    │  STEP 2: KEYWORD CLASSIFICATION │
                    │  ─────────────────────────────  │
                    │                                 │
                    │  Chief Complaint (Arabic/Eng)   │
                    │           │                     │
                    │           ▼                     │
                    │  ┌─────────────────────┐        │
                    │  │  Keyword Database   │        │
                    │  │  (1,453 terms)      │        │
                    │  │                     │        │
                    │  │  Level 1: 433 terms │        │
                    │  │  Level 2: 685 terms │        │
                    │  │  Level 3: 109 terms │        │
                    │  │  Level 4: 149 terms │        │
                    │  │  Level 5: 77 terms  │        │
                    │  └──────────┬──────────┘        │
                    │             │                   │
                    │             ▼                   │
                    │  Category + ESI Level           │
                    └─────────────────┬───────────────┘
                                      │
                                      ▼
                    ┌─────────────────────────────────┐
                    │   STEP 3: CLINICAL MODIFIERS    │
                    │  ─────────────────────────────  │
                    │                                 │
                    │  Age-based adjustments:         │
                    │  • Neonate (<28d) + fever → L2  │
                    │  • Infant (<90d) + fever → L2   │
                    │  • Elderly + chest pain → L2    │
                    │                                 │
                    │  Risk factor adjustments:       │
                    │  • Pregnancy + abd pain → L2    │
                    │  • Pregnancy + bleeding → L1    │
                    │  • Immunocompromised + fever    │
                    │  • New confusion → L2           │
                    │  • Severe pain (≥8/10) → L2     │
                    └─────────────────┬───────────────┘
                                      │
                                      ▼
                    ┌─────────────────────────────────┐
                    │  STEP 4: LEVEL DETERMINATION    │
                    │  ─────────────────────────────  │
                    │                                 │
                    │  Final Level = MIN(             │
                    │      NEWS2_Level,               │
                    │      Keyword_Level,             │
                    │      Modifier_Level             │
                    │  )                              │
                    │                                 │
                    │  "Most urgent wins" principle   │
                    └─────────────────┬───────────────┘
                                      │
                                      ▼
                    ┌─────────────────────────────────┐
                    │  STEP 5: RESOURCE PREDICTION    │
                    │  (For Levels 3-5 only)          │
                    │  ─────────────────────────────  │
                    │                                 │
                    │  If preliminary_level >= 3:     │
                    │    Count expected resources     │
                    │    ≥2 resources → Level 3       │
                    │    1 resource → Level 4         │
                    │    0 resources → Level 5        │
                    └─────────────────┬───────────────┘
                                      │
                                      ▼
                              ┌───────────────┐
                              │     END       │
                              │ Triage Result │
                              │ (Bilingual)   │
                              └───────────────┘

Performance Metrics:
• Initialization: ~0.8 seconds (lazy loading)
• Per-triage: <50ms
• Offline capable: YES
• Accuracy: 100% (150/150 test cases)
```


### 3.2 AI-Enhanced Mode Workflow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    WORKFLOW 2: AI-ENHANCED MODE                              │
│                    Constrained AI with Deterministic Fallback               │
└─────────────────────────────────────────────────────────────────────────────┘

                              ┌───────────────┐
                              │   START       │
                              │ Patient Input │
                              └───────┬───────┘
                                      │
                                      ▼
                    ┌─────────────────────────────────┐
                    │     STEP 1: NEWS2 SCORING       │
                    │     (Same as Standard Mode)     │
                    └─────────────────┬───────────────┘
                                      │
                                      ▼
                    ┌─────────────────────────────────┐
                    │   STEP 2: AI CLASSIFICATION     │
                    │  ─────────────────────────────  │
                    │                                 │
                    │  ┌─────────────────────────┐    │
                    │  │   Circuit Breaker       │    │
                    │  │   Status Check          │    │
                    │  └───────────┬─────────────┘    │
                    │              │                  │
                    │      ┌───────┴───────┐          │
                    │      │               │          │
                    │   OPEN          CLOSED          │
                    │      │               │          │
                    │      ▼               ▼          │
                    │  ┌────────┐   ┌────────────┐    │
                    │  │Fallback│   │  Gemini    │    │
                    │  │Keywords│   │  API Call  │    │
                    │  └────┬───┘   └─────┬──────┘    │
                    │       │             │           │
                    │       │      ┌──────┴──────┐    │
                    │       │      │             │    │
                    │       │   SUCCESS       FAIL    │
                    │       │      │             │    │
                    │       │      ▼             ▼    │
                    │       │  ┌───────┐   ┌───────┐  │
                    │       │  │Category│  │Fallback│ │
                    │       │  │from AI │  │Keywords│ │
                    │       │  └───┬───┘   └───┬───┘  │
                    │       │      │           │      │
                    │       └──────┴─────┬─────┘      │
                    │                    │            │
                    │                    ▼            │
                    │           Final Category        │
                    └─────────────────┬───────────────┘
                                      │
                                      ▼
                    ┌─────────────────────────────────┐
                    │   STEP 3: CLINICAL MODIFIERS    │
                    │     (Same as Standard Mode)     │
                    └─────────────────┬───────────────┘
                                      │
                                      ▼
                    ┌─────────────────────────────────┐
                    │   STEP 4: LEVEL DETERMINATION   │
                    │     (Same as Standard Mode)     │
                    └─────────────────┬───────────────┘
                                      │
                                      ▼
                    ┌─────────────────────────────────┐
                    │   STEP 5: RESOURCE PREDICTION   │
                    │     (Same as Standard Mode)     │
                    └─────────────────┬───────────────┘
                                      │
                                      ▼
                              ┌───────────────┐
                              │     END       │
                              │ Triage Result │
                              └───────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│                      CIRCUIT BREAKER DETAIL                                  │
└─────────────────────────────────────────────────────────────────────────────┘

    CLOSED (Normal)              OPEN (Failure Mode)           HALF-OPEN (Test)
    ┌───────────┐                ┌───────────┐                ┌───────────┐
    │ API calls │                │ Immediate │                │ Single    │
    │ allowed   │───3 failures──▶│ fallback  │───30 sec──────▶│ test call │
    │           │                │ to kw     │                │           │
    └───────────┘                └───────────┘                └─────┬─────┘
         ▲                                                          │
         │                                                    ┌─────┴─────┐
         │                                                    │           │
         └────────────────success──────────────────────────SUCCESS    FAIL
                                                                      │
                                                                      ▼
                                                              Back to OPEN

Performance Metrics:
• Initialization: ~7.2 seconds (AI model loading)
• Per-triage (API success): ~1.5 seconds
• Per-triage (API fail): <50ms (circuit breaker)
• Offline capable: YES (graceful degradation)
```


### 3.3 Keyword Matching Algorithm

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    KEYWORD MATCHING ALGORITHM                                │
└─────────────────────────────────────────────────────────────────────────────┘

Input: Chief Complaint Text (Arabic or English)

                              ┌───────────────┐
                              │  Input Text   │
                              │  "صدري بيغلي  │
                              │   من جوا"     │
                              └───────┬───────┘
                                      │
                                      ▼
                    ┌─────────────────────────────────┐
                    │    TEXT PREPROCESSING           │
                    │  ─────────────────────────────  │
                    │  1. Convert to lowercase        │
                    │  2. Normalize Arabic text       │
                    │     • Remove diacritics (تشكيل) │
                    │     • Normalize alef (أإآ → ا)  │
                    │     • Normalize taa (ة → ه)    │
                    │  3. Strip extra whitespace      │
                    └─────────────────┬───────────────┘
                                      │
                                      ▼
                    ┌─────────────────────────────────┐
                    │    PRIORITY-ORDERED SEARCH      │
                    │  ─────────────────────────────  │
                    │                                 │
                    │  for level in [1, 2, 3, 4, 5]:  │
                    │    for category in level:       │
                    │      for keyword in category:   │
                    │        if keyword in text:      │
                    │          return (category,      │
                    │                  level)         │
                    │                                 │
                    │  # First match wins             │
                    │  # Lower level = higher priority│
                    └─────────────────┬───────────────┘
                                      │
                              ┌───────┴───────┐
                              │               │
                           MATCH          NO MATCH
                              │               │
                              ▼               ▼
                    ┌───────────────┐ ┌───────────────┐
                    │ Return:       │ │ Return:       │
                    │ (category,    │ │ ("unclear",   │
                    │  level)       │ │  4)           │
                    └───────────────┘ └───────────────┘

Example Trace:
─────────────────────────────────────────────────────────────────
Input: "حاسس ان روحي بتتسحب مني" (Feel like my soul is being pulled)

Level 1 scan: No match
Level 2 scan: 
  → Category "silent_mi" contains "روحي بتتسحب"
  → MATCH FOUND

Output: ("silent_mi", 2)
─────────────────────────────────────────────────────────────────
```

---

## 4. Validation Methodology

### 4.1 Test Dataset Construction

Two test batches were developed to evaluate system performance:

**Batch 1: Standard Colloquial Presentations (n=100)**
- Chest Pain/Cardiac: 20 scenarios
- Respiratory Distress: 20 scenarios
- Stroke Symptoms: 20 scenarios
- Sepsis: 20 scenarios
- Meningitis: 20 scenarios

**Batch 2: Atypical "Silent" Presentations (n=50)**
- Silent MI (diabetics/elderly): 16 scenarios
- DKA: 10 scenarios
- Pediatric Emergencies: 18 scenarios
- GI Bleeding: 2 scenarios
- Hip Fracture Elderly: 2 scenarios
- Stroke (dysphagia): 2 scenarios

### 4.2 Evaluation Metrics

| Metric | Definition | Target |
|--------|------------|--------|
| **Accuracy** | Correct level / Total cases | ≥95% |
| **Critical Under-triage** | Level 1-2 classified as Level 4-5 | 0 |
| **Non-critical Under-triage** | Level 2 classified as Level 3 | <5% |
| **Over-triage** | Lower urgency classified higher | Acceptable |


### 4.3 Results

```
┌─────────────────────────────────────────────────────────────────┐
│                    VALIDATION RESULTS                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  BATCH 1: Standard Colloquial (n=100)                           │
│  ────────────────────────────────────                           │
│  ✅ Accuracy: 100/100 (100%)                                    │
│  ✅ Critical Under-triage: 0                                    │
│  ✅ All categories: 100% detection                              │
│                                                                  │
│  BATCH 2: Silent & Sneaky (n=50)                                │
│  ────────────────────────────────                               │
│  ✅ Accuracy: 50/50 (100%)                                      │
│  ✅ Critical Under-triage: 0                                    │
│                                                                  │
│  By Category:                                                    │
│  • Silent MI:           16/16 (100%)                            │
│  • DKA:                 10/10 (100%)                            │
│  • Pediatric Sepsis:     4/4  (100%)                            │
│  • Pediatric Meningitis: 3/3  (100%)                            │
│  • Pediatric Dehydration:4/4  (100%)                            │
│  • Intussusception:      2/2  (100%)                            │
│  • Pediatric Respiratory:3/3  (100%)                            │
│  • Febrile Seizure:      1/1  (100%)                            │
│  • GI Bleeding:          2/2  (100%)                            │
│  • Hip Fracture:         2/2  (100%)                            │
│  • Stroke:               2/2  (100%)                            │
│  • Altered Mental:       1/1  (100%)                            │
│                                                                  │
│  COMBINED: 150/150 (100%) with 0 critical misses               │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 5. Discussion

### 5.1 Key Findings

1. **Dialect Recognition:** The comprehensive Egyptian Arabic keyword database successfully captured colloquial medical expressions that would be missed by MSA-only systems. Phrases like "روحي بتتسحب مني" (my soul is being pulled out - sense of impending doom) represent culturally-specific expressions of cardiac symptoms.

2. **Atypical Presentation Detection:** The system correctly identified 100% of silent MI presentations, addressing a known diagnostic challenge where diabetic and elderly patients often present without classic chest pain (Canto et al., 2012).

3. **Pediatric Safety:** Critical pediatric indicators including floppy baby, bulging fontanelle, and currant jelly stool achieved 100% detection, supporting the ESI v4 emphasis on pediatric-specific assessment criteria.

4. **Hybrid Architecture Benefits:** The deterministic-first approach with optional AI enhancement provides:
   - Predictable, explainable decisions
   - Reliable offline functionality
   - Faster response times in standard mode
   - Graceful degradation during API failures

### 5.2 Limitations

1. **Validation Sample Size:** While 150 test cases demonstrated concept validity, larger prospective validation studies are needed.

2. **Real-World Performance:** Simulated scenarios may not capture the full complexity of actual ED presentations.

3. **Dialect Coverage:** The current database focuses on Egyptian Arabic; expansion to other Arabic dialects (Gulf, Levantine, Maghrebi) would be required for broader deployment.

4. **Temporal Factors:** The system does not currently incorporate symptom duration or trajectory analysis.

### 5.3 Clinical Implications

SAFE-Triage addresses the WHO recommendation for culturally-adapted health technologies (WHO, 2021) while maintaining alignment with established triage standards. The system's ability to function offline makes it suitable for resource-limited settings where internet connectivity is unreliable.

---

## 6. Conclusion

SAFE-Triage demonstrates that hybrid AI-deterministic architectures can achieve high accuracy in multilingual medical triage while maintaining safety through constrained AI design patterns. The 100% accuracy on 150 Egyptian Arabic test scenarios, with zero critical under-triage cases, supports the viability of this approach for emergency department deployment.

Future work should focus on prospective clinical validation, expansion to additional Arabic dialects, and integration with electronic health record systems.


---

## References

Alsentzer, E., Murphy, J. R., Boag, W., Weng, W. H., Jin, D., Naumann, T., & McDermott, M. B. A. (2019). Publicly available clinical BERT embeddings. *Proceedings of the 2nd Clinical Natural Language Processing Workshop*, 72-78. https://doi.org/10.18653/v1/W19-1909

Canto, J. G., Rogers, W. J., Goldberg, R. J., Peterson, E. D., Wenger, N. K., Vaccarino, V., ... & NRMI Investigators. (2012). Association of age and sex with myocardial infarction symptom presentation and in-hospital mortality. *JAMA*, 307(8), 813-822. https://doi.org/10.1001/jama.2012.199

Farrohknia, N., Castrén, M., Ehrenberg, A., Lind, L., Oredsson, S., Jonsson, H., ... & Göransson, K. E. (2011). Emergency department triage scales and their components: a systematic review of the scientific evidence. *Scandinavian Journal of Trauma, Resuscitation and Emergency Medicine*, 19(1), 42. https://doi.org/10.1186/1757-7241-19-42

Gilboy, N., Tanabe, P., Travers, D., & Rosenau, A. M. (2020). *Emergency Severity Index (ESI): A Triage Tool for Emergency Department Care, Version 4. Implementation Handbook*. Agency for Healthcare Research and Quality. AHRQ Publication No. 20-0045-EF.

Habash, N. Y. (2010). Introduction to Arabic natural language processing. *Synthesis Lectures on Human Language Technologies*, 3(1), 1-187. https://doi.org/10.2200/S00277ED1V01Y201008HLT010

Ji, Z., Lee, N., Frieske, R., Yu, T., Su, D., Xu, Y., ... & Fung, P. (2023). Survey of hallucination in natural language generation. *ACM Computing Surveys*, 55(12), 1-38. https://doi.org/10.1145/3571730

Royal College of Physicians. (2017). *National Early Warning Score (NEWS) 2: Standardising the assessment of acute-illness severity in the NHS*. RCP London. https://www.rcplondon.ac.uk/projects/outputs/national-early-warning-score-news-2

Shortliffe, E. H., & Sepúlveda, M. J. (2018). Clinical decision support in the era of artificial intelligence. *JAMA*, 320(21), 2199-2200. https://doi.org/10.1001/jama.2018.17163

World Health Organization. (2021). *Ethics and governance of artificial intelligence for health: WHO guidance*. World Health Organization. https://www.who.int/publications/i/item/9789240029200

---

## Appendix A: Sample Egyptian Arabic Keywords by Category

### A.1 Silent MI (Level 2)
| Arabic | Transliteration | English Translation |
|--------|-----------------|---------------------|
| روحي بتتسحب مني | ro7y betetsa7ab menny | My soul is being pulled out (sense of doom) |
| عرقان تلج | 3ar2an talg | Sweating ice cold |
| هبطان ومعدتي مقلوبة | habtan w me3dety ma2loba | Fatigued with upset stomach |
| معدتي واجعاني وبعرق | me3dety wag3any w ba3ra2 | Stomach hurts and sweating |

### A.2 Pediatric Emergencies (Level 2)
| Arabic | Transliteration | English Translation |
|--------|-----------------|---------------------|
| الواد طري خالص | el wad tarry khales | The boy is very floppy |
| مش بيعيط حتى | mesh bey3ayat 7atta | Not even crying |
| برازه زي الجيلي | barazo zay el gelly | Stool like jelly (intussusception) |
| اليافوخ منفوخ | el yafoukh manfoukh | Fontanelle is bulging |

### A.3 DKA (Level 2)
| Arabic | Transliteration | English Translation |
|--------|-----------------|---------------------|
| ريحة بقه زي التفاح المعفن | re7et bo2o zay el toffa7 | Mouth smells like rotten apples |
| نفسه عالي وعطشان موت | nafaso 3aly w 3atshan moot | Breathing high and dying of thirst |
| بيتنفس من بطنه | beyetnafes men batno | Breathing from belly (Kussmaul) |

---

## Appendix B: System Requirements

### B.1 Technical Specifications
- **Runtime:** Python 3.9+
- **Framework:** FastAPI
- **Database:** JSON-based keyword store (no external DB required)
- **AI API:** Google Gemini (optional)
- **Memory:** Minimum 512MB RAM
- **Storage:** 50MB for application + keywords

### B.2 Deployment Options
1. **Cloud:** Render, Heroku, AWS, GCP
2. **On-Premise:** Docker container or direct installation
3. **Offline:** Full functionality in Standard Mode without internet

---

*Document Version: 2.0*
*Last Updated: February 2026*
*Author: Ahmed Zayed, MBBCh*
*Institution: SAFE-Triage Project*
