"""Thread-safe UMLS RAG with semantic SNOMED/ICD guardrails."""

import os
import sqlite3
import threading
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import requests


TRAUMA_SNOMED_CODES = {
    "95659009",   # Post-traumatic headache
    "54012000",   # Posttraumatic headache (finding)
    "82271004",   # Injury of head
    "417163006",  # Traumatic injury
    "263204007",  # Fracture
}

TRAUMA_KEYWORDS = [
    "trauma",
    "fall",
    "accident",
    "injury",
    "hit",
    "hit head",
    "car crash",
    "mva",
    "سقوط",
    "حادث",
    "اصابه",
    "إصابة",
    "ضربة",
    "خبطت",
    "اتخبطت",
]

SYMPTOM_PARENT_FALLBACKS = {
    "95659009": "25064002",  # Post-traumatic headache -> Headache
    "54012000": "25064002",  # Posttraumatic headache -> Headache
    "82271004": "25064002",  # Injury of head -> Headache (symptom fallback)
}

SYMPTOM_TEXT_TO_SNOMED = [
    (["headache", "صداع"], "25064002"),
    (["nosebleed", "epistaxis", "nasal bleeding", "رعاف", "نزيف الانف", "نزيف الأنف"], "12441001"),
    (["chest pain", "الم صدر", "ألم صدر", "صدري"], "29857009"),
    (["abdominal pain", "stomach pain", "الم بطن", "ألم بطن", "بطني"], "21522001"),
    (["dyspnea", "shortness of breath", "ضيق نفس", "نهجان", "مش قادر اتنفس", "مش قادر أتنفس"], "267036007"),
    (["heartburn", "حرقان", "حموضة"], "16331000"),
    (["stroke", "جلطة", "جلطة في المخ", "سكتة", "سكتة دماغية"], "230690007"),
    (["aphasia", "cannot speak", "can't speak", "unable to speak", "مش قادر اتكلم", "فقدان النطق", "فقدان الكلام"], "87486003"),
    (["dysarthria", "slurred speech", "كلامي مش واضح", "لساني تقيل", "لسانه تقيل"], "29040004"),
    (["facial droop", "face drooping", "وشي مايل", "وشه مايل", "نص وشي وقع", "نص وشه وقع"], "95820000"),
    (["hemiplegia", "one side weakness", "one sided weakness", "نص جسمي مش بيتحرك", "نص جسمه مش بيتحرك"], "50582007"),
]

SYMPTOM_ICD10_MAP = {
    "25064002": "R51",       # Headache
    "250555004": "R51",      # Headache disorder (legacy cache entry)
    "12441001": "R04.0",     # Epistaxis
    "21522001": "R10.4",     # Abdominal pain
    "29857009": "R07.9",     # Chest pain
    "267036007": "R06.0",    # Dyspnea
    "16331000": "R12",       # Heartburn
    "87486003": "R47.01",    # Aphasia
    "29040004": "R47.1",     # Dysarthria
    "230690007": "I63.9",    # Cerebral infarction, unspecified
    "50582007": "G81.90",    # Hemiplegia, unspecified
    "95820000": "R29.810",   # Facial weakness
}

ICD10_DESCRIPTION_MAP = {
    "R51": "Headache",
    "R04.0": "Epistaxis",
    "R10.4": "Abdominal pain, unspecified",
    "R07.9": "Chest pain, unspecified",
    "R06.0": "Dyspnea",
    "R12": "Heartburn",
    "R47.01": "Aphasia",
    "R47.1": "Dysarthria and anarthria",
    "I63.9": "Cerebral infarction, unspecified",
    "G81.90": "Hemiplegia, unspecified",
    "R29.810": "Facial weakness",
    "R69": "Illness, unspecified",
}


@dataclass
class SNOMEDResult:
    concept_id: str
    term: str
    category: str
    esi_default: int
    red_flag: bool


@dataclass
class ICD10Result:
    code: str
    description: str


class UMLSMedicalRAG:
    BASE_URL = "https://uts-ws.nlm.nih.gov/rest"
    API_KEY = "af6da465-b936-4b0c-8238-fc6466988571"

    def __init__(self, cache_db: str = "umls_cache.db"):
        self.cache_db = self._resolve_db_path(cache_db)
        self.session = requests.Session()
        self._local = threading.local()
        self._has_term_ar = None

    def _resolve_db_path(self, cache_db: str) -> str:
        """Resolve sqlite path across local/dev and Cloud Run working dirs."""
        candidate = os.path.expanduser(str(cache_db))
        if os.path.isabs(candidate):
            return candidate

        # 1) Current working directory (legacy behavior)
        cwd_path = os.path.abspath(candidate)
        if os.path.exists(cwd_path):
            return cwd_path

        # 2) Next to this file (backend/umls_cache.db in container)
        module_path = os.path.join(os.path.dirname(__file__), candidate)
        if os.path.exists(module_path):
            return module_path

        # 3) Fallback to module path to avoid creating DB in unexpected cwd
        return module_path

    def _ensure_schema(self) -> None:
        """
        Ensure required cache tables exist.
        This prevents AI triage from failing hard if cache file is missing/corrupt.
        """
        self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS snomed_cache (
                concept_id TEXT PRIMARY KEY,
                term TEXT,
                category TEXT,
                esi_default INTEGER,
                red_flag INTEGER DEFAULT 0,
                cached_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                term_ar TEXT
            )
            """
        )
        self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS icd10_cache (
                snomed_code TEXT PRIMARY KEY,
                icd10_code TEXT NOT NULL,
                description TEXT NOT NULL,
                cached_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        self.conn.commit()

    @property
    def conn(self):
        if not hasattr(self._local, "conn"):
            self._local.conn = sqlite3.connect(self.cache_db, check_same_thread=False)
            self._local.conn.row_factory = sqlite3.Row
            self._ensure_schema()
            try:
                self._local.conn.execute("SELECT 1 FROM snomed_cache LIMIT 1")
            except sqlite3.OperationalError:
                self._ensure_schema()
                print("⚠️ snomed_cache table was missing — created empty table", flush=True)
        return self._local.conn

    def _check_term_ar(self) -> bool:
        if self._has_term_ar is not None:
            return self._has_term_ar
        try:
            cursor = self.conn.execute("PRAGMA table_info(snomed_cache)")
            cols = {row[1] for row in cursor.fetchall()}
            self._has_term_ar = "term_ar" in cols
        except Exception:
            self._has_term_ar = False
        return self._has_term_ar

    def search_snomed(self, symptom: str) -> List[SNOMEDResult]:
        like = f"%{symptom}%"
        try:
            if self._check_term_ar():
                cursor = self.conn.execute(
                    "SELECT * FROM snomed_cache WHERE term LIKE ? OR term_ar LIKE ? ORDER BY red_flag DESC LIMIT 5",
                    (like, like),
                )
            else:
                cursor = self.conn.execute(
                    "SELECT * FROM snomed_cache WHERE term LIKE ? ORDER BY red_flag DESC LIMIT 5",
                    (like,),
                )
            return [
                SNOMEDResult(
                    r["concept_id"],
                    r["term"],
                    r["category"],
                    r["esi_default"],
                    bool(r["red_flag"]),
                )
                for r in cursor.fetchall()
            ]
        except sqlite3.OperationalError as exc:
            # Do not crash AI path when cache schema/file is broken.
            print(f"⚠️ SNOMED cache lookup failed, returning empty results: {exc}", flush=True)
            self._ensure_schema()
            return []

    def get_snomed_result(self, concept_id: str) -> Optional[SNOMEDResult]:
        try:
            cursor = self.conn.execute(
                "SELECT * FROM snomed_cache WHERE concept_id = ? LIMIT 1",
                (str(concept_id).strip(),),
            )
            row = cursor.fetchone()
            if not row:
                return None
            return SNOMEDResult(
                row["concept_id"],
                row["term"],
                row["category"],
                row["esi_default"],
                bool(row["red_flag"]),
            )
        except Exception:
            return None

    def lookup_snomed_term(self, concept_id: str) -> Optional[str]:
        result = self.get_snomed_result(concept_id)
        return result.term if result else None

    @staticmethod
    def _flatten_text(extracted_features: Dict[str, Any]) -> str:
        complaint = str(extracted_features.get("chief_complaint", "") or "")
        symptoms = extracted_features.get("symptoms") or extracted_features.get("extracted_symptoms") or []
        symptom_text = " ".join(str(item) for item in symptoms)
        return f"{complaint} {symptom_text}".replace("أ", "ا").lower()

    def has_trauma_evidence(self, extracted_features: Dict[str, Any]) -> bool:
        text = self._flatten_text(extracted_features)
        return any(keyword in text for keyword in TRAUMA_KEYWORDS)

    def _infer_symptom_code_from_text(self, text: str) -> Optional[str]:
        normalized = (text or "").replace("أ", "ا").lower()
        for tokens, code in SYMPTOM_TEXT_TO_SNOMED:
            if any(token in normalized for token in tokens):
                return code
        return None

    def get_parent_symptom_code(
        self,
        snomed_code: str,
        extracted_features: Optional[Dict[str, Any]] = None,
    ) -> str:
        code = str(snomed_code or "").strip()
        if code in SYMPTOM_PARENT_FALLBACKS:
            return SYMPTOM_PARENT_FALLBACKS[code]

        if extracted_features:
            inferred = self._infer_symptom_code_from_text(self._flatten_text(extracted_features))
            if inferred:
                return inferred
        return code

    def validate_snomed_mapping(
        self,
        snomed_code: str,
        extracted_features: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Reject SNOMED codes that require evidence not present in complaint text."""
        code = str(snomed_code or "").strip()
        if not code:
            return code

        features = extracted_features or {}
        if code in TRAUMA_SNOMED_CODES and not self.has_trauma_evidence(features):
            return self.get_parent_symptom_code(code, features)
        return code

    def lookup_icd10_from_snomed(self, snomed_code: str) -> Optional[str]:
        code = str(snomed_code or "").strip()
        if not code:
            return None
        try:
            cursor = self.conn.execute(
                "SELECT icd10_code FROM icd10_cache WHERE snomed_code = ? LIMIT 1",
                (code,),
            )
            row = cursor.fetchone()
            if row:
                resolved = str(row[0] or "").strip().upper()
                if resolved and resolved != "R69":
                    return resolved
        except Exception:
            pass
        mapped = SYMPTOM_ICD10_MAP.get(code)
        return mapped if mapped and mapped != "R69" else None

    def _resolve_icd10_result(self, snomed_code: str, code: str, description: str) -> ICD10Result:
        resolved_code = str(code or "").strip().upper() or "R69"
        if resolved_code == "I20":
            resolved_code = "I20.9"

        preferred_symptom_code = SYMPTOM_ICD10_MAP.get(str(snomed_code or "").strip())
        if preferred_symptom_code:
            return ICD10Result(
                preferred_symptom_code,
                ICD10_DESCRIPTION_MAP.get(preferred_symptom_code, "Symptom code"),
            )

        if resolved_code == "R69":
            specific_code = self.lookup_icd10_from_snomed(snomed_code)
            if specific_code and specific_code != "R69":
                return ICD10Result(
                    specific_code,
                    ICD10_DESCRIPTION_MAP.get(specific_code, "Symptom code"),
                )

        resolved_description = str(description or "").strip()
        if not resolved_description:
            resolved_description = ICD10_DESCRIPTION_MAP.get(resolved_code, "Illness, unspecified")
        return ICD10Result(resolved_code, resolved_description)

    def get_icd10(self, snomed_code: str) -> ICD10Result:
        try:
            cursor = self.conn.execute(
                "SELECT icd10_code, description FROM icd10_cache WHERE snomed_code = ?",
                (snomed_code,),
            )
            row = cursor.fetchone()
            if row:
                return self._resolve_icd10_result(snomed_code, row[0], row[1])
        except Exception:
            pass
        try:
            url = f"{self.BASE_URL}/crosswalk/current/source/SNOMEDCT_US/{snomed_code}"
            response = self.session.get(
                url,
                params={"apiKey": self.API_KEY, "targetSource": "ICD10CM"},
                timeout=5,
            )
            data = response.json()
            results = data.get("result") or []
            if results:
                best = max(results, key=lambda r: len(r.get("ui", "")))
                return self._resolve_icd10_result(
                    snomed_code=snomed_code,
                    code=best.get("ui"),
                    description=best.get("name", ""),
                )
        except Exception:
            pass

        specific_code = self.lookup_icd10_from_snomed(snomed_code)
        if specific_code:
            return ICD10Result(
                specific_code,
                ICD10_DESCRIPTION_MAP.get(specific_code, "Symptom code"),
            )
        return ICD10Result("R69", "Illness, unspecified")
