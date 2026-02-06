"""SAFE-Triage AI Service - Vertex AI + UMLS RAG"""
import os
import json
import re
from typing import Any, Dict, List, Optional
import vertexai

# Support both GA and preview Vertex AI SDKs across versions.
try:
    from vertexai.generative_models import GenerativeModel
except Exception:  # pragma: no cover - runtime fallback
    from vertexai.preview.generative_models import GenerativeModel
from umls_rag import UMLSMedicalRAG

SNOMED_EXTRACTION_PROMPT = """
You are a medical coding expert for emergency department triage. Extract symptoms and map to SNOMED-CT codes.

CRITICAL RULES:
1. Extract ONLY explicitly stated symptoms
2. Code must match complaint category (neurological != cardiac != trauma)
3. If uncertain (confidence <70%) -> return empty array
4. One complaint may need MULTIPLE codes

SEMANTIC CATEGORIES:

NEUROLOGICAL: facial droop, weakness, speech problems (وجه وقع، ضعف، مش قادر اتكلم)
-> Valid: 230690007 (Stroke), 26544005 (Muscle weakness), 29164008 (Dysarthria)
-> Forbidden: 225566008 (Chest pain), 52072009 (Heat stroke)

CARDIAC: chest pain, صدري بيوجعني, radiating to arm
-> Valid: 225566008 (Ischemic chest pain), 29857009 (Chest pain)
-> Forbidden: 263204007 (Fracture), 230690007 (Stroke)

TRAUMA: fracture, كسر, injury, إصابة
-> Valid: 263204007 (Fracture), 417163006 (Traumatic injury)
-> Forbidden: 225566008 (Chest pain), 230690007 (Stroke)

VALIDATION STEPS:
1. Extract all symptoms from complaint
2. Identify primary category (neuro/cardiac/trauma/GI/respiratory)
3. Find candidate SNOMED codes
4. Verify: Does code category match complaint category?
5. Score confidence (>90% = high, 70-89% = medium, <70% = reject)

PATIENT COMPLAINT: {complaint}

Return JSON only:
{
  "symptoms_extracted": ["..."],
  "snomed_codes": [
    {"code": "...", "term": "...", "confidence": 0.0-1.0, "reasoning": "..."}
  ],
  "primary_category": "neurological|cardiac|trauma|respiratory|gi|other",
  "validation_passed": true|false
}

If confidence <70% or category mismatch: return empty snomed_codes array.
"""

class AIService:
    def __init__(self):
        self.client = None
        self.mode = "none"
        self.model_name = "gemini-2.0-flash-001"
        
        # Initialize UMLS RAG
        self.umls_rag = UMLSMedicalRAG("umls_cache.db")
        print(f"✅ UMLS RAG initialized", flush=True)

        try:
            vertexai.init(project="safe-triage-ai", location="us-central1")
            self.client = GenerativeModel(self.model_name)
            print(f"✅ Vertex AI initialized with {self.model_name}", flush=True)
            self.mode = "vertex_ai"
        except Exception as e:
            print(f"❌ Vertex AI init failed: {e}", flush=True)

    def get_status(self):
        return {"status": "ok" if self.client else "unavailable", "mode": self.mode, "model": self.model_name}

    def analyze_triage(self, patient_data: dict):
        if not self.client:
            return None

        prompt = f"""You are an ER triage expert. Analyze and respond with ONLY valid JSON (no markdown).

Patient: Age {patient_data.get('age')}, {patient_data.get('gender')}
Complaint: {patient_data.get('chief_complaint_text')}
Vitals: {json.dumps(patient_data.get('vitals', {}))}

Important classification hints:
- Neurologic red flags (facial droop, arm weakness, slurred speech, cannot move, one-sided numbness, worst headache of life, وشي مايل, دراعي مش بيتحرك, نص جسمي تنمل, مش قادر اتكلم, بلع لساني) should be treated as possible stroke.
- Extract these neurologic features explicitly in extracted_symptoms when present.
Use these internal categories when reasoning: chest_pain_cardiac, stroke_symptoms, respiratory_distress, abdominal_pain, sepsis_concern, trauma_fracture, allergic_reaction, psychiatric, unclear_needs_evaluation.

Return this exact JSON structure:
{{"extracted_symptoms": ["list of symptoms"], "clinical_impression": "brief assessment", "risk_factors": [], "recommended_workup": ["tests needed"], "differential_diagnosis": ["possible diagnoses"], "reasoning": "one sentence clinical reasoning in English", "reasoning_ar": "reasoning in Arabic", "followup_question": "one short follow-up question in English", "followup_question_ar": "follow-up question in Arabic"}}"""

        try:
            print(f"🤖 Calling Vertex AI...", flush=True)
            response = self.client.generate_content(prompt)
            text = response.text.strip()
            
            # Clean markdown
            text = re.sub(r'^```json\s*', '', text)
            text = re.sub(r'\s*```$', '', text)
            text = re.sub(r'^```\s*', '', text)
            
            result = json.loads(text.strip())
            print(f"✅ Vertex AI success!", flush=True)

            # Ensure optional fields exist to avoid empty UI slots
            if not result.get("reasoning"):
                result["reasoning"] = result.get("clinical_impression", "")
            if not result.get("reasoning_ar"):
                result["reasoning_ar"] = ""
            if not result.get("followup_question"):
                result["followup_question"] = ""
            if not result.get("followup_question_ar"):
                result["followup_question_ar"] = ""
            
            # Add SNOMED mapping
            snomed_data = self._map_to_snomed(result, patient_data)
            result.update(snomed_data)
            
            return result
            
        except Exception as e:
            print(f"❌ Vertex AI error: {e}", flush=True)
            return None
    
    def _map_to_snomed(self, gemini_result: dict, patient_data: dict) -> dict:
        """Map to SNOMED + ICD-10"""
        complaint = patient_data.get('chief_complaint_text', '')
        symptoms = gemini_result.get("extracted_symptoms") or []
        extracted = self._extract_snomed_with_prompt(complaint)
        if extracted:
            return extracted

        stroke_keywords = [
            "facial droop",
            "arm weakness",
            "slurred speech",
            "can't move",
            "cannot move",
            "can't move one side",
            "cannot move one side",
            "numbness one side",
            "one sided numbness",
            "one-sided numbness",
            "worst of my life",
            "worst headache",
            "thunderclap headache",
            "وشي مايل",
            "دراعي مش بيتحرك",
            "نص جسمي تنمل",
            "مش قادر اتكلم",
            "بلع لساني",
            "نص وشي وقع",
            "صداع مفاجئ شديد",
        ]

        search_terms = []
        for s in symptoms:
            if isinstance(s, str) and s.strip():
                search_terms.append(s.strip())
        if complaint and complaint not in search_terms:
            search_terms.append(complaint)

        normalized_all_text = " ".join(search_terms).replace("أ", "ا").lower()
        has_stroke_signal = any(k.replace("أ", "ا").lower() in normalized_all_text for k in stroke_keywords)
        if has_stroke_signal:
            # Push stroke-focused queries first so cache search favors neurologic concepts.
            search_terms = [
                "stroke",
                "stroke symptoms",
                "cerebrovascular accident",
                "facial droop",
                "arm weakness",
                "slurred speech",
            ] + search_terms

        snomed_results = []
        for term in search_terms:
            snomed_results.extend(self.umls_rag.search_snomed(term))

        if not snomed_results:
            arabic_fallbacks = {
                "مش قادر اتنفس": "dyspnea",
                "مش قادر أتنفس": "dyspnea",
                "ضيق نفس": "dyspnea",
                "صعوبة في التنفس": "dyspnea",
                "نهجان": "dyspnea",
                "وشي مايل": "stroke",
                "دراعي مش بيتحرك": "stroke",
                "نص جسمي تنمل": "stroke",
                "مش قادر اتكلم": "stroke",
                "بلع لساني": "stroke",
                "نص وشي وقع": "stroke",
                "صداع مفاجئ شديد": "stroke",
            }
            normalized = complaint.replace("أ", "ا").lower()
            for phrase, mapped in arabic_fallbacks.items():
                if phrase.replace("أ", "ا") in normalized:
                    snomed_results.extend(self.umls_rag.search_snomed(mapped))
                    break
        
        if not snomed_results:
            return {
                "snomed_code": None,
                "category": "unclear_needs_evaluation",
                "icd10_coding": {
                    "primary_code": "R69",
                    "description_en": "Illness, unspecified",
                    "gahar_compliant": True
                }
            }
        
        best = sorted(
            snomed_results,
            key=lambda r: (-int(r.red_flag), r.esi_default)
        )[0]
        if has_stroke_signal:
            preferred_stroke = next(
                (r for r in snomed_results if str(getattr(r, "concept_id", "")) == "230690007"),
                None,
            )
            stroke_candidates = [
                r for r in snomed_results
                if (r.category or "").lower() == "stroke_symptoms"
                or "stroke" in (r.term or "").lower()
                or "cerebrovascular" in (r.term or "").lower()
            ]
            stroke_candidates = [
                r for r in stroke_candidates
                if "heat stroke" not in (r.term or "").lower()
                and "sunstroke" not in (r.term or "").lower()
            ]
            if preferred_stroke is not None:
                best = preferred_stroke
            elif stroke_candidates:
                best = sorted(stroke_candidates, key=lambda r: (-int(r.red_flag), r.esi_default))[0]
            elif str(getattr(best, "concept_id", "")) != "230690007":
                # Canonical emergency fallback for acute stroke language.
                icd10 = self.umls_rag.get_icd10("230690007")
                return {
                    "snomed_code": "230690007",
                    "snomed_term": "Stroke",
                    "category": "stroke_symptoms",
                    "esi_default": 1,
                    "red_flag": True,
                    "icd10_coding": {
                        "primary_code": icd10.code,
                        "description_en": icd10.description,
                        "gahar_compliant": True
                    }
                }
        icd10 = self.umls_rag.get_icd10(best.concept_id)
        
        print(f"🔍 SNOMED: {best.concept_id} - {best.category}", flush=True)
        print(f"📋 ICD-10: {icd10.code}", flush=True)
        
        return {
            "snomed_code": best.concept_id,
            "snomed_term": best.term,
            "category": "stroke_symptoms" if has_stroke_signal else best.category,
            "esi_default": 1 if has_stroke_signal else best.esi_default,
            "red_flag": True if has_stroke_signal else best.red_flag,
            "icd10_coding": {
                "primary_code": icd10.code,
                "description_en": icd10.description,
                "gahar_compliant": True
            }
        }

    def _parse_json_response(self, raw_text: str) -> Optional[Dict[str, Any]]:
        cleaned = (raw_text or "").strip()
        cleaned = re.sub(r'^```json\s*', '', cleaned)
        cleaned = re.sub(r'\s*```$', '', cleaned)
        cleaned = re.sub(r'^```\s*', '', cleaned)
        try:
            return json.loads(cleaned)
        except Exception:
            return None

    def _semantic_guard(self, primary_category: str, code: str, term: str) -> bool:
        cat = (primary_category or "").strip().lower()
        code = str(code or "").strip()
        term_l = (term or "").strip().lower()

        forbidden_by_category = {
            "neurological": {"225566008", "52072009"},
            "cardiac": {"263204007", "230690007"},
            "trauma": {"225566008", "230690007"},
        }
        if code in forbidden_by_category.get(cat, set()):
            return False

        if cat == "neurological":
            if "heat stroke" in term_l or "sunstroke" in term_l:
                return False
        if cat == "cardiac":
            if any(t in term_l for t in ["fracture", "trauma", "stroke"]):
                return False
        if cat == "trauma":
            if any(t in term_l for t in ["angina", "chest pain", "stroke"]):
                return False
        return True

    def _map_primary_to_internal(self, primary_category: str) -> str:
        mapping = {
            "neurological": "stroke_symptoms",
            "cardiac": "chest_pain_cardiac",
            "trauma": "trauma_fracture",
            "respiratory": "respiratory_distress",
            "gi": "abdominal_pain",
            "other": "unclear_needs_evaluation",
        }
        return mapping.get((primary_category or "").strip().lower(), "unclear_needs_evaluation")

    def _extract_snomed_with_prompt(self, complaint: str) -> Optional[Dict[str, Any]]:
        if not complaint or not self.client:
            return None

        prompt = SNOMED_EXTRACTION_PROMPT.replace("{complaint}", complaint)
        try:
            response = self.client.generate_content(prompt)
            parsed = self._parse_json_response(getattr(response, "text", ""))
            if not isinstance(parsed, dict):
                return None

            primary_category = parsed.get("primary_category", "other")
            candidates = parsed.get("snomed_codes") or []
            valid_candidates: List[Dict[str, Any]] = []
            for item in candidates:
                if not isinstance(item, dict):
                    continue
                code = str(item.get("code", "")).strip()
                term = str(item.get("term", "")).strip()
                conf_raw = item.get("confidence", 0)
                try:
                    confidence = float(conf_raw)
                except Exception:
                    confidence = 0.0
                if not code or confidence < 0.7:
                    continue
                if not self._semantic_guard(primary_category, code, term):
                    continue
                valid_candidates.append(
                    {
                        "code": code,
                        "term": term,
                        "confidence": confidence,
                    }
                )

            if not valid_candidates:
                return None

            best = sorted(valid_candidates, key=lambda x: x["confidence"], reverse=True)[0]
            complaint_l = complaint.replace("أ", "ا").lower()
            acute_stroke_signals = [
                "facial droop",
                "arm weakness",
                "slurred speech",
                "can't move one side",
                "cannot move one side",
                "numbness one side",
                "worst headache of my life",
                "worst of my life",
                "وشي مايل",
                "دراعي مش بيتحرك",
                "نص جسمي تنمل",
                "مش قادر اتكلم",
                "بلع لساني",
                "نص وشي وقع",
                "صداع مفاجئ شديد",
            ]
            has_acute_stroke_signal = any(
                signal.replace("أ", "ا").lower() in complaint_l for signal in acute_stroke_signals
            )
            if has_acute_stroke_signal:
                primary_category = "neurological"
                stroke_candidate = next(
                    (c for c in valid_candidates if c.get("code") == "230690007"),
                    None,
                )
                best = stroke_candidate or {"code": "230690007", "term": "Stroke", "confidence": 0.99}
            icd10 = self.umls_rag.get_icd10(best["code"])
            internal_category = self._map_primary_to_internal(primary_category)
            red_flag = internal_category in {"stroke_symptoms", "chest_pain_cardiac", "respiratory_distress"}
            esi_default = 2 if red_flag else 3

            return {
                "snomed_code": best["code"],
                "snomed_term": best["term"],
                "category": internal_category,
                "esi_default": esi_default,
                "red_flag": red_flag,
                "icd10_coding": {
                    "primary_code": icd10.code,
                    "description_en": icd10.description,
                    "gahar_compliant": True,
                },
            }
        except Exception:
            return None

ai_service = AIService()
