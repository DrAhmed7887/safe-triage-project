"""
KTAS External Dataset Loader
=============================
Loads and validates the Korean Triage and Acuity Scale (KTAS) dataset.

Source: Kaggle ilkeryildiz/emergency-service-triage-application
Paper: Cross-sectional retrospective study of 1,267 adult patients
       from two Korean EDs (Oct 2016 - Sep 2017).
       Three triage experts determined true KTAS.

Gold standard: KTAS_expert (1-5)
Comparison:    KTAS_RN (nurse triage, 1-5)
"""

from __future__ import annotations

import csv
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DEFAULT_KTAS_PATH = "data/ktas/data.csv"

# Mental status → ACVPU mapping
# 1=Normal→Alert, 2=Intoxication→Confusion, 3=Psychiatric→Alert, 4=Other→Voice
MENTAL_TO_ACVPU = {1: "A", 2: "C", 3: "A", 4: "V"}

# Known encoding artifact for missing NRS_pain values
_PAIN_ARTIFACTS = frozenset({"#BOÞ!", "#BO\xdeÞ!", "#BO\xde!", ""})


# ---------------------------------------------------------------------------
# Data class
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class KTASCase:
    """One row from the KTAS dataset."""
    row_index: int
    ktas_expert: int          # Gold standard (1-5)
    ktas_rn: int              # Nurse triage (1-5)
    chief_complaint: str      # Free-text English
    age: float
    sex: int                  # 1=Male, 2=Female
    arrival_mode: int         # 1-7 (2=Ambulance)
    injury: int               # 1=non-injury, 2=injury
    mental: int               # 1-4

    # Vitals
    sbp: Optional[int]
    dbp: Optional[int]
    hr: Optional[int]
    rr: Optional[int]
    bt: Optional[float]       # Body temp in Celsius
    saturation: Optional[float]

    # Pain
    nrs_pain: Optional[int]   # 1-10, None if encoding artifact
    pain_present: int         # 0 or 1

    # Outcomes
    disposition: int          # 1-7
    diagnosis: str
    mistriage: Optional[int]  # 0=correct, 1=under, 2=over
    los_min: Optional[float]  # Length of stay in minutes


# ---------------------------------------------------------------------------
# Parsing helpers
# ---------------------------------------------------------------------------

def _safe_int(value: str) -> Optional[int]:
    """Parse an int, returning None for empty/invalid values."""
    if not value or value.strip() == "":
        return None
    try:
        return int(float(value.strip()))
    except (ValueError, TypeError):
        return None


def _safe_float(value: str) -> Optional[float]:
    """Parse a float, returning None for empty/invalid. Handles comma decimals."""
    if not value or value.strip() == "":
        return None
    try:
        return float(value.strip().replace(",", "."))
    except (ValueError, TypeError):
        return None


def _parse_nrs_pain(raw: str) -> Optional[int]:
    """Parse NRS pain score, handling the '#BOÞ!' encoding artifact."""
    cleaned = raw.strip() if raw else ""
    if cleaned in _PAIN_ARTIFACTS:
        return None
    try:
        val = int(float(cleaned))
        return max(0, min(10, val))
    except (ValueError, TypeError):
        return None


# ---------------------------------------------------------------------------
# Loader
# ---------------------------------------------------------------------------

def load_ktas_cases(
    data_path: str | Path | None = None,
) -> list[KTASCase]:
    """
    Load the KTAS dataset from a semicolon-delimited CSV.

    Args:
        data_path: Path to the CSV file. Defaults to DEFAULT_KTAS_PATH
                   relative to project root.

    Returns:
        List of KTASCase.

    Raises:
        FileNotFoundError: If the CSV file doesn't exist.
        ValueError: If no valid cases loaded.
    """
    path = _resolve_path(data_path)
    cases: list[KTASCase] = []
    skipped = 0

    with open(path, encoding="latin-1", newline="") as f:
        reader = csv.DictReader(f, delimiter=";")

        for i, row in enumerate(reader, start=2):  # row 2 = first data row
            ktas_expert = _safe_int(row.get("KTAS_expert", ""))
            ktas_rn = _safe_int(row.get("KTAS_RN", ""))

            if ktas_expert is None or ktas_expert < 1 or ktas_expert > 5:
                skipped += 1
                continue
            if ktas_rn is None or ktas_rn < 1 or ktas_rn > 5:
                skipped += 1
                continue

            complaint = row.get("Chief_complain", "").strip()
            if not complaint or complaint == "??":
                skipped += 1
                continue

            age_raw = _safe_float(row.get("Age", ""))
            if age_raw is None:
                skipped += 1
                continue

            sex = _safe_int(row.get("Sex", "")) or 1
            arrival_mode = _safe_int(row.get("Arrival mode", "")) or 3
            injury = _safe_int(row.get("Injury", "")) or 1
            mental = _safe_int(row.get("Mental", "")) or 1

            bt_raw = _safe_float(row.get("BT", ""))
            if bt_raw is not None and (bt_raw < 25.0 or bt_raw > 45.0):
                bt_raw = None  # Out of plausible Celsius range

            case = KTASCase(
                row_index=i,
                ktas_expert=ktas_expert,
                ktas_rn=ktas_rn,
                chief_complaint=complaint,
                age=age_raw,
                sex=sex,
                arrival_mode=arrival_mode,
                injury=injury,
                mental=mental,
                sbp=_safe_int(row.get("SBP", "")),
                dbp=_safe_int(row.get("DBP", "")),
                hr=_safe_int(row.get("HR", "")),
                rr=_safe_int(row.get("RR", "")),
                bt=bt_raw,
                saturation=_safe_float(row.get("Saturation", "")),
                nrs_pain=_parse_nrs_pain(row.get("NRS_pain", "")),
                pain_present=_safe_int(row.get("Pain", "")) or 0,
                disposition=_safe_int(row.get("Disposition", "")) or 1,
                diagnosis=row.get("Diagnosis in ED", "").strip(),
                mistriage=_safe_int(row.get("mistriage", "")),
                los_min=_safe_float(row.get("Length of stay_min", "")),
            )
            cases.append(case)

    if not cases:
        raise ValueError(
            f"No valid cases loaded from {path}. Skipped {skipped} rows."
        )

    return cases


# ---------------------------------------------------------------------------
# Path resolution
# ---------------------------------------------------------------------------

def _resolve_path(data_path: str | Path | None) -> Path:
    """Resolve the full path to the KTAS CSV."""
    if data_path is not None:
        path = Path(data_path)
    else:
        project_root = Path(__file__).resolve().parent.parent.parent
        path = project_root / DEFAULT_KTAS_PATH

    if not path.exists():
        raise FileNotFoundError(
            f"KTAS CSV not found: {path}\n"
            f"Download from Kaggle: ilkeryildiz/emergency-service-triage-application\n"
            f"Place at: {path}"
        )
    return path


# ---------------------------------------------------------------------------
# Summary / diagnostics
# ---------------------------------------------------------------------------

def ktas_summary(cases: list[KTASCase]) -> dict:
    """Return a summary of the loaded KTAS cases."""
    expert_dist = Counter(c.ktas_expert for c in cases)
    rn_dist = Counter(c.ktas_rn for c in cases)
    return {
        "total": len(cases),
        "ktas_expert_distribution": dict(sorted(expert_dist.items())),
        "ktas_rn_distribution": dict(sorted(rn_dist.items())),
        "missing_spo2": sum(1 for c in cases if c.saturation is None),
        "missing_pain": sum(1 for c in cases if c.nrs_pain is None),
        "age_mean": round(sum(c.age for c in cases) / len(cases), 1),
        "ambulance_arrivals": sum(1 for c in cases if c.arrival_mode == 2),
        "injury_cases": sum(1 for c in cases if c.injury == 2),
    }
