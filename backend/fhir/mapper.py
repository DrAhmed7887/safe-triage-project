import uuid
from datetime import datetime


def generate_id():
    return str(uuid.uuid4())


# -----------------------------
# Patient
# -----------------------------
def map_patient(data):
    patient = data.get("patient", {})

    return {
        "resourceType": "Patient",
        "id": generate_id(),
        "name": [{
            "text": patient.get("name", "Unknown")
        }],
        "gender": patient.get("gender", "unknown"),
        "birthDate": patient.get("birthDate", "1970-01-01")
    }


# -----------------------------
# Encounter
# -----------------------------
def map_encounter(data, patient_id):
    encounter = data.get("encounter", {})

    return {
        "resourceType": "Encounter",
        "id": generate_id(),
        "status": "in-progress",
        "class": {
            "system": "http://terminology.hl7.org/CodeSystem/v3-ActCode",
            "code": "EMER"
        },
        "subject": {
            "reference": f"Patient/{patient_id}"
        },
        "period": {
            "start": encounter.get("timestamp", datetime.now().isoformat())
        }
    }


# -----------------------------
# Observations
# -----------------------------
def map_observations(data, patient_id, encounter_id):
    vitals = data.get("vitals", {})

    loinc_map = {
        "heart_rate": "8867-4",
        "spo2": "2708-6",
        "temperature": "8310-5"
    }

    observations = []

    for key, loinc in loinc_map.items():
        if key in vitals:
            observations.append({
                "resourceType": "Observation",
                "id": generate_id(),
                "status": "final",
                "code": {
                    "coding": [{
                        "system": "http://loinc.org",
                        "code": loinc
                    }]
                },
                "subject": {
                    "reference": f"Patient/{patient_id}"
                },
                "encounter": {
                    "reference": f"Encounter/{encounter_id}"
                },
                "valueQuantity": {
                    "value": vitals[key]
                }
            })

    return observations


# -----------------------------
# Condition
# -----------------------------
def map_condition(data, patient_id):
    diagnosis = data.get("diagnosis", {})

    return {
        "resourceType": "Condition",
        "id": generate_id(),
        "code": {
            "coding": [{
                "system": "http://hl7.org/fhir/sid/icd-10",
                "code": diagnosis.get("icd10", "R69")
            }],
            "text": f"{diagnosis.get('chief_complaint_en', '')} / {diagnosis.get('chief_complaint_ar', '')}"
        },
        "subject": {
            "reference": f"Patient/{patient_id}"
        }
    }


# -----------------------------
# Main Mapper
# -----------------------------
def map_to_fhir(data):
    patient = map_patient(data)
    encounter = map_encounter(data, patient["id"])
    observations = map_observations(data, patient["id"], encounter["id"])
    condition = map_condition(data, patient["id"])

    return [patient, encounter, *observations, condition]