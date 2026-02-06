"""Thread-safe UMLS RAG"""
import requests, sqlite3, threading
from typing import List
from dataclasses import dataclass

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
        self.cache_db = cache_db
        self.session = requests.Session()
        self._local = threading.local()
        self._has_term_ar = None
    
    @property
    def conn(self):
        if not hasattr(self._local, 'conn'):
            self._local.conn = sqlite3.connect(self.cache_db, check_same_thread=False)
            self._local.conn.row_factory = sqlite3.Row
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
        return [SNOMEDResult(r['concept_id'], r['term'], r['category'], r['esi_default'], bool(r['red_flag'])) for r in cursor.fetchall()]
    
    def get_icd10(self, snomed_code: str) -> ICD10Result:
        try:
            cursor = self.conn.execute(
                "SELECT icd10_code, description FROM icd10_cache WHERE snomed_code = ?",
                (snomed_code,),
            )
            row = cursor.fetchone()
            if row:
                return ICD10Result(row[0], row[1])
        except Exception:
            pass
        try:
            url = f"{self.BASE_URL}/crosswalk/current/source/SNOMEDCT_US/{snomed_code}"
            response = self.session.get(url, params={'apiKey': self.API_KEY, 'targetSource': 'ICD10CM'}, timeout=5)
            data = response.json()
            results = data.get('result') or []
            if results:
                best = max(results, key=lambda r: len(r.get('ui', '')))
                code = best.get('ui')
                if code == "I20":
                    code = "I20.9"
                return ICD10Result(code, best.get('name', ''))
        except:
            pass
        return ICD10Result("R69", "Illness, unspecified")
