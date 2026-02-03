"""
ICD-10 Code Mapping for SAFE-Triage
Egyptian Hospital GAHAR Compliance

ICD-10 codes based on WHO ICD-10-CM classification
Focus on Chapter XVIII (R00-R99) - Symptoms, signs and abnormal clinical findings
Plus relevant codes from other chapters for specific conditions
"""

ICD10_MAPPING = {
    # ============ LEVEL 1 - RESUSCITATION ============
    "unconscious": {
        "code": "R40.20",
        "description": "Unspecified coma",
        "category": "Symptoms involving cognition"
    },
    "cardiac_arrest": {
        "code": "I46.9",
        "description": "Cardiac arrest, cause unspecified",
        "category": "Cardiac arrest"
    },
    "respiratory_arrest": {
        "code": "R09.2",
        "description": "Respiratory arrest",
        "category": "Respiratory symptoms"
    },
    "active_seizure": {
        "code": "R56.9",
        "description": "Unspecified convulsions",
        "category": "Convulsions"
    },
    "choking": {
        "code": "T17.9",
        "description": "Foreign body in respiratory tract, part unspecified",
        "category": "Foreign body airway"
    },
    "severe_trauma": {
        "code": "T07",
        "description": "Unspecified multiple injuries",
        "category": "Multiple trauma"
    },
    "anaphylaxis": {
        "code": "T78.2",
        "description": "Anaphylactic shock, unspecified",
        "category": "Anaphylaxis"
    },
    "poisoning_overdose": {
        "code": "T65.9",
        "description": "Toxic effect of unspecified substance",
        "category": "Poisoning/Overdose"
    },
    "drowning": {
        "code": "T75.1",
        "description": "Drowning and nonfatal submersion",
        "category": "Drowning"
    },
    "severe_bleeding": {
        "code": "R58",
        "description": "Hemorrhage, not elsewhere classified",
        "category": "Hemorrhage"
    },
    "ectopic_pregnancy": {
        "code": "O00.9",
        "description": "Ectopic pregnancy, unspecified",
        "category": "Ectopic pregnancy"
    },
    "aortic_dissection": {
        "code": "I71.0",
        "description": "Dissection of aorta",
        "category": "Aortic dissection"
    },
    "sepsis": {
        "code": "A41.9",
        "description": "Sepsis, unspecified organism",
        "category": "Sepsis"
    },
    "severe_hypothermia": {
        "code": "T68",
        "description": "Hypothermia",
        "category": "Hypothermia"
    },
    "pediatric_critical": {
        "code": "R68.89",
        "description": "Other general symptoms and signs",
        "category": "Pediatric emergency"
    },

    # ============ LEVEL 2 - EMERGENT ============
    "chest_pain_cardiac": {
        "code": "R07.9",
        "description": "Chest pain, unspecified",
        "category": "Chest pain"
    },
    "silent_mi": {
        "code": "I21.9",
        "description": "Acute myocardial infarction, unspecified",
        "category": "Myocardial infarction"
    },
    "gi_bleed": {
        "code": "K92.2",
        "description": "Gastrointestinal hemorrhage, unspecified",
        "category": "GI bleeding"
    },
    "hip_fracture": {
        "code": "S72.9",
        "description": "Unspecified fracture of femur",
        "category": "Hip fracture"
    },
    "stroke_symptoms": {
        "code": "I64",
        "description": "Stroke, not specified as hemorrhage or infarction",
        "category": "Stroke"
    },
    "respiratory_distress": {
        "code": "R06.0",
        "description": "Dyspnea",
        "category": "Respiratory distress"
    },
    "suicidal_homicidal": {
        "code": "R45.851",
        "description": "Suicidal ideations",
        "category": "Psychiatric emergency"
    },
    "obstetric_emergency": {
        "code": "O75.9",
        "description": "Complication of labor and delivery, unspecified",
        "category": "Obstetric emergency"
    },
    "diabetic_emergency": {
        "code": "E10.65",
        "description": "Type 1 diabetes mellitus with hyperglycemia",
        "category": "Diabetic emergency"
    },
    "pediatric_emergency": {
        "code": "R68.89",
        "description": "Other general symptoms and signs",
        "category": "Pediatric emergency"
    },
    "severe_headache": {
        "code": "R51.9",
        "description": "Headache, unspecified",
        "category": "Headache"
    },
    "severe_pain": {
        "code": "R52",
        "description": "Pain, unspecified",
        "category": "Pain"
    },
    "high_fever_toxic": {
        "code": "R50.9",
        "description": "Fever, unspecified",
        "category": "Fever"
    },
    "altered_mental_status": {
        "code": "R41.82",
        "description": "Altered mental status, unspecified",
        "category": "Altered mental status"
    },
    "allergic_reaction": {
        "code": "T78.40",
        "description": "Allergy, unspecified",
        "category": "Allergic reaction"
    },
    "testicular_pain": {
        "code": "N50.8",
        "description": "Other specified disorders of male genital organs",
        "category": "Testicular pain"
    },
    "dvt_pe": {
        "code": "I26.9",
        "description": "Pulmonary embolism without acute cor pulmonale",
        "category": "DVT/PE"
    },
    "hemoptysis": {
        "code": "R04.2",
        "description": "Hemoptysis",
        "category": "Hemoptysis"
    },
    "mesenteric_ischemia": {
        "code": "K55.0",
        "description": "Acute vascular disorders of intestine",
        "category": "Mesenteric ischemia"
    },

    # ============ LEVEL 3 - URGENT ============
    "abdominal_pain_moderate": {
        "code": "R10.9",
        "description": "Unspecified abdominal pain",
        "category": "Abdominal pain"
    },
    "fever_with_symptoms": {
        "code": "R50.9",
        "description": "Fever, unspecified",
        "category": "Fever"
    },
    "vomiting_dehydration": {
        "code": "R11.10",
        "description": "Vomiting, unspecified",
        "category": "Vomiting"
    },
    "moderate_bleeding": {
        "code": "R58",
        "description": "Hemorrhage, not elsewhere classified",
        "category": "Hemorrhage"
    },
    "fracture_deformity": {
        "code": "T14.8",
        "description": "Other injury of unspecified body region",
        "category": "Fracture"
    },
    "pediatric_distress": {
        "code": "R68.89",
        "description": "Other general symptoms and signs",
        "category": "Pediatric distress"
    },
    "moderate_dyspnea": {
        "code": "R06.0",
        "description": "Dyspnea",
        "category": "Dyspnea"
    },
    "chest_pain_noncardiac": {
        "code": "R07.89",
        "description": "Other chest pain",
        "category": "Chest pain"
    },
    "asthma_exacerbation": {
        "code": "J45.901",
        "description": "Unspecified asthma with (acute) exacerbation",
        "category": "Asthma"
    },
    "kidney_stone": {
        "code": "N20.0",
        "description": "Calculus of kidney",
        "category": "Renal colic"
    },
    "psychiatric_agitated": {
        "code": "R45.1",
        "description": "Restlessness and agitation",
        "category": "Psychiatric"
    },

    # ============ LEVEL 4 - LESS URGENT ============
    "minor_trauma": {
        "code": "T14.90",
        "description": "Injury, unspecified",
        "category": "Minor trauma"
    },
    "laceration_simple": {
        "code": "T14.1",
        "description": "Open wound of unspecified body region",
        "category": "Laceration"
    },
    "uri_symptoms": {
        "code": "J06.9",
        "description": "Acute upper respiratory infection, unspecified",
        "category": "URI"
    },
    "sore_throat": {
        "code": "J02.9",
        "description": "Acute pharyngitis, unspecified",
        "category": "Pharyngitis"
    },
    "earache": {
        "code": "H92.0",
        "description": "Otalgia",
        "category": "Ear pain"
    },
    "uti_symptoms": {
        "code": "N39.0",
        "description": "Urinary tract infection, site not specified",
        "category": "UTI"
    },
    "mild_allergic": {
        "code": "T78.40",
        "description": "Allergy, unspecified",
        "category": "Allergy"
    },
    "back_pain_chronic": {
        "code": "M54.5",
        "description": "Low back pain",
        "category": "Back pain"
    },
    "mild_gi": {
        "code": "K30",
        "description": "Functional dyspepsia",
        "category": "Dyspepsia"
    },
    "mild_pain": {
        "code": "R52",
        "description": "Pain, unspecified",
        "category": "Pain"
    },
    "headache_mild": {
        "code": "R51.9",
        "description": "Headache, unspecified",
        "category": "Headache"
    },
    "eye_complaint": {
        "code": "H57.9",
        "description": "Unspecified disorder of eye and adnexa",
        "category": "Eye complaint"
    },
    "dental": {
        "code": "K08.9",
        "description": "Disorder of teeth and supporting structures, unspecified",
        "category": "Dental"
    },
    "skin_fungal": {
        "code": "B35.9",
        "description": "Dermatophytosis, unspecified",
        "category": "Fungal infection"
    },
    "hiccups": {
        "code": "R06.6",
        "description": "Hiccough",
        "category": "Hiccups"
    },
    "ankle_sprain": {
        "code": "S93.40",
        "description": "Sprain of unspecified ligament of ankle",
        "category": "Ankle sprain"
    },
    "insect_bite": {
        "code": "T63.4",
        "description": "Toxic effect of venom of other arthropods",
        "category": "Insect bite"
    },

    # ============ LEVEL 5 - NON-URGENT ============
    "prescription_refill": {
        "code": "Z76.0",
        "description": "Encounter for issue of repeat prescription",
        "category": "Prescription refill"
    },
    "medical_certificate": {
        "code": "Z02.79",
        "description": "Encounter for issue of other medical certificate",
        "category": "Medical certificate"
    },
    "suture_removal": {
        "code": "Z48.02",
        "description": "Encounter for removal of sutures",
        "category": "Suture removal"
    },
    "chronic_stable": {
        "code": "Z87.89",
        "description": "Personal history of other specified conditions",
        "category": "Chronic stable"
    },
    "minor_complaint": {
        "code": "R68.89",
        "description": "Other general symptoms and signs",
        "category": "Minor complaint"
    },
    "wound_check": {
        "code": "Z48.00",
        "description": "Encounter for change or removal of dressing",
        "category": "Wound check"
    },
    "rash_minor": {
        "code": "R21",
        "description": "Rash and other nonspecific skin eruption",
        "category": "Rash"
    },
}

def get_icd10_code(category_key: str) -> dict:
    """Get ICD-10 code info for a category"""
    return ICD10_MAPPING.get(category_key, {
        "code": "R69",
        "description": "Illness, unspecified",
        "category": "Unspecified"
    })

def get_all_mappings() -> dict:
    """Return all ICD-10 mappings"""
    return ICD10_MAPPING
