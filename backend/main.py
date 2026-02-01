from fastapi import FastAPI, HTTPException, Depends, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import List
import tempfile
import os
import requests
from datetime import datetime

from .models import PatientInput, TriageResult
from .logic.deterministic_triage import DeterministicTriageEngine
from .database import engine, Base, get_db
from .sql_models import Patient
import uvicorn
from .ai_service import AIService
from .medasr_service import medasr_service

# Create Tables
Base.metadata.create_all(bind=engine)

app = FastAPI(title="SAFE-Triage AI System", version="2.0.0")

# CORS Setup
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Use the deterministic engine with keyword database
engine_logic = DeterministicTriageEngine()
ai_service = AIService()

# ============ TELEGRAM ALERT FUNCTION ============
def send_critical_alert(patient_data: dict, level: int):
    """Send Telegram alert for critical patients (Level 1 or 2) via n8n"""
    if level <= 2:
        try:
            vitals = patient_data.get("vitals", {})
            payload = {
                "patient_name": f"Patient-{patient_data.get('age', 'Unknown')}",
                "age": patient_data.get("age", "N/A"),
                "triage_level": level,
                "heart_rate": vitals.get("hr", "N/A"),
                "bp": f"{vitals.get('sbp', 'N/A')}/{vitals.get('dbp', 'N/A')}",
                "chief_complaint": patient_data.get("chief_complaint_text", "")[:100],
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            response = requests.post(
                "https://drahmedzayed.app.n8n.cloud/webhook/critical-alert",
                json=payload,
                timeout=5
            )
            print(f"[ALERT] Critical patient alert sent to Telegram: {response.status_code}")
        except Exception as e:
            print(f"[ALERT] Failed to send alert: {e}")

@app.get("/")
def read_root():
    return {"message": "SAFE-Triage AI System Active", "version": "2.0.0", "features": ["Voice Input", "AI Triage", "ESI v5", "Telegram Alerts"]}

@app.post("/transcribe")
async def transcribe_audio(audio: UploadFile = File(...)):
    """🎤 Voice Input: Convert speech to medical text via Gemini"""
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
            content = await audio.read()
            tmp.write(content)
            tmp_path = tmp.name
        
        result = medasr_service.transcribe(tmp_path)
        os.unlink(tmp_path)
        
        if result["success"]:
            return {"success": True, "transcription": result["transcription"]}
        else:
            raise HTTPException(status_code=500, detail=result["error"])
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/triage", response_model=TriageResult)
def triage_patient(patient: PatientInput, db: Session = Depends(get_db)):
    try:
        result = engine_logic.evaluate(patient)
        # Send alert for critical patients
        send_critical_alert(patient.model_dump(), result.level)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/ai-triage")
def ai_triage_patient(patient: PatientInput, db: Session = Depends(get_db)):
    try:
        ai_result = ai_service.analyze_triage(patient.model_dump())
        
        if "error" in ai_result:
             std_result = engine_logic.evaluate(patient)
             # Send alert for critical patients
             send_critical_alert(patient.model_dump(), std_result.level)
             return {
                 "level": std_result.level,
                 "color_code": std_result.color_code,
                 "label_en": std_result.label_en,
                 "label_ar": std_result.label_ar,
                 "reasoning": [ai_result.get("reasoning"), "Fallback to Standard Protocol"],
                 "red_flags": std_result.red_flags,
                 "ai_data": None
             }

        level = ai_result.get("triage_level", 3)
        colors = {1:"#ef4444", 2:"#f97316", 3:"#eab308", 4:"#22c55e", 5:"#3b82f6"}
        labels_en = {1:"Resuscitation", 2:"Emergent", 3:"Urgent", 4:"Less Urgent", 5:"Non-Urgent"}
        labels_ar = {1:"إنعاش", 2:"طوارئ", 3:"عاجل", 4:"أقل إلحاحاً", 5:"غير عاجل"}

        # Send alert for critical patients (Level 1 or 2)
        send_critical_alert(patient.model_dump(), level)

        return {
            "level": level,
            "color_code": colors.get(level, "#eab308"),
            "label_en": f"{labels_en.get(level)} (Level {level})",
            "label_ar": f"{labels_ar.get(level)} (مستوى {level})",
            "description": "AI-Assisted Assessment",
            "recommended_action": "Review AI suggestions below",
            "time_to_physician": "Based on acuity",
            "red_flags": ai_result.get("red_flags", []),
            "reasoning": [ai_result.get("reasoning")],
            "ai_data": {
                "reasoning_ar": ai_result.get("reasoning_ar"),
                "followup_question": ai_result.get("followup_question"),
                "followup_question_ar": ai_result.get("followup_question_ar"),
                "severity": ai_result.get("severity")
            },
            "confidence": "AI-Generated"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/patients")
def get_patients(skip: int = 0, limit: int = 50, db: Session = Depends(get_db)):
    patients = db.query(Patient).order_by(Patient.created_at.desc()).offset(skip).limit(limit).all()
    return patients

@app.get("/patients/{patient_id}")
def get_patient(patient_id: int, db: Session = Depends(get_db)):
    patient = db.query(Patient).filter(Patient.id == patient_id).first()
    if not patient:
         raise HTTPException(status_code=404, detail="Patient not found")
    return patient

if __name__ == "__main__":
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)
