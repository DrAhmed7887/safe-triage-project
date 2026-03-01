#!/usr/bin/env python3
"""Load english_clinical_keywords.json into sqlite cache."""

from __future__ import annotations

import argparse
from pathlib import Path

from logic.english_keyword_sqlite import keyword_row_count, load_keywords_json_to_sqlite, resolve_cache_db_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Load English clinical keywords into SQLite")
    parser.add_argument(
        "--json",
        type=Path,
        default=Path(__file__).resolve().parent / "logic" / "english_clinical_keywords.json",
        help="Path to english_clinical_keywords.json",
    )
    parser.add_argument(
        "--db",
        type=Path,
        default=None,
        help="Path to sqlite DB (defaults to umls_cache.db resolution)",
    )
    args = parser.parse_args()

    db_path = resolve_cache_db_path(str(args.db) if args.db else None)
    inserted = load_keywords_json_to_sqlite(args.json, cache_db_path=db_path)
    total = keyword_row_count(cache_db_path=db_path)
    print(f"Loaded/updated rows: {inserted}")
    print(f"Total rows in english_clinical_keywords: {total}")
    print(f"SQLite DB: {db_path}")


if __name__ == "__main__":
    main()
