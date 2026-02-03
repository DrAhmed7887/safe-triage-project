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
from .logic.icd10_integration import enrich_triage_with_icd10, check_silent_mi_pattern, format_icd10_for_hospital_record

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
# STANDARD MODE: No AI, only keyword matching (fast)
engine_logic = DeterministicTriageEngine(use_ai=False)

# AI-ENHANCED MODE: Uses AI classification with fallback
engine_logic_ai = DeterministicTriageEngine(use_ai=True)

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
        
        # Add ICD-10 coding for GAHAR compliance
        result_dict = result.model_dump() if hasattr(result, 'model_dump') else vars(result)
        result_dict["chief_complaint"] = patient.chief_complaint_text
        result_dict["category"] = getattr(result, 'category', 'general')
        enriched = enrich_triage_with_icd10(result_dict)
        
        # Check Silent MI pattern for diabetic patients
        patient_data = patient.model_dump()
        silent_mi = check_silent_mi_pattern(patient_data)
        if silent_mi["pattern_detected"]:
            enriched["silent_mi_alert"] = silent_mi
        
        # Send alert for critical patients
        send_critical_alert(patient.model_dump(), result.level)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/ai-triage")
def ai_triage_patient(patient: PatientInput, db: Session = Depends(get_db)):
    """
    AI-enhanced triage endpoint.
    
    AUDIT FIX: Properly handles AI fallback flag.
    When AI fails, uses deterministic engine instead of hardcoded Level 3.
    """
    try:
        ai_result = ai_service.analyze_triage(patient.model_dump())
        
        # AUDIT FIX: Check for fallback flag (not just "error" key)
        # This ensures deterministic engine handles failures safely
        if ai_result.get("fallback") or "error" in ai_result:
            # Use AI-enabled engine for fallback (it will use keyword matching)
            std_result = engine_logic_ai.evaluate(patient)
            # Send alert for critical patients
            send_critical_alert(patient.model_dump(), std_result.level.value if hasattr(std_result.level, 'value') else std_result.level)
            
            # Build informative response showing deterministic fallback was used
            fallback_reason = ai_result.get("message", ai_result.get("error", "AI unavailable"))
            
            # Add ICD-10 coding for GAHAR compliance
            fallback_dict = {
                "level": std_result.level.value if hasattr(std_result.level, 'value') else std_result.level,
                "category": getattr(std_result, 'category', 'general'),
                "chief_complaint": patient.chief_complaint_text
            }
            enriched = enrich_triage_with_icd10(fallback_dict)
            icd10_coding = enriched.get("icd10_coding", {})
            
            return {
                "level": std_result.level.value if hasattr(std_result.level, 'value') else std_result.level,
                "color_code": std_result.color_code,
                "label_en": std_result.label_en,
                "label_ar": std_result.label_ar,
                "description_ar": std_result.description_ar,
                "description_en": std_result.description_en,
                "action_ar": std_result.action_ar,
                "action_en": std_result.action_en,
                "time_ar": std_result.time_ar,
                "time_en": std_result.time_en,
                "reasoning": std_result.reasoning + [f"⚠️ {fallback_reason}"],
                "reasoning_ar": std_result.reasoning_ar + [ai_result.get("message_ar", "تم استخدام الفرز الحتمي")],
                "reasoning_en": std_result.reasoning_en + [fallback_reason],
                "red_flags": std_result.red_flags,
                "ai_data": None,
                "confidence": "Deterministic (AI Fallback)",
                "icd10_coding": icd10_coding
            }

        level = ai_result.get("triage_level", 3)
        colors = {1:"#ef4444", 2:"#f97316", 3:"#eab308", 4:"#22c55e", 5:"#3b82f6"}
        labels_en = {1:"Resuscitation", 2:"Emergent", 3:"Urgent", 4:"Less Urgent", 5:"Non-Urgent"}
        labels_ar = {1:"إنعاش", 2:"طوارئ", 3:"عاجل", 4:"أقل إلحاحاً", 5:"غير عاجل"}
        
        # ESI v4 time to physician guidelines
        times_en = {1:"Immediate", 2:"< 15 minutes", 3:"< 30 minutes", 4:"< 60 minutes", 5:"< 120 minutes"}
        times_ar = {1:"فوري", 2:"< 15 دقيقة", 3:"< 30 دقيقة", 4:"< 60 دقيقة", 5:"< 120 دقيقة"}
        actions_en = {
            1: "Resuscitation room immediately",
            2: "ICU room, continuous monitoring", 
            3: "Exam room, order labs/imaging",
            4: "Fast-track clinic",
            5: "Can wait / Clinic referral"
        }
        actions_ar = {
            1: "غرفة الإنعاش فوراً",
            2: "غرفة العناية المركزة، مراقبة مستمرة",
            3: "غرفة فحص، طلب تحاليل/أشعة", 
            4: "العيادة السريعة",
            5: "يمكن الانتظار / تحويل للعيادة"
        }

        # Send alert for critical patients (Level 1 or 2)
        send_critical_alert(patient.model_dump(), level)
        
        # Add ICD-10 coding for GAHAR compliance
        response_dict = {
            "level": level,
            "category": ai_result.get("category", "general"),
            "chief_complaint": patient.chief_complaint_text
        }
        enriched = enrich_triage_with_icd10(response_dict)
        icd10_coding = enriched.get("icd10_coding", {})
        
        # Check Silent MI pattern
        patient_data = patient.model_dump()
        silent_mi = check_silent_mi_pattern(patient_data)

        return {
            "level": level,
            "color_code": colors.get(level, "#eab308"),
            "label_en": f"{labels_en.get(level)} (Level {level})",
            "label_ar": f"{labels_ar.get(level)} (مستوى {level})",
            "description": f"{actions_ar.get(level)} / {actions_en.get(level)}",
            "description_ar": actions_ar.get(level),
            "description_en": actions_en.get(level),
            "recommended_action": f"{actions_ar.get(level)} / {actions_en.get(level)}",
            "action_ar": actions_ar.get(level),
            "action_en": actions_en.get(level),
            "time_to_physician": f"{times_ar.get(level)} / {times_en.get(level)}",
            "time_ar": times_ar.get(level),
            "time_en": times_en.get(level),
            "red_flags": ai_result.get("red_flags", []),
            "reasoning": [ai_result.get("reasoning")],
            "reasoning_ar": [ai_result.get("reasoning_ar")] if ai_result.get("reasoning_ar") else [],
            "reasoning_en": [ai_result.get("reasoning")] if ai_result.get("reasoning") else [],
            "ai_data": {
                "reasoning_ar": ai_result.get("reasoning_ar"),
                "followup_question": ai_result.get("followup_question"),
                "followup_question_ar": ai_result.get("followup_question_ar"),
                "severity": ai_result.get("severity")
            },
            "confidence": "AI-Generated",
            "icd10_coding": icd10_coding,
            "silent_mi_alert": silent_mi if silent_mi["pattern_detected"] else None
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
