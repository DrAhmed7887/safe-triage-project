#!/usr/bin/env python3
"""
Script to add ICD-10 codes to keywords_db.json
"""
import json
from icd10_mapping import ICD10_MAPPING

# Load existing keywords database
with open('keywords_db.json', 'r', encoding='utf-8') as f:
    keywords_db = json.load(f)

# Update metadata
keywords_db['metadata']['icd10_compliant'] = True
keywords_db['metadata']['icd10_version'] = "ICD-10-CM 2024"
keywords_db['metadata']['gahar_compliant'] = True

# Add ICD-10 codes to each category
for level in ['level_1', 'level_2', 'level_3', 'level_4', 'level_5']:
    if level in keywords_db:
        for category_key, category_data in keywords_db[level].items():
            if category_key in ICD10_MAPPING:
                icd_info = ICD10_MAPPING[category_key]
                category_data['icd10_code'] = icd_info['code']
                category_data['icd10_description'] = icd_info['description']
                category_data['icd10_category'] = icd_info['category']
            else:
                # Default fallback
                category_data['icd10_code'] = "R69"
                category_data['icd10_description'] = "Illness, unspecified"
                category_data['icd10_category'] = "Unspecified"

# Save updated database
with open('keywords_db.json', 'w', encoding='utf-8') as f:
    json.dump(keywords_db, f, ensure_ascii=False, indent=2)

print("✅ ICD-10 codes added to keywords_db.json")
print(f"   Total categories updated: {sum(len(keywords_db.get(f'level_{i}', {})) for i in range(1, 6))}")
