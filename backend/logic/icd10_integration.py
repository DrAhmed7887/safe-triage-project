"""
ICD-10 Integration for SAFE-Triage
===================================
Adds ICD-10-CM coding to triage output for GAHAR compliance.

Why ICD-10 (not SNOMED-CT):
1. Used in Egyptian hospitals
2. Required by GAHAR
3. Available now (SNOMED requires UMLS approval)
4. WHO standard with Arabic translations

Usage:
    from logic.icd10_integration import get_icd10_for_category, enrich_triage_with_icd10
"""

import json
import os
from typing import Dict, Optional, Any
from pathlib import Path


# Load ICD-10 codes on module import
_ICD10_DATA: Dict = {}
_ICD10_FILE = Path(__file__).parent / "icd10_codes.json"


def _load_icd10_data() -> Dict:
    """Load ICD-10 codes from JSON file"""
    global _ICD10_DATA
    if not _ICD10_DATA:
        try:
            with open(_ICD10_FILE, 'r', encoding='utf-8') as f:
                _ICD10_DATA = json.load(f)
        except FileNotFoundError:
            print(f"Warning: ICD-10 codes file not found at {_ICD10_FILE}")
            _ICD10_DATA = {"category_to_icd10": {}, "arabic_symptoms_to_icd10": {}}
        except json.JSONDecodeError as e:
            print(f"Warning: Error parsing ICD-10 codes: {e}")
            _ICD10_DATA = {"category_to_icd10": {}, "arabic_symptoms_to_icd10": {}}
    return _ICD10_DATA


def get_icd10_for_category(category: str, esi_level: int = 3) -> Dict[str, str]:
    """
    Get ICD-10 code for a triage category.
    
    Args:
        category: The complaint category (e.g., "chest_pain", "abdominal_pain")
        esi_level: ESI level (1-5) to look up appropriate code set
        
    Returns:
        Dict with icd10 code, description_en, description_ar
    """
    data = _load_icd10_data()
    category_map = data.get("category_to_icd10", {})
    
    # Normalize category name
    category_lower = category.lower().replace(" ", "_").replace("-", "_")
    
    # Try level-specific codes first
    level_key = f"level_{esi_level}_codes"
    if level_key in category_map:
        level_codes = category_map[level_key]
        if category_lower in level_codes:
            return level_codes[category_lower]
    
    # Search all levels
    for level in ["level_1_codes", "level_2_codes", "level_3_codes", 
                  "level_4_codes", "level_5_codes", "special_patterns"]:
        if level in category_map:
            codes = category_map[level]
            if category_lower in codes:
                return codes[category_lower]
    
    # Default fallback
    return {
        "icd10": "R69",
        "description_en": "Illness, unspecified",
        "description_ar": "مرض غير محدد"
    }


def get_icd10_from_arabic(arabic_text: str) -> Optional[str]:
    """
    Quick lookup of ICD-10 code from Arabic symptom text.
    
    Args:
        arabic_text: Arabic symptom description
        
    Returns:
        ICD-10 code if found, None otherwise
    """
    data = _load_icd10_data()
    arabic_map = data.get("arabic_symptoms_to_icd10", {})
    
    # Direct match
    if arabic_text in arabic_map:
        return arabic_map[arabic_text]
    
    # Partial match (check if any key is contained in text)
    for key, code in arabic_map.items():
        if key in arabic_text:
            return code
    
    return None


def enrich_triage_with_icd10(triage_result: Dict[str, Any]) -> Dict[str, Any]:
    """
    Add ICD-10 coding to a triage result.
    
    Args:
        triage_result: The triage result dictionary from the triage engine
        
    Returns:
        Enhanced triage result with ICD-10 codes
    """
    # Make a copy to avoid modifying original
    result = triage_result.copy()
    
    # Extract relevant fields
    category = result.get("category") or result.get("chief_complaint_category") or ""
    esi_level = result.get("esi_level") or result.get("level") or 3
    chief_complaint = result.get("chief_complaint") or result.get("complaint") or ""
    
    # Get ICD-10 for category
    icd10_info = get_icd10_for_category(category, esi_level)
    
    # Try Arabic lookup if available
    arabic_code = get_icd10_from_arabic(chief_complaint)
    if arabic_code:
        # Use more specific Arabic match if found
        icd10_info["icd10_from_complaint"] = arabic_code
    
    # Add to result
    result["icd10_coding"] = {
        "primary_code": icd10_info.get("icd10", "R69"),
        "description_en": icd10_info.get("description_en", "Unspecified"),
        "description_ar": icd10_info.get("description_ar", "غير محدد"),
        "coding_system": "ICD-10-CM",
        "coding_version": "2024",
        "gahar_compliant": True
    }
    
    return result


def check_silent_mi_pattern(patient_data: Dict) -> Dict[str, Any]:
    """
    Check for Silent MI pattern in diabetic patients.
    This is the "Silent Killer" case study from the thesis.
    
    Args:
        patient_data: Patient data including comorbidities, age, gender, complaint
        
    Returns:
        Dict with pattern_detected, upgrade_recommended, icd10_code
    """
    data = _load_icd10_data()
    silent_mi_info = data.get("category_to_icd10", {}).get("special_patterns", {}).get("silent_mi_diabetic", {})
    
    # Check risk factors
    is_diabetic = "diabetes" in str(patient_data.get("comorbidities", [])).lower() or \
                  "dm" in str(patient_data.get("comorbidities", [])).lower() or \
                  patient_data.get("diabetic", False)
    
    age = patient_data.get("age", 0)
    gender = patient_data.get("gender", "").lower()
    complaint = str(patient_data.get("chief_complaint", "")).lower()
    
    # Check for atypical GI symptoms in diabetic patient
    gi_symptoms = any(word in complaint for word in [
        "nausea", "غثيان", "indigestion", "سوء هضم", "heartburn", "حرقان",
        "stomach", "معدة", "vomiting", "قيء", "fatigue", "تعب", "هبطان"
    ])
    
    # High risk: diabetic + male + age > 50 + GI symptoms
    pattern_detected = is_diabetic and age > 50 and gi_symptoms
    strong_pattern = pattern_detected and gender == "male"
    
    return {
        "pattern_detected": pattern_detected,
        "strong_pattern": strong_pattern,
        "pattern_name": "Silent MI in Diabetic Patient",
        "upgrade_recommended": pattern_detected,
        "recommended_level": 2 if pattern_detected else None,
        "icd10_code": silent_mi_info.get("icd10", "R07.89"),
        "red_flags_present": {
            "diabetic": is_diabetic,
            "age_over_50": age > 50,
            "male": gender == "male",
            "gi_symptoms": gi_symptoms
        },
        "clinical_action": "Recommend ECG even for GI complaints" if pattern_detected else None
    }


def get_all_icd10_codes() -> Dict[str, str]:
    """Get all ICD-10 codes in the database for reference"""
    data = _load_icd10_data()
    all_codes = {}
    
    for level_key, categories in data.get("category_to_icd10", {}).items():
        if isinstance(categories, dict):
            for cat_name, cat_info in categories.items():
                if isinstance(cat_info, dict) and "icd10" in cat_info:
                    all_codes[cat_name] = cat_info["icd10"]
    
    return all_codes


def format_icd10_for_hospital_record(triage_result: Dict) -> str:
    """
    Format ICD-10 code for hospital medical record.
    
    Returns string like: "R07.9 - Chest pain, unspecified | ألم في الصدر"
    """
    icd10 = triage_result.get("icd10_coding", {})
    code = icd10.get("primary_code", "R69")
    desc_en = icd10.get("description_en", "Unspecified")
    desc_ar = icd10.get("description_ar", "غير محدد")
    
    return f"{code} - {desc_en} | {desc_ar}"


# Test function
if __name__ == "__main__":
    print("=" * 60)
    print("SAFE-Triage ICD-10 Integration Test")
    print("=" * 60)
    
    # Test category lookup
    test_categories = [
        ("chest_pain", 2),
        ("abdominal_pain", 3),
        ("fever", 3),
        ("headache", 3),
        ("unconscious", 1)
    ]
    
    print("\n1. Category to ICD-10 mapping:")
    for cat, level in test_categories:
        result = get_icd10_for_category(cat, level)
        print(f"   {cat} (ESI {level}): {result['icd10']} - {result['description_en']}")
    
    # Test Arabic lookup
    print("\n2. Arabic symptom lookup:")
    arabic_tests = ["صدري بيوجعني", "بطني بيوجعني", "دوخة"]
    for text in arabic_tests:
        code = get_icd10_from_arabic(text)
        print(f"   '{text}': {code}")
    
    # Test Silent MI pattern
    print("\n3. Silent MI Pattern Detection:")
    patient = {
        "age": 58,
        "gender": "male",
        "comorbidities": ["diabetes", "hypertension"],
        "chief_complaint": "عندي غثيان وتعب من الصبح"
    }
    pattern = check_silent_mi_pattern(patient)
    print(f"   Patient: 58M, diabetic, complaint: GI symptoms")
    print(f"   Pattern detected: {pattern['pattern_detected']}")
    print(f"   Upgrade to ESI: {pattern['recommended_level']}")
    print(f"   ICD-10: {pattern['icd10_code']}")
    
    # Test enrichment
    print("\n4. Triage result enrichment:")
    mock_triage = {
        "esi_level": 3,
        "category": "abdominal_pain",
        "chief_complaint": "بطني بيوجعني"
    }
    enriched = enrich_triage_with_icd10(mock_triage)
    print(f"   Original: {mock_triage}")
    print(f"   ICD-10 added: {enriched['icd10_coding']}")
    
    print("\n" + "=" * 60)
    print("All tests completed!")
    print(f"Total ICD-10 codes in database: {len(get_all_icd10_codes())}")
