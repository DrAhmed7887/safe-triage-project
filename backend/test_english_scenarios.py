#!/usr/bin/env python3
"""
SAFE-Triage English Clinical Scenarios Test Suite
Comprehensive testing of common ED presentations in English
Designed for extended agent validation sessions
"""

import sys
import os
import argparse
sys.path.append(os.path.join(os.getcwd(), 'backend'))

# Ensure offline tests do not pull HuggingFace models
os.environ.setdefault("DISABLE_RAG", "true")

from logic.deterministic_triage import DeterministicTriageEngine
from models import PatientInput, Vitals, Gender
import json
from datetime import datetime

# ANSI colors
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
RESET = "\033[0m"

def run_test(engine, test_case: dict) -> dict:
    """Run a single test and return detailed results"""
    patient = test_case["patient"]
    expected = test_case["expected_level"]
    
    result = engine.evaluate(patient)
    actual_level = int(result.level)
    passed = actual_level == expected
    critical_undertriage = expected <= 2 and actual_level > expected
    over_triage = actual_level < expected  # Not critical but worth noting
    guardrails_fired = [
        item for item in (getattr(result, "reasoning_en", None) or [])
        if str(item).startswith("GUARDRAIL_")
    ]
    
    return {
        "name": test_case["name"],
        "category": test_case["category"],
        "expected": expected,
        "actual": actual_level,
        "matched_category": result.label_en,
        "passed": passed,
        "critical_undertriage": critical_undertriage,
        "over_triage": over_triage,
        "complaint": patient.chief_complaint_text,
        "guardrails_fired": guardrails_fired,
    }

# =============================================================================
# ENGLISH CLINICAL SCENARIOS - 100 COMMON ED PRESENTATIONS
# =============================================================================

ENGLISH_SCENARIOS = [
    # =========================================================================
    # LEVEL 1 - RESUSCITATION (Immediate life-threatening)
    # =========================================================================
    
    # Cardiac Arrest / Pulseless
    {"name": "Cardiac arrest - witnessed collapse", "category": "cardiac_arrest",
     "patient": PatientInput(age=58, gender=Gender.MALE, chief_complaint_text="Patient collapsed, no pulse, not breathing", vitals=Vitals()),
     "expected_level": 1},
    {"name": "Cardiac arrest - found down", "category": "cardiac_arrest",
     "patient": PatientInput(age=72, gender=Gender.FEMALE, chief_complaint_text="Found unresponsive, no signs of life", vitals=Vitals()),
     "expected_level": 1},
    
    # Respiratory Failure
    {"name": "Complete airway obstruction", "category": "airway_obstruction",
     "patient": PatientInput(age=45, gender=Gender.MALE, chief_complaint_text="Choking, can't breathe at all, turning blue", vitals=Vitals()),
     "expected_level": 1},
    {"name": "Respiratory arrest", "category": "respiratory_arrest",
     "patient": PatientInput(age=68, gender=Gender.FEMALE, chief_complaint_text="Not breathing, apneic, needs intubation", vitals=Vitals()),
     "expected_level": 1},
    {"name": "Severe anaphylaxis", "category": "anaphylaxis",
     "patient": PatientInput(age=25, gender=Gender.MALE, chief_complaint_text="Bee sting, throat swelling shut, can't breathe, lips blue", vitals=Vitals()),
     "expected_level": 1},
    
    # Unresponsive / Coma
    {"name": "Unresponsive - unknown cause", "category": "unconscious",
     "patient": PatientInput(age=55, gender=Gender.MALE, chief_complaint_text="Completely unresponsive, won't wake up", vitals=Vitals()),
     "expected_level": 1},
    {"name": "GCS 3", "category": "unconscious",
     "patient": PatientInput(age=40, gender=Gender.FEMALE, chief_complaint_text="GCS 3, no response to pain", vitals=Vitals()),
     "expected_level": 1},
    
    # Severe Trauma
    {"name": "Major trauma - MVA ejection", "category": "severe_trauma",
     "patient": PatientInput(age=22, gender=Gender.MALE, chief_complaint_text="Ejected from vehicle, multiple injuries, bleeding heavily", vitals=Vitals()),
     "expected_level": 1},
    {"name": "Gunshot wound chest", "category": "severe_trauma",
     "patient": PatientInput(age=30, gender=Gender.MALE, chief_complaint_text="Gunshot wound to chest, difficulty breathing", vitals=Vitals()),
     "expected_level": 1},
    {"name": "Stab wound abdomen", "category": "severe_trauma",
     "patient": PatientInput(age=28, gender=Gender.MALE, chief_complaint_text="Stabbed in abdomen, bowel evisceration", vitals=Vitals()),
     "expected_level": 1},
    
    # Massive Hemorrhage
    {"name": "Massive GI bleed", "category": "severe_bleeding",
     "patient": PatientInput(age=65, gender=Gender.MALE, chief_complaint_text="Vomiting large amounts of blood, feeling faint",
                            vitals=Vitals(hr=130, sbp=80)),
     "expected_level": 1},
    {"name": "Ruptured AAA", "category": "severe_bleeding",
     "patient": PatientInput(age=75, gender=Gender.MALE, chief_complaint_text="Sudden severe back pain, pulsatile abdominal mass, hypotensive",
                            vitals=Vitals(hr=120, sbp=70)),
     "expected_level": 1},
    
    # Poisoning / Overdose - Critical
    {"name": "Opioid overdose - apneic", "category": "poisoning_overdose",
     "patient": PatientInput(age=28, gender=Gender.MALE, chief_complaint_text="Heroin overdose, not breathing, pinpoint pupils", vitals=Vitals()),
     "expected_level": 1},
    {"name": "Caustic ingestion", "category": "poisoning_overdose",
     "patient": PatientInput(age=3, gender=Gender.FEMALE, chief_complaint_text="Drank drain cleaner, mouth burns, drooling", vitals=Vitals()),
     "expected_level": 1},
    
    # Seizure - Active
    {"name": "Status epilepticus", "category": "active_seizure",
     "patient": PatientInput(age=35, gender=Gender.MALE, chief_complaint_text="Continuous seizure for 10 minutes, not stopping", vitals=Vitals()),
     "expected_level": 1},
    
    # =========================================================================
    # LEVEL 2 - EMERGENT (High risk, should not wait)
    # =========================================================================
    
    # Chest Pain - Cardiac
    {"name": "STEMI - classic presentation", "category": "chest_pain_cardiac",
     "patient": PatientInput(age=62, gender=Gender.MALE, chief_complaint_text="Crushing chest pain radiating to left arm, sweating, nausea", vitals=Vitals()),
     "expected_level": 2},
    {"name": "STEMI - diabetic atypical", "category": "chest_pain_cardiac",
     "patient": PatientInput(age=70, gender=Gender.FEMALE, chief_complaint_text="Diabetic with jaw pain, shortness of breath, feeling of doom", vitals=Vitals()),
     "expected_level": 2},
    {"name": "Unstable angina", "category": "chest_pain_cardiac",
     "patient": PatientInput(age=55, gender=Gender.MALE, chief_complaint_text="Chest pain at rest, not relieved by nitroglycerin", vitals=Vitals()),
     "expected_level": 2},
    {"name": "Chest pain with syncope", "category": "chest_pain_cardiac",
     "patient": PatientInput(age=58, gender=Gender.MALE, chief_complaint_text="Chest pain, passed out briefly, still having pain", vitals=Vitals()),
     "expected_level": 2},
    
    # Stroke / TIA
    {"name": "Acute stroke - facial droop", "category": "stroke_symptoms",
     "patient": PatientInput(age=68, gender=Gender.MALE, chief_complaint_text="Sudden facial droop, arm weakness, slurred speech", vitals=Vitals()),
     "expected_level": 2},
    {"name": "Stroke - wake up deficit", "category": "stroke_symptoms",
     "patient": PatientInput(age=72, gender=Gender.FEMALE, chief_complaint_text="Woke up unable to move right side, can't speak clearly", vitals=Vitals()),
     "expected_level": 2},
    {"name": "TIA - resolved symptoms", "category": "stroke_symptoms",
     "patient": PatientInput(age=65, gender=Gender.MALE, chief_complaint_text="Had sudden weakness and speech problems, lasted 20 minutes, now resolved", vitals=Vitals()),
     "expected_level": 2},
    
    # Respiratory Distress - Severe
    {"name": "Severe asthma exacerbation", "category": "respiratory_distress",
     "patient": PatientInput(age=25, gender=Gender.FEMALE, chief_complaint_text="Severe asthma attack, can barely speak, using accessory muscles",
                            vitals=Vitals(spo2=88, rr=32)),
     "expected_level": 2},
    {"name": "COPD exacerbation - severe", "category": "respiratory_distress",
     "patient": PatientInput(age=70, gender=Gender.MALE, chief_complaint_text="COPD flare, much worse than usual, can't catch breath",
                            vitals=Vitals(spo2=85, rr=28), is_copd=True),
     "expected_level": 2},
    {"name": "Pulmonary embolism suspected", "category": "respiratory_distress",
     "patient": PatientInput(age=45, gender=Gender.FEMALE, chief_complaint_text="Sudden shortness of breath, chest pain worse with breathing, recent surgery", vitals=Vitals()),
     "expected_level": 2},
    
    # Altered Mental Status
    {"name": "New confusion - elderly", "category": "altered_mental_status",
     "patient": PatientInput(age=80, gender=Gender.MALE, chief_complaint_text="Suddenly confused, doesn't know where he is, not his baseline", vitals=Vitals()),
     "expected_level": 2},
    {"name": "Altered consciousness post-fall", "category": "altered_mental_status",
     "patient": PatientInput(age=75, gender=Gender.FEMALE, chief_complaint_text="Fell and hit head, now drowsy and confused", vitals=Vitals()),
     "expected_level": 2},
    
    # Severe Pain
    {"name": "Worst headache of life", "category": "severe_headache",
     "patient": PatientInput(age=45, gender=Gender.FEMALE, chief_complaint_text="Sudden worst headache of my life, came on like a thunderclap", vitals=Vitals()),
     "expected_level": 2},
    {"name": "Headache with neck stiffness", "category": "severe_headache",
     "patient": PatientInput(age=30, gender=Gender.MALE, chief_complaint_text="Severe headache, stiff neck, fever, light hurts my eyes",
                            vitals=Vitals(temp=39.2)),
     "expected_level": 2},
    
    # Diabetic Emergencies
    {"name": "DKA - known diabetic", "category": "diabetic_emergency",
     "patient": PatientInput(age=22, gender=Gender.FEMALE, chief_complaint_text="Type 1 diabetic, vomiting, fruity breath, blood sugar over 500", vitals=Vitals()),
     "expected_level": 2},
    {"name": "Hypoglycemia - altered", "category": "diabetic_emergency",
     "patient": PatientInput(age=60, gender=Gender.MALE, chief_complaint_text="Diabetic, found confused and sweating, blood sugar 35", vitals=Vitals()),
     "expected_level": 2},
    
    # Psychiatric Emergency
    {"name": "Active suicidal ideation with plan", "category": "suicidal_ideation",
     "patient": PatientInput(age=35, gender=Gender.MALE, chief_complaint_text="Wants to kill himself, has a plan, brought in by family", vitals=Vitals()),
     "expected_level": 2},
    {"name": "Suicide attempt - recent", "category": "suicidal_ideation",
     "patient": PatientInput(age=19, gender=Gender.FEMALE, chief_complaint_text="Took a handful of pills 2 hours ago trying to end her life", vitals=Vitals()),
     "expected_level": 2},
    
    # OB/GYN Emergencies
    {"name": "Possible ectopic pregnancy", "category": "obstetric_emergency",
     "patient": PatientInput(age=28, gender=Gender.FEMALE, chief_complaint_text="Positive pregnancy test, severe one-sided pelvic pain, spotting",
                            vitals=Vitals(), is_pregnant=True),
     "expected_level": 2},
    {"name": "Vaginal bleeding in pregnancy - heavy", "category": "obstetric_emergency",
     "patient": PatientInput(age=32, gender=Gender.FEMALE, chief_complaint_text="20 weeks pregnant, heavy vaginal bleeding, soaking pads",
                            vitals=Vitals(), is_pregnant=True),
     "expected_level": 2},
    
    # Testicular Emergency
    {"name": "Testicular torsion suspected", "category": "testicular_torsion",
     "patient": PatientInput(age=16, gender=Gender.MALE, chief_complaint_text="Sudden severe testicular pain, testicle is swollen and riding high", vitals=Vitals()),
     "expected_level": 2},
    
    # Sepsis
    {"name": "Sepsis - fever with hypotension", "category": "sepsis",
     "patient": PatientInput(age=65, gender=Gender.FEMALE, chief_complaint_text="Fever, chills, feeling terrible, dizzy when standing",
                            vitals=Vitals(temp=39.5, hr=115, sbp=88)),
     "expected_level": 2},
    
    # Severe Allergic Reaction (not anaphylaxis)
    {"name": "Allergic reaction - progressing", "category": "allergic_reaction",
     "patient": PatientInput(age=30, gender=Gender.MALE, chief_complaint_text="Allergic reaction, hives spreading, starting to feel throat tightness", vitals=Vitals()),
     "expected_level": 2},
    
    # =========================================================================
    # LEVEL 3 - URGENT (Multiple resources needed)
    # =========================================================================
    
    # Abdominal Pain
    {"name": "Appendicitis suspected", "category": "abdominal_pain_moderate",
     "patient": PatientInput(age=22, gender=Gender.MALE, chief_complaint_text="Right lower abdominal pain, started around belly button, now localized", vitals=Vitals()),
     "expected_level": 3},
    {"name": "Abdominal pain with vomiting", "category": "abdominal_pain_moderate",
     "patient": PatientInput(age=45, gender=Gender.FEMALE, chief_complaint_text="Abdominal pain and vomiting for 2 days, can't keep anything down", vitals=Vitals()),
     "expected_level": 3},
    {"name": "Gallbladder pain", "category": "abdominal_pain_moderate",
     "patient": PatientInput(age=40, gender=Gender.FEMALE, chief_complaint_text="Right upper quadrant pain after eating fatty food, radiates to back", vitals=Vitals()),
     "expected_level": 3},
    {"name": "Kidney stone - moderate pain", "category": "kidney_stone",
     "patient": PatientInput(age=35, gender=Gender.MALE, chief_complaint_text="Flank pain radiating to groin, blood in urine, history of kidney stones", vitals=Vitals()),
     "expected_level": 3},
    {"name": "Diverticulitis suspected", "category": "abdominal_pain_moderate",
     "patient": PatientInput(age=60, gender=Gender.MALE, chief_complaint_text="Left lower quadrant pain, low grade fever, change in bowel habits",
                            vitals=Vitals(temp=38.3)),
     "expected_level": 3},
    
    # Fever / Infection
    {"name": "Pneumonia - stable", "category": "fever_with_symptoms",
     "patient": PatientInput(age=55, gender=Gender.MALE, chief_complaint_text="Cough with green sputum, fever for 3 days, short of breath with activity",
                            vitals=Vitals(temp=38.8, spo2=93)),
     "expected_level": 3},
    {"name": "Cellulitis - spreading", "category": "fever_with_symptoms",
     "patient": PatientInput(age=50, gender=Gender.MALE, chief_complaint_text="Red, swollen leg getting bigger, fever, red streaks going up",
                            vitals=Vitals(temp=38.5)),
     "expected_level": 3},
    {"name": "UTI with fever - pyelonephritis", "category": "fever_with_symptoms",
     "patient": PatientInput(age=28, gender=Gender.FEMALE, chief_complaint_text="Burning with urination, back pain, fever and chills",
                            vitals=Vitals(temp=39.0)),
     "expected_level": 3},
    
    # Dehydration / GI
    {"name": "Dehydration - moderate", "category": "vomiting_dehydration",
     "patient": PatientInput(age=70, gender=Gender.FEMALE, chief_complaint_text="Vomiting and diarrhea for 3 days, dizzy, not urinating much", vitals=Vitals()),
     "expected_level": 3},
    {"name": "GI bleed - stable", "category": "moderate_bleeding",
     "patient": PatientInput(age=55, gender=Gender.MALE, chief_complaint_text="Black tarry stools for 2 days, feels weak",
                            vitals=Vitals(hr=95, sbp=110)),
     "expected_level": 3},
    
    # Fractures
    {"name": "Ankle fracture - obvious deformity", "category": "fracture_deformity",
     "patient": PatientInput(age=35, gender=Gender.MALE, chief_complaint_text="Twisted ankle, obvious deformity, can't bear weight", vitals=Vitals()),
     "expected_level": 3},
    {"name": "Wrist fracture - fall on outstretched hand", "category": "fracture_deformity",
     "patient": PatientInput(age=65, gender=Gender.FEMALE, chief_complaint_text="Fell on hand, wrist is swollen and deformed, very painful", vitals=Vitals()),
     "expected_level": 3},
    {"name": "Hip fracture - elderly fall", "category": "fracture_deformity",
     "patient": PatientInput(age=82, gender=Gender.FEMALE, chief_complaint_text="Fell at home, can't move hip, leg is shortened and rotated out", vitals=Vitals()),
     "expected_level": 3},
    
    # Asthma - Moderate
    {"name": "Asthma exacerbation - moderate", "category": "asthma_exacerbation",
     "patient": PatientInput(age=20, gender=Gender.FEMALE, chief_complaint_text="Asthma flare, wheezing, used inhaler 4 times today, not helping much",
                            vitals=Vitals(spo2=94)),
     "expected_level": 3},
    
    # Lacerations requiring repair
    {"name": "Laceration - needs sutures", "category": "moderate_laceration",
     "patient": PatientInput(age=30, gender=Gender.MALE, chief_complaint_text="Cut hand on glass, deep laceration, bleeding controlled with pressure", vitals=Vitals()),
     "expected_level": 3},
    {"name": "Facial laceration", "category": "moderate_laceration",
     "patient": PatientInput(age=8, gender=Gender.MALE, chief_complaint_text="Hit face on table, laceration on forehead, will need stitches", vitals=Vitals()),
     "expected_level": 3},
    
    # Head injury - minor
    {"name": "Concussion - stable", "category": "head_injury",
     "patient": PatientInput(age=17, gender=Gender.MALE, chief_complaint_text="Hit head playing football, brief loss of consciousness, now alert but headache", vitals=Vitals()),
     "expected_level": 3},
    
    # =========================================================================
    # LEVEL 4 - LESS URGENT (Single resource needed)
    # =========================================================================
    
    # URI / Viral
    {"name": "Common cold", "category": "uri_symptoms",
     "patient": PatientInput(age=30, gender=Gender.FEMALE, chief_complaint_text="Runny nose, sore throat, cough for 3 days", vitals=Vitals()),
     "expected_level": 4},
    {"name": "Flu-like illness", "category": "uri_symptoms",
     "patient": PatientInput(age=35, gender=Gender.MALE, chief_complaint_text="Body aches, fever, cough, fatigue for 2 days",
                            vitals=Vitals(temp=38.3)),
     "expected_level": 4},
    {"name": "Sore throat - simple", "category": "uri_symptoms",
     "patient": PatientInput(age=25, gender=Gender.FEMALE, chief_complaint_text="Sore throat for 2 days, no fever, just want strep test", vitals=Vitals()),
     "expected_level": 4},
    {"name": "Sinus congestion", "category": "uri_symptoms",
     "patient": PatientInput(age=40, gender=Gender.MALE, chief_complaint_text="Sinus pressure and congestion for a week", vitals=Vitals()),
     "expected_level": 4},
    
    # UTI - Simple
    {"name": "UTI - uncomplicated", "category": "uti_symptoms",
     "patient": PatientInput(age=28, gender=Gender.FEMALE, chief_complaint_text="Burning when I pee, having to go frequently, no fever", vitals=Vitals()),
     "expected_level": 4},
    
    # Minor Injuries
    {"name": "Sprained ankle", "category": "minor_injury",
     "patient": PatientInput(age=25, gender=Gender.MALE, chief_complaint_text="Twisted ankle, yesterday, swollen but can walk on it", vitals=Vitals()),
     "expected_level": 4},
    {"name": "Minor laceration", "category": "minor_laceration",
     "patient": PatientInput(age=35, gender=Gender.FEMALE, chief_complaint_text="Small cut on finger, stopped bleeding, might need a stitch or two", vitals=Vitals()),
     "expected_level": 4},
    {"name": "Finger injury - jammed", "category": "minor_injury",
     "patient": PatientInput(age=15, gender=Gender.MALE, chief_complaint_text="Jammed finger playing basketball, swollen, can still move it", vitals=Vitals()),
     "expected_level": 4},
    
    # Ear/Eye
    {"name": "Ear pain - otitis", "category": "earache",
     "patient": PatientInput(age=5, gender=Gender.MALE, chief_complaint_text="Ear pain for 2 days, pulling at ear, fussy", vitals=Vitals()),
     "expected_level": 4},
    {"name": "Pink eye", "category": "eye_complaint",
     "patient": PatientInput(age=8, gender=Gender.FEMALE, chief_complaint_text="Red eye with yellow discharge, started this morning", vitals=Vitals()),
     "expected_level": 4},
    {"name": "Foreign body in eye", "category": "eye_complaint",
     "patient": PatientInput(age=40, gender=Gender.MALE, chief_complaint_text="Something flew into my eye at work, feels like something still in there", vitals=Vitals()),
     "expected_level": 4},
    
    # Skin
    {"name": "Rash - mild allergic", "category": "mild_allergic",
     "patient": PatientInput(age=30, gender=Gender.FEMALE, chief_complaint_text="Itchy rash on arms after new laundry detergent", vitals=Vitals()),
     "expected_level": 4},
    {"name": "Insect bite - local reaction", "category": "insect_bite",
     "patient": PatientInput(age=25, gender=Gender.MALE, chief_complaint_text="Spider bite on leg, red and swollen around the bite, no spreading", vitals=Vitals()),
     "expected_level": 4},
    {"name": "Minor burn", "category": "minor_burn",
     "patient": PatientInput(age=35, gender=Gender.FEMALE, chief_complaint_text="Burned hand on stove, small area, red and painful, no blisters", vitals=Vitals()),
     "expected_level": 4},
    
    # Pain - Chronic/Minor
    {"name": "Back pain - chronic", "category": "back_pain_chronic",
     "patient": PatientInput(age=50, gender=Gender.MALE, chief_complaint_text="Lower back pain, had it for years, worse this week, ran out of medication", vitals=Vitals()),
     "expected_level": 4},
    {"name": "Headache - tension type", "category": "headache_mild",
     "patient": PatientInput(age=35, gender=Gender.FEMALE, chief_complaint_text="Headache for 2 days, band-like pressure, stressed at work", vitals=Vitals()),
     "expected_level": 4},
    {"name": "Knee pain - chronic", "category": "joint_pain",
     "patient": PatientInput(age=60, gender=Gender.MALE, chief_complaint_text="Knee pain getting worse, probably arthritis, need something for pain", vitals=Vitals()),
     "expected_level": 4},
    
    # GI - Minor
    {"name": "Constipation", "category": "mild_gi",
     "patient": PatientInput(age=45, gender=Gender.FEMALE, chief_complaint_text="Haven't had a bowel movement in 5 days, uncomfortable", vitals=Vitals()),
     "expected_level": 4},
    {"name": "Mild diarrhea", "category": "mild_gi",
     "patient": PatientInput(age=30, gender=Gender.MALE, chief_complaint_text="Loose stools since yesterday, no blood, drinking fluids", vitals=Vitals()),
     "expected_level": 4},
    {"name": "Heartburn", "category": "mild_gi",
     "patient": PatientInput(age=50, gender=Gender.MALE, chief_complaint_text="Burning in chest after eating, happens a lot, need refill of my antacid", vitals=Vitals()),
     "expected_level": 4},
    
    # Pediatric - Minor
    {"name": "Child with cold", "category": "uri_symptoms",
     "patient": PatientInput(age=3, gender=Gender.FEMALE, chief_complaint_text="Runny nose and cough for 3 days, eating and drinking okay", vitals=Vitals()),
     "expected_level": 4},
    {"name": "Child with fever - well appearing", "category": "fever_simple",
     "patient": PatientInput(age=4, gender=Gender.MALE, chief_complaint_text="Fever since yesterday, still playing, eating less",
                            vitals=Vitals(temp=38.5)),
     "expected_level": 4},
    
    # =========================================================================
    # LEVEL 5 - NON-URGENT (No resources needed)
    # =========================================================================
    
    # Prescription Refills
    {"name": "Medication refill - BP meds", "category": "prescription_refill",
     "patient": PatientInput(age=60, gender=Gender.MALE, chief_complaint_text="Need refill of blood pressure medication, pharmacy is closed", vitals=Vitals()),
     "expected_level": 5},
    {"name": "Medication refill - inhaler", "category": "prescription_refill",
     "patient": PatientInput(age=35, gender=Gender.FEMALE, chief_complaint_text="Ran out of my asthma inhaler, feeling fine, just need a refill", vitals=Vitals()),
     "expected_level": 5},
    
    # Wound Checks / Suture Removal
    {"name": "Suture removal", "category": "suture_removal",
     "patient": PatientInput(age=40, gender=Gender.MALE, chief_complaint_text="Here to get my stitches out, been 10 days", vitals=Vitals()),
     "expected_level": 5},
    {"name": "Wound check", "category": "wound_check",
     "patient": PatientInput(age=55, gender=Gender.FEMALE, chief_complaint_text="Following up on wound from last week, looks good, no concerns", vitals=Vitals()),
     "expected_level": 5},
    {"name": "Dressing change", "category": "wound_check",
     "patient": PatientInput(age=65, gender=Gender.MALE, chief_complaint_text="Need my bandage changed, wound is healing well", vitals=Vitals()),
     "expected_level": 5},
    
    # Medical Certificates / Forms
    {"name": "Work note needed", "category": "medical_certificate",
     "patient": PatientInput(age=30, gender=Gender.MALE, chief_complaint_text="Had the flu last week, feeling better, just need a note for work", vitals=Vitals()),
     "expected_level": 5},
    {"name": "Sports physical", "category": "medical_certificate",
     "patient": PatientInput(age=14, gender=Gender.FEMALE, chief_complaint_text="Need a physical for soccer team", vitals=Vitals()),
     "expected_level": 5},
    
    # Stable Chronic Conditions
    {"name": "Routine BP check", "category": "chronic_stable",
     "patient": PatientInput(age=70, gender=Gender.FEMALE, chief_complaint_text="Just want to check my blood pressure, feeling fine", vitals=Vitals()),
     "expected_level": 5},
    {"name": "Diabetes check - stable", "category": "chronic_stable",
     "patient": PatientInput(age=55, gender=Gender.MALE, chief_complaint_text="Diabetic, sugars have been good, just want a check up", vitals=Vitals()),
     "expected_level": 5},
    
    # Minor Complaints - Very Low Acuity
    {"name": "Insomnia", "category": "minor_complaint",
     "patient": PatientInput(age=45, gender=Gender.FEMALE, chief_complaint_text="Having trouble sleeping for the past month", vitals=Vitals()),
     "expected_level": 5},
    {"name": "Mild dandruff", "category": "minor_complaint",
     "patient": PatientInput(age=25, gender=Gender.MALE, chief_complaint_text="Flaky scalp, need a recommendation for shampoo", vitals=Vitals()),
     "expected_level": 5},
]

def main():
    parser = argparse.ArgumentParser(description="Run SAFE-Triage English scenario tests.")
    parser.add_argument("--use-ai", action="store_true", help="Enable Gemini-assisted categorization")
    parser.add_argument("--limit", type=int, default=0, help="Run only the first N scenarios")
    parser.add_argument("--json-out", default="", help="Optional path to write a summary JSON")
    args = parser.parse_args()

    selected_scenarios = ENGLISH_SCENARIOS[: args.limit] if args.limit and args.limit > 0 else ENGLISH_SCENARIOS
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print("=" * 70)
    print(f"SAFE-Triage English Clinical Scenarios Test Suite")
    print(f"Started: {timestamp}")
    print(f"Total Scenarios: {len(selected_scenarios)}")
    print(f"Mode: {'AI-assisted' if args.use_ai else 'Deterministic only'}")
    print("=" * 70)
    
    engine = DeterministicTriageEngine(use_ai=args.use_ai)
    
    results = {
        "passed": [],
        "failed": [],
        "critical_undertriage": [],
        "over_triage": []
    }
    
    level_stats = {1: {"pass": 0, "fail": 0}, 2: {"pass": 0, "fail": 0}, 
                   3: {"pass": 0, "fail": 0}, 4: {"pass": 0, "fail": 0}, 
                   5: {"pass": 0, "fail": 0}}
    
    print("\n" + "-" * 70)
    
    for i, test in enumerate(selected_scenarios, 1):
        result = run_test(engine, test)
        
        # Categorize result
        if result["passed"]:
            results["passed"].append(result)
            level_stats[result["expected"]]["pass"] += 1
            status = f"{GREEN}✅ PASS{RESET}"
        elif result["critical_undertriage"]:
            results["critical_undertriage"].append(result)
            results["failed"].append(result)
            level_stats[result["expected"]]["fail"] += 1
            status = f"{RED}🚨 CRITICAL UNDER-TRIAGE{RESET}"
        elif result["over_triage"]:
            results["over_triage"].append(result)
            results["failed"].append(result)
            level_stats[result["expected"]]["fail"] += 1
            status = f"{YELLOW}⬆️ OVER-TRIAGE{RESET}"
        else:
            results["failed"].append(result)
            level_stats[result["expected"]]["fail"] += 1
            status = f"{YELLOW}❌ MISMATCH{RESET}"
        
        print(f"[{i:3}/{len(selected_scenarios)}] {status}: {result['name']}")
        print(f"         Expected: L{result['expected']} | Got: L{result['actual']} | Category: {result['matched_category']}")
        
        if not result["passed"]:
            print(f"         Complaint: \"{result['complaint'][:60]}...\"" if len(result['complaint']) > 60 else f"         Complaint: \"{result['complaint']}\"")
        
        print("-" * 70)
    
    # Summary
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    
    total = len(selected_scenarios)
    passed = len(results["passed"])
    failed = len(results["failed"])
    critical = len(results["critical_undertriage"])
    over = len(results["over_triage"])
    
    print(f"\n{CYAN}Overall Results:{RESET}")
    print(f"  Total Tests:           {total}")
    print(f"  {GREEN}Passed:                {passed} ({100*passed/total:.1f}%){RESET}")
    print(f"  {YELLOW}Failed:                {failed} ({100*failed/total:.1f}%){RESET}")
    print(f"  {RED}Critical Under-triage: {critical}{RESET}")
    print(f"  {YELLOW}Over-triage:           {over}{RESET}")
    
    print(f"\n{CYAN}Results by ESI Level:{RESET}")
    print(f"  {'Level':<8} {'Pass':<8} {'Fail':<8} {'Rate':<8}")
    print(f"  {'-'*32}")
    for level in range(1, 6):
        p = level_stats[level]["pass"]
        f = level_stats[level]["fail"]
        t = p + f
        rate = f"{100*p/t:.0f}%" if t > 0 else "N/A"
        print(f"  Level {level:<3} {p:<8} {f:<8} {rate:<8}")
    
    # List failures for debugging
    if results["critical_undertriage"]:
        print(f"\n{RED}{'='*70}")
        print("CRITICAL UNDER-TRIAGE CASES (MUST FIX)")
        print(f"{'='*70}{RESET}")
        for r in results["critical_undertriage"]:
            print(f"  • {r['name']}")
            print(f"    Expected: L{r['expected']} → Got: L{r['actual']}")
            print(f"    Complaint: \"{r['complaint']}\"")
            print(f"    Matched: {r['matched_category']}")
            print()
    
    if results["over_triage"]:
        print(f"\n{YELLOW}{'='*70}")
        print("OVER-TRIAGE CASES (Review if too conservative)")
        print(f"{'='*70}{RESET}")
        for r in results["over_triage"]:
            print(f"  • {r['name']}")
            print(f"    Expected: L{r['expected']} → Got: L{r['actual']}")
            print()

    if args.json_out:
        payload = {
            "timestamp": timestamp,
            "mode": "ai" if args.use_ai else "deterministic",
            "total": total,
            "passed": passed,
            "failed": failed,
            "critical_undertriage": critical,
            "over_triage": over,
            "pass_rate": round((passed / total) * 100, 2) if total else 0.0,
            "results": results,
        }
        with open(args.json_out, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)
        print(f"\nJSON summary written to: {args.json_out}")
    
    # Exit code
    if critical > 0:
        print(f"\n{RED}⚠️  CRITICAL: {critical} under-triage cases detected!{RESET}")
        print("These MUST be fixed before production deployment.")
        sys.exit(1)
    elif failed > 0:
        print(f"\n{YELLOW}⚠️  {failed} tests failed but no critical under-triage.{RESET}")
        print("Review over-triage cases if system is too conservative.")
        sys.exit(0)
    else:
        print(f"\n{GREEN}✅ All {total} English clinical scenarios passed!{RESET}")
        sys.exit(0)

if __name__ == "__main__":
    main()
