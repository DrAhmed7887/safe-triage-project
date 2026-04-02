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
        matched = False
        for eng_key, ar_val in _ESI_AR_MAP.items():
            if eng_key in reason_lower:
                ar_lines.append(ar_val)
                matched = True
                break
        if not matched:
            ar_lines.append("تم تقييم الحالة بالمحرك الحتمي")

    ar_lines.append(f"تقدير الموارد المتوقعة للحالة: {resource_count}")

    if silent_mi_forced:
        ar_lines.append("تم تطبيق قاعدة أمان الجلطة الصامتة لمنع تقليل شدة الفرز")
    if reasoning_floor_note:
        ar_lines.append("تم تطبيق تصعيد احتياطي بسبب نمط حرج في الاستدلال الطبي")
    if critical_floor_notes:
        ar_lines.append("تم تطبيق قواعد أمان حرجة مبنية على الشكوى قبل تحليل الذكاء الاصطناعي")

    return ar_lines
