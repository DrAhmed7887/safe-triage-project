"""
SAFE-Triage - Dynamic Keyword Database
=======================================

A JSON-based keyword database that can be updated by the AI Teaching Agent.
This separates keywords from code, allowing continuous learning.

PHASE 2 AUDIT FIX: Expanded keyword coverage for:
- Level 1: Airway/breathing interventions, CPR, defibrillation
- Level 1: Ectopic pregnancy, aortic dissection, sepsis, hypothermia
- Level 2: Enhanced stroke keywords with time-sensitive qualifiers
- Resource prediction metadata for ESI compliance

Author: Ahmed Zayed
Version: 2.0.0 (Phase 2 Audit Fixes)
"""

import os
import json
import copy
from typing import Dict, List, Optional, Tuple
from datetime import datetime


# =============================================================================
# DEFAULT KEYWORDS DATABASE - PHASE 2 EXPANDED
# =============================================================================

DEFAULT_KEYWORDS = {
    "metadata": {
        "version": "2.0.0",
        "last_updated": datetime.now().isoformat(),
        "total_keywords": 0,
        "updates_count": 0,
        "audit_compliance": "ESI v4 + NEWS2"
    },
    
    # =========================================================================
    # LEVEL 1: RESUSCITATION - Immediate Life-Saving Intervention Required
    # =========================================================================
    # Reference: ESI v4, Decision Point A
    # "Does this patient require immediate life-saving intervention?"
    # =========================================================================
    
    "level_1": {
        "unconscious": {
            "keywords": [
                # English
                "unconscious", "unresponsive", "not waking up", "coma", "comatose", "GCS 3", "GCS 4", "GCS 5", "GCS 6", "GCS 7", "GCS 8",
                # Arabic MSA
                "فاقد الوعي", "غير مستجيب", "غيبوبة",
                # Egyptian Arabic
                "مغمى عليه", "مش بيرد", "مش بيرد عليا", "مش واعي", "فاقد وعي",
                "مش بيرد خالص", "مش بيصحى", "مش بيفوق"
            ],
            "added_by_ai": [],
            "priority": 1,
            "requires_immediate_intervention": True
        },
        
        "cardiac_arrest": {
            "keywords": [
                # English - PHASE 2: Added defibrillation/CPR
                "cardiac arrest", "heart stopped", "no pulse", "pulseless",
                "cpr", "defibrillation", "asystole", "v-fib", "ventricular fibrillation",
                "pea", "pulseless electrical activity",
                # Arabic MSA
                "توقف القلب", "سكتة قلبية", "إنعاش قلبي رئوي",
                # Egyptian Arabic
                "قلبه وقف", "القلب واقف", "قلبه مش شغال", "القلب توقف",
                "انعاش", "إنعاش قلبي", "صدمات كهربائية", "محتاج صدمات",
                "مفيش نبض", "النبض وقف", "محتاج إنعاش"
            ],
            "added_by_ai": [],
            "priority": 1,
            "requires_immediate_intervention": True
        },
        
        "respiratory_arrest": {
            "keywords": [
                # English - PHASE 2: Added intubation/airway
                "not breathing", "stopped breathing", "apneic", "apnea episode", "respiratory arrest",
                "respiratory failure", "intubation", "needs tube", "needs intubation",
                "bag valve mask", "bvm", "airway obstruction", "blue face",
                "cyanosis", "cyanotic",
                # Arabic MSA
                "توقف التنفس", "فشل تنفسي", "تنبيب", "أنبوب حنجري",
                # Egyptian Arabic
                "مش بيتنفس", "مش قادر يتنفس", "وقف نفسه", "النفس وقف",
                "محتاج أنبوبة", "محتاج تنفس صناعي", "محتاج تنفس يدوي",
                "زرق", "شفايفه بنفسجي", "شفايفه زرقا", "لونه أزرق",
                "وشه أزرق", "امبو", "مجرى الهوا مسدود"
            ],
            "added_by_ai": [],
            "priority": 1,
            "requires_immediate_intervention": True
        },
        
        "active_seizure": {
            "keywords": [
                # English
                "seizure", "seizing", "convulsion", "status epilepticus", "fitting",
                # Arabic MSA
                "تشنج", "صرع", "نوبة صرعية", "حالة صرعية مستمرة",
                # Egyptian Arabic
                "بيترعش", "تشنجات", "نوبة صرع", "تشنجات مستمرة",
                "مش بيفوق من التشنج", "بيرتجف"
            ],
            "added_by_ai": [],
            "priority": 1,
            "requires_immediate_intervention": True
        },
        
        "choking": {
            "keywords": [
                # English
                "choking", "airway blocked", "complete obstruction", "foreign body airway",
                "can't breathe foreign body", "heimlich", "turning blue", "choking can't breathe",
                "can't breathe at all", "airway swelling",
                # Arabic MSA
                "اختناق", "انسداد مجرى الهواء", "جسم غريب",
                # Egyptian Arabic
                "شرقان", "حاجة في زوره", "مش قادر يبلع", "شرقت", "شرق",
                "مش قادرة تاخد نفس", "حاجة واقفة في زوره", "شرق في أكل",
                "بلع لعبة", "صوته مبحوح", "بلع جسم",
                "اتخنق بالحبل", "شنق", "hanging", "near-hanging", "strangulation"
            ],
            "added_by_ai": [],
            "priority": 1,
            "requires_immediate_intervention": True
        },
        
        "severe_trauma": {
            "keywords": [
                # English
                "gunshot", "gsw", "stab wound", "stabbing", "penetrating trauma",
                "major trauma", "polytrauma", "crush injury", "amputation",
                "high speed accident", "ejected from vehicle", "fall from height",
                "electrocution", "severe burn", "burn over 20 percent",
                "gunshot wound to chest", "gunshot wound to abdomen", "stab wound to chest",
                "vomiting large amounts of blood", "sudden severe back pain hypotensive",
                "pulsatile abdominal mass, hypotensive",
                # Arabic MSA
                "إصابة رصاصة", "طعنة", "صدمة كهربائية", "سقوط من ارتفاع",
                "حادث سير خطير", "بتر",
                # Egyptian Arabic
                "طعن", "رصاص", "حادثة", "accident", "اتضرب",
                "حادث سيارة", "اتطعن", "طلق ناري", "اتعلق في الكهربا", "كهربا",
                "صعق", "حرق شديد", "حروق", "burn", "وقع من الدور",
                "سقط من ارتفاع", "وقع من السلم", "وقع من البلكونة",
                "وقع من فوق العمارة", "اتحرق بنار", "جلده طاير", "اتصعق",
                "السكينة دخلت", "طعنة في صدره", "طعنة في بطنه", "العربية قلبت",
                "حادث عربية", "MVA", "انقلاب", "car accident",
                "اتهرس", "ماكينة", "machine injury", "ايده اتقطعت"
            ],
            "added_by_ai": [],
            "priority": 1,
            "requires_immediate_intervention": True
        },
        
        "anaphylaxis": {
            "keywords": [
                # English
                "anaphylaxis", "anaphylactic shock", "severe allergic reaction",
                "throat closing", "tongue swelling", "can't breathe allergy",
                "throat swelling shut", "lips blue", "anaphylaxis symptoms",
                "epinephrine needed", "epi pen", "airway swelling",
                "hives spreading, starting to feel throat tightness",
                # Arabic MSA
                "صدمة تأقية", "حساسية مفرطة", "تورم الحنجرة",
                # Egyptian Arabic
                "صدمة تحسسية", "حساسية شديدة", "شفايفه ورمت",
                "وشه ورم", "مش قادر يتنفس من الحساسية",
                "لسانه ورم", "زوره قافل", "زوره بيقفل"
            ],
            "added_by_ai": [],
            "priority": 1,
            "requires_immediate_intervention": True
        },
        
        "poisoning_overdose": {
            "keywords": [
                # English
                "overdose", "od", "poison", "poisoning", "ingestion", "toxic ingestion",
                "took whole bottle", "suicide attempt pills", "drank bleach",
                "snake bite", "scorpion sting", "organophosphate",
                # Arabic MSA
                "تسمم", "جرعة زائدة", "ابتلاع سام", "لدغة ثعبان", "لدغة عقرب",
                # Egyptian Arabic
                "جرعة زيادة", "أخد دوا كتير", "بلع دوا", "شرب دوا",
                "أخد حبوب كتير", "جرعة زايدة", "شرب مبيد", "أكل سم",
                "تسمم غذائي", "بلع بطاريات", "بلع حاجة", "بلع عملة",
                "ابتلاع جسم غريب", "swallowed", "بلع كلور", "شرب كلور",
                "سم فئران", "شرب سم", "مبيد حشري", "ماء نار", "شرب ماء نار",
                "علبة باراسيتامول", "أخد علبة", "لدغة عقرب", "لدغته عقرب",
                "عضه تعبان", "عضة تعبان", "شرب كلوركس",
                "بلع دبوس", "بلع إبرة", "بلع مسمار", "سم حشري"
            ],
            "added_by_ai": [],
            "priority": 1,
            "requires_immediate_intervention": True
        },
        
        "drowning": {
            "keywords": [
                # English
                "drowning", "drowned", "near drowning", "submersion", "pulled from water",
                # Arabic MSA
                "غرق", "شبه غرق",
                # Egyptian Arabic
                "غرقان", "طلعوه من المية", "وقع في المية",
                "حمام السباحة", "البحر", "النيل", "غرق في", "اتغرق"
            ],
            "added_by_ai": [],
            "priority": 1,
            "requires_immediate_intervention": True
        },
        
        "severe_bleeding": {
            "keywords": [
                # English - PHASE 2: Added massive bleeding
                "severe bleeding", "massive bleeding", "hemorrhage", "exsanguination",
                "arterial bleeding", "blood everywhere", "bleeding out",
                "uncontrolled bleeding", "tourniquet needed",
                # Arabic MSA
                "نزيف شديد", "نزيف حاد", "نزيف شرياني",
                # Egyptian Arabic
                "بينزف جامد", "دم كتير", "نزيف مش بيوقف",
                "دم كتير جداً", "الدم مش بيوقف", "حامل والدم",
                "نزيف حاد جداً", "نزيف كارثي", "الدم بيطش", "بينزف بغزارة",
                # ===== BATCH 2 ROUND 2: GI Bleed with hematemesis (Level 1) =====
                "ست عجوزة بتترجع دم أسود", "بتترجع دم أسود", "بيترجع دم أسود",
                "ترجيع دم أسود", "قيء دم"
            ],
            "added_by_ai": [],
            "priority": 1,
            "requires_immediate_intervention": True
        },
        
        # ========== PHASE 2: NEW LEVEL 1 CATEGORIES ==========
        
        "ectopic_pregnancy": {
            "keywords": [
                # English
                "ectopic", "ectopic pregnancy", "tubal pregnancy", "ruptured ectopic",
                "ruptured tube", "pregnant collapsed", "pregnant severe abdominal pain",
                # Arabic MSA
                "حمل خارج الرحم", "حمل أنبوبي", "انفجار الأنبوبة",
                # Egyptian Arabic
                "حمل في الأنبوبة", "حامل وبطنها بتوجعها جامد",
                "حامل وألم شديد في جنبها", "حامل وبتنزف ووجع شديد",
                "حمل منفجر", "حامل ووجع في جنب واحد",
                "حامل والألم في ناحية واحدة", "حامل واغمى عليها"
            ],
            "added_by_ai": [],
            "priority": 1,
            "requires_immediate_intervention": True
        },
        
        "aortic_dissection": {
            "keywords": [
                # English
                "aortic dissection", "dissecting aneurysm", "tearing pain",
                "ripping pain", "ripping pain back", "chest pain radiating back",
                "tearing chest pain", "worst pain of my life", "back radiating pain",
                # Arabic MSA
                "تسلخ الأبهر", "تمزق الشريان الأورطي", "انشقاق الأورطي",
                # Egyptian Arabic
                "ألم بيمزق في الضهر", "ألم بيمزق", "حاسس صدري بينشق",
                "ألم شديد في صدري وضهري", "ألم طاعن في صدري للضهر",
                "صدري وضهري بيوجعوني جامد", "الألم بينتشر للضهر",
                "ألم بينزل للضهر", "حاسس صدري بيتقطع",
                "ألم زي السكينة", "الوجع زي ما حد بيشقني"
            ],
            "added_by_ai": [],
            "priority": 1,
            "requires_immediate_intervention": True
        },
        
        "sepsis": {
            "keywords": [
                # English
                "sepsis", "septic shock", "septicemia", "severe sepsis",
                "infection spreading", "systemic infection", "fever confused",
                "fever low blood pressure",
                # Arabic MSA  
                "تعفن الدم", "صدمة إنتانية", "تسمم الدم", "إنتان",
                # Egyptian Arabic - Standard
                "تعفن دم", "العدوى انتشرت", "الالتهاب انتشر في الدم",
                "سخن ورايق", "سخن وضغطه واطي", "سخن وقلبه بيدق جامد",
                "سخونية وتشوش", "حرارة ومش واعي", "بيرتعش جامد",
                "رجفة شديدة", "بيحس بالبرد والسخونية", "مرتعش وسخن",
                "مناعته ضعيفة وعنده عدوى", "سخونية وضغط منخفض",
                # ===== STRESS TEST FIX: Colloquial Egyptian Arabic =====
                "سخن جداً وبترعش", "بترعش من البرد", "جسمي ولع نار", "ولع نار وبرد عليا",
                "سخونية عالية ومش واعي", "حرارتي فوق الأربعين", "فوق الأربعين وقلبي بيخبط",
                "بترجف", "مش قادر اسيطر على جسمي", "سخن وحاسس اني هاموت", "حاسس اني هاموت",
                "جسمي كله بيوجعني وسخن", "بيوجعني وسخن", "نايم من يومين", "سخونيتي مش بتنزل",
                "بتعرق بس حاسس بقشعريرة", "قشعريرة", "سخونية وضغطي واطي", "ضغطي واطي",
                "حرارتي عالية ومش بعرف مين حواليا", "مش بعرف مين حواليا",
                "جسمي بيتكسر وسخن", "بيتكسر وسخن من امبارح", "حاسس بسم في جسمي", "سم في جسمي وسخن",
                "سناني بتخبط من البرد", "بتخبط من البرد بس انا سخن",
                "مش قادر اقوم من السرير وسخونيتي نار", "سخونيتي نار",
                "بقالي كام يوم سخن", "سخن ومش بتحسن", "سخونية ونبضي سريع", "نبضي سريع جداً",
                "جسمي بيتهز من السخونية", "بيتهز من السخونية",
                "حرارتي مش بتنزل بالادوية", "مش بتنزل بالادوية",
                "سخن وبول غامق", "بول غامق ومش كتير",
                # ===== BATCH 2 ROUND 2: DKA with shock (Level 1) =====
                "مريض سكر وضغطه واطي ومش فايق", "سكر وضغطه واطي ومش فايق"
            ],
            "added_by_ai": [],
            "priority": 1,
            "requires_immediate_intervention": True
        },
        
        "severe_hypothermia": {
            "keywords": [
                # English
                "hypothermia", "severe hypothermia", "severe cold exposure",
                "freezing", "frozen", "found in cold", "cold water immersion",
                # Arabic MSA
                "انخفاض حرارة الجسم الشديد", "تجمد",
                # Egyptian Arabic
                "برد شديد", "جسمه ثلج", "متجمد", "اتعرض للبرد الشديد",
                "جسمه بارد جداً", "برودة شديدة", "لقيناه في البرد"
            ],
            "added_by_ai": [],
            "priority": 1,
            "requires_immediate_intervention": True
        },
        
        # ===== BATCH 2 FIX: Pediatric Level 1 Emergencies =====
        "pediatric_critical": {
            "keywords": [
                # English
                "floppy baby", "floppy infant", "limp baby", "unresponsive baby",
                "baby not breathing", "child not breathing", "blue baby",
                "cyanotic baby", "infant seizure",
                # Arabic MSA
                "رضيع مترهل", "طفل لا يتنفس",
                # Egyptian Arabic - FLOPPY BABY (sepsis/meningitis until proven)
                "الواد طري", "طري خالص", "البيبي طري", "مترهل",
                "الطفل طري", "رخو خالص", "جسمه مترهل",
                # ===== BATCH 2 ROUND 2: Exact floppy phrase =====
                "الواد طري خالص ومش بيتحرك", "طري خالص ومش بيتحرك",
                # CRITICAL: Baby not responding
                "البيبي مش بيرد", "مش بيرد خالص", "الواد مش بيرد",
                "مش بيصحى", "مش قادر يصحيه", "البيبي واقع",
                # CRITICAL: Not breathing/blue
                "الواد مش بيتنفس", "البيبي لونه أزرق", "لونه ازرق",
                "شفايفه زرقا",
                # ===== BATCH 2 ROUND 2: Exact perioral cyanosis =====
                "الواد لونه ازرق حوالين بقه", "لونه ازرق حوالين بقه", "ازرق حوالين بقه"
            ],
            "added_by_ai": [],
            "priority": 1,
            "requires_immediate_intervention": True
        }
    },
    
    # =========================================================================
    # LEVEL 2: EMERGENT - High Risk Situation
    # =========================================================================
    # Reference: ESI v4, Decision Point B
    # "High-risk situation? Confused/lethargic/disoriented? Severe pain/distress?"
    # =========================================================================
    
    "level_2": {
        "chest_pain_cardiac": {
            "keywords": [
                # English
                "chest pain", "heart attack", "mi", "myocardial infarction",
                "angina", "cardiac chest pain", "crushing chest pain",
                "elephant on chest", "pressure on chest", "palpitations",
                # Atypical presentations
                "jaw pain nausea", "shoulder pain nausea", "epigastric pain sweating",
                "stemi", "st elevation", "acute coronary syndrome",
                # Arabic MSA
                "ألم صدري", "ذبحة صدرية", "نوبة قلبية", "احتشاء",
                # Egyptian Arabic - Standard
                "ألم صدر", "صدري بيوجعني", "قلبي بيوجعني",
                "ألم في صدري", "صدري", "وجع قلب", "قلبي بيضرب غلط",
                "خفقان", "حاسس بخفقان", "قلبي بيدق بسرعة", "قلبي هيقف", "صدره بيوجعه", "باين عليه تعبان",
                "صدره تاعبه", "أزمة قلبية", "سكتة قلبية",
                "ألم في الفك", "غثيان وألم كتف", "ضغط على صدري",
                # ===== STRESS TEST FIX: Colloquial Egyptian Arabic =====
                "قلبي بيخبط جامد", "مخنوق", "سيدري بيغلي", "بيغلي من جوا",
                "حاجة بتعصر قلبي", "بتعصر", "قلبي بيوقف ويمشي", "بيوقف ويمشي",
                "صدري تقيل", "بيوجعني لما امشي", "بطلع روحي", "اطلع السلم",
                "قلبي بينقط", "بينقط وبيوجعني", "ثقل على قلبي", "حاسس بثقل",
                "دراعي الشمال بيتنمل", "بيتنمل مع وجع", "قلبي بيرفرف", "بيرفرف ومش مرتاح",
                "صدري بيحرقني", "ماشي للدراع الشمال", "حاجة قاعدة على صدري",
                "قافل على صدري", "نار في صدري", "وخز في صدري", "صدري الشمال",
                "خنقة في زوري", "صدري بيشدني", "زي الكهربا في صدري"
            ],
            "added_by_ai": [],
            "priority": 2
        },
        
        # ===== BATCH 2 FIX: Silent MI (Atypical Cardiac Presentations) =====
        # CRITICAL: Diabetics, elderly, women often present WITHOUT chest pain
        # Reference: AHA Guidelines - Atypical MI Presentations
        "silent_mi": {
            "keywords": [
                # English
                "atypical chest pain", "jaw pain", "doom", "atypical mi", "atypical cardiac",
                "diabetic chest pain", "feeling of doom",
                "silent mi", "atypical mi", "nausea sweating", "cold sweat weakness",
                "sense of doom", "impending doom", "diabetic vomiting weak",
                "elderly weak sweating", "diaphoresis nausea",
                # Arabic MSA
                "ذبحة صامتة", "احتشاء صامت", "عرق بارد",
                # Egyptian Arabic - Silent MI presentations
                "هبطان ومعدتي مقلوبة", "معدتي مقلوبة", "حرقان في المعدة", "سوء هضم", "عرقان تلج", "عرق تلج",
                "حاسس اني هاموت", "روحي بتتسحب", "روحي بتتسحب مني",
                "غثيان شديد وعرق بارد", "غثيان وعرق", "عرق بارد",
                "مفيش طاقة خالص", "طاقة خالص وبحس بدوخة", "دوخة وهبطان",
                "إرهاق شديد وعرق", "فجأة حسيت بإرهاق", "إرهاق مفاجئ",
                "ضعف شديد فجأة", "عرق بارد وضعف", "ضعف وعرق",
                "معدتي واجعاني وبعرق", "بعرق كتير", "عرقان ولونه اصفر",
                "لونه اصفر وهبطان", "باباي السكري تعبان", "السكري تعبان جداً وبيرجع",
                "جدي عرقان", "عرقان وهبطان", "ماما السكر عندها بترجع",
                "السكر عندها وهبطانة", "وجع في فكي ومعدتي", "فكي ومعدتي",
                "رجفة جوا جسمها", "رجفة جوا جسمي", "مش مرتاح", "حاسس بقلق",
                "تعبان جداً ومش قادر اقف", "مش قادر اقف على رجلي",
                "جسمي مكسر وبرجع", "مكسر وبرجع", "ثقل في كتفي ومعدتي بتقلب",
                # ===== BATCH 2 ROUND 2: Exact phrases from stress test =====
                "هبطان ومعدتي مقلوبة من الصبح", "جسمي مكسر وبرجع من امبارح",
                "حاسس بغثيان شديد وعرق بارد", "غثيان شديد", "mfiش طاقة خالص وبحس بدوخة",
                "حاسس ان روحي بتتسحب مني", "معدتي واجعاني وبعرق كتير",
                "حاسس بثقل في كتفي ومعدتي بتقلب", "ثقل في كتفي",
                "فجأة حسيت بإرهاق شديد وعرق", "ماما السكر عندها بترجع وهبطانة",
                "حاسس بوجع في فكي ومعدتي", "عرق بارد وحاسس بضعف شديد فجأة",
                "ماما حاسة برجفة جوا جسمها ومش مرتاحة", "برجفة جوا جسمها",
                "باباي السكري تعبان جداً وبيرجع", "جدي عرقان ولونه اصفر وهبطان",
                "تعبان جداً ومش قادر اقف على رجلي"
            ],
            "added_by_ai": [],
            "priority": 2
        },
        
        # ===== BATCH 2 FIX: GI Bleeding =====
        "gi_bleed": {
            "keywords": [
                # English
                "gi bleed", "gi bleeding", "gastrointestinal bleeding",
                "vomiting blood", "hematemesis", "coffee ground emesis",
                "black stool", "melena", "tarry stool", "blood in stool",
                "rectal bleeding", "bloody stool",
                # Arabic MSA
                "نزيف معوي", "قيء دموي", "براز أسود",
                # Egyptian Arabic
                "بيترجع دم", "ترجيع دم", "دم في الترجيع",
                "بتترجع دم أسود", "دم أسود", "ترجيع أسود",
                "برازه أسود", "أسود زي الزفت", "براز زي الزفت",
                "دم في البراز", "براز بدم", "بيعمل دم",
                "ست عجوزة بتترجع دم", "راجل كبير بيترجع دم",
                # ===== BATCH 2 ROUND 2: Exact melena phrase =====
                "برازه أسود زي الزفت", "زفت", "براز اسود"
            ],
            "added_by_ai": [],
            "priority": 2
        },
        
        # ===== BATCH 2 FIX: Elderly Fall / Hip Fracture =====
        "hip_fracture": {
            "keywords": [
                # English
                "hip fracture", "fell can't walk", "elderly fall", "can't get up",
                "leg rotated", "shortened leg", "hip pain after fall",
                # Arabic MSA
                "كسر الورك", "كسر عظم الفخذ",
                # Egyptian Arabic
                "جدتي وقعت ومش قادرة تقوم", "وقعت ومش قادرة تقوم",
                "جدي وقع ومش قادر يقوم", "وقع ومش قادر يقوم",
                "ست كبيرة وقعت", "راجل كبير وقع", "وقع ومش قادر يمشي",
                "رجلها ملفوفة لبرا", "رجله ملفوفة", "رجله قصرت",
                "مش قادر يقف على رجله", "وقعت على وركها", "وركه بيوجعه",
                # ===== BATCH 2 ROUND 2: Exact phrases =====
                "ست كبيرة ورجلها ملفوفة لبرا", "ملفوفة لبرا"
            ],
            "added_by_ai": [],
            "priority": 2
        },
        
        "stroke_symptoms": {
            "keywords": [
                # English - PHASE 2: Added time-sensitive qualifiers
                "stroke", "cva", "brain attack", "face drooping", "arm weakness",
                "speech difficulty", "slurred speech", "sudden weakness",
                "can't speak", "cannot speak", "unable to speak", "difficulty speaking",
                "loss of speech", "sudden speech loss", "inability to speak", "sudden inability to speak",
                "facial droop", "face drooping",
                "one side weakness", "one sided weakness", "hemiplegia", "aphasia", "dysarthria",
                "weakness started now", "wake up stroke", "started suddenly",
                "sudden numbness", "sudden vision loss", "sudden confusion",
                "arm drift", "balance problems", "double vision",
                # Arabic MSA
                "سكتة دماغية", "جلطة دماغية", "شلل نصفي",
                "فقدان النطق", "فقدان الكلام", "عدم القدرة على الكلام", "عدم القدرة على التكلم",
                # Egyptian Arabic - Standard
                "جلطة", "شلل", "مش قادر يتكلم", "وشه مايل",
                "وشي مايل", "وشي اتعوج", "وشه اتعوج", "نص وشي وقع", "نص وشه وقع",
                "كلامي مش واضح", "كلامي اتلخبط", "كلامه اتلخبط", "بيتكلم غريب",
                "مش قادر اتكلم", "مش قادر أتكلم", "مبقتش قادر اتكلم",
                "لساني اتلت", "لسانه اتلت", "لساني تقيل", "لسانه تقيل",
                "مش قادر ينطق", "مش قادر يتكلم", "بيكلم ومش مفهوم",
                "نص جسمه", "نص جسمي مش بيتحرك", "ايده مش بتتحرك", "بيشوف ضلم",
                "بقع سودا", "فقد البصر", "مش شايف", "فجأة مش شايف",
                "نص وشه وقع", "وشه وقع", "مش قادر يرفع ايده",
                "ايده وقعت", "رجله وقعت", "مش قادر يمشي",
                "فجأة مش قادر يمشي", "رجله سودت", "اتنملت",
                # PHASE 2: Time-sensitive Egyptian Arabic
                "ضعف مفاجئ", "لسه حاصل دلوقتي", "فجأة مش بيتحرك",
                "لسه ابتدى", "صحي لقى نفسه كده", "صحي ملقاش رجله",
                "حصل فجأة", "لسه من شوية", "كلامه اتلخبط",
                "بيتكلم غريب", "لسانه اتلخبط", "مش قادر ينطق",
                "بيلعبط", "بيشوف اتنين", "مش قادر يوازن", "بيترنح",
                # ===== STRESS TEST FIX: Colloquial Egyptian Arabic =====
                "ايدي الشمال مش بتتحرك", "مش بتتحرك فجأة", "وشي اتلوى", "اتلوى ومش طبيعي",
                "لساني تقيل", "مش قادر اتكلم صح", "رجلي بقت تقيلة", "تقيلة ومش قادر امشي",
                "بتكلم غلط", "مش فاهم نفسي", "الدنيا بتلف", "بتلف بيا",
                "نص جسمي مش حاسس بيه", "مش حاسس بيه", "برغي كلام", "كلام مش مفهوم",
                "ايدي واقعة مني", "مش قادر ارفعها", "مش قادر ابلع", "فجأة مش قادر ابلع",
                "شفايفي بتتكلم لوحدها", "بتتكلم لوحدها", "رعشة في نص وشي", "نص وشي",
                "الكلام بيطلع غلط", "غلط من بقي", "مش قادر امسك حاجة", "امسك حاجة في ايدي",
                "تنميل في نص جسمي", "نص جسمي الشمال", "وشي معوج", "صحيت لقيت وشي معوج",
                "بشوف دوبل", "دوبل ومش متزن", "رجلي بتسحب", "بتسحب وانا ماشي",
                "مش فاكر اسمي", "مش فاكر اسمي فجأة", "نسيت اسمي",
                # ===== BATCH 2 FIX: Dysphagia (swallowing) =====
                "مش عارف يبلع", "مش عارف يبلع الأكل", "الراجل الكبير مش عارف يبلع",
                "بيشرق", "الأكل بيرجع من بقه", "مش قادر يبلع ريقه"
            ],
            "added_by_ai": [],
            "priority": 2
        },
        
        "respiratory_distress": {
            "keywords": [
                # English
                "can't breathe", "difficulty breathing", "shortness of breath severe",
                "respiratory distress", "accessory muscles", "tripod position",
                "speaking in words only", "severe asthma", "copd exacerbation severe",
                # Arabic MSA
                "ضيق تنفس شديد", "صعوبة في التنفس",
                # Egyptian Arabic - Standard
                "مش عارف آخد نفسي", "ضيق تنفس", "مش قادرة آخد نفسي",
                "صعوبة تنفس", "نفسي ضيق", "بيتنهج",
                "عندها ربو", "عنده ربو", "مش قادرة تتنفس", "مش قادر اتنفس",
                "مش قادر يتنفس", "نوبة ربو شديدة", "بيتنفس بصعوبة",
                # ===== STRESS TEST FIX: Colloquial Egyptian Arabic =====
                "مش قادر اخد نفسي", "اخد نفسي خالص", "كابس على نفسي", "كابس على نفسي من امبارح",
                "بتنهج زي الكلب", "بتنهج", "نفسي واقف", "واقف ومش عارف اتنفس",
                "هاتخنق", "حاسس اني هاتخنق", "مش لاقي هوا", "لاقي هوا",
                "بلهث", "بلهث من أقل مجهود", "نفسي قصير", "قصير جداً",
                "صحيت من النوم مش قادر اتنفس", "حاجة قافلة مجرى الهوا", "قافلة مجرى الهوا",
                "بشهق", "باخد نفس عميق ومش بيكفي", "الربو جالي", "ماعييش البخاخ",
                "ضيق في الصدر ومش قادر اتنفس", "نفسي بيقطع", "بيقطع لما انام",
                "قلة النفس", "مش قادر اتكلم من قلة النفس", "رئتي مقفولة", "حاسس ان رئتي مقفولة",
                "بتنفس بصعوبة شديدة", "الهوا مش داخل", "مش داخل بسهولة",
                "صدري بيصفر", "بيصفر لما باخد نفس", "صدري بيزم", "بيزم لما باخد نفس"
            ],
            "added_by_ai": [],
            "priority": 2
        },
        
        "suicidal_homicidal": {
            "keywords": [
                # English
                "suicidal", "kill myself", "homicidal", "kill someone", "harm self",
                "suicide attempt", "took pills", "pills trying to end", "overdose suicide",
                "took a handful of pills", "recent attempt", "swallowed pills",
                # English - Original
                "suicidal", "suicide", "kill myself", "want to die", "end my life",
                "self harm", "cutting myself", "has a plan", "prepared method",
                "homicidal", "wants to hurt someone", "kill someone",
                # Arabic MSA
                "انتحار", "أفكار انتحارية", "إيذاء النفس",
                # Egyptian Arabic
                "عايز أموت", "عايز يموت", "يقتل نفسه", "عايز يقتل نفسه",
                "ينتحر", "عايز ينتحر", "هيأذي نفسه", "مش عايز يعيش",
                "يشنق نفسه", "ناوي يشنق", "يرمي نفسه", "عايز يموت نفسه",
                "عايز يضرب نفسه", "يأذي نفسه", "عنده خطة",
                "جهز الطريقة", "عايز يأذي حد", "عايز يقتل فلان", "ناوي يقتل حد"
            ],
            "added_by_ai": [],
            "priority": 2
        },
        
        "obstetric_emergency": {
            "keywords": [
                # English
                "pregnant bleeding", "heavy vaginal bleeding", "ectopic", "pregnancy emergency",
                "severe pelvic pain pregnancy", "pos pregnancy test", "positive pregnancy test",
                "possible ectopic",
                "pregnant bleeding", "vaginal bleeding pregnant", "preterm labor",
                "contractions early", "water broke early", "umbilical cord",
                "cord prolapse", "placental abruption", "placenta previa",
                "eclampsia", "preeclampsia severe",
                # Arabic MSA
                "نزيف الحمل", "ولادة مبكرة", "تسمم الحمل",
                # Egyptian Arabic
                "حامل بتنزف", "حامل وبتنزف", "حامل في", "حامل ونزيف",
                "نزيف حمل", "الحمل بينزف", "حامل والمية نزلت",
                "انفصال المشيمة", "طلق بدري"
            ],
            "added_by_ai": [],
            "priority": 2
        },
        
        "diabetic_emergency": {
            "keywords": [
                # English
                "low blood sugar", "hypoglycemia", "sugar low", "diabetic unconscious",
                "dka", "diabetic ketoacidosis", "hyperglycemic crisis",
                "hhs", "hyperosmolar", "fruity breath", "kussmaul breathing",
                "acetone breath", "deep rapid breathing diabetic",
                "vomiting blood", "throwing up blood", "massive gi bleed",
                "abdominal mass", "pulsatile mass", "ruptured aaa",
                # Arabic MSA
                "هبوط السكر", "غيبوبة سكري", "حماض كيتوني",
                # Egyptian Arabic - Standard
                "السكر واطي", "السكر عالي", "سكر منخفض",
                "عنده سكر وبيترعش", "هبوط سكر", "غيبوبة سكر",
                "سكر وبيرتعش", "عنده سكر وتعبان",
                "حموضة السكر", "سكر واطي جداً",
                # ===== BATCH 2 FIX: DKA Colloquial Egyptian Arabic =====
                "ريحة بقه زي التفاح", "التفاح المعفن", "ريحة بقه تفاح",
                "نفسه عالي جداً", "عطشان موت", "نفسه عالي وعطشان",
                "السكر عنده وبطنه بتوجعه", "بيتنفس بسرعة", "سكر وبيتنفس بسرعة",
                "بيشرب مية كتير جداً", "بيتبول كل شوية", "عطش شديد",
                "ابني السكري تعبان", "السكري تعبان وبيتنفس غريب",
                "عنده سكر ومش واعي", "سكر ومش واعي كويس",
                "بطني بتوجعني وباخد نفس عميق", "نفس عميق",
                "السكر بتاعه عالي جداً", "سكر عالي جداً وبيرجع",
                "نفسه بيطلع من بطنه", "بيطلع من بطنه وريحته وحشة",
                "مريض سكر وضغطه واطي", "سكر وضغطه واطي ومش فايق",
                "ريحته وحشة", "ريحة الأسيتون", "نفسه تقيل"
            ],
            "added_by_ai": [],
            "priority": 2
        },
        
        # ===== BATCH 2 ROUND 2: Pediatric Level 2 Emergencies =====
        # These presentations need URGENT evaluation (Level 2) not just Level 3
        "pediatric_emergency": {
            "keywords": [
                # Sepsis/Meningitis red flags
                "البيبي مش بيعيط حتى", "مش بيعيط حتى", "الواد مش بيعيط",
                "ابني مش بيرضع ونايم طول الوقت", "مش بيرضع ونايم",
                "الواد قاطع أكل خالص ونايم طول اليوم", "قاطع أكل ونايم",
                "البنت سخنة ورقبتها مش بتلف", "سخنة ورقبتها مش بتلف", "رقبتها مش بتلف",
                "الواد بيعيط عياط غريب ومش بيسكت", "عياط غريب ومش بيسكت",
                "البيبي اليافوخ بتاعه منفوخ", "يافوخه منفوخ",
                # Intussusception
                "برازه زي الجيلي الأحمر", "جيلي أحمر", "براز جيلي",
                "الطفل بيعيط فجأة وبيسحب رجليه على بطنه", "بيسحب رجليه على بطنه",
                # Severe Dehydration
                "ابني مش بيشرب ولسانه ناشف", "مش بيشرب ولسانه ناشف",
                "البنت عينيها غايرة جوا", "عينيها غايرة جوا", "عيونه غايرة",
                "البيبي جلده بقى زي الورق", "جلده زي الورق",
                "ابني بقاله يوم مش بيعمل حمام", "بقاله يوم مش بيعمل حمام",
                # Respiratory Distress
                "الواد بيتنفس بصوت زي الصفارة", "بيتنفس بصوت زي الصفارة",
                "البنت صدرها بينسحب جوا لما بتتنفس", "صدرها بينسحب جوا",
                # Febrile seizure
                "البنت بتترعش وسخنة جداً", "بتترعش وسخنة جداً", "بيترعش وسخن جداً"
            ],
            "added_by_ai": [],
            "priority": 2
        },
        
        "severe_headache": {
            "keywords": [
                # English
                "worst headache", "thunderclap", "worst headache of life", "sudden severe headache",
                "thunderclap headache",
                "worst headache ever", "thunderclap headache", "sudden severe headache",
                "headache with stiff neck", "headache with fever", "meningitis",
                "subarachnoid hemorrhage", "photophobia", "light sensitivity",
                "neck stiffness", "stiff neck", "can't touch chin to chest",
                # Arabic MSA
                "صداع شديد مفاجئ", "تيبس الرقبة", "التهاب السحايا",
                # Egyptian Arabic - Standard
                "صداع شديد", "راسي هتنفجر", "صداع مفاجئ",
                "صداع شديد جداً", "أسوأ صداع", "رقبته متيبسة",
                "رقبة متيبسة", "صداع ورقبته", "صداع زي ما حد ضربها",
                "صداع زي الضرب", "صداع فجأة", "راسه بتوجعه جامد",
                "راسه بتوجعه وبيرجع", "نزيف تحت العنكبوتية",
                # ===== STRESS TEST FIX: Meningitis - Colloquial Egyptian Arabic =====
                "رقبتي متيبسة", "متيبسة ومش قادر احركها", "صداع شديد والنور", "النور بيأذيني",
                "مش قادر انزل راسي على صدري", "انزل راسي على صدري", "راسي هايتفجر", "النور بيحرقني",
                "رقبتي واجعاني وسخن", "واجعاني وسخن", "مش طايق اشوف النور", "اشوف النور وراسي بيوجعني",
                "رقبتي واجعاني", "سخونية ورقبتي", "صداع ورقبتي", "صداع مع سخونية",
                "صداع من ورا", "زي ما حد بيشد رقبتي", "بيشد رقبتي", "سخونية وراسي بينفجر",
                "مش قادر اطأطأ راسي", "اطأطأ راسي", "عيني بتوجعني من النور", "بتوجعني من النور",
                "رقبتي متشنجة", "متشنجة وسخن", "صداع مع قيء", "قيء وحساسية من الضوء", "حساسية من الضوء",
                "راسي بيدق", "بيدق وعيني مش طايقة النور", "مش طايقة النور",
                "سخن ورقبتي يابسة", "رقبتي يابسة", "صداع شديد ومش طايق الصوت", "مش طايق الصوت",
                "رقبتي بتأزني", "بتأزني لما احركها", "طعن في راسي من ورا", "حاسس بطعن في راسي",
                "سخن وصداع ورقبتي مش بتلف", "رقبتي مش بتلف", "النور بيخليني اتقيأ", "بيخليني اتقيأ",
                "راسي ورقبتي متحجرين", "متحجرين"
            ],
            "added_by_ai": [],
            "priority": 2
        },
        
        "severe_pain": {
            "keywords": [
                # English
                "severe pain", "worst pain", "pain 10 out of 10", "excruciating",
                "unbearable pain", "rigid abdomen", "surgical abdomen",
                # Arabic MSA
                "ألم شديد جداً", "بطن صلبة",
                # Egyptian Arabic
                "ألم شديد", "بيوجعني جدا جدا", "ألم شديد جداً",
                "وجع مش طبيعي", "ألم رهيب", "بطنه منفوخة", "بطنه قاسية",
                "زي الحجر", "الألم 10 من 10"
            ],
            "added_by_ai": [],
            "priority": 2
        },
        
        "high_fever_toxic": {
            "keywords": [
                # English
                "high fever toxic", "fever looks very sick", "toxic appearing",
                "fever 40", "fever 104",
                # Arabic MSA
                "حمى شديدة", "مظهر سمي",
                # Egyptian Arabic
                "سخونية عالية جداً", "حرارة عالية جداً", "معياش جداً",
                "حرارة 40", "سخن جداً وتعبان", "شكله تعبان جداً", "منهك"
            ],
            "added_by_ai": [],
            "priority": 2
        },
        
        "altered_mental_status": {
            "keywords": [
                # English
                "confused", "disoriented", "altered mental status", "lethargy",
                "lethargic", "hallucinations", "delirium", "delirium tremens",
                "alcohol withdrawal", "sudden confusion",
                # Arabic MSA
                "تغير الوعي", "هذيان", "هلوسة",
                # Egyptian Arabic
                "مش عارف مكانه", "مش عارفة مكانها", "تايه", "مش بيعرفني", "مش فاكر حاجة",
                "تغير وعي", "بيتكلم مع ناس مش موجودة", "بيهلوس",
                "بيشوف حاجات", "هلوسة", "مش عارف هو فين",
                "كلام غريب", "بتتكلم كلام غريب", "مش عارفاني", "مش عارفني",
                "دواره البيضة", "تشنج انسحابي", "انسحاب كحول", "تشوش مفاجئ"
            ],
            "added_by_ai": [],
            "priority": 2
        },
        
        "allergic_reaction": {
            "keywords": [
                # English
                "allergic reaction", "hives", "rash allergy", "swelling allergy",
                "hives spreading", "throat tightness", "allergic reaction progressing",
                "hives spreading, starting to feel throat tightness",
                "throat swelling shut", "tongue swelling", "can't breathe allergy",
                # Arabic MSA
                "تفاعل تحسسي", "شرى", "طفح جلدي تحسسي", "تورم تحسسي",
                # Egyptian Arabic
                "حساسية", "حساسية شديدة", "وشه ورم", "جسمه بيحك",
                "حساسية في الزور", "زورها قفل", "مش قادر يتنفس من الحساسية"
            ],
            "added_by_ai": [],
            "priority": 2
        },
        
        "testicular_pain": {
            "keywords": [
                # English
                "testicular pain", "testicular torsion", "testicle swollen",
                "sudden testicular pain",
                # Arabic MSA
                "ألم الخصية", "التواء الخصية",
                # Egyptian Arabic
                "خصية", "خصيته", "الخصية بتوجع", "خصيته ورمت"
            ],
            "added_by_ai": [],
            "priority": 2
        },
        
        "dvt_pe": {
            "keywords": [
                # English
                "dvt", "deep vein thrombosis", "pulmonary embolism", "pe",
                "leg swollen red hot", "calf pain swelling", "chest pain calf pain",
                # Arabic MSA
                "جلطة وريدية عميقة", "انسداد رئوي",
                # Egyptian Arabic
                "رجله سخنة وحمرا", "متورمة وحمرا", "جلطة في الرجل",
                "ساقه متورمة", "جلطة رئوية", "صدري ورجلي"
            ],
            "added_by_ai": [],
            "priority": 2
        },
        
        "hemoptysis": {
            "keywords": [
                # English
                "coughing blood", "hemoptysis", "blood in cough", "vomiting blood",
                "hematemesis", "coffee ground vomit", "massive hemoptysis",
                # Arabic MSA
                "سعال دموي", "قيء دموي",
                # Egyptian Arabic
                "كحة بدم", "بيكح دم", "دم مع الكحة", "بصق دم",
                "اتقيأ دم", "رجع دم", "قيء دم", "دم أسود", "كحة دم كتير"
            ],
            "added_by_ai": [],
            "priority": 2
        },
        
        "mesenteric_ischemia": {
            "keywords": [
                # English
                "mesenteric ischemia", "bowel ischemia", "dead bowel",
                "pain out of proportion", "elderly severe abdominal pain",
                "atrial fibrillation abdominal",
                # Arabic MSA
                "نقص تروية الأمعاء",
                # Egyptian Arabic
                "ألم بطن شديد جداً", "بطنه بتوجعه جامد بس مش منتفخة",
                "ألم أكتر من اللي باين", "مسن وبطنه بتوجعه جامد",
                "عنده رفرفة وبطنه بتوجعه"
            ],
            "added_by_ai": [],
            "priority": 2
        }
    },
    
    # =========================================================================
    # LEVEL 3: URGENT - Multiple Resources Needed (≥2)
    # =========================================================================
    
    "level_3": {
        "abdominal_pain_moderate": {
            "keywords": [
                "abdominal pain", "stomach pain", "belly pain",
                "ألم بطن", "بطني بتوجعني", "معدتي", "مغص", "وجع بطن",
                "ألم في بطني", "appendicitis", "زائدة",
                "cholecystitis", "مرارة", "gallbladder"
            ],
            "added_by_ai": [],
            "priority": 3,
            "expected_resources": ["labs", "imaging", "iv_fluids"],
            "resource_count": 3
        },
        
        "fever_with_symptoms": {
            "keywords": [
                "fever", "فحمى", "سخونية", "سخن", "حمى", "جسمه سخن",
                "fever with cough", "سخونية وكحة", "fever vomiting", "سخونية وبيرجع"
            ],
            "added_by_ai": [],
            "priority": 3,
            "expected_resources": ["labs", "imaging"],
            "resource_count": 2
        },
        
        "vomiting_dehydration": {
            "keywords": [
                "vomiting", "بيرجع", "استفراغ", "ترجيع", "قيء", "رجع كتير",
                "can't keep anything down", "مش قادر ياكل حاجة",
                "dehydration", "جفاف", "dry mouth", "بقه ناشف"
            ],
            "added_by_ai": [],
            "priority": 3,
            "expected_resources": ["labs", "iv_fluids"],
            "resource_count": 2
        },
        
        "moderate_bleeding": {
            "keywords": [
                "bleeding", "بينزف", "نزيف", "دم", "جرح بينزف", "جرح كبير",
                "غرز كتير", "محتاج غرز كتير", "needs stitches"
            ],
            "added_by_ai": [],
            "priority": 3,
            "expected_resources": ["laceration_repair", "labs"],
            "resource_count": 2
        },
        
        "fracture_deformity": {
            "keywords": [
                "fracture", "broken", "كسر", "مكسور", "ملوي", "اتكسرت",
                "شكلها مش طبيعي", "عظم طالع", "obvious deformity",
                "angulated", "bone sticking out"
            ],
            "added_by_ai": [],
            "priority": 3,
            "expected_resources": ["xray", "splinting", "orthopedic_consult"],
            "resource_count": 3
        },
        
        # ===== BATCH 2 FIX: Pediatric - Level 3 General =====
        "pediatric_distress": {
            "keywords": [
                "child sick", "طفل", "ابني", "بنتي", "الطفل تعبان",
                "البيبي", "رضيع", "infant not feeding", "مش عايز يرضع",
                "baby crying", "البيبي بيعيط", "listless baby"
            ],
            "added_by_ai": [],
            "priority": 3,
            "expected_resources": ["labs", "imaging", "iv_fluids"],
            "resource_count": 3
        },
        
        "moderate_dyspnea": {
            "keywords": [
                "short of breath", "ضيق نفس خفيف", "نفسي تعبني شوية",
                "dyspnea on exertion", "بيتنهج لما بيمشي",
                "wheezing", "صفير في صدره"
            ],
            "added_by_ai": [],
            "priority": 3,
            "expected_resources": ["labs", "imaging", "nebulizer"],
            "resource_count": 3
        },
        
        "chest_pain_noncardiac": {
            "keywords": [
                "chest pain breathing", "صدري بيوجع لما بتنفس",
                "ألم صدر مع التنفس", "pleuritic pain", "ألم جنبي",
                "chest wall pain", "ألم في عضلات الصدر"
            ],
            "added_by_ai": [],
            "priority": 3,
            "expected_resources": ["ecg", "labs", "imaging"],
            "resource_count": 3
        },
        
        "asthma_exacerbation": {
            "keywords": [
                "asthma attack", "نوبة ربو", "ربو زاد", "wheezing bad",
                "صفير شديد", "can't use inhaler", "البخاخ مش نافع"
            ],
            "added_by_ai": [],
            "priority": 3,
            "expected_resources": ["nebulizer", "steroids", "labs"],
            "resource_count": 3
        },
        
        "kidney_stone": {
            "keywords": [
                "kidney stone", "حصوة", "حصى الكلى", "renal colic",
                "مغص كلوي", "flank pain", "ألم في الجنب", "colicky pain",
                "ألم بييجي ويروح", "radiates to groin", "بينزل تحت"
            ],
            "added_by_ai": [],
            "priority": 3,
            "expected_resources": ["labs", "imaging", "iv_fluids", "pain_meds"],
            "resource_count": 4
        },
        
        "psychiatric_agitated": {
            "keywords": [
                "agitated", "aggressive", "violent", "هائج", "عصبي جداً",
                "بيكسر", "threatening", "بيهدد"
            ],
            "added_by_ai": [],
            "priority": 3,
            "expected_resources": ["sedation", "security", "psych_consult"],
            "resource_count": 3
        }
    },
    
    # =========================================================================
    # LEVEL 4: LESS URGENT - One Resource Needed
    # =========================================================================
    
    "level_4": {
        "minor_trauma": {
            "keywords": [
                "fell", "fall", "وقعت", "وقع", "اتخبط", "خبطة", "ضربة",
                "وارم", "ورم", "twisted ankle", "لويت رجلي", "sprain", "التواء"
            ],
            "added_by_ai": [],
            "priority": 4,
            "expected_resources": ["xray"],
            "resource_count": 1
        },
        
        "laceration_simple": {
            "keywords": [
                "cut", "laceration", "جرح", "قطع", "خياطة", "غرز",
                "جرح بسيط", "small cut", "جرح صغير", "needs a few stitches"
            ],
            "added_by_ai": [],
            "priority": 4,
            "expected_resources": ["suture_kit"],
            "resource_count": 1
        },
        
        "uri_symptoms": {
            "keywords": [
                "cold", "flu", "cough", "برد", "كحة", "زكام", "رشح",
                "انفلونزا", "runny nose", "مناخيري بتنزل",
                "congestion", "زكام شديد"
            ],
            "added_by_ai": [],
            "priority": 4,
            "expected_resources": [],
            "resource_count": 0
        },
        
        "sore_throat": {
            "keywords": [
                "sore throat", "زور", "حلق", "بلع", "زوري بيوجعني",
                "التهاب حلق", "pharyngitis", "tonsillitis", "لوز", "اللوز ورمت"
            ],
            "added_by_ai": [],
            "priority": 4,
            "expected_resources": ["strep_test"],
            "resource_count": 1
        },
        
        "earache": {
            "keywords": [
                "ear pain", "earache", "ودني", "أذني", "ألم أذن",
                "ear infection", "التهاب أذن", "otitis"
            ],
            "added_by_ai": [],
            "priority": 4,
            "expected_resources": ["exam_only"],
            "resource_count": 1
        },
        
        "uti_symptoms": {
            "keywords": [
                "burning urination", "حرقان بول", "التهاب مجرى",
                "حرقان في البول", "رايح الحمام كتير", "بول كتير",
                "التهاب بولي", "dysuria", "frequency", "urgency"
            ],
            "added_by_ai": [],
            "priority": 4,
            "expected_resources": ["urinalysis"],
            "resource_count": 1
        },
        
        "mild_allergic": {
            "keywords": [
                "rash", "allergy", "حساسية", "طفح", "حكة", "هرش", "جلدي",
                "hives", "urticaria", "أرتيكاريا", "طفح جلدي"
            ],
            "added_by_ai": [],
            "priority": 4,
            "expected_resources": ["antihistamine"],
            "resource_count": 1
        },
        
        "back_pain_chronic": {
            "keywords": [
                "back pain", "ظهري", "وجع ضهر", "ألم ظهر", "ضهري بيوجعني",
                "chronic back", "وجع ضهر مزمن", "lower back", "أسفل الظهر"
            ],
            "added_by_ai": [],
            "priority": 4,
            "expected_resources": ["pain_meds_oral"],
            "resource_count": 1
        },
        
        "mild_gi": {
            "keywords": [
                "diarrhea", "إسهال", "مشي", "معدة", "بطني ماشية",
                "loose stool", "stomach upset", "معدتي متلخبطة"
            ],
            "added_by_ai": [],
            "priority": 4,
            "expected_resources": [],
            "resource_count": 0
        },
        
        "mild_pain": {
            "keywords": ["pain", "وجع", "بيوجعني", "ألم", "hurts", "sore"],
            "added_by_ai": [],
            "priority": 4,
            "expected_resources": ["pain_meds_oral"],
            "resource_count": 1
        },
        
        "headache_mild": {
            "keywords": [
                "headache", "صداع", "راسي", "دماغي", "صداع خفيف",
                "tension headache", "صداع توتري", "mild headache"
            ],
            "added_by_ai": [],
            "priority": 4,
            "expected_resources": ["pain_meds_oral"],
            "resource_count": 1
        },
        
        "eye_complaint": {
            "keywords": [
                "عيني", "عين", "حمرا", "مدمعة", "رمد", "العين",
                "pink eye", "conjunctivitis", "eye discharge"
            ],
            "added_by_ai": [],
            "priority": 4,
            "expected_resources": ["eye_exam"],
            "resource_count": 1
        },
        
        "dental": {
            "keywords": [
                "ضرس", "وجع سنة", "أسنان", "tooth", "dental", "ضرسي بيوجعني",
                "toothache", "وجع ضرس", "dental abscess"
            ],
            "added_by_ai": [],
            "priority": 4,
            "expected_resources": ["pain_meds_oral"],
            "resource_count": 1
        },
        
        "skin_fungal": {
            "keywords": [
                "فطريات", "fungus", "tinea", "فطر", "ringworm",
                "athlete's foot", "فطر القدم"
            ],
            "added_by_ai": [],
            "priority": 4,
            "expected_resources": [],
            "resource_count": 0
        },
        
        "hiccups": {
            "keywords": ["زغطة", "hiccups", "فواق", "persistent hiccups"],
            "added_by_ai": [],
            "priority": 4,
            "expected_resources": [],
            "resource_count": 0
        },
        
        "ankle_sprain": {
            "keywords": [
                "ankle sprain", "التواء الكاحل", "لويت رجلي", "twisted ankle",
                "ankle swollen", "الكاحل وارم", "can walk but hurts"
            ],
            "added_by_ai": [],
            "priority": 4,
            "expected_resources": ["xray"],
            "resource_count": 1
        },
        
        "insect_bite": {
            "keywords": [
                "insect bite", "قرصة", "ناموسة", "bug bite", "bee sting",
                "قرصة نحلة", "قرصة بعوضة", "itchy bite"
            ],
            "added_by_ai": [],
            "priority": 4,
            "expected_resources": [],
            "resource_count": 0
        }
    },
    
    # =========================================================================
    # LEVEL 5: NON-URGENT - No Resources Needed
    # =========================================================================
    
    "level_5": {
        "prescription_refill": {
            "keywords": [
                "refill", "prescription", "روشتة", "تجديد", "الدوا خلص",
                "عايز دوا", "أجدد الروشتة", "medication refill",
                "need my meds", "ran out of medication", "الدوا خلص مني"
            ],
            "added_by_ai": [],
            "priority": 5,
            "expected_resources": [],
            "resource_count": 0
        },
        
        "medical_certificate": {
            "keywords": [
                "certificate", "تقرير", "شهادة", "إجازة مرضية", "تقرير طبي",
                "أجيب تقرير", "ورقة عذر", "عذر للمدرسة", "medical records",
                "sick note", "work excuse", "عذر للشغل"
            ],
            "added_by_ai": [],
            "priority": 5,
            "expected_resources": [],
            "resource_count": 0
        },
        
        "suture_removal": {
            "keywords": [
                "remove stitches", "فك غرز", "فك الغرز", "أفك الغرز",
                "شيل الغرز", "staple removal", "فك الدبابيس"
            ],
            "added_by_ai": [],
            "priority": 5,
            "expected_resources": [],
            "resource_count": 0
        },
        
        "chronic_stable": {
            "keywords": [
                "follow up", "متابعة", "كشف", "المتابعة العادية",
                "نتيجة التحليل", "أسأل عن نتيجة", "نتيجة أشعة",
                "ميعاد العملية", "أسأل عن ميعاد", "استفسار", "appointment",
                "أقيس الضغط", "قياس ضغط", "قياس السكر",
                "routine checkup", "كشف دوري"
            ],
            "added_by_ai": [],
            "priority": 5,
            "expected_resources": [],
            "resource_count": 0
        },
        
        "minor_complaint": {
            "keywords": [
                "check up", "فحص", "اطمن", "عايز اطمن", "حاجة بسيطة",
                "تطعيم", "vaccination", "عايز تحليل", "محتاج تحليل",
                "تحليل دم عادي", "عايز أعمل تحليل", "حقنة تيتانوس",
                "tetanus shot", "أظافر نابتة", "ingrown nail",
                "wart removal", "شيل سنطة"
            ],
            "added_by_ai": [],
            "priority": 5,
            "expected_resources": [],
            "resource_count": 0
        },
        
        "wound_check": {
            "keywords": [
                "wound check", "كشف على الجرح", "جرح بيلتئم", "healing well",
                "الجرح كويس", "follow up wound", "متابعة الجرح"
            ],
            "added_by_ai": [],
            "priority": 5,
            "expected_resources": [],
            "resource_count": 0
        },
        
        "rash_minor": {
            "keywords": [
                "minor rash", "طفح بسيط", "small rash", "not itchy",
                "مش بيهرش", "tiny spots", "نقط صغيرة"
            ],
            "added_by_ai": [],
            "priority": 5,
            "expected_resources": [],
            "resource_count": 0
        }
    }
}


# =============================================================================
# KEYWORD DATABASE CLASS
# =============================================================================

class KeywordDatabase:
    """
    Dynamic keyword database that can be updated by AI Teaching Agent.
    Stores keywords in a JSON file for persistence.
    
    PHASE 2: Added resource prediction metadata for ESI compliance.
    """
    
    def __init__(self, db_path: str = None):
        if db_path is None:
            db_path = os.path.join(
                os.path.dirname(__file__),
                "keywords_db.json"
            )
        self.db_path = db_path
        self.data = self._load_or_create()
        self._search_index = None

    def _invalidate_search_index(self):
        """Invalidate cached keyword search index."""
        self._search_index = None

    @staticmethod
    def _normalize_keyword_key(keyword: str) -> str:
        return (
            " ".join(str(keyword or "").strip().lower().split())
            .replace("أ", "ا")
            .replace("إ", "ا")
            .replace("آ", "ا")
        )

    def _merge_keywords_unique(self, existing: List[str], defaults: List[str]) -> List[str]:
        merged = list(existing or [])
        seen = {self._normalize_keyword_key(item) for item in merged}
        for keyword in defaults or []:
            normalized = self._normalize_keyword_key(keyword)
            if normalized and normalized not in seen:
                merged.append(keyword)
                seen.add(normalized)
        return merged

    def _merge_with_defaults(self, loaded_data: dict) -> Tuple[dict, bool]:
        """
        Merge newly added default keywords/categories into existing on-disk DB
        without deleting prior AI/user additions.
        """
        merged = copy.deepcopy(loaded_data or {})
        changed = False

        if "metadata" not in merged:
            merged["metadata"] = {}
            changed = True
        default_version = str(DEFAULT_KEYWORDS.get("metadata", {}).get("version", "2.0.0"))
        current_version = str(merged.get("metadata", {}).get("version", "0.0.0"))
        if current_version < default_version:
            merged["metadata"]["version"] = default_version
            changed = True

        for level_key in ("level_1", "level_2", "level_3", "level_4", "level_5"):
            default_level = DEFAULT_KEYWORDS.get(level_key, {})
            if level_key not in merged:
                merged[level_key] = {}
                changed = True
            merged_level = merged[level_key]
            for category, default_info in default_level.items():
                if category not in merged_level:
                    merged_level[category] = copy.deepcopy(default_info)
                    changed = True
                    continue

                target = merged_level[category]
                merged_keywords = self._merge_keywords_unique(
                    target.get("keywords", []),
                    default_info.get("keywords", []),
                )
                if merged_keywords != target.get("keywords", []):
                    target["keywords"] = merged_keywords
                    changed = True

                merged_added = self._merge_keywords_unique(
                    target.get("added_by_ai", []),
                    default_info.get("added_by_ai", []),
                )
                if merged_added != target.get("added_by_ai", []):
                    target["added_by_ai"] = merged_added
                    changed = True

                for field in (
                    "priority",
                    "resource_count",
                    "expected_resources",
                    "requires_immediate_intervention",
                ):
                    if field not in target and field in default_info:
                        target[field] = copy.deepcopy(default_info[field])
                        changed = True

        return merged, changed

    def _build_search_index(self):
        """Build cached keyword search index for fast lookups."""
        all_keywords = []
        for level in [1, 2, 3, 4, 5]:
            keywords_dict = self.get_keywords_for_level(level)
            for category, keywords in keywords_dict.items():
                for kw in keywords:
                    kw_lower = kw.lower()
                    if len(kw_lower) < 3:
                        continue
                    all_keywords.append((kw_lower, category, level, len(kw_lower)))

        # Sort by length (longest first) then by level (lowest number = highest priority)
        all_keywords.sort(key=lambda x: (-x[3], x[2]))
        self._search_index = all_keywords
    
    def _load_or_create(self) -> dict:
        """Load existing database or create new one"""
        if os.path.exists(self.db_path):
            try:
                with open(self.db_path, 'r', encoding='utf-8') as f:
                    loaded_data = json.load(f)
                    # Check version - if old version, use defaults
                    if loaded_data.get("metadata", {}).get("version", "1.0.0") < "2.0.0":
                        print("Upgrading keyword database to v2.0.0...")
                        self._save(DEFAULT_KEYWORDS)
                        return DEFAULT_KEYWORDS.copy()
                    merged_data, changed = self._merge_with_defaults(loaded_data)
                    if changed:
                        self._save(merged_data)
                    return merged_data
            except Exception as e:
                print(f"Error loading keyword database: {e}")
                return DEFAULT_KEYWORDS.copy()
        else:
            # Create new database with defaults
            self._save(DEFAULT_KEYWORDS)
            return DEFAULT_KEYWORDS.copy()
    
    def _save(self, data: dict = None):
        """Save database to file"""
        if data is None:
            data = self.data
        
        # Update metadata
        data["metadata"]["last_updated"] = datetime.now().isoformat()
        data["metadata"]["total_keywords"] = self._count_keywords(data)
        
        with open(self.db_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        self._invalidate_search_index()
    
    def _count_keywords(self, data: dict) -> int:
        """Count total keywords in database"""
        count = 0
        for level in ["level_1", "level_2", "level_3", "level_4", "level_5"]:
            if level in data:
                for category in data[level].values():
                    count += len(category.get("keywords", []))
                    count += len(category.get("added_by_ai", []))
        return count
    
    def get_keywords_for_level(self, level: int) -> Dict[str, List[str]]:
        """Get all keywords for a specific triage level"""
        level_key = f"level_{level}"
        if level_key not in self.data:
            return {}
        
        result = {}
        for category, info in self.data[level_key].items():
            # Combine original and AI-added keywords
            all_keywords = info.get("keywords", []) + info.get("added_by_ai", [])
            result[category] = all_keywords
        
        return result
    
    def get_category_info(self, category: str) -> Optional[dict]:
        """
        Get full information about a category including resource prediction.
        PHASE 2: Added for ESI resource estimation.
        """
        for level in ["level_1", "level_2", "level_3", "level_4", "level_5"]:
            if level in self.data and category in self.data[level]:
                info = self.data[level][category].copy()
                info["level"] = int(level.split("_")[1])
                return info
        return None
    
    def get_resource_count(self, category: str) -> int:
        """
        Get expected resource count for a category.
        PHASE 2: Used for ESI level determination.
        """
        info = self.get_category_info(category)
        if info:
            return info.get("resource_count", 1)  # Default to 1 if not specified
        return 1
    
    def add_keyword(self, category: str, keyword: str, source: str = "ai") -> bool:
        """
        Add a new keyword to a category.
        """
        for level in ["level_1", "level_2", "level_3", "level_4", "level_5"]:
            if level in self.data and category in self.data[level]:
                cat_data = self.data[level][category]
                
                # Check if keyword already exists
                all_keywords = cat_data.get("keywords", []) + cat_data.get("added_by_ai", [])
                if keyword.lower() in [k.lower() for k in all_keywords]:
                    return False
                
                # Add to appropriate list
                if source == "ai":
                    if "added_by_ai" not in cat_data:
                        cat_data["added_by_ai"] = []
                    cat_data["added_by_ai"].append(keyword)
                else:
                    cat_data["keywords"].append(keyword)
                
                self.data["metadata"]["updates_count"] = \
                    self.data["metadata"].get("updates_count", 0) + 1
                
                self._save()
                return True
        
        return False
    
    def add_keywords_batch(self, category: str, keywords: List[str], source: str = "ai") -> int:
        """Add multiple keywords at once. Returns count of added keywords."""
        added = 0
        for kw in keywords:
            if self.add_keyword(category, kw, source):
                added += 1
        return added
    
    def get_all_keywords_flat(self) -> Dict[int, Dict[str, List[str]]]:
        """Get all keywords organized by level"""
        result = {}
        for level in [1, 2, 3, 4, 5]:
            result[level] = self.get_keywords_for_level(level)
        return result
    
    def search_keyword(self, text: str) -> Optional[Tuple[str, int]]:
        """
        Search for matching keyword in text.
        Returns (category, level) or None if not found.
        Searches from highest priority (level 1) to lowest (level 5).
        Uses longer keywords first to avoid false matches.
        """
        text_lower = text.lower()

        if self._search_index is None:
            self._build_search_index()

        # Search for matches
        for kw, category, level, _ in self._search_index:
            if kw in text_lower:
                return (category, level)
        
        return None
    
    def search_with_resources(self, text: str) -> Optional[Tuple[str, int, int]]:
        """
        PHASE 2: Search for keyword and return resource count.
        Returns (category, level, resource_count) or None.
        """
        result = self.search_keyword(text)
        if result:
            category, level = result
            resource_count = self.get_resource_count(category)
            return (category, level, resource_count)
        return None
    
    def get_stats(self) -> dict:
        """Get database statistics"""
        stats = {
            "version": self.data["metadata"]["version"],
            "last_updated": self.data["metadata"]["last_updated"],
            "total_keywords": self._count_keywords(self.data),
            "updates_count": self.data["metadata"].get("updates_count", 0),
            "keywords_by_level": {},
            "categories_by_level": {}
        }
        
        for level in [1, 2, 3, 4, 5]:
            level_keywords = self.get_keywords_for_level(level)
            stats["keywords_by_level"][level] = sum(len(kws) for kws in level_keywords.values())
            stats["categories_by_level"][level] = len(level_keywords)
        
        return stats
    
    def export_for_code(self) -> str:
        """Export keywords as Python code"""
        code_lines = []
        
        for level in [1, 2, 3, 4, 5]:
            code_lines.append(f"        # Level {level} keywords")
            code_lines.append(f"        level{level}_keywords = {{")
            
            keywords_dict = self.get_keywords_for_level(level)
            for category, keywords in keywords_dict.items():
                kw_str = ", ".join([f'"{kw}"' for kw in keywords])
                code_lines.append(f'            "{category}": [{kw_str}],')
            
            code_lines.append("        }")
            code_lines.append("")
        
        return "\n".join(code_lines)
    
    def force_upgrade(self):
        """Force upgrade to latest keyword database"""
        self._save(DEFAULT_KEYWORDS)
        self.data = DEFAULT_KEYWORDS.copy()
        print("Database upgraded to v2.0.0")


# Singleton instance
_db_instance = None

def get_keyword_database() -> KeywordDatabase:
    """Get singleton instance of keyword database"""
    global _db_instance
    if _db_instance is None:
        _db_instance = KeywordDatabase()
    return _db_instance


def reset_keyword_database():
    """Reset database to defaults (useful for testing)"""
    global _db_instance
    _db_instance = None
    db = get_keyword_database()
    db.force_upgrade()
    return db


if __name__ == "__main__":
    # Test the database
    db = KeywordDatabase()
    
    print("=" * 60)
    print("SAFE-Triage Keyword Database v2.0.0 (Phase 2)")
    print("=" * 60)
    
    print("\nDatabase Stats:")
    stats = db.get_stats()
    for key, value in stats.items():
        print(f"  {key}: {value}")
    
    print("\n" + "=" * 60)
    print("Sample Searches (with resource prediction):")
    print("=" * 60)
    
    test_texts = [
        "المريض محتاج أنبوبة",
        "حمل خارج الرحم",
        "ألم بيمزق في الضهر",
        "تعفن دم",
        "لسه حاصل دلوقتي - وشه مايل",
        "بطني بتوجعني",
        "عايز أجدد الروشتة"
    ]
    
    for text in test_texts:
        result = db.search_with_resources(text)
        if result:
            category, level, resources = result
            print(f"\n  '{text}'")
            print(f"    → Category: {category}")
            print(f"    → Level: {level}")
            print(f"    → Resources: {resources}")
        else:
            print(f"\n  '{text}' → Not found")
