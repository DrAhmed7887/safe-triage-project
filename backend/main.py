from fastapi import FastAPI
from backend.fhir.mapper import map_to_fhir
from backend.fhir.fhir_bundle import build_bundle
from backend.validators import validate_gender_complaint
app = FastAPI()


@app.get("/")
def home():
    return {"message": "Safe Triage API is running 🚀"}


@app.post("/triage")
def triage(data: dict):
    patient = data.get("patient", {})
    diagnosis = data.get("diagnosis", {})

    gender = patient.get("gender", "")
    complaint = diagnosis.get("chief_complaint_en", "")

    validation = validate_gender_complaint(gender, complaint)

    if not validation["valid"]:
        return {"error": validation}

    resources = map_to_fhir(data)
    bundle = build_bundle(resources)

    return bundle