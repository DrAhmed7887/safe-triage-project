#!/usr/bin/env python3
"""Add Arabic terms to SNOMED cache for key concepts."""
import sqlite3

ARABIC_MAPPINGS = {
    "225566008": "ألم صدر إقفاري",
    "29857009": "ألم صدر",
    "426396005": "ألم صدر قلبي",
    "274664007": "ألم صدر مع التنفس",
    "81953000": "ألم صدر مع المجهود",
    "230690007": "جلطة دماغية",
    "267036007": "ضيق تنفس",
    "22298006": "احتشاء عضلة القلب",
    "22298006": "احتشاء عضلة القلب",
    "386661006": "حمى",
    "165816005": "فقدان الوعي",
    "271807003": "إغماء",
    "401314000": "توقف التنفس",
    "410429000": "سكتة قلبية",
    "40917007": "تشنج",
    "248567008": "نزيف شديد",
    "386705008": "نزيف بالجهاز الهضمي",
    "16114001": "نوبة ربو",
    "192961005": "نقص تروية",
    "373573001": "ألم شديد",
    "197480006": "صداع شديد",
    "422400008": "ضيق تنفس شديد",
    "62315008": "حساسية شديدة",
    "10509002": "تسمم",
    "162573006": "حمل خارج الرحم",
    "56265001": "تسمم دم",
}


def main():
    conn = sqlite3.connect("umls_cache.db")
    try:
        conn.execute("ALTER TABLE snomed_cache ADD COLUMN term_ar TEXT")
    except sqlite3.OperationalError:
        pass
    updated = 0
    for snomed_id, arabic_term in ARABIC_MAPPINGS.items():
        cur = conn.execute(
            "UPDATE snomed_cache SET term_ar = ? WHERE concept_id = ?",
            (arabic_term, snomed_id),
        )
        updated += cur.rowcount
    conn.commit()
    print(f"✅ Added Arabic terms for {updated} SNOMED concepts")


if __name__ == "__main__":
    main()
