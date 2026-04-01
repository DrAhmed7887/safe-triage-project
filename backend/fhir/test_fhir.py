from backend.fhir.mapper import map_to_fhir
from backend.fhir.fhir_bundle import build_bundle


def test_fhir_mapping():
    sample_data = {
        "patient": {
            "name": "Ahmed Ali",
            "gender": "male",
            "birthDate": "1990-01-01"
        },
        "encounter": {
            "timestamp": "2026-01-01T10:00:00"
        },
        "vitals": {
            "heart_rate": 110,
            "spo2": 95,
            "temperature": 38
        },
        "diagnosis": {
            "icd10": "R07.9",
            "chief_complaint_en": "Chest pain",
            "chief_complaint_ar": "ألم في الصدر"
        }
    }

    resources = map_to_fhir(sample_data)
    bundle = build_bundle(resources)

    assert bundle["resourceType"] == "Bundle"
    assert len(bundle["entry"]) > 0