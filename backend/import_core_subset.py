"""Import SNOMED CT CORE subset into cache"""
import csv
import sqlite3
import zipfile
import os
from pathlib import Path

class CORESubsetImporter:
    def __init__(self, cache_db: str = "umls_cache.db"):
        self.cache_db = cache_db
        self.conn = sqlite3.connect(cache_db)
        self.conn.row_factory = sqlite3.Row
    
    def import_core_subset(self, zip_path: str):
        print(f"📦 Importing SNOMED CT CORE subset")
        
        # Extract
        extract_dir = Path(zip_path).parent / "CORE_EXTRACTED"
        extract_dir.mkdir(exist_ok=True)
        
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(extract_dir)
        
        # Find description file
        concepts_file = None
        for file in extract_dir.rglob("*Description*.txt"):
            if file.is_file():
                concepts_file = file
                break
        
        if not concepts_file:
            print("❌ Description file not found")
            return
        
        print(f"📄 Importing from {concepts_file.name}")
        
        # Import
        imported = 0
        with open(concepts_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f, delimiter='\t')
            
            for row in reader:
                if row['active'] == '1' and row['languageCode'] == 'en':
                    concept_id = row['conceptId']
                    term = row['term']
                    
                    # Map to category
                    category = self._map_category(term)
                    esi = self._get_esi(category)
                    red_flag = category in {'chest_pain_cardiac', 'respiratory_distress', 'stroke_symptoms', 'severe_trauma', 'severe_bleeding'}
                    
                    self.conn.execute("""
                    INSERT OR REPLACE INTO snomed_cache
                    (concept_id, term, category, esi_default, red_flag)
                    VALUES (?, ?, ?, ?, ?)
                    """, (concept_id, term, category, esi, int(red_flag)))
                    
                    imported += 1
                    if imported % 100 == 0:
                        print(f"  {imported} concepts...", end='\r')
        
        self.conn.commit()
        
        # Stats
        cursor = self.conn.execute("SELECT COUNT(*) FROM snomed_cache")
        total = cursor.fetchone()[0]
        print(f"\n✅ Imported {imported} concepts (total: {total})")
        
        size_mb = os.path.getsize(self.cache_db) / 1024 / 1024
        print(f"💾 Database size: {size_mb:.1f} MB")
    
    def _map_category(self, term: str) -> str:
        term_lower = term.lower()
        if any(x in term_lower for x in ['cardiac', 'chest pain', 'angina', 'myocardial', 'coronary']):
            return "chest_pain_cardiac"
        elif any(x in term_lower for x in ['dyspnea', 'respiratory', 'breathing']):
            return "respiratory_distress"
        elif any(x in term_lower for x in ['stroke', 'cerebrovascular', 'cva']):
            return "stroke_symptoms"
        elif any(x in term_lower for x in ['trauma', 'injury', 'fracture']):
            return "severe_trauma"
        elif any(x in term_lower for x in ['hemorrhage', 'bleeding']):
            return "severe_bleeding"
        elif any(x in term_lower for x in ['abdominal', 'abdomen']):
            return "abdominal_pain_moderate"
        else:
            return "unclear_needs_evaluation"
    
    def _get_esi(self, category: str) -> int:
        defaults = {
            "chest_pain_cardiac": 2,
            "respiratory_distress": 2,
            "stroke_symptoms": 1,
            "severe_trauma": 2,
            "severe_bleeding": 1,
            "altered_mental_status": 2,
            "abdominal_pain_moderate": 3,
            "unclear_needs_evaluation": 3
        }
        return defaults.get(category, 3)

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python3 import_core_subset.py <path_to_zip>")
        sys.exit(1)
    
    importer = CORESubsetImporter("umls_cache.db")
    importer.import_core_subset(sys.argv[1])
