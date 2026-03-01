"""SAFE-Triage AI Service - Vertex AI + UMLS RAG"""
import atexit
import os
import json
import logging
import re
import time
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError
from typing import Any, Dict, List, Optional
import vertexai

# Support both GA and preview Vertex AI SDKs across versions.
try:
    from vertexai.generative_models import GenerativeModel
except Exception:  # pragma: no cover - runtime fallback
    from vertexai.preview.generative_models import GenerativeModel
from umls_rag import UMLSMedicalRAG, SNOMEDResult

logger = logging.getLogger(__name__)

SNOMED_EXTRACTION_PROMPT = """
You are a medical coding expert for emergency department triage.
Extract ONLY explicitly stated symptoms and map each symptom to SNOMED-CT.

SNOMED MAPPING RULES - CRITICAL:
1. NEVER assign trauma-related codes (post-traumatic, fracture, injury) unless trauma/accident/fall/injury is explicitly reported.
2. NEVER assign specific etiology/diagnosis codes when only symptoms are reported.
   - "headache" -> 25064002 (Headache), NOT 95659009 (Post-traumatic headache) unless trauma is explicit
   - "nosebleed" -> 12441001 (Epistaxis)
   - "chest pain" -> 29857009 (Chest pain), NOT MI unless explicitly diagnosed
3. When multiple symptoms are reported, map EACH symptom and return an array of codes.
4. If uncertain, prefer a general parent symptom code rather than a specific child etiology.
5. For ICD-10 mapping: use symptom chapter codes (R00-R99) when presentation is symptom-only.
6. Do NOT use R69 (Illness unspecified) when a specific symptom ICD-10 exists.

SEMANTIC SAFETY:
- Category must match complaint context.
- If confidence < 0.70 for a code candidate, discard it.

PATIENT COMPLAINT: {complaint}

Return JSON only:
{
  "symptoms_extracted": ["explicit symptoms only"],
  "snomed_codes": [
    {"code": "...", "term": "...", "confidence": 0.0-1.0, "reasoning": "..."}
  ],
  "icd10_codes": [
    {"code": "...", "description": "..."}
  ],
  "primary_category": "neurological|cardiac|trauma|respiratory|gi|other",
  "validation_passed": true|false
}

If no safe confident mapping exists: return empty snomed_codes array.
"""

EXPECTED_RESOURCE_ORDER = [
    "labs",
    "ecg",
    "imaging",
    "iv_meds_or_fluids",
    "procedure",
    "specialty_consult",
    "monitoring",
]

EXPECTED_RESOURCE_ALIASES = {
    "labs": "labs",
    "lab": "labs",
    "blood_work": "labs",
    "bloodwork": "labs",
    "urinalysis": "labs",
    "cultures": "labs",
    "ecg": "ecg",
    "ekg": "ecg",
    "electrocardiogram": "ecg",
    "imaging": "imaging",
    "xray": "imaging",
    "x_ray": "imaging",
    "ct": "imaging",
    "ultrasound": "imaging",
    "mri": "imaging",
    "iv_fluids": "iv_meds_or_fluids",
    "iv_medications": "iv_meds_or_fluids",
    "iv_meds": "iv_meds_or_fluids",
    "iv_meds_or_fluids": "iv_meds_or_fluids",
    "procedure": "procedure",
    "sutures": "procedure",
    "sutures_repair": "procedure",
    "splinting": "procedure",
    "incision_and_drainage": "procedure",
    "i_d": "procedure",
    "catheter": "procedure",
    "foley": "procedure",
    "specialty_consult": "specialty_consult",
    "consult": "specialty_consult",
    "consultation": "specialty_consult",
    "monitoring": "monitoring",
    "cardiac_monitoring": "monitoring",
    "continuous_pulse_ox": "monitoring",
}

RESOURCE_TRANSFER_HINTS = {
    "transfer",
    "transferred",
    "xfer",
    "outside hospital",
    "direct admit",
}

RESOURCE_URINARY_RETENTION_HINTS = {
    "urinary retention",
    "acute urinary retention",
    "retention of urine",
    "احتباس بول",
}

RESOURCE_WOUND_HINTS = {
    "wound eval",
    "wound evaluation",
    "wound",
    "laceration",
    "lac",
    "cut",
    "abrasion",
    "جرح",
    "قطع",
}

RESOURCE_WOUND_FOLLOWUP_HINTS = {
    "wound check",
    "post op wound",
    "post-op wound",
    "suture removal",
    "dressing change",
}

RESOURCE_SORE_THROAT_HINTS = {
    "sore throat",
    "throat pain",
    "التهاب حلق",
    "وجع حلق",
}

RESOURCE_FEVER_HINTS = {
    "fever",
    "febrile",
    "temp",
    "temperature",
    "حمى",
    "سخونية",
    "سخونه",
    "حرارة",
}


class ComplaintValidator:
    """Validates chief complaint text before AI processing."""

    MIN_LENGTH = 3
    MAX_LENGTH = 2000

    @staticmethod
    def validate(complaint: str) -> Dict[str, Any]:
        if complaint is None:
            complaint = ""
        text = str(complaint).strip()

        if not text:
            return {
                "valid": False,
                "error": "empty_complaint",
                "message": "Chief complaint is required",
                "message_ar": "الشكوى الرئيسية مطلوبة",
                "action": "require_reentry",
            }

        if len(text) < ComplaintValidator.MIN_LENGTH:
            return {
                "valid": False,
                "error": "complaint_too_short",
                "message": f"Chief complaint too short (minimum {ComplaintValidator.MIN_LENGTH} characters)",
                "message_ar": "الشكوى قصيرة جدًا (الحد الأدنى 3 أحرف)",
                "action": "require_reentry",
            }

        if len(text) > ComplaintValidator.MAX_LENGTH:
            return {
                "valid": False,
                "error": "complaint_too_long",
                "message": f"Chief complaint too long (maximum {ComplaintValidator.MAX_LENGTH} characters)",
                "message_ar": f"الشكوى طويلة جدًا (الحد الأقصى {ComplaintValidator.MAX_LENGTH} حرف)",
                "action": "require_reentry",
            }

        if re.match(r'^\d+$', text):
            return {
                "valid": False,
                "error": "numbers_only",
                "message": "Chief complaint cannot be only numbers",
                "message_ar": "لا يمكن أن تكون الشكوى أرقامًا فقط",
                "action": "require_reentry",
            }

        if re.match(r'^[^a-zA-Zأ-ي0-9]+$', text):
            return {
                "valid": False,
                "error": "special_chars_only",
                "message": "Chief complaint must contain words",
                "message_ar": "يجب أن تحتوي الشكوى على كلمات",
                "action": "require_reentry",
            }

        has_letters = bool(re.search(r'[a-zA-Zأ-ي]', text))
        if not has_letters:
            return {
                "valid": False,
                "error": "no_letters_detected",
                "message": "Chief complaint must contain letters (Arabic or English)",
                "message_ar": "يجب أن تحتوي الشكوى على حروف (عربية أو إنجليزية)",
                "action": "require_reentry",
            }

        word_count = len(text.split())
        if word_count < 2 and len(text) < 10:
            return {
                "valid": False,
                "error": "insufficient_detail",
                "message": "Chief complaint needs more detail (at least 2 words)",
                "message_ar": "الشكوى تحتاج تفاصيل أكثر (كلمتان على الأقل)",
                "action": "prompt_elaboration",
            }

        return {"valid": True}


class AIService:
    def __init__(self):
        self.client = None
        self.mode = "none"
        self.model_name = "gemini-2.5-flash"
        self.gemini_timeout_seconds = float(os.getenv("GEMINI_TIMEOUT_SECONDS", "15.0"))
        self.snomed_timeout_seconds = float(os.getenv("SNOMED_GEMINI_TIMEOUT_SECONDS", "2.0"))
        self._executor = ThreadPoolExecutor(max_workers=int(os.getenv("GEMINI_WORKERS", "4")))
        atexit.register(lambda: self._executor.shutdown(wait=False, cancel_futures=True))
        
        # Initialize UMLS RAG
        cache_path = os.path.join(os.path.dirname(__file__), "umls_cache.db")
        self.umls_rag = UMLSMedicalRAG(cache_path)
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

    def _generate_content_with_timeout(self, prompt: str, timeout_seconds: float, label: str):
        if not self.client:
            raise RuntimeError("Vertex client unavailable")
        started = time.perf_counter()
        future = self._executor.submit(self.client.generate_content, prompt)
        try:
            response = future.result(timeout=timeout_seconds)
            print(
                f"[Timing] {label}: {(time.perf_counter() - started):.3f}s",
                flush=True,
            )
            return response
        except FutureTimeoutError as exc:
            future.cancel()
            raise TimeoutError(f"{label} timed out after {timeout_seconds:.1f}s") from exc

    @staticmethod
    def _sanitize_confidence(value: Any, default: float = 0.80) -> float:
        try:
            parsed = float(value)
        except (TypeError, ValueError):
            parsed = float(default)
        return max(0.0, min(1.0, parsed))

    @staticmethod
    def _normalize_text(value: Any) -> str:
        return (
            str(value or "")
            .strip()
            .lower()
            .replace("أ", "ا")
            .replace("إ", "ا")
            .replace("آ", "ا")
            .replace("-", " ")
        )

    @classmethod
    def _normalize_expected_resource(cls, value: Any) -> Optional[str]:
        normalized = cls._normalize_text(value).replace(" ", "_")
        if not normalized:
            return None
        return EXPECTED_RESOURCE_ALIASES.get(normalized)

    @classmethod
    def _normalize_expected_resources(cls, values: Any) -> List[str]:
        if values is None:
            return []
        if isinstance(values, str):
            stripped = values.strip()
            if not stripped:
                return []
            if stripped.startswith("["):
                try:
                    values = json.loads(stripped)
                except Exception:
                    values = [item.strip() for item in stripped.strip("[]").split(",") if item.strip()]
            else:
                values = [item.strip() for item in stripped.split(",") if item.strip()]

        if not isinstance(values, list):
            return []

        normalized: List[str] = []
        seen = set()
        for item in values:
            mapped = cls._normalize_expected_resource(item)
            if not mapped or mapped in seen:
                continue
            normalized.append(mapped)
            seen.add(mapped)
        return normalized

    @classmethod
    def _infer_resources_from_workup(cls, recommended_workup: Any) -> List[str]:
        if not isinstance(recommended_workup, list):
            return []

        inferred: List[str] = []
        for item in recommended_workup:
            text = cls._normalize_text(item)
            if not text:
                continue
            if any(token in text for token in {"cbc", "cmp", "lab", "blood", "urinalysis", "culture"}):
                inferred.append("labs")
            if any(token in text for token in {"ecg", "ekg", "electrocardiogram"}):
                inferred.append("ecg")
            if any(token in text for token in {"x ray", "xray", "ct", "ultrasound", "mri", "imaging"}):
                inferred.append("imaging")
            if any(token in text for token in {"iv", "intravenous", "cannula", "fluid", "medication"}):
                inferred.append("iv_meds_or_fluids")
            if any(
                token in text
                for token in {"suture", "splint", "catheter", "foley", "i&d", "incision", "drainage", "procedure"}
            ):
                inferred.append("procedure")
            if any(token in text for token in {"consult", "specialty", "specialist"}):
                inferred.append("specialty_consult")
            if any(token in text for token in {"monitor", "telemetry", "pulse ox", "continuous"}):
                inferred.append("monitoring")
        return cls._normalize_expected_resources(inferred)

    @classmethod
    def _has_any_hint(cls, text: str, hints: set[str]) -> bool:
        return any(cls._normalize_text(hint) in text for hint in hints)

    @classmethod
    def _apply_resource_expectation_overrides(cls, result: Dict[str, Any], patient_data: Dict[str, Any]) -> None:
        expected_resources = cls._normalize_expected_resources(result.get("expected_resources"))
        inferred_from_workup = cls._infer_resources_from_workup(result.get("recommended_workup"))
        expected_resources = cls._normalize_expected_resources(expected_resources + inferred_from_workup)

        raw_count = result.get("resource_count")
        try:
            resource_count = int(float(raw_count))
        except (TypeError, ValueError):
            resource_count = len(expected_resources)

        complaint = cls._normalize_text(
            patient_data.get("chief_complaint_text")
            or patient_data.get("chief_complaint")
            or ""
        )
        category = cls._normalize_text(result.get("category"))
        symptoms = " ".join(cls._normalize_text(item) for item in (result.get("extracted_symptoms") or []))
        impression = cls._normalize_text(result.get("clinical_impression"))
        reasoning = cls._normalize_text(result.get("reasoning"))
        combined = " ".join([complaint, category, symptoms, impression, reasoning]).strip()

        has_transfer = cls._has_any_hint(combined, RESOURCE_TRANSFER_HINTS)
        has_urinary_retention = cls._has_any_hint(combined, RESOURCE_URINARY_RETENTION_HINTS)
        has_wound = cls._has_any_hint(combined, RESOURCE_WOUND_HINTS)
        is_wound_followup = cls._has_any_hint(combined, RESOURCE_WOUND_FOLLOWUP_HINTS)
        has_sore_throat = cls._has_any_hint(combined, RESOURCE_SORE_THROAT_HINTS)
        has_fever = cls._has_any_hint(combined, RESOURCE_FEVER_HINTS)

        if has_transfer:
            expected_resources = cls._normalize_expected_resources(
                expected_resources + ["specialty_consult", "monitoring"]
            )
            resource_count = max(resource_count, 2)
            if category in {"", "minor_complaint", "unclear", "unknown"}:
                result["category"] = "transfer_patient"

        if has_urinary_retention:
            expected_resources = cls._normalize_expected_resources(expected_resources + ["procedure", "labs"])
            resource_count = max(resource_count, 2)
            if category in {"", "minor_complaint", "unclear", "unknown"}:
                result["category"] = "urinary_retention"

        if has_wound:
            expected_resources = cls._normalize_expected_resources(expected_resources + ["procedure"])
            if is_wound_followup:
                resource_count = max(resource_count, 1)
            else:
                expected_resources = cls._normalize_expected_resources(expected_resources + ["imaging"])
                resource_count = max(resource_count, 2)
            if category in {"", "minor_complaint", "unclear", "unknown"}:
                result["category"] = "minor_laceration"

        if has_sore_throat and has_fever:
            expected_resources = cls._normalize_expected_resources(expected_resources + ["labs", "imaging"])
            resource_count = max(resource_count, 2)
            if category in {"", "minor_complaint", "unclear", "unknown"}:
                result["category"] = "sore_throat"
        elif has_sore_throat:
            expected_resources = cls._normalize_expected_resources(expected_resources + ["labs"])
            resource_count = max(resource_count, 1)
            if category in {"", "minor_complaint", "unclear", "unknown"}:
                result["category"] = "sore_throat"

        resource_count = max(resource_count, len(expected_resources))
        resource_count = max(0, min(int(resource_count), 10))
        result["expected_resources"] = expected_resources
        result["resource_count"] = resource_count

    def analyze_triage(self, patient_data: dict):
        if not self.client:
            return None

        complaint = patient_data.get('chief_complaint_text') or patient_data.get('chief_complaint') or ""
        validation = ComplaintValidator.validate(complaint)
        if not validation.get("valid", False):
            return {
                "success": False,
                "error": validation["error"],
                "message": validation["message"],
                "message_ar": validation.get("message_ar"),
                "action": validation["action"],
                "confidence_score": 0.0,
            }

        prompt = f"""You are an ER triage expert. Analyze and respond with ONLY valid JSON (no markdown).

Patient: Age {patient_data.get('age')}, {patient_data.get('gender')}
Complaint: {patient_data.get('chief_complaint_text')}
Vitals: {json.dumps(patient_data.get('vitals', {}))}

Important classification hints:
- Neurologic red flags (facial droop, arm weakness, slurred speech, cannot move, one-sided numbness, worst headache of life, وشي مايل, دراعي مش بيتحرك, نص جسمي تنمل, مش قادر اتكلم, بلع لساني) should be treated as possible stroke.
- Extract these neurologic features explicitly in extracted_symptoms when present.
- Silent MI red flags: if patient has diabetes AND atypical GI symptoms (epigastric pain, heartburn, indigestion, dyspepsia, ألم فم المعدة, حرقان المعدة) AND fatigue/weakness/nausea,
  then treat as atypical ACS risk, set cardiac concern, and do NOT downplay based on words like mild/خفيف.
- Confidence calibration: for classic, unambiguous patterns (e.g., chest pain radiating to left arm), set confidence >= 0.85.
Use these internal categories when reasoning: chest_pain_cardiac, stroke_symptoms, respiratory_distress, abdominal_pain, sepsis_concern, trauma_fracture, allergic_reaction, psychiatric, unclear_needs_evaluation.

For this patient, estimate expected ED resources likely needed:
- Labs (blood work, urinalysis, cultures)
- ECG
- Imaging (X-ray, CT, ultrasound)
- IV fluids or IV medications
- Procedure (sutures, splinting, I&D, catheter)
- Specialty consult
- Monitoring (cardiac monitoring, continuous pulse ox)
Return standardized resource labels using only:
["labs", "ecg", "imaging", "iv_meds_or_fluids", "procedure", "specialty_consult", "monitoring"]

Return this exact JSON structure:
{{"extracted_symptoms": ["list of symptoms"], "clinical_impression": "brief assessment", "risk_factors": [], "recommended_workup": ["tests needed"], "expected_resources": ["labs", "imaging"], "resource_count": 2, "differential_diagnosis": ["possible diagnoses"], "reasoning": "one sentence clinical reasoning in English", "reasoning_ar": "reasoning in Arabic", "followup_question": "one short follow-up question in English", "followup_question_ar": "follow-up question in Arabic", "confidence": 0.0, "confidence_rationale": "short reason for confidence level"}}"""

        try:
            print(f"🤖 Calling Vertex AI...", flush=True)
            response = self._generate_content_with_timeout(
                prompt,
                timeout_seconds=self.gemini_timeout_seconds,
                label="Gemini triage analysis call",
            )
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
            confidence_value = self._sanitize_confidence(
                result.get("confidence_score", result.get("confidence")),
                default=0.80,
            )
            result["confidence_score"] = confidence_value
            result["confidence"] = confidence_value
            
            # Add SNOMED mapping
            snomed_started = time.perf_counter()
            snomed_data = self._map_to_snomed(result, patient_data)
            print(
                f"[Timing] UMLS/SNOMED mapping: {(time.perf_counter() - snomed_started):.3f}s",
                flush=True,
            )
            result.update(snomed_data)
            self._apply_resource_expectation_overrides(result, patient_data)
            
            return result
            
        except TimeoutError as e:
            logger.error("Gemini timeout: %s", e)
            print(f"❌ Vertex AI timeout: {e}", flush=True)
            return {
                "fallback": True,
                "success": False,
                "error": "gemini_timeout",
                "fallback_reason": "timeout",
                "message": "Gemini request timed out",
                "message_ar": "انتهت مهلة طلب Gemini",
            }
        except json.JSONDecodeError as e:
            logger.error("Gemini JSON parse error: %s", e)
            print(f"❌ Vertex AI JSON parse error: {e}", flush=True)
            return {
                "fallback": True,
                "success": False,
                "error": "gemini_parse_error",
                "fallback_reason": "parse_error",
                "message": "Gemini response parsing failed",
                "message_ar": "فشل تحليل استجابة Gemini",
            }
        except Exception as e:
            logger.error("Gemini API error: %s", e)
            print(f"❌ Vertex AI error: {e}", flush=True)
            return {
                "fallback": True,
                "success": False,
                "error": "gemini_api_error",
                "fallback_reason": "api_error",
                "message": "Gemini API request failed",
                "message_ar": "فشل طلب Gemini API",
            }
    
    def _map_to_snomed(self, gemini_result: dict, patient_data: dict) -> dict:
        """Map to SNOMED + ICD-10"""
        complaint = patient_data.get('chief_complaint_text', '')
        symptoms = gemini_result.get("extracted_symptoms") or []
        extracted = self._extract_snomed_with_prompt(
            complaint,
            symptoms=symptoms,
            patient_data=patient_data,
        )
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

        extracted_features = {
            "chief_complaint": complaint,
            "symptoms": symptoms,
            "comorbidities": patient_data.get("comorbidities") or [],
        }

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
            normalized = complaint.replace("أ", "ا").lower()
            keyword_fallbacks = [
                {
                    "tokens": ["chest pain", "left arm", "radiating", "الم صدر", "ألم صدر", "صدري"],
                    "code": "29857009",
                    "term": "Chest pain",
                    "category": "chest_pain_cardiac",
                    "esi_default": 2,
                    "red_flag": True,
                },
                {
                    "tokens": ["dyspnea", "shortness of breath", "ضيق نفس", "مش قادر اتنفس"],
                    "code": "267036007",
                    "term": "Dyspnea",
                    "category": "respiratory_distress",
                    "esi_default": 2,
                    "red_flag": True,
                },
                {
                    "tokens": ["headache", "صداع", "cephalalgia"],
                    "code": "25064002",
                    "term": "Headache",
                    "category": "headache_mild",
                    "esi_default": 3,
                    "red_flag": False,
                },
                {
                    "tokens": ["nosebleed", "nasal bleeding", "epistaxis", "رعاف", "نزيف الانف", "نزيف الأنف"],
                    "code": "12441001",
                    "term": "Epistaxis",
                    "category": "unclear_needs_evaluation",
                    "esi_default": 3,
                    "red_flag": False,
                },
                {
                    "tokens": ["abdominal pain", "stomach pain", "الم بطن", "ألم بطن", "بطني"],
                    "code": "21522001",
                    "term": "Abdominal pain",
                    "category": "abdominal_pain",
                    "esi_default": 3,
                    "red_flag": False,
                },
                {
                    "tokens": ["heartburn", "حرقان", "حموضة"],
                    "code": "16331000",
                    "term": "Heartburn",
                    "category": "abdominal_pain",
                    "esi_default": 3,
                    "red_flag": False,
                },
            ]
            keyword_candidates: List[SNOMEDResult] = []
            for rule in keyword_fallbacks:
                if any(token in normalized for token in rule["tokens"]):
                    safe_code = self.umls_rag.validate_snomed_mapping(rule["code"], extracted_features)
                    if not safe_code:
                        continue
                    safe_result = self.umls_rag.get_snomed_result(safe_code)
                    if safe_result is not None:
                        keyword_candidates.append(safe_result)
                        continue
                    keyword_candidates.append(
                        SNOMEDResult(
                            concept_id=safe_code,
                            term=self.umls_rag.lookup_snomed_term(safe_code) or rule["term"],
                            category=rule["category"],
                            esi_default=rule["esi_default"],
                            red_flag=rule["red_flag"],
                        )
                    )
            if keyword_candidates:
                snomed_results = keyword_candidates

        if snomed_results:
            validated_results: Dict[str, SNOMEDResult] = {}
            for result in snomed_results:
                candidate_code = str(getattr(result, "concept_id", "")).strip()
                if not candidate_code:
                    continue
                safe_code = self.umls_rag.validate_snomed_mapping(candidate_code, extracted_features)
                if not safe_code:
                    continue
                safe_result = result
                if safe_code != candidate_code:
                    looked_up = self.umls_rag.get_snomed_result(safe_code)
                    safe_result = looked_up or SNOMEDResult(
                        concept_id=safe_code,
                        term=self.umls_rag.lookup_snomed_term(safe_code) or result.term,
                        category=result.category,
                        esi_default=result.esi_default,
                        red_flag=result.red_flag,
                    )
                if safe_code not in validated_results:
                    validated_results[safe_code] = safe_result

            # Ensure multi-symptom complaints keep explicit symptom codes even when cache search
            # returns only one branch of the presentation.
            normalized = complaint.replace("أ", "ا").lower()
            supplemental_rules = [
                {
                    "tokens": ["headache", "صداع", "cephalalgia"],
                    "code": "25064002",
                    "term": "Headache",
                    "category": "headache_mild",
                    "esi_default": 3,
                    "red_flag": False,
                },
                {
                    "tokens": ["nosebleed", "nasal bleeding", "epistaxis", "رعاف", "نزيف الانف", "نزيف الأنف"],
                    "code": "12441001",
                    "term": "Epistaxis",
                    "category": "unclear_needs_evaluation",
                    "esi_default": 3,
                    "red_flag": False,
                },
            ]
            for rule in supplemental_rules:
                if not any(token in normalized for token in rule["tokens"]):
                    continue
                safe_code = self.umls_rag.validate_snomed_mapping(rule["code"], extracted_features)
                if not safe_code or safe_code in validated_results:
                    continue
                safe_result = self.umls_rag.get_snomed_result(safe_code) or SNOMEDResult(
                    concept_id=safe_code,
                    term=self.umls_rag.lookup_snomed_term(safe_code) or rule["term"],
                    category=rule["category"],
                    esi_default=rule["esi_default"],
                    red_flag=rule["red_flag"],
                )
                validated_results[safe_code] = safe_result
            snomed_results = list(validated_results.values())

        if not snomed_results:
            return {
                "snomed_code": None,
                "snomed_codes": [],
                "snomed_terms": [],
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
                    "snomed_codes": ["230690007"],
                    "snomed_terms": ["Stroke"],
                    "category": "stroke_symptoms",
                    "esi_default": 1,
                    "red_flag": True,
                    "icd10_coding": {
                        "primary_code": icd10.code,
                        "description_en": icd10.description,
                        "gahar_compliant": True
                    }
                }
        validated_code = self.umls_rag.validate_snomed_mapping(str(best.concept_id), extracted_features)
        if validated_code and validated_code != str(best.concept_id):
            safe_best = self.umls_rag.get_snomed_result(validated_code)
            if safe_best is not None:
                best = safe_best
            else:
                best = SNOMEDResult(
                    concept_id=validated_code,
                    term=self.umls_rag.lookup_snomed_term(validated_code) or best.term,
                    category=best.category,
                    esi_default=best.esi_default,
                    red_flag=best.red_flag,
                )
        icd10 = self.umls_rag.get_icd10(best.concept_id)
        
        print(f"🔍 SNOMED: {best.concept_id} - {best.category}", flush=True)
        print(f"📋 ICD-10: {icd10.code}", flush=True)

        ranked_unique: Dict[str, SNOMEDResult] = {}
        for result in sorted(snomed_results, key=lambda r: (-int(r.red_flag), r.esi_default)):
            code = str(getattr(result, "concept_id", "")).strip()
            if code and code not in ranked_unique:
                ranked_unique[code] = result
        priority_codes = []
        for code in ("25064002", "12441001", "29857009", "21522001", "267036007", "16331000"):
            if code in ranked_unique:
                priority_codes.append(code)
        for code in ranked_unique.keys():
            if code not in priority_codes:
                priority_codes.append(code)
        snomed_codes = priority_codes[:4] or [str(best.concept_id)]
        snomed_terms = [ranked_unique[code].term for code in snomed_codes if code in ranked_unique]
        if not snomed_terms:
            snomed_terms = [best.term]
        secondary_icd10: List[Dict[str, str]] = []
        for code in snomed_codes[1:4]:
            mapped = self.umls_rag.get_icd10(code)
            if mapped.code and mapped.code != icd10.code and str(mapped.code).upper() != "R69":
                secondary_icd10.append({"code": mapped.code, "description_en": mapped.description})
        
        resolved_category = "stroke_symptoms" if has_stroke_signal else best.category
        resolved_category = self._refine_internal_category(
            complaint=complaint,
            internal_category=resolved_category,
            snomed_code=str(best.concept_id),
            snomed_term=best.term,
            has_acute_stroke_signal=has_stroke_signal,
        )
        resolved_red_flag = True if has_stroke_signal else bool(best.red_flag)
        if resolved_category in {"sepsis_concern", "chest_pain_cardiac", "respiratory_distress"}:
            resolved_red_flag = True

        return {
            "snomed_code": best.concept_id,
            "snomed_term": best.term,
            "snomed_codes": snomed_codes,
            "snomed_terms": snomed_terms,
            "category": resolved_category,
            "esi_default": 1 if has_stroke_signal else best.esi_default,
            "red_flag": resolved_red_flag,
            "icd10_coding": {
                "primary_code": icd10.code,
                "description_en": icd10.description,
                "secondary_codes": secondary_icd10,
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

    def _refine_internal_category(
        self,
        complaint: str,
        internal_category: str,
        snomed_code: str,
        snomed_term: str,
        has_acute_stroke_signal: bool,
    ) -> str:
        text = (complaint or "").replace("أ", "ا").lower()
        term_l = (snomed_term or "").replace("أ", "ا").lower()
        code = str(snomed_code or "").strip()

        sepsis_signals = [
            "fever", "chills", "infection", "sepsis",
            "حراره", "حرارة", "رعشه", "رعشة", "عدوى", "تعفن",
        ]
        gi_signals = [
            "indigestion", "heartburn", "dyspepsia", "epigastric", "abdominal pain",
            "سوء هضم", "حرقان", "حموضة", "الم بطن", "ألم بطن",
        ]
        minor_wound_signals = [
            "cut", "laceration", "wound", "abrasion",
            "جرح", "قطع", "خدش",
        ]
        headache_signals = ["headache", "صداع", "cephalalgia"]
        acute_neuro_headache_signals = ["worst headache", "worst of my life", "thunderclap", "صداع مفاجئ شديد"]

        if any(s in text for s in sepsis_signals):
            return "sepsis_concern"
        if any(s in text for s in gi_signals):
            return "abdominal_pain"
        if any(s in text for s in headache_signals) and not has_acute_stroke_signal:
            # Guard against overcalling stroke on non-acute headache complaints.
            if not any(s in text for s in acute_neuro_headache_signals):
                return "headache_mild"
        if code == "250555004" and not has_acute_stroke_signal:
            return "headache_mild"
        if code == "709240003" or any(s in text for s in minor_wound_signals) or any(
            s in term_l for s in ["laceration", "wound", "cut"]
        ):
            return "minor_trauma"
        if internal_category == "stroke_symptoms" and not has_acute_stroke_signal and code == "250555004":
            return "headache_mild"
        return internal_category

    def _extract_snomed_with_prompt(
        self,
        complaint: str,
        *,
        symptoms: Optional[List[str]] = None,
        patient_data: Optional[Dict[str, Any]] = None,
    ) -> Optional[Dict[str, Any]]:
        if not complaint or not self.client:
            return None

        patient_data = patient_data or {}
        symptom_list = [str(item).strip() for item in (symptoms or []) if str(item).strip()]
        complaint_l = complaint.replace("أ", "ا").lower()
        combined_l = f"{complaint_l} {' '.join(symptom_list).replace('أ', 'ا').lower()}"
        extracted_features = {
            "chief_complaint": complaint,
            "symptoms": symptom_list,
            "comorbidities": patient_data.get("comorbidities") or [],
        }

        prompt = SNOMED_EXTRACTION_PROMPT.replace("{complaint}", complaint)
        try:
            response = self._generate_content_with_timeout(
                prompt,
                timeout_seconds=self.snomed_timeout_seconds,
                label="Gemini SNOMED extraction call",
            )
            parsed = self._parse_json_response(getattr(response, "text", ""))
            if not isinstance(parsed, dict):
                return None

            primary_category = parsed.get("primary_category", "other")
            candidates = parsed.get("snomed_codes") or []
            merged_candidates: Dict[str, Dict[str, Any]] = {}

            def add_candidate(code: str, term: str, confidence: float) -> None:
                safe_code = self.umls_rag.validate_snomed_mapping(code, extracted_features)
                if not safe_code:
                    return
                safe_term = (term or "").strip() or self.umls_rag.lookup_snomed_term(safe_code) or safe_code
                existing = merged_candidates.get(safe_code)
                confidence_clamped = max(0.0, min(1.0, float(confidence)))
                if existing and float(existing.get("confidence", 0.0)) >= confidence_clamped:
                    return
                merged_candidates[safe_code] = {
                    "code": safe_code,
                    "term": safe_term,
                    "confidence": confidence_clamped,
                }

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
                add_candidate(code, term, confidence)

            deterministic_rules = [
                {"tokens": ["headache", "صداع"], "code": "25064002", "term": "Headache"},
                {"tokens": ["nosebleed", "nasal bleeding", "epistaxis", "رعاف", "نزيف الانف", "نزيف الأنف"], "code": "12441001", "term": "Epistaxis"},
                {"tokens": ["chest pain", "الم صدر", "ألم صدر", "صدري"], "code": "29857009", "term": "Chest pain"},
                {"tokens": ["abdominal pain", "stomach pain", "الم بطن", "ألم بطن", "بطني"], "code": "21522001", "term": "Abdominal pain"},
                {"tokens": ["shortness of breath", "dyspnea", "ضيق نفس", "مش قادر اتنفس", "مش قادر أتنفس", "نهجان"], "code": "267036007", "term": "Dyspnea"},
                {"tokens": ["heartburn", "حرقان", "حموضة"], "code": "16331000", "term": "Heartburn"},
            ]
            for rule in deterministic_rules:
                if any(token in combined_l for token in rule["tokens"]):
                    add_candidate(rule["code"], rule["term"], 0.96)

            if self.umls_rag.has_trauma_evidence(extracted_features) and any(
                token in combined_l for token in ["headache", "صداع"]
            ):
                add_candidate("95659009", "Post-traumatic headache", 0.92)

            valid_candidates = sorted(
                merged_candidates.values(),
                key=lambda item: item["confidence"],
                reverse=True,
            )
            if not valid_candidates:
                return None

            best = valid_candidates[0]
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
                best = merged_candidates.get("230690007") or {
                    "code": "230690007",
                    "term": "Stroke",
                    "confidence": 0.99,
                }
                merged_candidates["230690007"] = best
                valid_candidates = sorted(
                    merged_candidates.values(),
                    key=lambda item: item["confidence"],
                    reverse=True,
                )

            icd10 = self.umls_rag.get_icd10(best["code"])
            secondary_icd10: List[Dict[str, str]] = []
            for item in valid_candidates[1:4]:
                mapped = self.umls_rag.get_icd10(item["code"])
                if mapped.code and mapped.code != icd10.code and str(mapped.code).upper() != "R69":
                    secondary_icd10.append({"code": mapped.code, "description_en": mapped.description})

            internal_category = self._map_primary_to_internal(primary_category)
            internal_category = self._refine_internal_category(
                complaint=complaint,
                internal_category=internal_category,
                snomed_code=best["code"],
                snomed_term=best["term"],
                has_acute_stroke_signal=has_acute_stroke_signal,
            )
            comorbidities_l = str(patient_data.get("comorbidities", [])).replace("أ", "ا").lower()
            has_diabetes = any(token in comorbidities_l for token in ["diabetes", "dm", "سكري", "سكر"])
            high_cardiac_risk = bool(patient_data.get("history_cardiac", False)) or any(
                token in comorbidities_l
                for token in ["hypertension", "hyperlipidemia", "smoker", "coronary", "cad", "cardiac", "heart failure"]
            )
            has_gi_signal = any(
                token in combined_l
                for token in [
                    "epigastric", "indigestion", "heartburn", "dyspepsia",
                    "stomach pain", "abdominal pain", "حرقان", "حموضة", "فم المعدة", "معدة",
                ]
            )
            has_atypical_signal = any(
                token in combined_l
                for token in [
                    "fatigue", "weakness", "nausea", "diaphoresis", "sweating",
                    "تعب", "ضعف", "غثيان", "عرق", "دوخة", "هبطان",
                ]
            )
            age = float(patient_data.get("age") or 0)
            force_silent_mi = (
                (has_diabetes and age >= 50 and has_gi_signal)
                or (high_cardiac_risk and age >= 65 and has_gi_signal)
                or ((has_diabetes or high_cardiac_risk) and age >= 45 and has_gi_signal and has_atypical_signal)
            )
            if force_silent_mi:
                internal_category = "chest_pain_cardiac"

            red_flag = internal_category in {"stroke_symptoms", "chest_pain_cardiac", "respiratory_distress"}
            if internal_category == "sepsis_concern":
                red_flag = True
            if force_silent_mi:
                red_flag = True
            esi_default = 2 if red_flag else 3

            snomed_codes = [item["code"] for item in valid_candidates[:4]]
            snomed_terms = [item["term"] for item in valid_candidates[:4]]

            result = {
                "snomed_code": best["code"],
                "snomed_term": best["term"],
                "snomed_codes": snomed_codes,
                "snomed_terms": snomed_terms,
                "category": internal_category,
                "esi_default": esi_default,
                "red_flag": red_flag,
                "icd10_coding": {
                    "primary_code": icd10.code,
                    "description_en": icd10.description,
                    "secondary_codes": secondary_icd10,
                    "gahar_compliant": True,
                },
            }
            if force_silent_mi:
                result["red_flags"] = ["silent_mi_risk", "atypical_acs_diabetic"]
            return result
        except Exception:
            return None

ai_service = AIService()
# Upgraded to gemini-2.5-flash Sat Feb 14 22:15:13 EET 2026
