"""SQLite helpers for English clinical keyword enrichment."""

from __future__ import annotations

import json
import os
import sqlite3
from pathlib import Path
from typing import Dict, List, Optional

TABLE_NAME = "english_clinical_keywords"

CREATE_TABLE_SQL = f"""
CREATE TABLE IF NOT EXISTS {TABLE_NAME} (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    keyword_text TEXT NOT NULL UNIQUE,
    base_esi INTEGER NOT NULL,
    is_red_flag BOOLEAN DEFAULT 0,
    resource_estimate INTEGER DEFAULT 2,
    risk_tier TEXT,
    high_acuity_pct REAL,
    sample_size INTEGER
);
"""


def resolve_cache_db_path(cache_db: Optional[str] = None) -> Path:
    if cache_db:
        return Path(cache_db).expanduser().resolve()

    env_path = os.getenv("UMLS_CACHE_DB")
    if env_path:
        return Path(env_path).expanduser().resolve()

    here = Path(__file__).resolve()
    candidates = [
        here.parent.parent / "umls_cache.db",
        Path.cwd() / "umls_cache.db",
        Path("/app/umls_cache.db"),
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate.resolve()
    return candidates[0].resolve()


def ensure_table(conn: sqlite3.Connection) -> None:
    conn.execute(CREATE_TABLE_SQL)


def load_keywords_json_to_sqlite(
    json_path: Path,
    *,
    cache_db_path: Optional[Path] = None,
) -> int:
    payload = json.loads(Path(json_path).read_text())
    if not isinstance(payload, list):
        raise ValueError("english_clinical_keywords.json must contain a list")

    db_path = resolve_cache_db_path(str(cache_db_path) if cache_db_path else None)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    inserted = 0

    with sqlite3.connect(db_path) as conn:
        ensure_table(conn)
        for row in payload:
            if not isinstance(row, dict):
                continue
            keyword_text = str(row.get("keyword_text") or "").strip().lower()
            if not keyword_text:
                continue
            conn.execute(
                f"""
                INSERT OR REPLACE INTO {TABLE_NAME}
                (keyword_text, base_esi, is_red_flag, resource_estimate, risk_tier, high_acuity_pct, sample_size)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    keyword_text,
                    int(row.get("base_esi", 3)),
                    int(bool(row.get("is_red_flag", False))),
                    int(row.get("resource_estimate", 2)),
                    str(row.get("risk_tier") or ""),
                    float(row.get("high_acuity_pct", 0.0)),
                    int(row.get("sample_size", 0)),
                ),
            )
            inserted += 1
        conn.commit()
    return inserted


def load_keyword_index_from_sqlite(cache_db_path: Optional[Path] = None) -> Dict[str, Dict[str, object]]:
    db_path = resolve_cache_db_path(str(cache_db_path) if cache_db_path else None)
    if not db_path.exists():
        return {}

    with sqlite3.connect(db_path) as conn:
        ensure_table(conn)
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            f"""
            SELECT keyword_text, base_esi, is_red_flag, resource_estimate, risk_tier, high_acuity_pct, sample_size
            FROM {TABLE_NAME}
            """
        ).fetchall()
        return {
            str(row["keyword_text"]).strip().lower(): {
                "base_esi": int(row["base_esi"]),
                "is_red_flag": bool(row["is_red_flag"]),
                "resource_estimate": int(row["resource_estimate"] or 2),
                "risk_tier": str(row["risk_tier"] or ""),
                "high_acuity_pct": float(row["high_acuity_pct"] or 0.0),
                "sample_size": int(row["sample_size"] or 0),
            }
            for row in rows
        }


def keyword_row_count(cache_db_path: Optional[Path] = None) -> int:
    db_path = resolve_cache_db_path(str(cache_db_path) if cache_db_path else None)
    if not db_path.exists():
        return 0
    with sqlite3.connect(db_path) as conn:
        ensure_table(conn)
        row = conn.execute(f"SELECT COUNT(*) FROM {TABLE_NAME}").fetchone()
        return int(row[0]) if row else 0
