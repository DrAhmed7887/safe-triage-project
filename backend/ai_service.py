import os
import json
from google import genai
from google.genai import types
from dotenv import load_dotenv

load_dotenv()

class AIService:
    def __init__(self):
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            print("Warning: GEMINI_API_KEY not found in environment variables.")
            self.client = None
        else:
            self.client = genai.Client(api_key=api_key)
            print("[Gemini] AI Service initialized with new SDK")

    def analyze_triage(self, patient_data: dict):
        """
        Analyze patient data using AI.
        
        AUDIT FIX: No longer returns hardcoded Level 3 on failure.
        Instead returns a flag to force deterministic engine fallback.
        This prevents dangerous under-triage of actual emergencies.
        """
        if not self.client:
            # AUDIT FIX: Return fallback flag, NOT hardcoded level
            return {
                "error": "AI_UNAVAILABLE",
                "fallback": True,
                "message": "AI Service not configured (Missing API Key). System will use deterministic triage.",
                "message_ar": "خدمة الذكاء الاصطناعي غير متاحة. سيستخدم النظام الفرز الحتمي."
            }

        # Helper to format vitals
        raw_vitals = patient_data.get('vitals', {})
        formatted_vitals = {}
        # Ensure we capture all standard vitals, marking missing ones explicitly
        standard_keys = ['hr', 'rr', 'spo2', 'temp', 'sbp', 'dbp', 'gcs', 'pain_score']
        for key in standard_keys:
            val = raw_vitals.get(key)
            if val is None:
                formatted_vitals[key] = "Not Recorded"
            else:
                formatted_vitals[key] = val

        prompt = f"""
        You are an expert ER doctor in an Egyptian hospital. Analyze the patient and respond in JSON only.
        
        CRITICAL INSTRUCTION - Missing Vital Signs:
        - If a vital sign is missing, null, or marked "Not Recorded":
          * State explicitly: "[Vital] not available for assessment"
          * Do NOT infer, estimate, or assume any value
          * Adjust triage reasoning to acknowledge this data gap
          * If missing vitals are critical for accurate triage (e.g. absent HR/BP in chest pain), note this limitation and consider it a red flag.
        - NEVER use phrases like "vitals appear normal" or "vitals are stable" unless ALL critical vitals (HR, RR, BP, SpO2) are present and within normal range.
        
        Patient Data:
        Age: {patient_data.get('age')}
        Gender: {patient_data.get('gender')}
        Complaint: {patient_data.get('chief_complaint_text')}
        Vitals: {json.dumps(formatted_vitals)}
        
        Format Requirement:
        {{
            "symptoms": ["list of extracted symptoms"],
            "severity": "mild/moderate/severe",
            "red_flags": ["list any red flags or empty array"],
            "triage_level": 1-5 (Integer),
            "reasoning": "brief clinical reasoning in English",
            "reasoning_ar": "التفسير السريري بالعربي",
            "followup_question": "single most important question to ask patient",
            "followup_question_ar": "السؤال بالعربي"
        }}
        """

        try:
            response = self.client.models.generate_content(
                model='gemini-2.0-flash',
                contents=prompt
            )
            # Clean response if it contains markdown code blocks
            text = response.text.replace("```json", "").replace("```", "").strip()
            return json.loads(text)
        except Exception as e:
            print(f"AI Error: {e}")
            # AUDIT FIX: Return fallback flag, NOT hardcoded level
            # This ensures the deterministic engine handles the patient safely
            return {
                "error": "AI_FAILED",
                "fallback": True,
                "message": f"AI temporarily unavailable - using deterministic triage",
                "message_ar": "فشل تحليل الذكاء الاصطناعي. سيستخدم النظام الفرز الحتمي."
            }
