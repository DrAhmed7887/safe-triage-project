"""
Expanded Arabic keyword registry for deterministic offline triage extraction.

This module builds a single keyword -> metadata dictionary by:
1) flattening the existing dynamic keyword database defaults (~1,500 unique terms),
2) adding a curated Egyptian-Arabic expansion set,
3) generating severity-modifier variants,
4) selecting 348 net-new unique keywords (deterministic order).

Output schema per keyword:
{
    "snomed": "<code>",
    "category": "<deterministic category id>",
    "base_esi": <int 1-5>,
    "red_flag": <bool>
}
"""

from __future__ import annotations

from typing import Dict, Iterable, List, Tuple

try:
    from logic.keyword_database import DEFAULT_KEYWORDS
except ImportError:
    from backend.logic.keyword_database import DEFAULT_KEYWORDS


TARGET_NEW_KEYWORD_COUNT = 560
UNKNOWN_SNOMED = "404684003"  # Clinical finding (fallback)


CATEGORY_ALIAS = {
    "allergic_reaction": "allergic_reaction_moderate",
}


CATEGORY_SNOMED: Dict[str, str] = {
    "unconscious": "422768004",
    "cardiac_arrest": "410429000",
    "respiratory_arrest": "397829000",
    "active_seizure": "91175000",
    "severe_trauma": "417746004",
    "choking": "3415004",
    "anaphylaxis": "39579001",
    "poisoning_overdose": "75478009",
    "drowning": "21454007",
    "severe_bleeding": "50960005",
    "ectopic_pregnancy": "34801009",
    "aortic_dissection": "308546005",
    "sepsis": "91302008",
    "severe_hypothermia": "386689009",
    "pediatric_critical": "248549005",
    "chest_pain_cardiac": "29857009",
    "stroke_symptoms": "230690007",
    "respiratory_distress": "271825005",
    "altered_mental_status": "419284004",
    "suicidal_homicidal": "225337009",
    "severe_pain": "22253000",
    "obstetric_emergency": "267036007",
    "diabetic_emergency": "73211009",
    "testicular_pain": "63901009",
    "severe_headache": "25064002",
    "high_fever_toxic": "386661006",
    "dvt_pe": "706870000",
    "hemoptysis": "66857006",
    "mesenteric_ischemia": "82196007",
    "silent_mi": "57054005",
    "gi_bleed": "74474003",
    "hip_fracture": "359817006",
    "intussusception": "35327006",
    "pediatric_meningitis": "7180009",
    "pediatric_dehydration": "34095006",
    "pediatric_respiratory": "248548009",
    "febrile_seizure": "41497008",
    "pediatric_sepsis": "91302008",
    "pediatric_emergency": "408467006",
    "abdominal_pain_moderate": "21522001",
    "chest_pain_noncardiac": "29857009",
    "moderate_dyspnea": "267036007",
    "fracture_deformity": "125605004",
    "moderate_bleeding": "50960005",
    "fever_with_symptoms": "386661006",
    "vomiting_dehydration": "422400008",
    "psychiatric_agitated": "24199005",
    "pediatric_distress": "248549005",
    "asthma_exacerbation": "195967001",
    "kidney_stone": "95570007",
    "minor_trauma": "417746004",
    "laceration_simple": "312608009",
    "mild_pain": "22253000",
    "uri_symptoms": "54150009",
    "uti_symptoms": "68566005",
    "mild_allergic": "271807003",
    "allergic_reaction_moderate": "271807003",
    "earache": "16001004",
    "sore_throat": "162397003",
    "mild_gi": "62315008",
    "back_pain_chronic": "161891005",
    "headache_mild": "25064002",
    "eye_complaint": "422587007",
    "dental": "27355003",
    "skin_fungal": "3218000",
    "hiccups": "65958008",
    "ankle_sprain": "44465007",
    "insect_bite": "283344005",
    "prescription_refill": "182836005",
    "minor_complaint": "162155001",
    "chronic_stable": "281666001",
    "suture_removal": "183438009",
    "medical_certificate": "371530004",
    "wound_check": "183945002",
    "rash_minor": "271807003",
    "unclear": UNKNOWN_SNOMED,
}


HIGH_RISK_CATEGORIES = {
    "unconscious",
    "cardiac_arrest",
    "respiratory_arrest",
    "active_seizure",
    "severe_trauma",
    "choking",
    "anaphylaxis",
    "poisoning_overdose",
    "drowning",
    "severe_bleeding",
    "ectopic_pregnancy",
    "aortic_dissection",
    "sepsis",
    "chest_pain_cardiac",
    "stroke_symptoms",
    "respiratory_distress",
    "altered_mental_status",
    "suicidal_homicidal",
    "diabetic_emergency",
    "silent_mi",
    "gi_bleed",
}


MANDATORY_NEW_KEYWORDS: List[Tuple[str, str]] = [
    ("abdominal_pain_moderate", "بطني بتقطع"),
    ("abdominal_pain_moderate", "بطني بتولع"),
    ("abdominal_pain_moderate", "بطني بتولع فيا"),
    ("abdominal_pain_moderate", "بطني نار"),
    ("abdominal_pain_moderate", "مغص جامد"),
    ("abdominal_pain_moderate", "بطني متحجرة"),
    ("respiratory_distress", "مش قادر أخد نفسي"),
    ("respiratory_distress", "بنهج"),
    ("respiratory_distress", "بلهث"),
    ("respiratory_distress", "النفس مقطوع"),
    ("respiratory_distress", "بيتخنق"),
    ("respiratory_distress", "كتمة"),
    ("respiratory_distress", "كتمة في صدري"),
    ("high_fever_toxic", "سخونية ورعشة"),
    ("high_fever_toxic", "حرارة مع ألم بطن"),
    ("high_fever_toxic", "سخونية جامدة"),
    ("severe_bleeding", "بستفرغ دم"),
    ("severe_bleeding", "بستفرغ لون بني"),
    ("altered_mental_status", "أغمى عليا"),
    ("altered_mental_status", "وقعت من الدوخة"),
    ("altered_mental_status", "فقدت وعيي"),
    ("altered_mental_status", "عيني بتسود"),
    ("altered_mental_status", "رجليا مش شايلاني"),
    ("altered_mental_status", "هلكان"),
    ("stroke_symptoms", "نص جسمي مش بيتحرك"),
    ("chest_pain_cardiac", "صدري بيضغط عليا"),
    ("chest_pain_cardiac", "حاسس بتقل على صدري"),
    ("chest_pain_cardiac", "الألم بيمشي لدراعي"),
    ("chest_pain_cardiac", "قلبي بينط"),
    ("silent_mi", "سكر وعندي حرقان في المعدة"),
    ("diabetic_emergency", "غيبوبة سكر"),
    ("gi_bleed", "إسهال فيه دم"),
    ("gi_bleed", "البراز فيه دم"),
    ("severe_trauma", "حادثة عربية"),
    ("severe_trauma", "اتطعن"),
    ("severe_trauma", "طلق ناري"),
    ("severe_bleeding", "نزيف مش بيوقف"),
    ("stroke_symptoms", "وشي اتلوى"),
    ("stroke_symptoms", "وشي مال"),
    ("stroke_symptoms", "كلامي بقى مش مفهوم"),
    ("stroke_symptoms", "لساني تقيل"),
    ("active_seizure", "تشنجات"),
    ("active_seizure", "اتشنج"),
    ("active_seizure", "عنده نوبة"),
    ("anaphylaxis", "لساني ورم"),
    ("anaphylaxis", "حساسية وضيق نفس"),
    ("suicidal_homicidal", "عايز أموت"),
    ("poisoning_overdose", "بلعت حبوب"),
    ("poisoning_overdose", "شربت كلور"),
    ("chest_pain_cardiac", "ضيقة في الصدر"),
    ("stroke_symptoms", "ضعف في الجنب الشمال"),
    ("abdominal_pain_moderate", "وجع في البطن"),
]


EXPANDED_NEW_KEYWORD_POOL: Dict[str, List[str]] = {
    "abdominal_pain_moderate": [
        "بطني بتعورني",
        "بطني مقلوبة",
        "بطني مش مستحملة",
        "وجع بطن مش طبيعي",
        "ألم شديد في بطني",
        "بطني وجعها قاتل",
        "وجع بطني بيزيد",
        "بطني بتموتني",
        "وجع في نص بطني",
        "وجع في جنب بطني",
        "بطني مربوطة",
        "مغص حاد",
        "مغص مش بيروح",
        "مغص بيصحيني من النوم",
        "معدتي محروقة جدا",
        "بطني ناشفة",
        "بطني منفوخة وبتوجع",
        "وجع تحت السرة",
        "وجع فوق السرة",
        "وجع بطن مع ترجيع",
        "وجع بطن مع سخونية",
        "ألم بطن حاد",
        "ألم بطن مفاجئ",
        "مغص مستمر",
        "وجع بطن فظيع",
    ],
    "respiratory_distress": [
        "مش عارف أتنفس",
        "نفسي ضيق جدا",
        "باخد نفسي بالعافية",
        "حاسي اني مكتوم",
        "تنفسي سريع جدا",
        "نفسي تقيل",
        "نفسي واقف",
        "حاسي بخنقة",
        "الهواء مش داخل",
        "بكح ومش قادر اخد نفس",
        "تعبان في النفس",
        "بتنفس بصعوبة",
        "نهجان قوي",
        "نهجان من أقل مجهود",
        "بيجري وراه النفس",
        "نفسي مش مكفيني",
        "حاسس اختناق",
        "محتاج أكسجين",
        "صفير مع ضيق نفس",
        "نوبة ضيق نفس",
    ],
    "high_fever_toxic": [
        "حرارتي مولعة",
        "سخونية عالية جدا",
        "حرارة مش بتنزل",
        "جسمي سخن ومكسر",
        "حرارة مع هبوط",
        "حرارة مع دوخة",
        "حرارة مع قئ",
        "حرارة مع اسهال",
        "رعشة وسخونية",
        "جسمي بيترعش من السخونية",
        "سخونية مع صداع شديد",
        "حرارة مع كحة شديدة",
        "حمى شديدة",
    ],
    "severe_bleeding": [
        "دم بينزل بغزارة",
        "بنزف ومش قادر أوقفه",
        "نزيف شديد جدا",
        "الدم بيتدفق",
        "دم كتير قوي",
        "نزيف متواصل",
        "قيء دم غامق",
        "ترجيع دم بني",
        "بتقيأ دم",
        "دم مع القيء",
        "براز اسود مع دوخة",
        "نزيف داخلي محتمل",
        "دم فاتح كتير",
        "الجرح بينزف بغزارة",
    ],
    "altered_mental_status": [
        "حصل لي اغماء",
        "بدوخ وبقع",
        "الدنيا سودة قدامي",
        "مش مركز خالص",
        "مخنوق ومش واعي",
        "مش حاسس بنفسي",
        "حاسس اني هغيب",
        "مش قادر أقف من الدوخة",
        "دوخة شديدة جدا",
        "الوعي بيروح وييجي",
        "توهان شديد",
        "تشوش شديد",
    ],
    "stroke_symptoms": [
        "ايدي ورجلي ضعفوا فجأة",
        "مش قادر احرك ايدي",
        "نص وشي واقع",
        "الكلام متلخبط فجأة",
        "مش قادر انطق",
        "تنميل في نص الجسم",
        "ضعف مفاجئ في طرف",
        "سكتة دماغية محتملة",
        "فمي مايل",
        "مش فاهم الكلام",
        "مش بعرف اتكلم كويس",
        "ثقل في اللسان فجأة",
    ],
    "chest_pain_cardiac": [
        "وجع صدر ضاغط",
        "ضغط على الصدر",
        "صدري مقبوض",
        "حرقان صدر مع ضيق نفس",
        "وجع في القلب",
        "ألم صدر مفاجئ",
        "وجع صدر بيزيد مع الحركة",
        "وجع صدر ممتد للدراع الشمال",
        "خفقان شديد مع وجع صدر",
        "صدري مخنوق",
        "ثقل شديد على الصدر",
        "ألم صدر مع عرق",
    ],
    "silent_mi": [
        "سكري ووجع معدة",
        "سكري وحرقان صدر",
        "مريض سكر وتعب شديد",
        "سكري مع غثيان مفاجئ",
        "سكري مع عرق بارد",
        "سكري مع نهجان",
    ],
    "diabetic_emergency": [
        "سكر منخفض جدا",
        "سكر عالي جدا",
        "دخل في غيبوبة سكر",
        "مريض سكر ومش واعي",
        "هبوط سكر شديد",
        "ارتفاع سكر شديد",
        "تخبيط في السكر",
    ],
    "gi_bleed": [
        "اسهال مدمم",
        "دم في الاسهال",
        "دم مع البراز",
        "براز لونه اسود",
        "نزيف شرجي واضح",
        "دم أحمر في البراز",
        "اسهال اسود",
    ],
    "severe_trauma": [
        "خبطه جامدة في الراس",
        "حادث موتوسيكل",
        "اتخبطت بالعربية",
        "وقعت من مكان عالي",
        "إصابة نافذة",
        "جرح عميق جدا",
        "إصابة شديدة في البطن",
        "ضربة قوية في الصدر",
        "إصابة خطيرة",
        "سقوط عنيف",
        "ضربة سكينة",
        "إصابة رصاص",
    ],
    "active_seizure": [
        "حالة صرع",
        "بيعمل تشنجات",
        "نوبة تشنج",
        "اتشنجات متكررة",
        "رعشة في الجسم كله",
        "فقد وعي مع تشنج",
        "صرع مستمر",
    ],
    "anaphylaxis": [
        "حساسية شديدة جدا",
        "تورم اللسان",
        "زوري بيقفل من الحساسية",
        "نهجان بسبب الحساسية",
        "تورم في الحلق",
    ],
    "suicidal_homicidal": [
        "مش عايز اعيش",
        "نفسي أنهي حياتي",
        "هأذي نفسي",
        "عندي أفكار انتحار",
        "حاولت انتحر",
        "عايز أقتل نفسي",
    ],
    "poisoning_overdose": [
        "ابتلعت حبوب كتير",
        "شربت مادة كاوية",
        "خدت جرعة كبيرة",
        "أكلت سم",
        "شربت منظف",
        "بلع مادة سامة",
        "شرب كلوركس",
    ],
    "severe_headache": [
        "راسي هتنفجر",
        "صداع فظيع",
        "صداع مفاجئ قوي",
        "وجع راس قاتل",
        "صداع مش طبيعي",
        "صداع مع زغللة",
        "صداع مع قيء",
    ],
}


SEVERITY_MODIFIERS = ["جامد", "شديد", "فجأة", "بيزيد", "مش قادر أنام من الوجع"]

SEVERITY_TEMPLATE_POOL: Dict[str, List[str]] = {
    "abdominal_pain_moderate": ["بطني بتوجعني", "وجع بطن", "مغص", "ألم بطني"],
    "respiratory_distress": ["مش قادر اخد نفسي", "ضيق نفس", "نهجان", "خنقة"],
    "chest_pain_cardiac": ["وجع صدر", "ضغط على صدري", "ألم قلبي", "ثقل على صدري"],
    "severe_headache": ["صداع", "وجع راس", "راسي بتوجعني", "صداع نصفي"],
    "fever_with_symptoms": ["سخونية", "حرارة", "حمى", "جسمي سخن"],
    "vomiting_dehydration": ["ترجيع", "استفراغ", "قيء", "بستفرغ"],
    "moderate_bleeding": ["نزيف", "دم بينزل", "بأنزف", "جرح بينزف"],
    "fracture_deformity": ["كسر", "ايدي مكسورة", "رجلي مكسورة", "تورم بعد خبطة"],
    "kidney_stone": ["مغص كلوي", "وجع جنب", "حصوة", "وجع في الكلى"],
    "severe_pain": ["وجع", "ألم", "تعب", "مغص"],
}


KEYWORD_OVERRIDES = {
    "بطني بتقطع": {"base_esi": 2, "red_flag": True},
    "بطني بتولع": {"base_esi": 2, "red_flag": True},
    "بطني بتولع فيا": {"base_esi": 2, "red_flag": True},
    "بطني نار": {"base_esi": 2, "red_flag": True},
    "مغص جامد": {"base_esi": 2, "red_flag": True},
    "بطني متحجرة": {"base_esi": 2, "red_flag": True},
    "سخونية ورعشة": {"base_esi": 2, "red_flag": True},
    "حرارة مع ألم بطن": {"base_esi": 2, "red_flag": True},
    "بستفرغ دم": {"base_esi": 1, "red_flag": True},
    "بستفرغ لون بني": {"base_esi": 1, "red_flag": True},
    "نص جسمي مش بيتحرك": {"base_esi": 1, "red_flag": True},
    "غيبوبة سكر": {"base_esi": 1, "red_flag": True},
    "إسهال فيه دم": {"base_esi": 2, "red_flag": True},
    "البراز فيه دم": {"base_esi": 2, "red_flag": True},
    "طلق ناري": {"base_esi": 1, "red_flag": True},
    "نزيف مش بيوقف": {"base_esi": 1, "red_flag": True},
    "وشي اتلوى": {"base_esi": 1, "red_flag": True},
    "وشي مال": {"base_esi": 1, "red_flag": True},
    "كلامي بقى مش مفهوم": {"base_esi": 1, "red_flag": True},
    "لساني تقيل": {"base_esi": 1, "red_flag": True},
    "لساني ورم": {"base_esi": 1, "red_flag": True},
    "حساسية وضيق نفس": {"base_esi": 1, "red_flag": True},
    "عايز أموت": {"base_esi": 1, "red_flag": True},
    "بلعت حبوب": {"base_esi": 1, "red_flag": True},
    "شربت كلور": {"base_esi": 1, "red_flag": True},
    "سكر وعندي حرقان في المعدة": {"base_esi": 2, "red_flag": True},
}


# Populated by GEMINI_EXPANDED_KEYWORDS block below — declared here so
# _iter_new_keyword_candidates can reference it before module load completes.
GEMINI_EXPANDED_KEYWORDS: Dict[str, List[str]] = {}


SCRAPED_DIALECT_KEYWORDS: dict[str, list[str]] = {}
HF_MEDICALCORPUS_TRANSLATED: dict[str, list[str]] = {}
KALEELA_TRANSLATED_KEYWORDS: dict[str, list[str]] = {}

def _normalize_keyword(text: str) -> str:
    return " ".join(str(text or "").strip().split()).lower()


def _build_category_level_map() -> Dict[str, int]:
    mapping: Dict[str, int] = {}
    for level_key in ("level_1", "level_2", "level_3", "level_4", "level_5"):
        level = int(level_key.split("_")[1])
        for raw_category in DEFAULT_KEYWORDS.get(level_key, {}).keys():
            category = CATEGORY_ALIAS.get(raw_category, raw_category)
            mapping[category] = min(level, mapping.get(category, level))
    return mapping


CATEGORY_LEVELS = _build_category_level_map()


def _default_base_esi(category: str) -> int:
    return int(CATEGORY_LEVELS.get(category, 3))


def _default_red_flag(category: str, base_esi: int) -> bool:
    return bool(base_esi <= 2 or category in HIGH_RISK_CATEGORIES)


def _append_keyword(
    entries: Dict[str, Dict[str, object]],
    *,
    keyword: str,
    category: str,
    base_esi: int,
    red_flag: bool | None = None,
    snomed: str | None = None,
) -> bool:
    normalized = _normalize_keyword(keyword)
    if not normalized:
        return False

    payload = {
        "snomed": snomed or CATEGORY_SNOMED.get(category, UNKNOWN_SNOMED),
        "category": category,
        "base_esi": int(base_esi),
        "red_flag": _default_red_flag(category, int(base_esi)) if red_flag is None else bool(red_flag),
    }

    existing = entries.get(normalized)
    if existing is None:
        entries[normalized] = payload
        return True

    existing_base = int(existing.get("base_esi", 3))
    payload_base = int(payload["base_esi"])
    if payload_base < existing_base:
        entries[normalized] = payload
        return False

    if payload_base == existing_base and payload["red_flag"] and not bool(existing.get("red_flag")):
        entries[normalized] = payload

    return False


def _build_base_keyword_entries() -> Dict[str, Dict[str, object]]:
    entries: Dict[str, Dict[str, object]] = {}
    for level_key in ("level_1", "level_2", "level_3", "level_4", "level_5"):
        level = int(level_key.split("_")[1])
        for raw_category, info in DEFAULT_KEYWORDS.get(level_key, {}).items():
            category = CATEGORY_ALIAS.get(raw_category, raw_category)
            all_keywords = info.get("keywords", []) + info.get("added_by_ai", [])
            for keyword in all_keywords:
                _append_keyword(
                    entries,
                    keyword=keyword,
                    category=category,
                    base_esi=level,
                )
    return entries


def _iter_new_keyword_candidates() -> Iterable[Tuple[str, str]]:
    for category, keyword in MANDATORY_NEW_KEYWORDS:
        yield category, keyword

    for category, keywords in EXPANDED_NEW_KEYWORD_POOL.items():
        for keyword in keywords:
            yield category, keyword

    for category, keywords in GEMINI_EXPANDED_KEYWORDS.items():
        for keyword in keywords:
            yield category, keyword

    for category, keywords in SCRAPED_DIALECT_KEYWORDS.items():
        for keyword in keywords:
            yield category, keyword

    for category, keywords in HF_MEDICALCORPUS_TRANSLATED.items():
        for keyword in keywords:
            yield category, keyword

    for category, keywords in KALEELA_TRANSLATED_KEYWORDS.items():
        for keyword in keywords:
            yield category, keyword

    for category, templates in SEVERITY_TEMPLATE_POOL.items():
        for phrase in templates:
            for modifier in SEVERITY_MODIFIERS:
                yield category, f"{phrase} {modifier}"
                yield category, f"{modifier} {phrase}"
                yield category, f"{phrase} جدا {modifier}"


def _build_keywords_v2() -> Tuple[Dict[str, Dict[str, object]], int]:
    entries = _build_base_keyword_entries()
    base_count = len(entries)
    new_unique_added = 0

    for raw_category, keyword in _iter_new_keyword_candidates():
        category = CATEGORY_ALIAS.get(raw_category, raw_category)
        normalized = _normalize_keyword(keyword)
        was_missing = normalized not in entries
        override = KEYWORD_OVERRIDES.get(normalized, {})

        # Always allow mandatory/override upgrades to improve acuity metadata.
        if not was_missing and not override:
            continue

        if was_missing and new_unique_added >= TARGET_NEW_KEYWORD_COUNT:
            continue

        _append_keyword(
            entries,
            keyword=keyword,
            category=category,
            base_esi=int(override.get("base_esi", _default_base_esi(category))),
            red_flag=override.get("red_flag"),
        )

        if was_missing and normalized in entries:
            new_unique_added += 1

    if new_unique_added < TARGET_NEW_KEYWORD_COUNT:
        raise RuntimeError(
            f"Unable to reach target new keywords: required {TARGET_NEW_KEYWORD_COUNT}, built {new_unique_added}"
        )

    return entries, base_count


# --- GEMINI_EXPANDED_KEYWORDS_V2 ---
# Auto-generated from MIETIC + KTAS complaints via Gemini CLI
# Run: python backend/tools/generate_arabic_keywords.py to regenerate
# This block MUST stay between the function definitions and _build_keywords_v2() call.
GEMINI_EXPANDED_KEYWORDS.update({
    "altered_mental_status": [
        "دايخ أوي ودماغي بتلف بيا",
        "مغمى عليه ومش راضي يفوق",
        "جسمي مسيب خالص ومش حاسس بأطرافي",
        "مش مركز خالص وبيقول كلام غريب",
        "لقيناه واقع في الصالة ومبيتحركش",
        "مبيردش علينا ونايم نوم تقيل أوي",
        "تايه ومش عارف هو فين ولا الساعة كام",
        "حاسس بدوخة شديدة وهقع من طولي",
    ],
    "chest_pain_cardiac": [
        "وجع في نص صدري زي ما يكون حد دايس عليه",
        "ناغزة في قلبي مسمعة في كتفي الشمال",
        "قلبي بيدق جامد أوي وحاسس بخنقة",
        "صدري واجعني ومطبق عليا وعرقان أوي",
        "حاسس بتقل على صدري مش مخليني أتنفس",
        "نغزة في الناحية الشمال مسمعة في فكي",
        "صدري واجعني وعرقان غرقان مية",
    ],
    "gi_bleed": [
        "بيرجع دم لونه أحمر فاقع",
        "ترجيعه لونه أسود زي القهوة",
        "الحمام لونه أسود زي القار",
        "حمامي فيه دم كتير وريحته وحشة",
        "بينزف من ورا ولونه بقى أصفر",
        "ترجيع دم مابيقفش خالص",
        "لقيت دم في البراز ودوخت فجأة",
    ],
    "obstetric_emergency": [
        "نزيف مهبلي شديد ومعاه وجع تحت",
        "أنا حامل ولقيت دم نازل عليا كتير",
        "وجع فظيع تحت بطني مش قادرة أستحمله",
        "عليها دم كتير وهي في الشهر الخامس",
        "المية نزلت عليا مرة واحدة والوجع شغال",
        "وجع في الحوض والدم مغرق الهدوم",
        "حامل وبتنزف دم ومغص شديد",
    ],
    "active_seizure": [
        "جاله تشنج وجسمه خشب مرة واحدة",
        "كان بيترعش وعينه قلبت لفوق",
        "وقع وتشنج في الأرض وطلع رغاوي من بقه",
        "لسه فايق من نوبة صرع ومش دريان بحاجة",
        "جاله تشنجات وفضل يرتعش دقايق",
        "ابني اتشنج في البيت وجبناه جري",
        "كان متخشب خالص ومش حاسس بينا",
    ],
    "stroke_symptoms": [
        "كلامه تقل فجأة ومبقيناش فاهمينه",
        "جنبه اليمين وقف خالص ومبيتحركش",
        "بقه اتعوج ناحية واحدة وشكله غريب",
        "إيده فجأة بقت خشب مش حاسس بيها",
        "مش عارف يتكلم ولا يجمع جملة مفيدة",
        "نص جسمه اليمين خذل مرة واحدة",
        "ذراعه وقع منه مش قادر يرفعه خالص",
        "لسانه مبيتحركش في بقه والريالة نازلة",
    ],
    "allergic_reaction_moderate": [
        "جسمي كله طلع فيه بطش حمرا بتهرشني",
        "هرش رهيب وجسمي كله مولع نار",
        "طفح جلدي غريب طلع فجأة بعد الأكل",
        "وشي ورم جامد بعد ما خدت الحقنة",
        "عروق حمرا وهرش فظيع في كل حتة",
        "جلدي منمل ومورم وبيهرشني أوي",
        "عيني وشفايفي ورموا فجأة وحمرا جدا",
        "حساسية شديدة وبقيت شبه المحمرة خالص",
    ],
    "kidney_stone": [
        "جنبي بيقطّعني مش قادر أصلب طولي",
        "وجع في جنبي مسمع في رجلي من تحت",
        "مغص كلوي شديد هيموتني من الوجع",
        "وجع فظيع في جنابي من ورا ناحية الكلى",
        "حاسس بسكاكين في جنبي الشمال ومش طايق الهدوم",
        "مش عارف أتبول والوجع بيزيد في الحالب",
        "وجع حاد بيجي ويروح في جنبي ومخليني أصرخ",
        "جنابي واجعاني وعمال أتلوى من الألم",
    ],
    "vomiting_dehydration": [
        "عندي ترجيع مش بيبطل من الصبح خالص",
        "كل ما يشرب بوق مية يرجعه في ساعتها",
        "نفسي غامة عليا وبرجع على طول مش قادر",
        "بنتي بترجع بقالها يومين وهبطانة وناشفة",
        "مفيش حاجة بتثبت في بطني خالص وبنشف",
        "ترجيع مستمر لونه غريب ومعدتي مقلوبة",
        "الطفل بيرجع كل اللي بياكله فورا ومعدش فيه حيل",
        "معدتي واجعاني وبترجع أي لقمة باكلها",
    ],
    "psychiatric_agitated": [
        "حاسس إن روحي بتطلع من الخوف والرعب",
        "مخلوق ومش قادر أتنفس وحاسس إني هموت",
        "قلبي بيدق بسرعة وعمال أترعش من القلق",
        "عنده حالة هياج وبيرمي الحاجات وبيصرخ",
        "داخل في نوبة قلق ومش طبيعي بقاله ساعة",
        "بنهج جامد وحاسس بمصيبة هتحصل لي",
        "مش طايق نفسي وعايز أكسر الدنيا من الضيق",
        "خوف فجأة ومن غير أي سبب وضربات قلبي سريعة",
    ],
    "respiratory_distress": [
        "مش قادر آخد نفسي ومعايا كحة",
        "صدري بيزيق ومش عارف أتنفس",
        "مش عارف أنام مفرود من نهجان صدري",
        "بنهج جامد ونفسي سريع قوي",
        "أزمة ربو وحاسس إني بتخنق",
        "نفسه مقطوع خالص وشفايفه مزرقة",
        "أمي مش قادرة تتنفس وصدرها تعبان",
    ],
    "back_pain_chronic": [
        "ضهري واجعني من تحت قوي",
        "وجع فظيع في ضهري مش بيفصل",
        "ضهري واجعني ومش قادر أتحرك من مكاني",
        "الوجع في أسفل ضهري ومسمع في رجلي",
        "مش قادر أفرد ضهري من الوجع",
        "عرق النسا ضارب في رجلي وضهري",
        "بقالي فترة ضهري تاعبني ومش عارف أمشي",
    ],
    "mild_gi": [
        "عندي إسهال بقالي يومين",
        "بطني ماشية وعندي ترجيع",
        "نازلة معوية وتعبان قوي",
        "كل شوية بدخل الحمام وبطني مقلوبة",
        "مغص فظيع وإسهال مش راضي يقف",
        "الواد عنده نزلة معوية وبيرجع",
        "ترجيع وإسهال وحاسس بدوخة",
    ],
    "moderate_bleeding": [
        "عندي جرح مفتوح وبينزف",
        "اتعورت تعويرة جامدة والدم مش بيوقف",
        "إيدي اتفتحت ومحتاجة غرز بسرعة",
        "وشه اتفتح من الوقعة وبينزف دم كتير",
        "خبطة في راسي وطلعت دم كتير",
        "جرح غويط قوي والدم مغرق الهدوم",
        "صباعي اتقطع وعايز يتخيط",
    ],
    "eye_complaint": [
        "عيني وجعاني قوي ومش طايق النور",
        "عيني حمرا قوي وبدمع لوحدها",
        "مش شايف كويس وحاسس بزغللة فجأة",
        "في حاجة دخلت في عيني ومضايقاني",
        "عيني اتخبطت وورمت خالص ومش بفتحها",
        "حاسس برمل في عيني وبتحرقني قوي",
        "رؤيتي مش واضحة وعيني مزغللة",
    ],
    "fracture_deformity": [
        "رجل ابني اتلوت ومش قادر يدوس عليها",
        "وقعت على إيدي وورمت جامد",
        "كاحل رجلي وارم ومزرق بعد الوقعة",
        "حاسس إن عظمة إيدي مش في مكانها",
        "وجع رهيب في مفصل الإيد بعد ما اتخبطت",
        "رجلي اتكسرت وشكلها غريب",
        "الرجل وارمة ومش قادر يحركها خالص",
    ],
    "mild_allergic": [
        "جسمي كله طلع فيه هرش واحمرار",
        "في طفح جلدي في دراعي وبياكلني",
        "حساسية مفاجئة في جسمي كله",
        "بنت اختي جسمها كله بقع حمراء",
        "هرش جامد في الجلد مع احمرار بسيط",
        "في حتت حمراء طلعت في وشي فجأة",
        "طفح جلدي بسيط بس بياكلني أوي",
    ],
    "uti_symptoms": [
        "حرقان شديد في البول مش طايقه",
        "كل شوية بدخل الحمام والبول بينزل بالعافية",
        "وجع جامد وأنا بعمل حمام مية",
        "في دم نازل مع البول يا دكتور",
        "مغص أسفل البطن مع حرقان في البول",
        "بخش الحمام كتير جداً وفي وجع",
        "حاسس بنار وأنا بعمل حمام مية",
    ],
    "silent_mi": [
        "والدي مريض سكر وحاسس بوجع في فكه",
        "عندي سكر وهمدان أوي ومش قادر أتحرك",
        "حاسس بغممان نفس بس وأنا مريض سكر",
        "وجع في ضهري مسمع قدام وأنا عندي سكر",
        "الحج عنده سكر ووقع مننا فجأة",
        "تعب شديد ونهجان من غير سبب لمريض سكر",
        "وجع في الرقبة والكتف لواحد عنده سكر",
    ],
    "abdominal_pain_moderate": [
        "وجع في فم المعدة مش راضي يروح",
        "بطني من فوق بتوجعني أوي",
        "وجع في الجنب اليمين من فوق",
        "بطنها منفوخة أوي وحاسة بكرشة نفس",
        "وجع شديد في الشرج ومش قادر أقعد",
        "مش عارف أبلع الأكل خالص وزوري واجعني",
        "حاسس بتقل ووجع في بطني كلها",
        "مغص في الجزء العلوي من البطن",
    ],
})

# --- SCRAPED_DIALECT_KEYWORDS ---
# Auto-scraped from Desert-Sky medicine vocabulary + Cleo Lingo Egyptian phrases
# Sources: arabic.desert-sky.net/medicine.html | cleolingo.com
# Run: python backend/tools/scrape_arabic_medical_vocab.py to regenerate

SCRAPED_DIALECT_KEYWORDS.update({
    "altered_mental_status": [
        "انا عيان",
        "مش كويس",
        "حاسس انك عيان؟",
        "عيان بقالك قد ايه؟",
    ],
    "chest_pain_cardiac": [
        "ضغط دم عالي",
    ],
    "fever_with_symptoms": [
        "انا سخن",
        "عندي حرارة",
        "انا سخن / عندي حرارة",
    ],
    "fracture_deformity": [
        "(دراع) مكسور",
    ],
    "kidney_stone": [
        "حصوة",
        "عندي حصوة",
    ],
    "mild_gi": [
        "مغص",
        "عندي مغص",
    ],
    "minor_trauma": [
        "اتعوّر",
        "اتجرحت",
        "فيه جرح",
    ],
    "respiratory_distress": [
        "ازمة",
        "عندي ازمة",
        "نزلة صدرية",
        "نزلة شعبية",
    ],
    "severe_headache": [
        "انا عندي صداع",
        "راسي بيوجعني جدا",
    ],
    "stroke_symptoms": [
        "جلطة في المخ",
        "جلطة دماغية",
    ],
    "uri_symptoms": [
        "برد",
        "عندي برد",
        "التهاب في الحنجرة",
        "عندي التهاب في الحنجرة",
        "كحّة",
        "عندي كحّة",
        "مناخير مسدودة",
        "مناخير بتشرّ",
        "انا عندي كحة",
        "انا عندي برد",
    ],
    "vomiting_dehydration": [
        "طراش",
        "عندي طراش",
        "جزع",
        "عندي جزع",
        "بيرجّع",
        "رجّعت",
        "محتاج اخد دوا",
    ],
})



# --- HF_MEDICALCORPUS_TRANSLATED ---
# MSA symptom phrases from arbml/MedicalCorpus (HuggingFace) -> translated to
# Egyptian dialect by Gemini CLI, verified for authenticity.

HF_MEDICALCORPUS_TRANSLATED.update({
    "respiratory_distress": [
        "مش قادر آخد نفسي",
        "نفسي مكتوم",
        "في خنقة في صدري",
        "كحة بتموتني",
        "صدري واجعني كأن حد دايس عليه",
    ],
    "mild_gi": [
        "وجع في بطني ومعدتي",
        "مغص فظيع وإسهال",
        "بطني مقلوبة",
    ],
    "vomiting_dehydration": [
        "بترجع وعندي إسهال جامد",
        "بترجع كل اللي فيها",
    ],
    "chest_pain_cardiac": [
        "رفرفة في قلبي",
        "دقات قلبي سريعة جدا",
        "قلبي بيدق بسرعة اوي",
    ],
    "altered_mental_status": [
        "بيغمى عليا كتير",
        "بقع من طولي",
        "غم عليا",
    ],
    "severe_headache": [
        "دماغي هتنفجر من الصداع",
        "دايخ وزغللة",
        "صداع ودوخة وطنين",
    ],
    "fever_with_symptoms": [
        "سخونية وصداع وتكسير في جسمي",
        "سخن مولع وبترعش",
        "جسمي همدان ومش قادر أقف",
    ],
    "severe_pain": [
        "عضمي ومفاصلي بيوجعوني اوي",
        "تكسير في جسمي كله",
    ],
    "allergic_reaction_moderate": [
        "جسمي كله بيأكلني",
        "بهرش هرش فظيع",
        "جلدي مقلوب حساسية",
        "جسمي كله وارم",
        "جلدي محمر ومش عارف ابلع",
        "رقبتي ورمت فجأة",
    ],
})

# --- KALEELA_TRANSLATED_KEYWORDS ---
# MSA phrases from Kaleela Egyptian Arabic medical guide -> translated to
# authentic Egyptian dialect by Gemini CLI (filling coverage gaps).

KALEELA_TRANSLATED_KEYWORDS.update({
    "respiratory_distress": [
        "صدري تعبان وقافش عليا خالص",
        "عندي نهجان وصدري واجعني اوي",
        "حاسس بتقل جامد في صدري",
    ],
    "severe_pain": [
        "وجع شديد مش طايق نفسي",
        "ألم فظيع ما يتسكتش عليه",
        "وجع ما بيتحملش",
    ],
    "allergic_reaction_moderate": [
        "جسمي كله ورم وحساسية مبهدلاني",
        "وشي نفخ ووارم بعد الاكلة دي",
        "مش عارف ابلع وزوري قافل خالص",
    ],
    "uti_symptoms": [
        "البول بيحرقني اوي",
        "بدخل الحمام كتير ووجع بيموتني",
        "البول نازل بدم",
    ],
    "eye_complaint": [
        "عيني محمرة وبتحرقني",
        "حاسس ان فيه رملة جوا عيني",
        "ودني بتوجعني بزيادة",
    ],
})
ARABIC_KEYWORDS_V2, BASE_KEYWORD_COUNT = _build_keywords_v2()
TOTAL_KEYWORD_COUNT = len(ARABIC_KEYWORDS_V2)
NEW_KEYWORD_COUNT = TOTAL_KEYWORD_COUNT - BASE_KEYWORD_COUNT


def get_keywords_v2() -> Dict[str, Dict[str, object]]:
    return ARABIC_KEYWORDS_V2


if __name__ == "__main__":
    print(
        f"Arabic keywords v2 loaded: total={TOTAL_KEYWORD_COUNT}, "
        f"base={BASE_KEYWORD_COUNT}, new={NEW_KEYWORD_COUNT}"
    )
