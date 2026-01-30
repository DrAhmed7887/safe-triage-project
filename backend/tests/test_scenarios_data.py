"""
SAFE-Triage - Pre-defined Clinical Test Scenarios
==================================================

A comprehensive set of clinical scenarios for testing the deterministic
triage classification without requiring AI API calls.

These scenarios cover:
- All 5 ESI triage levels
- Various Arabic dialects (Egyptian, Levantine, Gulf, MSA)
- Edge cases and challenging presentations
- Common misclassification patterns

Author: Ahmed Zayed
"""

# Pre-defined test scenarios organized by expected triage level
# Each scenario includes complaint in Arabic/English, vitals, and expected classification

LEVEL_1_SCENARIOS = [
    {
        "id": "L1-001",
        "complaint_ar": "مش بيرد عليا خالص والنفس ضعيف جداً",
        "complaint_en": "Not responding at all and breathing very weak",
        "age": 55,
        "gender": "male",
        "vitals": {"hr": 40, "rr": 6, "spo2": 82, "sbp": 70, "gcs": 3},
        "expected_level": 1,
        "expected_categories": ["unconscious", "respiratory_arrest", "cardiac_arrest"],
        "dialect": "egyptian"
    },
    {
        "id": "L1-002",
        "complaint_ar": "قلبه وقف فجأة وبنحاول ننعشه",
        "complaint_en": "His heart stopped suddenly and we're trying to resuscitate",
        "age": 62,
        "gender": "male",
        "vitals": {"gcs": 3},
        "expected_level": 1,
        "expected_categories": ["cardiac_arrest"],
        "dialect": "egyptian"
    },
    {
        "id": "L1-003",
        "complaint_ar": "بيترعش بس مش عارفين نوقفه",
        "complaint_en": "Having seizures and we can't stop them",
        "age": 28,
        "gender": "female",
        "vitals": {"hr": 130, "gcs": 6},
        "expected_level": 1,
        "expected_categories": ["active_seizure"],
        "dialect": "egyptian"
    },
    {
        "id": "L1-004",
        "complaint_ar": "شرقت في أكل ومش قادرة تاخد نفس",
        "complaint_en": "Choked on food and can't breathe",
        "age": 70,
        "gender": "female",
        "vitals": {"spo2": 75, "rr": 4},
        "expected_level": 1,
        "expected_categories": ["choking"],
        "dialect": "egyptian"
    },
    {
        "id": "L1-005",
        "complaint_ar": "اتضرب برصاصة في بطنه وبينزف جامد",
        "complaint_en": "Shot in the abdomen and bleeding heavily",
        "age": 30,
        "gender": "male",
        "vitals": {"hr": 140, "sbp": 60, "rr": 28, "gcs": 12},
        "expected_level": 1,
        "expected_categories": ["severe_trauma", "severe_bleeding"],
        "dialect": "egyptian"
    },
    {
        "id": "L1-006",
        "complaint_ar": "أخد دوا كتير وعايز ينتحر",
        "complaint_en": "Took many pills, suicide attempt",
        "age": 22,
        "gender": "female",
        "vitals": {"hr": 50, "sbp": 80, "gcs": 10},
        "expected_level": 1,
        "expected_categories": ["poisoning_overdose"],
        "dialect": "egyptian"
    },
    {
        "id": "L1-007",
        "complaint_ar": "حساسية شديدة جداً وشفايفه ورمت ومش قادر يتنفس",
        "complaint_en": "Severe allergic reaction, lips swollen, can't breathe",
        "age": 35,
        "gender": "male",
        "vitals": {"hr": 130, "sbp": 70, "spo2": 85, "rr": 30},
        "expected_level": 1,
        "expected_categories": ["anaphylaxis"],
        "dialect": "egyptian"
    },
    {
        "id": "L1-008",
        "complaint_ar": "غرق في حمام السباحة وطلعوه لسه",
        "complaint_en": "Drowned in swimming pool, just pulled out",
        "age": 8,
        "gender": "male",
        "vitals": {"gcs": 5, "spo2": 70},
        "expected_level": 1,
        "expected_categories": ["drowning"],
        "dialect": "egyptian"
    },
]

LEVEL_2_SCENARIOS = [
    {
        "id": "L2-001",
        "complaint_ar": "صدري بيوجعني جامد من نص ساعة وبينتشر في دراعي الشمال",
        "complaint_en": "Severe chest pain for 30 min radiating to left arm",
        "age": 58,
        "gender": "male",
        "vitals": {"hr": 100, "sbp": 160, "rr": 22, "spo2": 94, "pain_score": 9},
        "expected_level": 2,
        "expected_categories": ["chest_pain_cardiac"],
        "dialect": "egyptian"
    },
    {
        "id": "L2-002",
        "complaint_ar": "وشه مايل فجأة ومش قادر يرفع إيده",
        "complaint_en": "Face drooping suddenly and can't raise arm",
        "age": 72,
        "gender": "male",
        "vitals": {"hr": 88, "sbp": 190, "gcs": 14},
        "expected_level": 2,
        "expected_categories": ["stroke_symptoms"],
        "dialect": "egyptian"
    },
    {
        "id": "L2-003",
        "complaint_ar": "مش قادرة آخد نفسي وبلع صعب جداً",
        "complaint_en": "Can't catch my breath and swallowing is very difficult",
        "age": 45,
        "gender": "female",
        "vitals": {"hr": 120, "rr": 32, "spo2": 88},
        "expected_level": 2,
        "expected_categories": ["respiratory_distress"],
        "dialect": "egyptian"
    },
    {
        "id": "L2-004",
        "complaint_ar": "عنده سكر وبيترعش ومش عارف مكانه",
        "complaint_en": "Diabetic, shaking, confused and doesn't know where he is",
        "age": 55,
        "gender": "male",
        "vitals": {"hr": 110, "gcs": 13, "temp": 36.0},
        "expected_level": 2,
        "expected_categories": ["diabetic_emergency", "altered_mental_status"],
        "dialect": "egyptian"
    },
    {
        "id": "L2-005",
        "complaint_ar": "حامل في الشهر التامن وبتنزف كتير",
        "complaint_en": "8 months pregnant and heavy bleeding",
        "age": 28,
        "gender": "female",
        "vitals": {"hr": 115, "sbp": 95, "rr": 20},
        "expected_level": 2,
        "expected_categories": ["obstetric_emergency"],
        "dialect": "egyptian"
    },
    {
        "id": "L2-006",
        "complaint_ar": "عايز يقتل نفسه وقال كده",
        "complaint_en": "Says he wants to kill himself",
        "age": 35,
        "gender": "male",
        "vitals": {"hr": 90, "sbp": 130},
        "expected_level": 2,
        "expected_categories": ["suicidal_homicidal"],
        "dialect": "egyptian"
    },
    {
        "id": "L2-007",
        "complaint_ar": "صداع شديد جداً مفاجئ زي ما حد ضربه في راسه",
        "complaint_en": "Sudden severe headache like being hit in the head",
        "age": 48,
        "gender": "female",
        "vitals": {"hr": 95, "sbp": 180, "gcs": 14},
        "expected_level": 2,
        "expected_categories": ["severe_headache"],
        "dialect": "egyptian"
    },
    {
        "id": "L2-008",
        "complaint_ar": "خصيته اليمين بتوجعه جداً من ساعتين فجأة",
        "complaint_en": "Right testicle severe pain suddenly 2 hours ago",
        "age": 18,
        "gender": "male",
        "vitals": {"hr": 100, "pain_score": 10},
        "expected_level": 2,
        "expected_categories": ["testicular_pain", "severe_pain"],
        "dialect": "egyptian"
    },
    {
        "id": "L2-009",
        "complaint_ar": "سخونية عالية جداً ومش بيرد كويس ومعياش جداً",
        "complaint_en": "Very high fever, not responding well, very sick looking",
        "age": 3,
        "gender": "male",
        "vitals": {"hr": 160, "temp": 40.2, "rr": 40, "gcs": 13},
        "expected_level": 2,
        "expected_categories": ["high_fever_toxic"],
        "dialect": "egyptian"
    },
]

LEVEL_3_SCENARIOS = [
    {
        "id": "L3-001",
        "complaint_ar": "بطني بتوجعني من امبارح في الجنب الأيمن تحت",
        "complaint_en": "Abdominal pain since yesterday, right lower side",
        "age": 25,
        "gender": "female",
        "vitals": {"hr": 95, "temp": 38.2, "pain_score": 7},
        "expected_level": 3,
        "expected_categories": ["abdominal_pain_moderate"],
        "dialect": "egyptian"
    },
    {
        "id": "L3-002",
        "complaint_ar": "صدري بيوجعني بس بيزيد لما بتنفس",
        "complaint_en": "Chest pain that increases with breathing",
        "age": 32,
        "gender": "male",
        "vitals": {"hr": 88, "rr": 20, "spo2": 96, "pain_score": 6},
        "expected_level": 3,
        "expected_categories": ["chest_pain_noncardiac"],
        "dialect": "egyptian"
    },
    {
        "id": "L3-003",
        "complaint_ar": "رجلي اتكسرت وشكلها مش طبيعي",
        "complaint_en": "My leg is broken and looks deformed",
        "age": 40,
        "gender": "male",
        "vitals": {"hr": 100, "pain_score": 8},
        "expected_level": 3,
        "expected_categories": ["fracture_deformity"],
        "dialect": "egyptian"
    },
    {
        "id": "L3-004",
        "complaint_ar": "بيرجع من امبارح ومش قادر ياكل حاجة",
        "complaint_en": "Vomiting since yesterday, can't eat anything",
        "age": 55,
        "gender": "male",
        "vitals": {"hr": 105, "sbp": 100, "temp": 37.5},
        "expected_level": 3,
        "expected_categories": ["vomiting_dehydration"],
        "dialect": "egyptian"
    },
    {
        "id": "L3-005",
        "complaint_ar": "عنده سخونية من يومين وكحة شديدة وضيق نفس شوية",
        "complaint_en": "Fever for 2 days, severe cough, mild shortness of breath",
        "age": 60,
        "gender": "male",
        "vitals": {"hr": 98, "temp": 38.8, "rr": 22, "spo2": 93},
        "expected_level": 3,
        "expected_categories": ["fever_with_symptoms", "moderate_dyspnea"],
        "dialect": "egyptian"
    },
    {
        "id": "L3-006",
        "complaint_ar": "إيده بتنزف من جرح كبير",
        "complaint_en": "Hand bleeding from a large wound",
        "age": 35,
        "gender": "male",
        "vitals": {"hr": 95, "sbp": 120},
        "expected_level": 3,
        "expected_categories": ["moderate_bleeding"],
        "dialect": "egyptian"
    },
    {
        "id": "L3-007",
        "complaint_ar": "ابني عنده سنتين وعياط كتير ومش عايز ياكل وسخن",
        "complaint_en": "My 2 year old is crying a lot, won't eat, and has fever",
        "age": 2,
        "gender": "male",
        "vitals": {"hr": 140, "temp": 39.0, "rr": 30},
        "expected_level": 3,
        "expected_categories": ["pediatric_distress", "fever_with_symptoms"],
        "dialect": "egyptian"
    },
]

LEVEL_4_SCENARIOS = [
    {
        "id": "L4-001",
        "complaint_ar": "وقعت وركبتي وارمة شوية",
        "complaint_en": "Fell and my knee is slightly swollen",
        "age": 30,
        "gender": "male",
        "vitals": {"hr": 78, "sbp": 120, "pain_score": 4},
        "expected_level": 4,
        "expected_categories": ["minor_trauma"],
        "dialect": "egyptian"
    },
    {
        "id": "L4-002",
        "complaint_ar": "جرحت إيدي بسكينة وعايزة غرز",
        "complaint_en": "Cut my hand with a knife, needs stitches",
        "age": 28,
        "gender": "female",
        "vitals": {"hr": 80, "sbp": 118},
        "expected_level": 4,
        "expected_categories": ["laceration_simple"],
        "dialect": "egyptian"
    },
    {
        "id": "L4-003",
        "complaint_ar": "عندي برد وزكام وكحة من 3 أيام",
        "complaint_en": "Cold, runny nose and cough for 3 days",
        "age": 35,
        "gender": "female",
        "vitals": {"hr": 82, "temp": 37.8, "rr": 16, "spo2": 98},
        "expected_level": 4,
        "expected_categories": ["uri_symptoms"],
        "dialect": "egyptian"
    },
    {
        "id": "L4-004",
        "complaint_ar": "زوري بيوجعني ومش قادرة أبلع",
        "complaint_en": "Sore throat and difficulty swallowing",
        "age": 22,
        "gender": "female",
        "vitals": {"hr": 85, "temp": 38.0},
        "expected_level": 4,
        "expected_categories": ["sore_throat"],
        "dialect": "egyptian"
    },
    {
        "id": "L4-005",
        "complaint_ar": "ودني بتوجعني من امبارح",
        "complaint_en": "Ear pain since yesterday",
        "age": 8,
        "gender": "male",
        "vitals": {"hr": 90, "temp": 37.5},
        "expected_level": 4,
        "expected_categories": ["earache"],
        "dialect": "egyptian"
    },
    {
        "id": "L4-006",
        "complaint_ar": "حرقان في البول ورايح الحمام كتير",
        "complaint_en": "Burning urination and frequent bathroom trips",
        "age": 45,
        "gender": "female",
        "vitals": {"hr": 80, "temp": 37.2},
        "expected_level": 4,
        "expected_categories": ["uti_symptoms"],
        "dialect": "egyptian"
    },
    {
        "id": "L4-007",
        "complaint_ar": "عندي حساسية وجسمي فيه حكة وطفح",
        "complaint_en": "Allergy with itching and rash on my body",
        "age": 30,
        "gender": "male",
        "vitals": {"hr": 82, "sbp": 120},
        "expected_level": 4,
        "expected_categories": ["mild_allergic"],
        "dialect": "egyptian"
    },
    {
        "id": "L4-008",
        "complaint_ar": "ظهري بيوجعني من فترة بس اليوم زاد",
        "complaint_en": "Back pain for a while but worse today",
        "age": 50,
        "gender": "male",
        "vitals": {"hr": 78, "sbp": 130, "pain_score": 5},
        "expected_level": 4,
        "expected_categories": ["back_pain_chronic", "mild_pain"],
        "dialect": "egyptian"
    },
    {
        "id": "L4-009",
        "complaint_ar": "عندي صداع خفيف من الصبح",
        "complaint_en": "Mild headache since morning",
        "age": 35,
        "gender": "female",
        "vitals": {"hr": 75, "sbp": 120},
        "expected_level": 4,
        "expected_categories": ["headache_mild"],
        "dialect": "egyptian"
    },
    {
        "id": "L4-010",
        "complaint_ar": "عندي إسهال من امبارح بس مش شديد",
        "complaint_en": "Diarrhea since yesterday but not severe",
        "age": 28,
        "gender": "male",
        "vitals": {"hr": 85, "temp": 37.5},
        "expected_level": 4,
        "expected_categories": ["mild_gi"],
        "dialect": "egyptian"
    },
]

LEVEL_5_SCENARIOS = [
    {
        "id": "L5-001",
        "complaint_ar": "عايز أجدد الروشتة بتاعة الضغط",
        "complaint_en": "Need to refill my blood pressure prescription",
        "age": 60,
        "gender": "male",
        "vitals": {"hr": 72, "sbp": 135, "rr": 14, "spo2": 99},
        "expected_level": 5,
        "expected_categories": ["prescription_refill"],
        "dialect": "egyptian"
    },
    {
        "id": "L5-002",
        "complaint_ar": "عايز أفك الغرز من العملية",
        "complaint_en": "Need to remove stitches from surgery",
        "age": 45,
        "gender": "male",
        "vitals": {"hr": 70, "sbp": 120},
        "expected_level": 5,
        "expected_categories": ["suture_removal"],
        "dialect": "egyptian"
    },
    {
        "id": "L5-003",
        "complaint_ar": "جاي للمتابعة العادية بتاعتي",
        "complaint_en": "Here for my regular follow up",
        "age": 55,
        "gender": "female",
        "vitals": {"hr": 75, "sbp": 125, "rr": 15, "spo2": 98},
        "expected_level": 5,
        "expected_categories": ["chronic_stable"],
        "dialect": "egyptian"
    },
    {
        "id": "L5-004",
        "complaint_ar": "عايز تقرير طبي للشغل",
        "complaint_en": "Need a medical certificate for work",
        "age": 35,
        "gender": "male",
        "vitals": {"hr": 72, "sbp": 118},
        "expected_level": 5,
        "expected_categories": ["medical_certificate"],
        "dialect": "egyptian"
    },
    {
        "id": "L5-005",
        "complaint_ar": "عندي حاجة بسيطة عايز اطمن عليها",
        "complaint_en": "Minor issue, just want to check on it",
        "age": 40,
        "gender": "female",
        "vitals": {"hr": 74, "sbp": 120, "rr": 14, "spo2": 99},
        "expected_level": 5,
        "expected_categories": ["minor_complaint"],
        "dialect": "egyptian"
    },
]

# Challenging edge cases that are commonly misclassified
EDGE_CASES = [
    {
        "id": "EDGE-001",
        "complaint_ar": "قلبي بيدق بسرعة بس مش بيوجعني",
        "complaint_en": "Heart racing but no pain",
        "age": 35,
        "gender": "female",
        "vitals": {"hr": 150, "sbp": 110, "spo2": 97},
        "expected_level": 2,
        "expected_categories": ["chest_pain_cardiac", "respiratory_distress"],
        "notes": "Tachycardia without chest pain - should still be emergent"
    },
    {
        "id": "EDGE-002",
        "complaint_ar": "حاسس بدوخة وهتقع",
        "complaint_en": "Feeling dizzy and about to fall",
        "age": 75,
        "gender": "male",
        "vitals": {"hr": 50, "sbp": 85, "gcs": 14},
        "expected_level": 2,
        "expected_categories": ["altered_mental_status", "diabetic_emergency"],
        "notes": "Elderly with bradycardia and hypotension - emergent"
    },
    {
        "id": "EDGE-003",
        "complaint_ar": "بنتي رافضة الأكل من يومين",
        "complaint_en": "My daughter refusing to eat for 2 days",
        "age": 1,
        "gender": "female",
        "vitals": {"hr": 140, "temp": 38.5},
        "expected_level": 3,
        "expected_categories": ["pediatric_distress"],
        "notes": "Infant with fever and poor feeding - urgent"
    },
    {
        "id": "EDGE-004",
        "complaint_ar": "عندي ألم في الصدر بس من الكحة",
        "complaint_en": "Chest pain but from coughing",
        "age": 28,
        "gender": "female",
        "vitals": {"hr": 85, "sbp": 115, "spo2": 97, "temp": 37.8},
        "expected_level": 4,
        "expected_categories": ["chest_pain_noncardiac", "uri_symptoms"],
        "notes": "Musculoskeletal chest pain - less urgent"
    },
    {
        "id": "EDGE-005",
        "complaint_ar": "عيني حمرا ومدمعة من الصبح",
        "complaint_en": "Red watery eye since morning",
        "age": 40,
        "gender": "male",
        "vitals": {"hr": 75, "sbp": 120},
        "expected_level": 4,
        "expected_categories": ["minor_complaint", "mild_allergic"],
        "notes": "Eye complaint without vision changes"
    },
]

# All scenarios combined
ALL_SCENARIOS = (
    LEVEL_1_SCENARIOS + 
    LEVEL_2_SCENARIOS + 
    LEVEL_3_SCENARIOS + 
    LEVEL_4_SCENARIOS + 
    LEVEL_5_SCENARIOS + 
    EDGE_CASES
)


def get_scenarios_by_level(level: int) -> list:
    """Get all scenarios for a specific triage level"""
    if level == 1:
        return LEVEL_1_SCENARIOS
    elif level == 2:
        return LEVEL_2_SCENARIOS
    elif level == 3:
        return LEVEL_3_SCENARIOS
    elif level == 4:
        return LEVEL_4_SCENARIOS
    elif level == 5:
        return LEVEL_5_SCENARIOS
    else:
        return []


def get_random_scenario(level: int = None) -> dict:
    """Get a random scenario, optionally filtered by level"""
    import random
    if level:
        scenarios = get_scenarios_by_level(level)
    else:
        scenarios = ALL_SCENARIOS
    return random.choice(scenarios) if scenarios else None


if __name__ == "__main__":
    print(f"Total scenarios: {len(ALL_SCENARIOS)}")
    print(f"  Level 1 (Resuscitation): {len(LEVEL_1_SCENARIOS)}")
    print(f"  Level 2 (Emergent):      {len(LEVEL_2_SCENARIOS)}")
    print(f"  Level 3 (Urgent):        {len(LEVEL_3_SCENARIOS)}")
    print(f"  Level 4 (Less Urgent):   {len(LEVEL_4_SCENARIOS)}")
    print(f"  Level 5 (Non-Urgent):    {len(LEVEL_5_SCENARIOS)}")
    print(f"  Edge Cases:              {len(EDGE_CASES)}")
