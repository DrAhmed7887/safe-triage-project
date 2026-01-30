"""
SAFE-Triage - Dynamic Keyword Database
=======================================

A JSON-based keyword database that can be updated by the AI Teaching Agent.
This separates keywords from code, allowing continuous learning.

Author: Ahmed Zayed
"""

import os
import json
from typing import Dict, List, Optional
from datetime import datetime


# Default keywords - will be loaded into JSON if file doesn't exist
DEFAULT_KEYWORDS = {
    "metadata": {
        "version": "1.0.0",
        "last_updated": datetime.now().isoformat(),
        "total_keywords": 0,
        "updates_count": 0
    },
    "level_1": {
        "unconscious": {
            "keywords": ["unconscious", "unresponsive", "فاقد الوعي", "مغمى عليه", "مش بيرد",
                        "مش بيرد عليا", "مش واعي", "فاقد وعي", "مش بيرد خالص"],
            "added_by_ai": [],
            "priority": 1
        },
        "cardiac_arrest": {
            "keywords": ["cardiac arrest", "قلبه وقف", "القلب واقف", "قلبه مش شغال", "القلب توقف"],
            "added_by_ai": [],
            "priority": 1
        },
        "respiratory_arrest": {
            "keywords": ["not breathing", "مش بيتنفس", "توقف التنفس", "مش قادر يتنفس", "وقف نفسه",
                        "زرق", "شفايفه بنفسجي", "شفايفه زرقا", "cyanosis", "لونه أزرق"],
            "added_by_ai": [],
            "priority": 1
        },
        "active_seizure": {
            "keywords": ["seizure", "تشنج", "صرع", "بيترعش", "تشنجات", "نوبة صرع"],
            "added_by_ai": [],
            "priority": 1
        },
        "choking": {
            "keywords": ["choking", "شرقان", "حاجة في زوره", "مش قادر يبلع", "شرقت", "شرق",
                        "اختناق", "مش قادرة تاخد نفس", "حاجة واقفة في زوره", "شرق في أكل",
                        "بلع لعبة", "صوته مبحوح", "بلع جسم", "foreign body",
                        "اتخنق بالحبل", "شنق", "hanging", "near-hanging", "strangulation"],
            "added_by_ai": [],
            "priority": 1
        },
        "severe_trauma": {
            "keywords": ["gunshot", "stab", "طعن", "رصاص", "حادثة", "accident", "اتضرب",
                        "حادث سيارة", "اتطعن", "طلق ناري", "اتعلق في الكهربا", "كهربا",
                        "صعق", "electrocution", "حرق شديد", "حروق", "burn", "وقع من الدور",
                        "سقط من ارتفاع", "fall from height", "وقع من السلم", "وقع من البلكونة",
                        "وقع من فوق العمارة", "اتحرق بنار", "جلده طاير", "اتصعق",
                        "السكينة دخلت", "طعنة في صدره", "طعنة في بطنه", "العربية قلبت",
                        "حادث عربية", "MVA", "انقلاب", "car accident"],
            "added_by_ai": [],
            "priority": 1
        },
        "anaphylaxis": {
            "keywords": ["anaphylaxis", "صدمة تحسسية", "حساسية شديدة", "شفايفه ورمت",
                        "وشه ورم", "مش قادر يتنفس من الحساسية"],
            "added_by_ai": [],
            "priority": 1
        },
        "poisoning_overdose": {
            "keywords": ["overdose", "poison", "تسمم", "جرعة زيادة", "أخد دوا كتير",
                        "بلع دوا", "شرب دوا", "أخد حبوب كتير", "جرعة زايدة",
                        "شرب مبيد", "أكل سم", "تسمم غذائي", "بلع بطاريات", "بلع حاجة",
                        "بلع عملة", "ابتلاع جسم غريب", "swallowed", "بلع كلور",
                        "شرب كلور", "سم فئران", "شرب سم", "مبيد حشري",
                        "ماء نار", "شرب ماء نار", "علبة باراسيتامول", "أخد علبة",
                        "لدغة عقرب", "لدغته عقرب", "عضه تعبان", "عضة تعبان",
                        "snake bite", "scorpion", "شرب كلوركس", "بلع دبوس",
                        "بلع إبرة", "بلع مسمار"],
            "added_by_ai": [],
            "priority": 1
        },
        "drowning": {
            "keywords": ["drowning", "drown", "غرق", "غرقان", "طلعوه من المية", "وقع في المية",
                        "حمام السباحة", "البحر", "النيل", "غرق في"],
            "added_by_ai": [],
            "priority": 1
        },
        "severe_bleeding": {
            "keywords": ["severe bleeding", "نزيف شديد", "بينزف جامد", "دم كتير",
                        "نزيف مش بيوقف", "دم كتير جداً", "الدم مش بيوقف",
                        "حامل والدم", "hemorrhage"],
            "added_by_ai": [],
            "priority": 1
        }
    },
    "level_2": {
        "chest_pain_cardiac": {
            "keywords": ["chest pain", "ألم صدر", "صدري بيوجعني", "قلبي بيوجعني",
                        "ألم في صدري", "صدري", "وجع قلب", "قلبي بيضرب غلط",
                        "خفقان", "palpitations", "قلبي هيقف", "صدره بيوجعه",
                        "باين عليه تعبان", "صدره تاعبه"],
            "added_by_ai": [],
            "priority": 2
        },
        "stroke_symptoms": {
            "keywords": ["stroke", "جلطة", "شلل", "مش قادر يتكلم", "وشه مايل",
                        "جلطة دماغية", "نص جسمه", "ايده مش بتتحرك", "بيشوف ضلم",
                        "بقع سودا", "فقد البصر", "vision loss", "sudden blindness",
                        "مش شايف", "فجأة مش شايف", "نص وشه وقع", "وشه وقع",
                        "مش قادر يرفع ايده", "ايده وقعت", "رجله وقعت",
                        "مش قادر يمشي", "فجأة مش قادر يمشي", "رجله سودت",
                        "اتنملت", "acute limb ischemia"],
            "added_by_ai": [],
            "priority": 2
        },
        "respiratory_distress": {
            "keywords": ["can't breathe", "مش عارف آخد نفسي", "ضيق تنفس",
                        "مش قادرة آخد نفسي", "صعوبة تنفس", "نفسي ضيق", "بيتنهج",
                        "عندها ربو", "عنده ربو", "مش قادرة تتنفس", "مش قادر يتنفس",
                        "ربو", "asthma"],
            "added_by_ai": [],
            "priority": 2
        },
        "suicidal_homicidal": {
            "keywords": ["suicidal", "kill myself", "عايز أموت", "عايز يموت",
                        "يقتل نفسه", "عايز يقتل نفسه", "ينتحر", "عايز ينتحر",
                        "هيأذي نفسه", "مش عايز يعيش", "انتحار", "يشنق نفسه",
                        "ناوي يشنق", "يرمي نفسه", "عايز يموت نفسه",
                        "عايز يضرب نفسه", "يأذي نفسه", "self-harm"],
            "added_by_ai": [],
            "priority": 2
        },
        "obstetric_emergency": {
            "keywords": ["pregnant bleeding", "حامل بتنزف", "حامل وبتنزف",
                        "حامل في", "حامل ونزيف", "نزيف حمل", "الحمل بينزف",
                        "حامل والمية نزلت", "ولادة مبكرة"],
            "added_by_ai": [],
            "priority": 2
        },
        "diabetic_emergency": {
            "keywords": ["sugar low", "السكر واطي", "السكر عالي", "سكر منخفض",
                        "عنده سكر وبيترعش", "هبوط سكر", "غيبوبة سكر",
                        "سكر وبيرتعش", "عنده سكر وتعبان"],
            "added_by_ai": [],
            "priority": 2
        },
        "severe_headache": {
            "keywords": ["worst headache", "صداع شديد", "راسي هتنفجر", "صداع مفاجئ",
                        "صداع شديد جداً", "أسوأ صداع", "رقبته متيبسة", "رقبة متيبسة",
                        "stiff neck", "meningitis", "صداع ورقبته", "thunderclap",
                        "صداع زي ما حد ضربها", "صداع زي الضرب", "صداع فجأة",
                        "راسه بتوجعه جامد", "راسه بتوجعه وبيرجع"],
            "added_by_ai": [],
            "priority": 2
        },
        "severe_pain": {
            "keywords": ["severe pain", "ألم شديد", "بيوجعني جدا جدا", "ألم شديد جداً",
                        "وجع مش طبيعي", "ألم رهيب", "بطنه منفوخة", "بطنه قاسية",
                        "rigid abdomen", "زي الحجر", "surgical abdomen"],
            "added_by_ai": [],
            "priority": 2
        },
        "high_fever_toxic": {
            "keywords": ["سخونية عالية جداً", "حرارة عالية جداً", "معياش جداً",
                        "حرارة 40", "سخن جداً وتعبان"],
            "added_by_ai": [],
            "priority": 2
        },
        "altered_mental_status": {
            "keywords": ["confused", "مش عارف مكانه", "تايه", "مش بيعرفني",
                        "مش فاكر حاجة", "تغير وعي", "بيتكلم مع ناس مش موجودة",
                        "بيهلوس", "hallucinations", "بيشوف حاجات", "هلوسة",
                        "مش عارف هو فين", "disoriented", "كلام غريب",
                        "بتتكلم كلام غريب", "مش عارفاني", "مش عارفني"],
            "added_by_ai": [],
            "priority": 2
        },
        "testicular_pain": {
            "keywords": ["testicular", "خصية", "خصيته", "الخصية بتوجع"],
            "added_by_ai": [],
            "priority": 2
        },
        "dvt_pe": {
            "keywords": ["رجله سخنة وحمرا", "متورمة وحمرا", "DVT", "جلطة في الرجل",
                        "ساقه متورمة", "leg swollen red hot", "pulmonary embolism"],
            "added_by_ai": [],
            "priority": 2
        },
        "hemoptysis": {
            "keywords": ["كحة بدم", "بيكح دم", "coughing blood", "hemoptysis",
                        "دم مع الكحة", "بصق دم", "اتقيأ دم", "رجع دم",
                        "قيء دم", "دم أسود", "coffee ground", "hematemesis"],
            "added_by_ai": [],
            "priority": 2
        }
    },
    "level_3": {
        "abdominal_pain_moderate": {
            "keywords": ["abdominal pain", "stomach pain", "ألم بطن", "بطني بتوجعني",
                        "معدتي", "مغص", "وجع بطن", "ألم في بطني"],
            "added_by_ai": [],
            "priority": 3
        },
        "fever_with_symptoms": {
            "keywords": ["fever", "سخونية", "حرارة", "سخن", "حمى", "جسمه سخن"],
            "added_by_ai": [],
            "priority": 3
        },
        "vomiting_dehydration": {
            "keywords": ["vomiting", "بيرجع", "استفراغ", "ترجيع", "قيء", "رجع كتير"],
            "added_by_ai": [],
            "priority": 3
        },
        "moderate_bleeding": {
            "keywords": ["bleeding", "بينزف", "نزيف", "دم", "جرح بينزف", "جرح كبير",
                        "غرز كتير", "محتاج غرز كتير"],
            "added_by_ai": [],
            "priority": 3
        },
        "fracture_deformity": {
            "keywords": ["fracture", "broken", "كسر", "مكسور", "ملوي", "اتكسرت",
                        "شكلها مش طبيعي", "عظم طالع"],
            "added_by_ai": [],
            "priority": 3
        },
        "pediatric_distress": {
            "keywords": ["child sick", "طفل", "ابني", "بنتي", "الطفل تعبان",
                        "البيبي", "رضيع"],
            "added_by_ai": [],
            "priority": 3
        },
        "moderate_dyspnea": {
            "keywords": ["short of breath", "ضيق نفس خفيف", "نفسي تعبني شوية"],
            "added_by_ai": [],
            "priority": 3
        },
        "chest_pain_noncardiac": {
            "keywords": ["chest pain breathing", "صدري بيوجع لما بتنفس", "ألم صدر مع التنفس"],
            "added_by_ai": [],
            "priority": 3
        }
    },
    "level_4": {
        "minor_trauma": {
            "keywords": ["fell", "fall", "وقعت", "وقع", "اتخبط", "خبطة", "ضربة", "وارم", "ورم"],
            "added_by_ai": [],
            "priority": 4
        },
        "laceration_simple": {
            "keywords": ["cut", "laceration", "جرح", "قطع", "خياطة", "غرز", "جرح بسيط"],
            "added_by_ai": [],
            "priority": 4
        },
        "uri_symptoms": {
            "keywords": ["cold", "flu", "cough", "برد", "كحة", "زكام", "رشح", "انفلونزا"],
            "added_by_ai": [],
            "priority": 4
        },
        "sore_throat": {
            "keywords": ["sore throat", "زور", "حلق", "بلع", "زوري بيوجعني", "التهاب حلق"],
            "added_by_ai": [],
            "priority": 4
        },
        "earache": {
            "keywords": ["ear pain", "earache", "ودني", "أذني", "ألم أذن"],
            "added_by_ai": [],
            "priority": 4
        },
        "uti_symptoms": {
            "keywords": ["burning urination", "حرقان بول", "التهاب مجرى", "حرقان في البول",
                        "رايح الحمام كتير", "بول كتير", "التهاب بولي"],
            "added_by_ai": [],
            "priority": 4
        },
        "mild_allergic": {
            "keywords": ["rash", "allergy", "حساسية", "طفح", "حكة", "هرش", "جلدي"],
            "added_by_ai": [],
            "priority": 4
        },
        "back_pain_chronic": {
            "keywords": ["back pain", "ظهري", "وجع ضهر", "ألم ظهر", "ضهري بيوجعني"],
            "added_by_ai": [],
            "priority": 4
        },
        "mild_gi": {
            "keywords": ["diarrhea", "إسهال", "مشي", "معدة", "بطني ماشية"],
            "added_by_ai": [],
            "priority": 4
        },
        "mild_pain": {
            "keywords": ["pain", "وجع", "بيوجعني", "ألم"],
            "added_by_ai": [],
            "priority": 4
        },
        "headache_mild": {
            "keywords": ["headache", "صداع", "راسي", "دماغي", "صداع خفيف"],
            "added_by_ai": [],
            "priority": 4
        },
        "eye_complaint": {
            "keywords": ["عيني", "عين", "حمرا", "مدمعة", "رمد", "العين"],
            "added_by_ai": [],
            "priority": 4
        },
        "dental": {
            "keywords": ["ضرس", "سنة", "أسنان", "tooth", "dental", "ضرسي بيوجعني"],
            "added_by_ai": [],
            "priority": 4
        },
        "skin_fungal": {
            "keywords": ["فطريات", "fungus", "tinea", "فطر"],
            "added_by_ai": [],
            "priority": 4
        },
        "hiccups": {
            "keywords": ["زغطة", "hiccups", "فواق"],
            "added_by_ai": [],
            "priority": 4
        }
    },
    "level_5": {
        "prescription_refill": {
            "keywords": ["refill", "prescription", "روشتة", "تجديد", "الدوا خلص", "عايز دوا",
                        "أجدد الروشتة"],
            "added_by_ai": [],
            "priority": 5
        },
        "medical_certificate": {
            "keywords": ["certificate", "تقرير", "شهادة", "إجازة مرضية", "تقرير طبي",
                        "أجيب تقرير", "ورقة عذر", "عذر للمدرسة", "medical records"],
            "added_by_ai": [],
            "priority": 5
        },
        "suture_removal": {
            "keywords": ["remove stitches", "فك غرز", "فك الغرز", "أفك الغرز", "شيل الغرز"],
            "added_by_ai": [],
            "priority": 5
        },
        "chronic_stable": {
            "keywords": ["follow up", "متابعة", "كشف", "المتابعة العادية", "نتيجة التحليل",
                        "أسأل عن نتيجة", "نتيجة أشعة", "ميعاد العملية", "أسأل عن ميعاد",
                        "استفسار", "appointment", "أقيس الضغط", "قياس ضغط",
                        "قياس السكر"],
            "added_by_ai": [],
            "priority": 5
        },
        "minor_complaint": {
            "keywords": ["check up", "فحص", "اطمن", "عايز اطمن", "حاجة بسيطة", "تطعيم",
                        "vaccination", "عايز تحليل", "محتاج تحليل", "تحليل دم عادي",
                        "عايز أعمل تحليل", "حقنة تيتانوس", "tetanus shot",
                        "أظافر نابتة", "ingrown nail"],
            "added_by_ai": [],
            "priority": 5
        }
    }
}


class KeywordDatabase:
    """
    Dynamic keyword database that can be updated by AI Teaching Agent.
    Stores keywords in a JSON file for persistence.
    """
    
    def __init__(self, db_path: str = None):
        if db_path is None:
            db_path = os.path.join(
                os.path.dirname(__file__),
                "keywords_db.json"
            )
        self.db_path = db_path
        self.data = self._load_or_create()
    
    def _load_or_create(self) -> dict:
        """Load existing database or create new one"""
        if os.path.exists(self.db_path):
            try:
                with open(self.db_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
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
    
    def add_keyword(self, category: str, keyword: str, source: str = "ai") -> bool:
        """
        Add a new keyword to a category.
        
        Args:
            category: The category to add to (e.g., "choking", "chest_pain_cardiac")
            keyword: The keyword to add
            source: "ai" for AI-added, "manual" for human-added
        
        Returns:
            True if added, False if already exists
        """
        # Find which level contains this category
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
                
                # Update count
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
    
    def search_keyword(self, text: str) -> Optional[tuple]:
        """
        Search for matching keyword in text.
        Returns (category, level) or None if not found.
        Searches from highest priority (level 1) to lowest (level 5).
        Uses longer keywords first to avoid false matches.
        """
        text_lower = text.lower()
        
        # Collect all keywords with their info, sorted by length (longest first)
        all_keywords = []
        for level in [1, 2, 3, 4, 5]:
            keywords_dict = self.get_keywords_for_level(level)
            for category, keywords in keywords_dict.items():
                for kw in keywords:
                    all_keywords.append((kw.lower(), category, level, len(kw)))
        
        # Sort by length (longest first) then by level (lowest number = highest priority)
        all_keywords.sort(key=lambda x: (-x[3], x[2]))
        
        # Search for matches
        for kw, category, level, _ in all_keywords:
            # Skip very short keywords that could cause false matches
            if len(kw) < 3:
                continue
            if kw in text_lower:
                return (category, level)
        
        return None
    
    def get_stats(self) -> dict:
        """Get database statistics"""
        stats = {
            "version": self.data["metadata"]["version"],
            "last_updated": self.data["metadata"]["last_updated"],
            "total_keywords": self._count_keywords(self.data),
            "updates_count": self.data["metadata"].get("updates_count", 0),
            "keywords_by_level": {}
        }
        
        for level in [1, 2, 3, 4, 5]:
            level_keywords = self.get_keywords_for_level(level)
            stats["keywords_by_level"][level] = sum(len(kws) for kws in level_keywords.values())
        
        return stats
    
    def export_for_code(self) -> str:
        """Export keywords as Python code for embedding in deterministic_triage.py"""
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


# Singleton instance
_db_instance = None

def get_keyword_database() -> KeywordDatabase:
    """Get singleton instance of keyword database"""
    global _db_instance
    if _db_instance is None:
        _db_instance = KeywordDatabase()
    return _db_instance


if __name__ == "__main__":
    # Test the database
    db = KeywordDatabase()
    
    print("Keyword Database Stats:")
    stats = db.get_stats()
    for key, value in stats.items():
        print(f"  {key}: {value}")
    
    print("\nSample search:")
    test_texts = [
        "المريض غرق في حمام السباحة",
        "عايز يقتل نفسه",
        "بطني بتوجعني",
        "عايز أجدد الروشتة"
    ]
    
    for text in test_texts:
        result = db.search_keyword(text)
        if result:
            print(f"  '{text}' → {result[0]} (Level {result[1]})")
        else:
            print(f"  '{text}' → Not found")
