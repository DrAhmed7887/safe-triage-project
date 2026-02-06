from typing import List, Dict, Optional

RESOURCE_LABELS: Dict[str, Dict[str, str]] = {
    "X-ray": {"en": "Chest X-ray (PA/Lateral)", "ar": "أشعة صدر (أمامية/جانبية)"},
    "Labs": {"en": "CBC, CMP, Coagulation", "ar": "صورة دم كاملة، وظائف كبد وكلى، سيولة"},
    "Cardiac_labs": {"en": "Troponin I/T, CK-MB, BNP", "ar": "إنزيمات القلب"},
    "ECG": {"en": "12-Lead ECG", "ar": "رسم قلب 12 قناة"},
    "CT": {"en": "CT Scan (specify region)", "ar": "أشعة مقطعية"},
    "CT_head": {"en": "CT Head (non-contrast)", "ar": "أشعة مقطعية على المخ"},
    "Monitor": {"en": "Continuous Cardiac Monitoring", "ar": "مونيتور قلب مستمر"},
    "IV_access": {"en": "IV Access (18G or larger)", "ar": "تركيب كانيولا"},
    "US_abd": {"en": "Abdominal Ultrasound", "ar": "سونار على البطن"},
    "CT_angio": {"en": "CT Angiography", "ar": "أشعة مقطعية بالصبغة"},
    "Sepsis_labs": {"en": "Sepsis panel (CBC, lactate, cultures)", "ar": "تحليل سيبسس (صورة دم، لاكتات، مزرعة)"},
    "Pain_assessment": {"en": "Pain Assessment (VAS Scale)", "ar": "تقييم الألم"},
    "Neuro_exam": {"en": "Neurovascular Examination", "ar": "فحص الأعصاب والأوعية الدموية"},
    "Splint": {"en": "Splint / Immobilization", "ar": "جبيرة / تثبيت"},
    "Ortho_xray": {"en": "X-ray of Affected Limb", "ar": "أشعة على الطرف المصاب"},
    "Orthopedic_eval": {"en": "Orthopedic Evaluation", "ar": "تقييم عظام"},
}


CATEGORY_RESOURCES: Dict[str, List[str]] = {
    "chest_pain_cardiac": ["ECG", "Cardiac_labs", "Labs", "Monitor", "IV_access", "X-ray"],
    "chest_pain_respiratory": ["X-ray", "Labs", "CT_angio", "ECG", "Monitor"],
    "stroke_symptoms": ["CT_head", "Labs", "ECG", "Monitor"],
    "dyspnea": ["X-ray", "Labs", "ECG", "Monitor"],
    "respiratory_distress": ["X-ray", "Labs", "ECG", "Monitor", "IV_access"],
    "abdominal_pain": ["Labs", "US_abd", "ECG"],
    "sepsis_concern": ["Sepsis_labs", "IV_access", "Monitor", "X-ray"],
    "fracture_deformity": ["Ortho_xray", "Pain_assessment", "Neuro_exam", "Splint"],
    "moderate_trauma": ["Ortho_xray", "Pain_assessment", "Neuro_exam", "Splint"],
    "minor_trauma": ["Ortho_xray", "Pain_assessment", "Splint"],
    "hip_fracture_elderly": ["Ortho_xray", "Pain_assessment", "Neuro_exam", "Splint"],
}


def get_resources_for_category(category: str) -> List[Dict[str, str]]:
    if not category:
        return []
    codes = CATEGORY_RESOURCES.get(category, [])
    resources = []
    for code in codes:
        label = RESOURCE_LABELS.get(code)
        if label:
            resources.append({"code": code, "label_en": label["en"], "label_ar": label["ar"]})
        else:
            resources.append({"code": code, "label_en": code, "label_ar": code})
    return resources


WORKUP_KEYWORD_MAP = [
    ("Ortho_xray", ["affected leg", "x-ray of leg", "x ray of leg", "x-ray of forearm", "x ray of forearm", "forearm x-ray", "leg x-ray", "limb x-ray", "xray limb", "orthopedic xray", "اشعة على الطرف", "أشعة على الطرف"]),
    ("X-ray", ["x-ray", "x ray", "xray", "radiograph", "cxr", "chest xray", "chest x-ray", "chest x ray", "اشعة", "أشعة"]),
    ("Labs", ["lab", "blood", "cbc", "cmp", "coagulation", "تحاليل", "تحليل"]),
    ("Cardiac_labs", ["troponin", "ck-mb", "cardiac enzymes", "انزيمات القلب", "إنزيمات القلب"]),
    ("ECG", ["ecg", "ekg", "رسم قلب"]),
    ("CT", ["ct", "cat scan", "اشعة مقطعية", "أشعة مقطعية"]),
    ("Monitor", ["monitor", "monitoring", "telemetry", "مراقبة", "مونيتور"]),
    ("Pain_assessment", ["pain", "vas", "analgesia score", "ألم", "الالم"]),
    ("Neuro_exam", ["neuro", "neurovascular", "nv exam", "neurologic", "عصب", "أعصاب"]),
    ("Splint", ["splint", "immobil", "cast", "جبيرة", "تثبيت"]),
    ("Orthopedic_eval", ["ortho", "fracture", "كسر"]),
    ("IV_access", ["iv", "cannula", "كانيولا", "line access"]),
]


def _normalize_text(text: str) -> str:
    return (text or "").strip().lower().replace("-", " ")


def _map_workup_item_to_code(item_text: str) -> Optional[str]:
    normalized = _normalize_text(item_text)
    if not normalized:
        return None
    for code, keywords in WORKUP_KEYWORD_MAP:
        for keyword in keywords:
            if keyword in normalized:
                return code
    return None


def get_resources_for_workup(workup_items: List[str]) -> List[Dict[str, str]]:
    if not workup_items:
        return []

    resources: List[Dict[str, str]] = []
    seen_codes = set()

    for item in workup_items:
        item_text = str(item or "").strip()
        if not item_text:
            continue

        code = _map_workup_item_to_code(item_text)
        if code and code in RESOURCE_LABELS:
            if code in seen_codes:
                continue
            label = RESOURCE_LABELS[code]
            resources.append({"code": code, "label_en": label["en"], "label_ar": label["ar"]})
            seen_codes.add(code)
            continue

        resources.append({"code": "custom", "label_en": item_text, "label_ar": "فحص إضافي"})

    return resources
