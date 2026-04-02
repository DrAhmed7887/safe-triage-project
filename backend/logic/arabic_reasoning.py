"""Derive safe Arabic clinical reasoning from trusted deterministic fields.

Instead of passing free-form Gemini Arabic reasoning, we derive Arabic lines
from the ESI v5 engine output (which is already constrained by deterministic
logic).  This prevents hallucinated Arabic clinical text from reaching the
user-facing UI.
"""

from typing import List, Optional

_ESI_AR_MAP = {
    "immediate life-saving": "يتطلب تدخل فوري لإنقاذ الحياة",
    "high risk": "خطورة عالية",
    "vital signs abnormal": "العلامات الحيوية غير طبيعية",
    "news2": "تقييم NEWS2",
    "safety floor": "تم تطبيق قاعدة أمان",
    "resource": "تقدير الموارد",
    "red flag": "علامة حمراء",
    "chest pain": "ألم في الصدر",
    "altered mental": "تغير في مستوى الوعي",
    "respiratory": "ضيق في التنفس",
    "sepsis": "اشتباه تسمم دم",
    "stroke": "اشتباه سكتة دماغية",
    "trauma": "إصابة / حادث",
    # ESI v5 vital-sign specific
    "heart rate": "معدل ضربات القلب غير طبيعي",
    "blood pressure": "ضغط الدم غير طبيعي",
    "oxygen": "تشبع الأكسجين منخفض",
    "temperature": "درجة الحرارة غير طبيعية",
    "respiratory rate": "معدل التنفس غير طبيعي",
    "gcs": "تقييم مستوى الوعي (GCS)",
    "pain score": "درجة الألم",
    "fever": "ارتفاع في الحرارة",
    "tachycardia": "تسارع في ضربات القلب",
    "hypotension": "انخفاض في ضغط الدم",
    "hypertension": "ارتفاع في ضغط الدم",
    "hypoxia": "نقص الأكسجين",
    "tachypnea": "سرعة في التنفس",
    "bradycardia": "بطء في ضربات القلب",
    "seizure": "نوبة صرعية",
    "syncope": "إغماء",
    "cardiac": "اشتباه مشكلة قلبية",
    "neurological": "أعراض عصبية",
    "abdominal": "ألم في البطن",
    "obstetric": "حالة نسائية / توليد",
    "psychiatric": "حالة نفسية",
    "allergic": "تفاعل تحسسي",
    "overdose": "جرعة زائدة / تسمم",
    "deterministic fallback": "تم استخدام المحرك الحتمي البديل",
    "keyword match": "تم تحديد الحالة بمطابقة الكلمات المفتاحية",
    "within-one": "الفرز ضمن مستوى واحد من التوقع",
}


def derive_safe_arabic_reasoning(
    esi_reasoning: List[str],
    resource_count: int,
    silent_mi_forced: bool = False,
    reasoning_floor_note: Optional[str] = None,
    critical_floor_notes: Optional[List[str]] = None,
) -> List[str]:
    """Build Arabic reasoning from trusted deterministic fields only."""
    ar_lines: List[str] = []

    for reason in esi_reasoning or []:
        reason_lower = reason.lower()
        matches = [ar_val for eng_key, ar_val in _ESI_AR_MAP.items() if eng_key in reason_lower]
        # Deduplicate while preserving order
        seen: set = set()
        for m in matches:
            if m not in seen:
                ar_lines.append(m)
                seen.add(m)
        if not matches:
            ar_lines.append("تم تقييم الحالة بالمحرك الحتمي")

    ar_lines.append(f"تقدير الموارد المتوقعة للحالة: {resource_count}")

    if silent_mi_forced:
        ar_lines.append("تم تطبيق قاعدة أمان الجلطة الصامتة لمنع تقليل شدة الفرز")
    if reasoning_floor_note:
        ar_lines.append("تم تطبيق تصعيد احتياطي بسبب نمط حرج في الاستدلال الطبي")
    if critical_floor_notes:
        ar_lines.append("تم تطبيق قواعد أمان حرجة مبنية على الشكوى قبل تحليل الذكاء الاصطناعي")

    return ar_lines
