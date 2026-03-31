"""
MIETIC Dataset Loader
=====================
Loads and validates the MIMIC-IV-ED Triage Instruction Corpus (MIETIC).

Two sub-datasets:
  1. MIETIC Main Corpus (MIETIC.csv)
     - 165,580 instruction-tuning examples
     - 3 columns: instruction, input, output
     - ESI level encoded in the instruction text:
       * ESI 1: "immediate life-saving interventions"
       * ESI 2: "ESI Level 2 criteria"
       * ESI 3-5: "resources likely required" (exact ESI not distinguishable)

  2. MIETIC Validated Samples (MIETIC-validate-samples.csv)
     - 50 cases with expert review (36 RETAIN, 14 REMOVE)
     - 57 columns including vitals, acuity, intervention flags, expert opinions
     - This is the gold-standard benchmark subset

Data source: mimic-iv-ext-triage-instruction-corpus-1.0.0/
"""

from __future__ import annotations

import csv
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DEFAULT_MIETIC_DIR = "mimic-iv-ext-triage-instruction-corpus-1.0.0"
MAIN_CORPUS_FILE = "MIETIC.csv"
VALIDATE_SAMPLES_FILE = "MIETIC-validate-samples.csv"

# Required columns for the validated samples file
VALIDATE_REQUIRED_COLUMNS = frozenset({
    "subject_id", "stay_id", "acuity", "chiefcomplaint",
    "heartrate", "resprate", "o2sat", "sbp", "dbp", "temperature",
    "pain", "gender", "age", "tiragecase",
    "Expert 1 Opinion", "Expert 2 Opinion", "Final Decision",
})

# Instruction text patterns that map to ESI levels
_ESI1_PATTERN = "immediate life-saving interventions"
_ESI2_PATTERN = "ESI Level 2"
_ESI_RESOURCE_PATTERN = "resources likely required"


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class MIETICCorpusEntry:
    """One row from the main MIETIC instruction-tuning corpus."""
    instruction: str
    input_text: str
    output_text: str
    esi_band: str  # "1", "2", or "3-5"


@dataclass(frozen=True)
class MIETICValidatedCase:
    """One expert-validated case from MIETIC-validate-samples.csv."""
    subject_id: int
    stay_id: int
    acuity: int  # ESI 1-5 (ground truth from original triage)
    chief_complaint: str
    triage_case: str  # Full clinical vignette

    # Demographics
    age: float
    gender: str  # "M" or "F"
    arrival_transport: str
    disposition: str

    # Vitals (nullable — some cases have missing vitals)
    heartrate: Optional[float]
    resprate: Optional[float]
    o2sat: Optional[float]
    sbp: Optional[float]
    dbp: Optional[float]
    temperature: Optional[float]
    pain: Optional[str]  # Can be numeric or "Critical", "uta", etc.

    # Intervention flags (binary 0/1)
    invasive_ventilation: int
    transfer_to_icu_in_1h: int
    transfer_to_icu_beyond_1h: int
    expired_within_1h: int
    expired_beyond_1h: int
    critical_procedure: int
    tier1_med_usage_1h: int

    # Resource counts
    lab_event_count: int
    resources_used: int

    # Expert validation
    expert_1_opinion: str  # AGREE / DISAGREE / UNCERTAIN / ""
    expert_2_opinion: str
    expert_3_opinion: str
    final_decision: str  # RETAIN / REMOVE


# ---------------------------------------------------------------------------
# Schema validation
# ---------------------------------------------------------------------------

class MIETICSchemaError(Exception):
    """Raised when MIETIC files have unexpected schema."""
    pass


def _strip_bom_from_columns(columns: list[str]) -> list[str]:
    """
    Strip BOM artifacts from column names.

    The MIETIC-validate-samples.csv has a corrupted BOM prefix on the first
    column: the UTF-8 BOM (EF BB BF) was double-encoded into Chinese
    characters '锘縮' which also consumed the leading 's' of 'subject_id',
    resulting in '锘縮ubject_id'. We strip non-ASCII prefix and restore
    the known column name.
    """
    if not columns:
        return columns
    first = columns[0]
    # Strip any non-ASCII prefix (BOM, double-encoded BOM, etc.)
    cleaned = re.sub(r'^[^\x00-\x7f]+', '', first)
    # The corruption eats the leading 's' from 'subject_id' -> 'ubject_id'
    # Restore it if we detect this specific known corruption pattern
    if cleaned == "ubject_id":
        cleaned = "subject_id"
    return [cleaned] + columns[1:]


def _validate_corpus_header(columns: list[str]) -> None:
    """Validate the main corpus CSV has the expected 3 columns."""
    expected = {"instruction", "input", "output"}
    actual = set(columns)
    if not expected.issubset(actual):
        missing = expected - actual
        raise MIETICSchemaError(
            f"MIETIC main corpus missing columns: {missing}. "
            f"Found: {actual}"
        )


def _validate_samples_header(columns: list[str]) -> None:
    """Validate the validated samples CSV has all required columns."""
    actual = set(columns)
    missing = VALIDATE_REQUIRED_COLUMNS - actual
    if missing:
        raise MIETICSchemaError(
            f"MIETIC validated samples missing columns: {missing}. "
            f"Found {len(actual)} columns total."
        )


# ---------------------------------------------------------------------------
# Parsing helpers
# ---------------------------------------------------------------------------

def _parse_esi_band(instruction: str) -> str:
    """
    Infer the ESI band from the MIETIC instruction text.

    Returns "1", "2", or "3-5".
    Raises ValueError if the instruction doesn't match any known pattern.
    """
    text = instruction.strip()
    if _ESI1_PATTERN in text:
        return "1"
    if _ESI2_PATTERN in text:
        return "2"
    if _ESI_RESOURCE_PATTERN in text:
        return "3-5"
    raise ValueError(
        f"Cannot determine ESI band from instruction: {text[:100]}..."
    )


def _safe_float(value: str) -> Optional[float]:
    """Parse a float, returning None for empty/invalid values."""
    if not value or value.strip() == "":
        return None
    try:
        return float(value)
    except (ValueError, TypeError):
        return None


def _safe_int(value: str, default: int = 0) -> int:
    """Parse an int, returning default for empty/invalid values."""
    if not value or value.strip() == "":
        return default
    try:
        return int(float(value))  # handle "1.0" style
    except (ValueError, TypeError):
        return default


# ---------------------------------------------------------------------------
# Loaders
# ---------------------------------------------------------------------------

def load_mietic_corpus(
    mietic_dir: str | Path | None = None,
    *,
    limit: int | None = None,
) -> list[MIETICCorpusEntry]:
    """
    Load the main MIETIC instruction-tuning corpus.

    Args:
        mietic_dir: Path to the MIETIC directory. Defaults to
            DEFAULT_MIETIC_DIR relative to the project root.
        limit: Max rows to load (for testing/smoke tests).

    Returns:
        List of MIETICCorpusEntry with ESI band inferred from instruction.

    Raises:
        FileNotFoundError: If the CSV file doesn't exist.
        MIETICSchemaError: If the schema is unexpected.
    """
    path = _resolve_path(mietic_dir, MAIN_CORPUS_FILE)

    entries: list[MIETICCorpusEntry] = []
    skipped = 0

    with open(path, encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        assert reader.fieldnames is not None
        _validate_corpus_header(list(reader.fieldnames))

        for i, row in enumerate(reader):
            if limit is not None and len(entries) >= limit:
                break
            instruction = row.get("instruction", "").strip()
            if not instruction or instruction == "instruction":
                skipped += 1
                continue
            try:
                esi_band = _parse_esi_band(instruction)
            except ValueError:
                skipped += 1
                continue
            entries.append(MIETICCorpusEntry(
                instruction=instruction,
                input_text=row.get("input", "").strip(),
                output_text=row.get("output", "").strip(),
                esi_band=esi_band,
            ))

    if not entries:
        raise MIETICSchemaError(
            f"No valid entries loaded from {path}. "
            f"Skipped {skipped} rows."
        )

    return entries


def load_mietic_validated(
    mietic_dir: str | Path | None = None,
    *,
    retain_only: bool = True,
) -> list[MIETICValidatedCase]:
    """
    Load the MIETIC expert-validated samples.

    Args:
        mietic_dir: Path to the MIETIC directory.
        retain_only: If True (default), only return cases where
            Final Decision == "RETAIN" (expert-confirmed correct labels).

    Returns:
        List of MIETICValidatedCase.

    Raises:
        FileNotFoundError: If the CSV file doesn't exist.
        MIETICSchemaError: If the schema is unexpected or no valid cases found.
    """
    path = _resolve_path(mietic_dir, VALIDATE_SAMPLES_FILE)

    cases: list[MIETICValidatedCase] = []

    with open(path, encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        assert reader.fieldnames is not None
        columns = _strip_bom_from_columns(list(reader.fieldnames))

        # Rebuild the reader with cleaned column names
        # (csv.DictReader already consumed the header, so we re-map)
        _validate_samples_header(columns)

        for raw_row in reader:
            # Re-key the row using cleaned column names
            values = list(raw_row.values())
            row = dict(zip(columns, values))

            final_decision = row.get("Final Decision", "").strip()
            if retain_only and final_decision != "RETAIN":
                continue

            acuity_raw = row.get("acuity", "")
            acuity = _safe_int(acuity_raw)
            if acuity < 1 or acuity > 5:
                continue  # Skip cases without valid ESI

            case = MIETICValidatedCase(
                subject_id=_safe_int(row.get("subject_id", "")),
                stay_id=_safe_int(row.get("stay_id", "")),
                acuity=acuity,
                chief_complaint=row.get("chiefcomplaint", "").strip(),
                triage_case=row.get("tiragecase", "").strip(),
                age=_safe_float(row.get("age", "")) or 40.0,
                gender=row.get("gender", "M").strip(),
                arrival_transport=row.get("arrival_transport", "").strip(),
                disposition=row.get("disposition", "").strip(),
                heartrate=_safe_float(row.get("heartrate", "")),
                resprate=_safe_float(row.get("resprate", "")),
                o2sat=_safe_float(row.get("o2sat", "")),
                sbp=_safe_float(row.get("sbp", "")),
                dbp=_safe_float(row.get("dbp", "")),
                temperature=_safe_float(row.get("temperature", "")),
                pain=row.get("pain", "").strip() or None,
                invasive_ventilation=_safe_int(row.get("invasive_ventilation", "")),
                transfer_to_icu_in_1h=_safe_int(row.get("transfer_to_icu_in_1h", "")),
                transfer_to_icu_beyond_1h=_safe_int(row.get("transfer_to_icu_beyond_1h", "")),
                expired_within_1h=_safe_int(row.get("expired_within_1h", "")),
                expired_beyond_1h=_safe_int(row.get("expired_beyond_1h", "")),
                critical_procedure=_safe_int(row.get("critical_procedure", "")),
                tier1_med_usage_1h=_safe_int(row.get("tier1_med_usage_1h", "")),
                lab_event_count=_safe_int(row.get("lab_event_count", "")),
                resources_used=_safe_int(row.get("resources_used", "")),
                expert_1_opinion=row.get("Expert 1 Opinion", "").strip(),
                expert_2_opinion=row.get("Expert 2 Opinion", "").strip(),
                expert_3_opinion=row.get("Expert 3 Opinion", "").strip(),
                final_decision=final_decision,
            )
            cases.append(case)

    if not cases:
        raise MIETICSchemaError(
            f"No valid cases loaded from {path}. "
            f"Check retain_only={retain_only} and file contents."
        )

    return cases


# ---------------------------------------------------------------------------
# Path resolution
# ---------------------------------------------------------------------------

def _resolve_path(mietic_dir: str | Path | None, filename: str) -> Path:
    """Resolve the full path to a MIETIC file."""
    if mietic_dir is not None:
        base = Path(mietic_dir)
    else:
        # Walk up from this file to find the project root
        project_root = Path(__file__).resolve().parent.parent.parent
        base = project_root / DEFAULT_MIETIC_DIR

    path = base / filename
    if not path.exists():
        raise FileNotFoundError(
            f"MIETIC file not found: {path}\n"
            f"Expected directory: {base}\n"
            f"Make sure the MIETIC dataset is extracted in the project root."
        )
    return path


# ---------------------------------------------------------------------------
# Summary / diagnostics
# ---------------------------------------------------------------------------

def corpus_summary(entries: list[MIETICCorpusEntry]) -> dict:
    """Return a summary of the loaded corpus."""
    from collections import Counter
    band_counts = Counter(e.esi_band for e in entries)
    return {
        "total": len(entries),
        "esi_1": band_counts.get("1", 0),
        "esi_2": band_counts.get("2", 0),
        "esi_3_5": band_counts.get("3-5", 0),
    }


def validated_summary(cases: list[MIETICValidatedCase]) -> dict:
    """Return a summary of the loaded validated cases."""
    from collections import Counter
    acuity_counts = Counter(c.acuity for c in cases)
    return {
        "total": len(cases),
        "acuity_distribution": dict(sorted(acuity_counts.items())),
        "has_missing_vitals": sum(
            1 for c in cases
            if c.heartrate is None or c.resprate is None or c.o2sat is None
        ),
    }
