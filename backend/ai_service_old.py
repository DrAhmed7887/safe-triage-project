"""SAFE-Triage AI Service - Vertex AI"""
import os
import json
import re
import vertexai
from vertexai.generative_models import GenerativeModel

class AIService:
    def __init__(self):
        self.client = None
        self.mode = "none"
        self.model_name = "gemini-2.0-flash-001"

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

Return this exact JSON structure:
{{"extracted_symptoms": ["list of symptoms"], "clinical_impression": "brief assessment", "risk_factors": [], "recommended_workup": ["tests needed"], "differential_diagnosis": ["possible diagnoses"]}}"""

        try:
            print(f"🤖 Calling Vertex AI...", flush=True)
            response = self.client.generate_content(prompt)
            text = response.text.strip()
            print(f"📝 Response: {text[:150]}...", flush=True)
            
            # Clean markdown formatting
            text = re.sub(r'^```json\s*', '', text)
            text = re.sub(r'\s*```$', '', text)
            text = re.sub(r'^```\s*', '', text)
            
            result = json.loads(text.strip())
            print(f"✅ Vertex AI success!", flush=True)
            return result
        except Exception as e:
            print(f"❌ Vertex AI error: {e}", flush=True)
            return None

ai_service = AIService()
