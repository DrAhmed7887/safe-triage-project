#!/usr/bin/env python3
"""
Populate ICD-10 cache for offline mode using UMLS crosswalk.

Usage:
  python3 populate_icd10_cache.py
  python3 populate_icd10_cache.py --limit 200 --sleep 0.2
"""
import argparse
import sqlite3
import time
from typing import List

from umls_rag import UMLSMedicalRAG


def fetch_missing_codes(conn: sqlite3.Connection) -> List[str]:
    cursor = conn.execute(
        """
        SELECT concept_id
        FROM snomed_cache
        WHERE concept_id NOT IN (SELECT snomed_code FROM icd10_cache)
        ORDER BY concept_id
        """
    )
    return [row[0] for row in cursor.fetchall()]


def main():
    parser = argparse.ArgumentParser(description="Populate ICD-10 cache from UMLS.")
    parser.add_argument("--db", default="umls_cache.db", help="Path to sqlite cache db")
    parser.add_argument("--limit", type=int, default=None, help="Limit number of concepts")
    parser.add_argument("--sleep", type=float, default=0.1, help="Sleep between API calls (seconds)")
    parser.add_argument("--batch", type=int, default=100, help="Commit batch size")
    args = parser.parse_args()

    conn = sqlite3.connect(args.db)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS icd10_cache (
            snomed_code TEXT PRIMARY KEY,
            icd10_code TEXT NOT NULL,
            description TEXT NOT NULL,
            cached_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    missing = fetch_missing_codes(conn)
    if args.limit:
        missing = missing[: args.limit]

    total = len(missing)
    print(f"Found {total} SNOMED concepts missing ICD-10 cache")
    if total == 0:
        return

    rag = UMLSMedicalRAG(args.db)
    start = time.time()
    success = 0

    for idx, snomed_code in enumerate(missing, 1):
        icd10 = rag.get_icd10(snomed_code)
        conn.execute(
            "INSERT OR REPLACE INTO icd10_cache (snomed_code, icd10_code, description) VALUES (?, ?, ?)",
            (snomed_code, icd10.code, icd10.description),
        )
        success += 1

        if idx % args.batch == 0:
            conn.commit()
            elapsed = time.time() - start
            rate = idx / elapsed if elapsed else 0
            remaining = total - idx
            eta = remaining / rate if rate else 0
            print(
                f"[{idx}/{total}] cached | rate={rate:.2f}/s | eta={eta/60:.1f} min"
            )

        if args.sleep:
            time.sleep(args.sleep)

    conn.commit()
    elapsed = time.time() - start
    print(f"✅ Cached {success} ICD-10 mappings in {elapsed/60:.1f} min")


if __name__ == "__main__":
    main()
