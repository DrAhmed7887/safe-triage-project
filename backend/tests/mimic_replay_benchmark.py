#!/usr/bin/env python3
"""
SAFE-Triage MIMIC-IV-ED retrospective replay benchmark.

STATUS: SECONDARY / EXTERNAL ROBUSTNESS BENCHMARK
======================================================================
This is NOT the primary public benchmark for SAFE-Triage.
The primary benchmark is MIETIC (see backend/benchmarks/mietic_benchmark.py).

This script replays raw MIMIC-IV-ED triage cases through the engine as a
noisy, real-world stress test. It lacks demographics, clinical vignettes,
and expert validation — making it unsuitable for headline claims.

Use this for:
  - Robustness testing against high-volume real ED data
  - Regression detection on large sample sizes
  - Identifying complaint categories that need attention

Do NOT use this for:
  - Primary accuracy claims in papers or presentations
  - Safety gate pass/fail decisions (use MIETIC for that)
======================================================================

It supports two modes:
1. `--sample-only`: create a stratified benchmark sample and dataset summary
   without importing the SAFE-Triage runtime.
2. Default run: create the sample and then replay it through the deterministic
   engine if the local Python environment has the backend dependencies installed.

Important limitation:
- The local `mimic-iv-ed-2.2/ed/triage.csv.gz` file provides complaint, triage
  vitals, and acuity. It does not include demographics, so replay mode uses
  configurable neutral placeholders for age/gender unless a richer upstream
  dataset is provided later.
"""

from __future__ import annotations

import argparse
import csv
import gzip
import json
import os
import random
import re
import sys
import time
import types
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple


ROOT_DIR = Path(__file__).resolve().parents[2]
DEFAULT_TRIAGE_PATH = ROOT_DIR / "mimic-iv-ed-2.2" / "ed" / "triage.csv.gz"
DEFAULT_EDSTAYS_PATH = ROOT_DIR / "mimic-iv-ed-2.2" / "ed" / "edstays.csv.gz"
DEFAULT_VITALSIGN_PATH = ROOT_DIR / "mimic-iv-ed-2.2" / "ed" / "vitalsign.csv.gz"
DEFAULT_OUTPUT_DIR = Path(__file__).resolve().parent / "benchmark_outputs"
DEFAULT_PATIENTS_PATH = ROOT_DIR / "mimic-iv-ed-2.2" / "patients.csv.gz"
NON_INFORMATIVE_COMPLAINT_TOKENS = {
    "s",
    "p",
    "n",
    "v",
    "w",
}


@dataclass
class ReplayCase:
    stay_id: str
    source_row: int
    complaint: str
    complaint_bucket: str
    actual_esi: int
    vitals: Dict[str, Any]
    gender: Optional[str] = None           # From edstays: "F" or "M"
    age: Optional[float] = None             # From patients: anchor_age (real age)
    arrival_transport: Optional[str] = None  # From edstays: AMBULANCE, WALK IN, etc.
    disposition: Optional[str] = None        # From edstays: ADMITTED, HOME, etc.
    worst_vitals: Optional[Dict[str, Any]] = None  # From vitalsign: most abnormal readings


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create and optionally run a SAFE-Triage retrospective replay benchmark on MIMIC-IV-ED."
    )
    parser.add_argument(
        "--triage-path",
        type=Path,
        default=DEFAULT_TRIAGE_PATH,
        help="Path to MIMIC-IV-ED triage.csv.gz",
    )
    parser.add_argument(
        "--target-cases",
        type=int,
        default=7000,
        help="Target number of replay cases to sample",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed for reproducible sampling",
    )
    parser.add_argument(
        "--sample-only",
        action="store_true",
        help="Only build the benchmark sample and summary; do not run the engine",
    )
    parser.add_argument(
        "--max-per-complaint-bucket",
        type=int,
        default=0,
        help="Optional cap per normalized complaint bucket (0 = unlimited)",
    )
    parser.add_argument(
        "--default-age",
        type=float,
        default=40.0,
        help="Fallback age for replay mode when demographics are unavailable",
    )
    parser.add_argument(
        "--default-gender",
        choices=("male", "female"),
        default="male",
        help="Fallback gender for replay mode when demographics are unavailable",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help="Directory for benchmark artifacts",
    )
    parser.add_argument(
        "--tag",
        default=None,
        help="Optional custom suffix for output filenames",
    )
    parser.add_argument(
        "--enrich",
        action="store_true",
        help="Join edstays.csv + vitalsign.csv for real gender and worst vitals",
    )
    parser.add_argument(
        "--edstays-path",
        type=Path,
        default=DEFAULT_EDSTAYS_PATH,
        help="Path to MIMIC-IV-ED edstays.csv.gz",
    )
    parser.add_argument(
        "--vitalsign-path",
        type=Path,
        default=DEFAULT_VITALSIGN_PATH,
        help="Path to MIMIC-IV-ED vitalsign.csv.gz",
    )
    parser.add_argument(
        "--patients-path",
        type=Path,
        default=DEFAULT_PATIENTS_PATH,
        help="Path to MIMIC-IV core patients.csv.gz (hosp module) for real anchor_age",
    )
    parser.add_argument(
        "--clean-only",
        action="store_true",
        help=(
            "After enrichment, keep only outcome-confirmed cases: "
            "ESI 1/2 with disposition ADMITTED or EXPIRED (true critical), "
            "and ESI 4/5 with disposition HOME (true non-urgent). "
            "Drops ESI 3 entirely. Requires --enrich."
        ),
    )
    parser.add_argument(
        "--clean-all-esi",
        action="store_true",
        help=(
            "After enrichment, keep outcome-confirmed cases across ALL ESI levels: "
            "ESI 1/2 ADMITTED/EXPIRED, ESI 3 ADMITTED or HOME, ESI 4/5 HOME. "
            "Drops cases where outcome contradicts the label. Requires --enrich."
        ),
    )
    parser.add_argument(
        "--heuristic-filter",
        action="store_true",
        help=(
            "Remove 'impossible' label cases before running: "
            "suture removal/med refill labeled ESI 1-2, "
            "transfer complaints (acuity set by referring hospital), "
            "and ESI 5 cases with clearly critical vitals (HR>130 or SpO2<88)."
        ),
    )
    parser.add_argument(
        "--engine-fair",
        action="store_true",
        help=(
            "Only keep cases the engine can fairly evaluate: "
            "complaint must resolve to a known symptom category (not 'unclear') "
            "AND at least 3 core vitals (HR, RR, SpO2, SBP, Temp) must be present "
            "so NEWS2 can meaningfully score. Requires backend runtime."
        ),
    )
    return parser.parse_args()


def parse_float(value: str) -> Optional[float]:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def parse_int(value: str) -> Optional[int]:
    parsed = parse_float(value)
    if parsed is None:
        return None
    return int(round(parsed))


def parse_acuity(value: str) -> Optional[int]:
    parsed = parse_int(value)
    if parsed is None:
        return None
    if parsed < 1 or parsed > 5:
        return None
    return parsed


def clamp(value: Optional[float], lower: float, upper: float) -> Optional[float]:
    if value is None:
        return None
    return max(lower, min(upper, value))


def sanitize_pain_score(value: Optional[int]) -> Optional[int]:
    if value is None:
        return None
    return int(clamp(value, 0, 10))


def normalize_bucket(chief_complaint: str) -> str:
    text = (chief_complaint or "").strip().lower()
    if not text:
        return "unknown"

    first_fragment = re.split(r"[,;]| with | and | w/", text, maxsplit=1)[0].strip()
    normalized = re.sub(r"[^a-z0-9\s]+", " ", first_fragment)
    normalized = re.sub(r"\s+", " ", normalized).strip()
    if not normalized:
        return "unknown"

    tokens = [token for token in normalized.split() if token]
    informative_tokens = [token for token in tokens if token not in NON_INFORMATIVE_COMPLAINT_TOKENS]
    if informative_tokens:
        return " ".join(informative_tokens[:4])
    return " ".join(tokens[:4]) or "unknown"


def load_edstays_lookup(edstays_path: Path) -> Dict[str, Dict[str, str]]:
    """Build stay_id -> {subject_id, gender, arrival_transport, disposition} lookup from edstays."""
    lookup: Dict[str, Dict[str, str]] = {}
    with gzip.open(edstays_path, "rt", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            stay_id = row.get("stay_id", "").strip()
            if stay_id:
                lookup[stay_id] = {
                    "subject_id": row.get("subject_id", "").strip(),
                    "gender": row.get("gender", "").strip(),
                    "arrival_transport": row.get("arrival_transport", "").strip(),
                    "disposition": row.get("disposition", "").strip(),
                }
    return lookup


def load_patients_lookup(patients_path: Path) -> Dict[str, float]:
    """Build subject_id -> anchor_age lookup from MIMIC-IV core patients.csv.gz.

    anchor_age is the patient's age at the anchor_year. Since MIMIC shifts dates
    by a random offset within ±3 years of anchor_year, anchor_age is a close
    approximation of the true age at ED visit — accurate enough for age-based
    triage modifiers (pediatric <3, elderly >=65).
    """
    lookup: Dict[str, float] = {}
    if not patients_path.exists():
        return lookup
    with gzip.open(patients_path, "rt", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            subject_id = row.get("subject_id", "").strip()
            anchor_age_raw = row.get("anchor_age", "").strip()
            if subject_id and anchor_age_raw:
                parsed = parse_float(anchor_age_raw)
                if parsed is not None:
                    lookup[subject_id] = parsed
    return lookup


def load_worst_vitals(vitalsign_path: Path, stay_ids: set) -> Dict[str, Dict[str, Any]]:
    """Build stay_id -> worst (most abnormal) vitals from serial readings.

    For triage, "worst" means the most clinically concerning value:
    - HR: highest (tachycardia) or lowest (bradycardia) — whichever is farther from normal (80)
    - RR: highest (tachypnea) or lowest — whichever is farther from normal (16)
    - SpO2: lowest (desaturation)
    - SBP: lowest (hypotension) — more dangerous than hypertension for acute triage
    - Temp: highest (fever) or lowest (hypothermia) — whichever is farther from normal (37°C/98.6°F)
    - Pain: highest
    """
    # Collect all readings per stay
    readings: Dict[str, List[Dict[str, Any]]] = defaultdict(list)

    with gzip.open(vitalsign_path, "rt", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            stay_id = row.get("stay_id", "").strip()
            if stay_id not in stay_ids:
                continue
            vitals = {
                "hr": parse_float(row.get("heartrate", "")),
                "rr": parse_float(row.get("resprate", "")),
                "spo2": parse_float(row.get("o2sat", "")),
                "temp": parse_float(row.get("temperature", "")),
                "sbp": parse_float(row.get("sbp", "")),
                "dbp": parse_float(row.get("dbp", "")),
                "pain_score": parse_float(row.get("pain", "")),
            }
            readings[stay_id].append(vitals)

    worst: Dict[str, Dict[str, Any]] = {}
    for stay_id, all_readings in readings.items():
        w: Dict[str, Any] = {}

        # HR: most abnormal (farthest from 80 bpm)
        hr_vals = [r["hr"] for r in all_readings if r["hr"] is not None]
        if hr_vals:
            w["hr"] = int(round(max(hr_vals, key=lambda v: abs(v - 80))))

        # RR: most abnormal (farthest from 16)
        rr_vals = [r["rr"] for r in all_readings if r["rr"] is not None]
        if rr_vals:
            w["rr"] = int(round(max(rr_vals, key=lambda v: abs(v - 16))))

        # SpO2: lowest (worst desaturation)
        spo2_vals = [r["spo2"] for r in all_readings if r["spo2"] is not None]
        if spo2_vals:
            w["spo2"] = min(spo2_vals)

        # SBP: lowest (worst hypotension)
        sbp_vals = [r["sbp"] for r in all_readings if r["sbp"] is not None]
        if sbp_vals:
            w["sbp"] = int(round(min(sbp_vals)))

        # DBP: lowest
        dbp_vals = [r["dbp"] for r in all_readings if r["dbp"] is not None]
        if dbp_vals:
            w["dbp"] = int(round(min(dbp_vals)))

        # Temp: most abnormal (farthest from 98.6°F)
        temp_vals = [r["temp"] for r in all_readings if r["temp"] is not None]
        if temp_vals:
            w["temp"] = max(temp_vals, key=lambda v: abs(v - 98.6))

        # Pain: highest
        pain_vals = [r["pain_score"] for r in all_readings if r["pain_score"] is not None]
        if pain_vals:
            w["pain_score"] = sanitize_pain_score(int(round(max(pain_vals))))

        if w:
            worst[stay_id] = w

    return worst


def enrich_cases(
    cases: List[ReplayCase],
    edstays_path: Path,
    vitalsign_path: Path,
    patients_path: Optional[Path] = None,
) -> Tuple[List[ReplayCase], Dict[str, Any]]:
    """Enrich replay cases with real demographics and worst vitals."""
    print("Loading edstays lookup...")
    edstays_lookup = load_edstays_lookup(edstays_path)
    print(f"  Loaded {len(edstays_lookup):,} edstays records")

    # Load patients table for real anchor_age if path provided and exists
    patients_lookup: Dict[str, float] = {}
    if patients_path is not None and patients_path.exists():
        print(f"Loading patients age lookup from {patients_path.name}...")
        patients_lookup = load_patients_lookup(patients_path)
        print(f"  Loaded {len(patients_lookup):,} patient ages")
    else:
        print("  patients.csv.gz not found — age will use placeholder (--patients-path to enable)")

    stay_ids = {case.stay_id for case in cases}
    print("Loading worst vitals for sampled cases...")
    worst_vitals_lookup = load_worst_vitals(vitalsign_path, stay_ids)
    print(f"  Loaded worst vitals for {len(worst_vitals_lookup):,} stays")

    enriched_gender = 0
    enriched_age = 0
    enriched_transport = 0
    enriched_vitals = 0
    enriched_cases: List[ReplayCase] = []

    for case in cases:
        ed_info = edstays_lookup.get(case.stay_id)
        wv = worst_vitals_lookup.get(case.stay_id)

        new_gender = None
        new_age: Optional[float] = None
        new_transport = None
        new_disposition = None

        if ed_info:
            new_gender = ed_info.get("gender") or None
            new_transport = ed_info.get("arrival_transport") or None
            new_disposition = ed_info.get("disposition") or None
            if new_gender:
                enriched_gender += 1
            if new_transport:
                enriched_transport += 1
            # Join to patients via subject_id for real age
            subject_id = ed_info.get("subject_id", "")
            if subject_id and subject_id in patients_lookup:
                new_age = patients_lookup[subject_id]
                enriched_age += 1

        # Merge worst vitals with triage vitals: use worst where available
        merged_vitals = dict(case.vitals)
        if wv:
            enriched_vitals += 1
            for key, val in wv.items():
                if val is not None:
                    triage_val = case.vitals.get(key)
                    if triage_val is None:
                        merged_vitals[key] = val
                    elif key == "spo2":
                        merged_vitals[key] = min(val, triage_val)
                    elif key in ("sbp", "dbp"):
                        merged_vitals[key] = min(val, triage_val)
                    elif key == "pain_score":
                        merged_vitals[key] = max(val, triage_val)
                    elif key == "hr":
                        merged_vitals[key] = max(val, triage_val, key=lambda v: abs(v - 80))
                    elif key == "rr":
                        merged_vitals[key] = max(val, triage_val, key=lambda v: abs(v - 16))
                    elif key == "temp":
                        merged_vitals[key] = max(val, triage_val, key=lambda v: abs(v - 98.6))

        enriched_cases.append(
            ReplayCase(
                stay_id=case.stay_id,
                source_row=case.source_row,
                complaint=case.complaint,
                complaint_bucket=case.complaint_bucket,
                actual_esi=case.actual_esi,
                vitals=merged_vitals,
                gender=new_gender,
                age=new_age,
                arrival_transport=new_transport,
                disposition=new_disposition,
                worst_vitals=wv,
            )
        )

    enrich_summary = {
        "enriched_gender": enriched_gender,
        "enriched_age": enriched_age,
        "enriched_transport": enriched_transport,
        "enriched_worst_vitals": enriched_vitals,
        "total_cases": len(cases),
        "age_coverage_pct": round(enriched_age / len(cases) * 100, 1) if cases else 0.0,
    }
    print(
        f"  Enriched: {enriched_gender} genders, {enriched_age} ages "
        f"({enrich_summary['age_coverage_pct']}%), {enriched_transport} transports, "
        f"{enriched_vitals} worst vitals"
    )
    return enriched_cases, enrich_summary


_CLEAN_CRITICAL_DISPOSITIONS = {"ADMITTED", "EXPIRED"}
_CLEAN_NONCRITICAL_DISPOSITIONS = {"HOME"}

# All-ESI outcome-confirmation rules:
# Each ESI level maps to the set of dispositions that are CONSISTENT with that label.
# Cases whose disposition contradicts the label are dropped as noisy.
_CLEAN_ALL_ESI_RULES: Dict[int, set] = {
    1: {"ADMITTED", "EXPIRED"},                # ESI 1 → must be admitted or died
    2: {"ADMITTED", "EXPIRED"},                # ESI 2 → must be admitted or died
    3: {"ADMITTED", "HOME"},                   # ESI 3 → workup then home OR admitted (both valid)
    4: {"HOME"},                               # ESI 4 → minor, sent home
    5: {"HOME"},                               # ESI 5 → non-urgent, sent home
}

_HEURISTIC_NOISE_BUCKETS = {"suture removal", "med refill", "suture", "staple removal"}
_HEURISTIC_TRANSFER_BUCKETS = {"transfer", "transfer from outside hospital", "transferred"}


def apply_clean_filter(
    cases: List[ReplayCase],
    all_esi: bool = False,
) -> Tuple[List[ReplayCase], Dict[str, Any]]:
    """Keep only outcome-confirmed cases.

    If all_esi=False (legacy mode):
        ESI 1/2 ADMITTED/EXPIRED + ESI 4/5 HOME.  ESI 3 is dropped entirely.
    If all_esi=True:
        All ESI levels kept when disposition is consistent with the label.
        ESI 3 accepts ADMITTED or HOME (both are valid outcomes for mid-acuity).
        Noise = label contradicts outcome (e.g. ESI 5 ADMITTED, ESI 1 HOME).
    """
    clean: List[ReplayCase] = []
    stats: Dict[str, int] = {
        "total_in": len(cases),
        "dropped_no_disposition": 0,
        "dropped_ambiguous": 0,
    }
    kept_by_level: Counter[int] = Counter()
    dropped_by_level: Counter[int] = Counter()

    for case in cases:
        disp = (case.disposition or "").strip().upper()
        if not disp or disp in ("LEFT WITHOUT BEING SEEN", "ELOPED", "LEFT AGAINST MEDICAL ADVICE", "OTHER"):
            stats["dropped_no_disposition"] += 1
            continue

        if all_esi:
            allowed = _CLEAN_ALL_ESI_RULES.get(case.actual_esi, set())
            if disp in allowed:
                clean.append(case)
                kept_by_level[case.actual_esi] += 1
            else:
                stats["dropped_ambiguous"] += 1
                dropped_by_level[case.actual_esi] += 1
        else:
            # Legacy mode: ESI 1/2 + ESI 4/5 only
            if case.actual_esi <= 2 and disp in _CLEAN_CRITICAL_DISPOSITIONS:
                clean.append(case)
                kept_by_level[case.actual_esi] += 1
            elif case.actual_esi >= 4 and disp in _CLEAN_NONCRITICAL_DISPOSITIONS:
                clean.append(case)
                kept_by_level[case.actual_esi] += 1
            else:
                stats["dropped_ambiguous"] += 1
                dropped_by_level[case.actual_esi] += 1

    stats["total_out"] = len(clean)
    stats["kept_by_level"] = {str(k): v for k, v in sorted(kept_by_level.items())}
    stats["dropped_by_level"] = {str(k): v for k, v in sorted(dropped_by_level.items())}
    return clean, stats


def apply_heuristic_filter(cases: List[ReplayCase]) -> Tuple[List[ReplayCase], Dict[str, Any]]:
    """Remove cases with obviously impossible label/presentation combinations.

    Removes:
    - Noise-complaint buckets (suture removal, med refill) labeled ESI 1-2
    - Transfer complaints (acuity was assigned by referring hospital, not this nurse)
    - ESI 5 cases with critical vitals (HR >130 or SpO2 <88) — clear mislabels
    """
    kept: List[ReplayCase] = []
    stats: Dict[str, int] = {
        "total_in": len(cases),
        "removed_noise_complaint": 0,
        "removed_transfer": 0,
        "removed_esi5_critical_vitals": 0,
    }

    for case in cases:
        bucket = case.complaint_bucket.lower()

        # Routine-complaint labeled as high-acuity: almost certainly a nurse data-entry error
        if case.actual_esi <= 2 and bucket in _HEURISTIC_NOISE_BUCKETS:
            stats["removed_noise_complaint"] += 1
            continue

        # Transfer cases: the acuity was set by the referring hospital, not the triage nurse here
        if bucket in _HEURISTIC_TRANSFER_BUCKETS:
            stats["removed_transfer"] += 1
            continue

        # ESI 5 with critical vitals — physiologically impossible to be non-urgent
        if case.actual_esi == 5:
            hr = case.vitals.get("hr")
            spo2 = case.vitals.get("spo2")
            if (hr is not None and hr > 130) or (spo2 is not None and spo2 < 88):
                stats["removed_esi5_critical_vitals"] += 1
                continue

        kept.append(case)

    stats["total_out"] = len(kept)
    return kept, stats


def apply_engine_fair_filter(cases: List[ReplayCase]) -> Tuple[List[ReplayCase], Dict[str, Any]]:
    """Keep only cases the engine can meaningfully evaluate.

    Excludes cases where the engine fundamentally lacks input signal:
    1. Complaint text resolves to 'unclear' (no keyword match → engine flying blind)
    2. Fewer than 3 core vitals present (NEWS2 can't meaningfully score)

    This filter requires importing the backend classification engine.
    """
    # Late import — only needed when --engine-fair is used
    runtime, runtime_error = import_runtime()
    if runtime is None:
        print(f"WARNING: --engine-fair requires backend runtime. Error: {runtime_error}")
        print("Skipping engine-fair filter.")
        return cases, {"skipped": True, "error": runtime_error}

    _DeterministicTriageEngine = runtime[0]
    os.environ.setdefault("DISABLE_RAG", "true")
    _engine = _DeterministicTriageEngine(use_ai=False)

    kept: List[ReplayCase] = []
    stats: Dict[str, int] = {
        "total_in": len(cases),
        "excluded_unclear": 0,
        "excluded_no_vitals": 0,
        "excluded_both": 0,
    }

    _CORE_VITAL_KEYS = ("hr", "rr", "spo2", "sbp", "temp")

    for case in cases:
        # Check vitals completeness
        core_count = sum(1 for k in _CORE_VITAL_KEYS if case.vitals.get(k) is not None)
        has_vitals = core_count >= 3

        # Check if engine can classify the complaint
        category = _engine.ai_classifier._fallback_keyword_match(case.complaint)
        is_unclear = category == "unclear"

        if is_unclear and not has_vitals:
            stats["excluded_both"] += 1
        elif is_unclear:
            stats["excluded_unclear"] += 1
        elif not has_vitals:
            stats["excluded_no_vitals"] += 1
        else:
            kept.append(case)

    stats["total_out"] = len(kept)
    return kept, stats


def load_replay_cases(triage_path: Path) -> Tuple[List[ReplayCase], Dict[str, Any]]:
    if not triage_path.exists():
        raise FileNotFoundError(f"Triage file not found: {triage_path}")

    rows_total = 0
    non_null_complaint = 0
    non_null_acuity = 0
    usable_rows = 0
    unique_buckets: set[str] = set()
    acuity_counter: Counter[int] = Counter()
    cases: List[ReplayCase] = []

    with gzip.open(triage_path, "rt", newline="") as handle:
        reader = csv.DictReader(handle)
        for rows_total, row in enumerate(reader, start=1):
            complaint = (row.get("chiefcomplaint") or "").strip()
            acuity = parse_acuity(row.get("acuity", ""))

            if complaint:
                non_null_complaint += 1
            if acuity is not None:
                non_null_acuity += 1

            if not complaint or acuity is None:
                continue

            usable_rows += 1
            acuity_counter[acuity] += 1
            bucket = normalize_bucket(complaint)
            unique_buckets.add(bucket)

            vitals = {
                "hr": parse_int(row.get("heartrate", "")),
                "rr": parse_int(row.get("resprate", "")),
                "spo2": parse_float(row.get("o2sat", "")),
                "temp": parse_float(row.get("temperature", "")),
                "sbp": parse_int(row.get("sbp", "")),
                "dbp": parse_int(row.get("dbp", "")),
                "pain_score": sanitize_pain_score(parse_int(row.get("pain", ""))),
            }
            vitals = {key: value for key, value in vitals.items() if value is not None}

            cases.append(
                ReplayCase(
                    stay_id=str(row.get("stay_id") or ""),
                    source_row=rows_total,
                    complaint=complaint,
                    complaint_bucket=bucket,
                    actual_esi=acuity,
                    vitals=vitals,
                )
            )

    dataset_summary = {
        "triage_path": str(triage_path),
        "rows_total": rows_total,
        "non_null_chiefcomplaint": non_null_complaint,
        "non_null_acuity": non_null_acuity,
        "usable_rows": usable_rows,
        "unique_complaint_buckets": len(unique_buckets),
        "acuity_distribution": {str(level): acuity_counter[level] for level in sorted(acuity_counter)},
    }
    return cases, dataset_summary


def build_level_targets(total_target: int, counts_by_level: Dict[int, int]) -> Dict[int, int]:
    levels = [1, 2, 3, 4, 5]
    available_total = sum(counts_by_level.get(level, 0) for level in levels)
    if available_total == 0:
        return {level: 0 for level in levels}

    total_target = min(total_target, available_total)
    base = total_target // len(levels)
    targets = {level: min(base, counts_by_level.get(level, 0)) for level in levels}
    assigned = sum(targets.values())

    while assigned < total_target:
        progressed = False
        for level in levels:
            available = counts_by_level.get(level, 0)
            if targets[level] < available:
                targets[level] += 1
                assigned += 1
                progressed = True
                if assigned >= total_target:
                    break
        if not progressed:
            break

    return targets


def sample_cases(
    cases: Iterable[ReplayCase],
    target_cases: int,
    seed: int,
    max_per_bucket: int,
) -> Tuple[List[ReplayCase], Dict[str, Any]]:
    by_level: Dict[int, List[ReplayCase]] = defaultdict(list)
    for case in cases:
        by_level[case.actual_esi].append(case)

    level_counts = {level: len(by_level.get(level, [])) for level in [1, 2, 3, 4, 5]}
    level_targets = build_level_targets(target_cases, level_counts)

    rng = random.Random(seed)
    selected: List[ReplayCase] = []
    bucket_counter: Counter[str] = Counter()
    selected_by_level: Counter[int] = Counter()

    for level in [1, 2, 3, 4, 5]:
        pool = list(by_level.get(level, []))
        rng.shuffle(pool)
        target = level_targets[level]
        for case in pool:
            if selected_by_level[level] >= target:
                break
            if max_per_bucket > 0 and bucket_counter[case.complaint_bucket] >= max_per_bucket:
                continue
            selected.append(case)
            bucket_counter[case.complaint_bucket] += 1
            selected_by_level[level] += 1

    if len(selected) < sum(level_targets.values()):
        # Fill remaining slots with any unused case, respecting bucket caps if possible.
        selected_ids = {(case.stay_id, case.source_row) for case in selected}
        remaining_pool = [case for level in [1, 2, 3, 4, 5] for case in by_level.get(level, [])]
        rng.shuffle(remaining_pool)
        target_total = sum(level_targets.values())
        for case in remaining_pool:
            key = (case.stay_id, case.source_row)
            if key in selected_ids:
                continue
            if max_per_bucket > 0 and bucket_counter[case.complaint_bucket] >= max_per_bucket:
                continue
            selected.append(case)
            selected_ids.add(key)
            bucket_counter[case.complaint_bucket] += 1
            if len(selected) >= target_total:
                break

    selected.sort(key=lambda case: (case.actual_esi, case.source_row))

    sample_summary = {
        "requested_cases": target_cases,
        "selected_cases": len(selected),
        "seed": seed,
        "max_per_complaint_bucket": max_per_bucket,
        "level_targets": {str(level): level_targets[level] for level in sorted(level_targets)},
        "level_selected": {
            str(level): sum(1 for case in selected if case.actual_esi == level) for level in [1, 2, 3, 4, 5]
        },
        "top_complaint_buckets": bucket_counter.most_common(20),
    }
    return selected, sample_summary


def ensure_output_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def make_output_prefix(output_dir: Path, tag: Optional[str], target_cases: int) -> Path:
    ensure_output_dir(output_dir)
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    suffix = tag or f"{target_cases}cases"
    return output_dir / f"mimic_replay_{suffix}_{timestamp}"


def write_sample_csv(path: Path, cases: Iterable[ReplayCase]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            [
                "stay_id",
                "source_row",
                "actual_esi",
                "complaint_bucket",
                "chief_complaint_text",
                "hr",
                "rr",
                "spo2",
                "temp",
                "sbp",
                "dbp",
                "pain_score",
            ]
        )
        for case in cases:
            writer.writerow(
                [
                    case.stay_id,
                    case.source_row,
                    case.actual_esi,
                    case.complaint_bucket,
                    case.complaint,
                    case.vitals.get("hr"),
                    case.vitals.get("rr"),
                    case.vitals.get("spo2"),
                    case.vitals.get("temp"),
                    case.vitals.get("sbp"),
                    case.vitals.get("dbp"),
                    case.vitals.get("pain_score"),
                ]
            )


def import_runtime() -> Tuple[Optional[Tuple[Any, Any, Any, Any]], Optional[str]]:
    try:
        import dotenv  # type: ignore  # noqa: F401
    except ModuleNotFoundError:
        stub = types.ModuleType("dotenv")
        stub.load_dotenv = lambda *args, **kwargs: False
        sys.modules["dotenv"] = stub

    backend_dir = ROOT_DIR / "backend"
    if str(backend_dir) not in sys.path:
        sys.path.insert(0, str(backend_dir))

    try:
        from logic.deterministic_triage import DeterministicTriageEngine
        from models import Gender, PatientInput, Vitals
    except Exception as exc:  # pragma: no cover - environment-dependent
        return None, f"{type(exc).__name__}: {exc}"

    return (DeterministicTriageEngine, PatientInput, Vitals, Gender), None


def run_replay(
    cases: Iterable[ReplayCase],
    default_age: float,
    default_gender: str,
) -> Dict[str, Any]:
    runtime, runtime_error = import_runtime()
    if runtime is None:
        return {
            "summary": {
                "engine_available": False,
                "engine_import_error": runtime_error,
            },
            "predictions": [],
            "failures": [],
        }

    DeterministicTriageEngine, PatientInput, Vitals, Gender = runtime
    os.environ.setdefault("DISABLE_RAG", "true")
    engine = DeterministicTriageEngine(use_ai=False)

    default_gender_value = Gender.MALE if default_gender == "male" else Gender.FEMALE

    predictions: List[Dict[str, Any]] = []
    failures: List[Dict[str, Any]] = []
    confusion: Dict[str, Counter[int]] = defaultdict(Counter)
    exact_matches = 0
    within_one = 0
    over_triage = 0
    under_triage = 0
    critical_under_triage = 0

    for case in cases:
        try:
            # Use real gender from edstays if available
            if case.gender == "F":
                case_gender = Gender.FEMALE
            elif case.gender == "M":
                case_gender = Gender.MALE
            else:
                case_gender = default_gender_value

            # Use ambulance arrival as a signal (arrived_by_ambulance field)
            arrived_by_ambulance = (case.arrival_transport or "").upper() == "AMBULANCE"

            patient_kwargs: Dict[str, Any] = {
                "age": case.age if case.age is not None else default_age,
                "gender": case_gender,
                "chief_complaint_text": case.complaint,
                "vitals": Vitals(**case.vitals),
                "consciousness": "A",
            }
            # Only pass arrived_by_ambulance if the engine supports it
            if arrived_by_ambulance:
                patient_kwargs["arrived_by_ambulance"] = True

            patient = PatientInput(**patient_kwargs)
            result = engine.evaluate(patient)
            predicted = int(getattr(result.level, "value", result.level))
            exact = predicted == case.actual_esi
            within_one_match = abs(predicted - case.actual_esi) <= 1
            critical_under = case.actual_esi <= 2 and predicted > case.actual_esi
            over = predicted < case.actual_esi
            under = predicted > case.actual_esi

            if exact:
                exact_matches += 1
            if within_one_match:
                within_one += 1
            if over:
                over_triage += 1
            if under:
                under_triage += 1
            if critical_under:
                critical_under_triage += 1

            confusion[str(case.actual_esi)][predicted] += 1
            predictions.append(
                {
                    "stay_id": case.stay_id,
                    "source_row": case.source_row,
                    "complaint_bucket": case.complaint_bucket,
                    "chief_complaint_text": case.complaint,
                    "actual_esi": case.actual_esi,
                    "predicted_esi": predicted,
                    "exact_match": exact,
                    "within_one_level": within_one_match,
                    "over_triage": over,
                    "under_triage": under,
                    "critical_under_triage": critical_under,
                    "label_en": getattr(result, "label_en", ""),
                    "extraction_method": getattr(result, "extraction_method", ""),
                    "gender": case.gender or "",
                    "arrival_transport": case.arrival_transport or "",
                    "disposition": case.disposition or "",
                }
            )
        except Exception as exc:  # pragma: no cover - runtime-dependent
            failures.append(
                {
                    "stay_id": case.stay_id,
                    "source_row": case.source_row,
                    "chief_complaint_text": case.complaint,
                    "actual_esi": case.actual_esi,
                    "error": f"{type(exc).__name__}: {exc}",
                }
            )

    valid = len(predictions)
    total = valid + len(failures)
    result_summary = {
        "engine_available": True,
        "total_attempted": total,
        "valid_predictions": valid,
        "failed_predictions": len(failures),
        "exact_match_accuracy": round((exact_matches / valid) * 100, 2) if valid else 0.0,
        "within_one_level_accuracy": round((within_one / valid) * 100, 2) if valid else 0.0,
        "over_triage_rate": round((over_triage / valid) * 100, 2) if valid else 0.0,
        "under_triage_rate": round((under_triage / valid) * 100, 2) if valid else 0.0,
        "critical_under_triage_rate": round((critical_under_triage / valid) * 100, 4) if valid else 0.0,
        "critical_under_triage_count": critical_under_triage,
        "confusion_matrix": {
            actual: {str(pred): count for pred, count in sorted(counter.items())}
            for actual, counter in sorted(confusion.items())
        },
        "top_miss_buckets": top_miss_buckets(predictions),
        "notes": _build_replay_notes(cases),
        "failures_preview": failures[:20],
    }
    return {
        "summary": result_summary,
        "predictions": predictions,
        "failures": failures,
    }


def _build_replay_notes(cases: Iterable[ReplayCase]) -> List[str]:
    cases_list = list(cases) if not isinstance(cases, list) else cases
    has_gender = any(c.gender is not None for c in cases_list)
    has_real_age = any(c.age is not None for c in cases_list)
    if has_gender and has_real_age:
        return [
            "Replay used complaint text from MIMIC-IV-ED triage table.",
            "Real age (anchor_age) joined from MIMIC-IV core patients.csv.gz via edstays.subject_id. "
            "Pediatric (<3) and elderly (>=65) age modifiers fully active.",
            "Gender enriched from edstays.csv.gz.",
            "Vitals merged: worst (most abnormal) reading from vitalsign.csv.gz combined with triage vitals.",
            "Arrival transport from edstays used for arrived_by_ambulance flag.",
            "This is suitable for retrospective replay benchmarking, not for claiming prospective clinical validation.",
        ]
    if has_gender:
        return [
            "Replay used complaint text from MIMIC-IV-ED triage table.",
            "Demographics (gender) enriched from edstays.csv.gz. Age used neutral placeholder — "
            "run with --patients-path to enable real age and activate age-based modifiers.",
            "Vitals merged: worst (most abnormal) reading from vitalsign.csv.gz combined with triage vitals.",
            "Arrival transport from edstays used for arrived_by_ambulance flag.",
            "This is suitable for retrospective replay benchmarking, not for claiming prospective clinical validation.",
        ]
    return [
        "Replay used complaint text and triage vitals from MIMIC-IV-ED.",
        "Age/gender were neutral placeholders because the local ED extract does not include demographics.",
        "This is suitable for retrospective replay benchmarking, not for claiming prospective clinical validation.",
    ]


def top_miss_buckets(predictions: Iterable[Dict[str, Any]]) -> List[Tuple[str, int]]:
    counter: Counter[str] = Counter()
    for row in predictions:
        if not row.get("exact_match"):
            counter[str(row.get("complaint_bucket") or "unknown")] += 1
    return counter.most_common(20)


def write_predictions_csv(path: Path, predictions: Iterable[Dict[str, Any]]) -> None:
    predictions = list(predictions)
    if not predictions:
        with path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            writer.writerow(["stay_id", "chief_complaint_text", "actual_esi", "predicted_esi"])
        return

    fieldnames = list(predictions[0].keys())
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in predictions:
            writer.writerow(row)


def main() -> int:
    args = parse_args()
    cases, dataset_summary = load_replay_cases(args.triage_path)
    sampled_cases, sample_summary = sample_cases(
        cases=cases,
        target_cases=args.target_cases,
        seed=args.seed,
        max_per_bucket=args.max_per_complaint_bucket,
    )

    # Enrich with real demographics and worst vitals if requested
    enrich_summary = None
    if args.enrich or args.clean_only or args.clean_all_esi:
        sampled_cases, enrich_summary = enrich_cases(
            sampled_cases,
            edstays_path=args.edstays_path,
            vitalsign_path=args.vitalsign_path,
            patients_path=args.patients_path,
        )

    # Phase 2: heuristic filter — strip impossible label/presentation combos
    heuristic_filter_summary = None
    if args.heuristic_filter:
        sampled_cases, heuristic_filter_summary = apply_heuristic_filter(sampled_cases)
        removed = heuristic_filter_summary["total_in"] - heuristic_filter_summary["total_out"]
        print(
            f"Heuristic filter removed {removed} impossible cases "
            f"({heuristic_filter_summary['removed_noise_complaint']} noise-complaint, "
            f"{heuristic_filter_summary['removed_transfer']} transfer, "
            f"{heuristic_filter_summary['removed_esi5_critical_vitals']} ESI5-critical-vitals)"
        )

    # Phase 1: clean filter — keep only outcome-confirmed cases
    clean_filter_summary = None
    use_all_esi = args.clean_all_esi
    use_clean = args.clean_only or use_all_esi

    if use_clean:
        sampled_cases, clean_filter_summary = apply_clean_filter(sampled_cases, all_esi=use_all_esi)
        kept_by_level = clean_filter_summary.get("kept_by_level", {})
        level_str = ", ".join(f"ESI {k}={v}" for k, v in sorted(kept_by_level.items()))
        mode_label = "all-ESI" if use_all_esi else "critical+non-urgent"
        print(
            f"Clean filter ({mode_label}): kept {clean_filter_summary['total_out']} outcome-confirmed cases "
            f"({level_str}) from {clean_filter_summary['total_in']} enriched cases"
        )
        if clean_filter_summary["total_out"] == 0:
            print("ERROR: No cases remain after clean filter. Check that disposition data is available.")
            return 1

    # Engine-fair filter: only keep cases the engine can meaningfully evaluate
    engine_fair_summary = None
    if args.engine_fair:
        sampled_cases, engine_fair_summary = apply_engine_fair_filter(sampled_cases)
        if not engine_fair_summary.get("skipped"):
            excluded = engine_fair_summary["total_in"] - engine_fair_summary["total_out"]
            print(
                f"Engine-fair filter: kept {engine_fair_summary['total_out']} classifiable cases "
                f"(excluded {engine_fair_summary['excluded_unclear']} unclear, "
                f"{engine_fair_summary['excluded_no_vitals']} no-vitals, "
                f"{engine_fair_summary['excluded_both']} both) "
                f"from {engine_fair_summary['total_in']}"
            )

    tag = args.tag
    if tag is None:
        clean_prefix = "clean-all" if use_all_esi else "clean" if args.clean_only else ""
        heuristic_suffix = "-heuristic" if args.heuristic_filter else ""
        fair_suffix = "-fair" if args.engine_fair else ""
        if clean_prefix:
            tag = f"{clean_prefix}{heuristic_suffix}{fair_suffix}-{args.target_cases}"
        elif args.heuristic_filter or args.engine_fair:
            tag = f"{'heuristic' if args.heuristic_filter else ''}{fair_suffix}-{args.target_cases}".lstrip("-")
        elif args.enrich:
            tag = f"enriched-{args.target_cases}"
    prefix = make_output_prefix(args.output_dir, tag, args.target_cases)
    sample_csv_path = prefix.with_suffix(".sample.csv")
    summary_json_path = prefix.with_suffix(".summary.json")
    predictions_csv_path = prefix.with_suffix(".predictions.csv")

    write_sample_csv(sample_csv_path, sampled_cases)

    payload: Dict[str, Any] = {
        "dataset_summary": dataset_summary,
        "sample_summary": sample_summary,
        "artifacts": {
            "sample_csv": str(sample_csv_path),
        },
    }
    if enrich_summary:
        payload["enrich_summary"] = enrich_summary
    if heuristic_filter_summary:
        payload["heuristic_filter_summary"] = heuristic_filter_summary
    if clean_filter_summary:
        payload["clean_filter_summary"] = clean_filter_summary
    if engine_fair_summary and not engine_fair_summary.get("skipped"):
        payload["engine_fair_summary"] = engine_fair_summary

    if not args.sample_only:
        replay_result = run_replay(
            cases=sampled_cases,
            default_age=args.default_age,
            default_gender=args.default_gender,
        )
        payload["replay_summary"] = replay_result["summary"]
        if replay_result["summary"].get("engine_available"):
            write_predictions_csv(predictions_csv_path, replay_result["predictions"])
            payload["artifacts"]["predictions_csv"] = str(predictions_csv_path)
        else:
            payload["artifacts"]["predictions_csv"] = None

    summary_json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    print("=" * 72)
    print("SAFE-Triage MIMIC Replay Benchmark")
    print("=" * 72)
    print(f"Usable MIMIC-IV-ED rows: {dataset_summary['usable_rows']:,}")
    print(f"Unique complaint buckets: {dataset_summary['unique_complaint_buckets']:,}")
    print(f"Sample selected: {sample_summary['selected_cases']:,}")
    if heuristic_filter_summary:
        print(f"After heuristic filter: {heuristic_filter_summary['total_out']:,} cases")
    if clean_filter_summary:
        kept_by_level = clean_filter_summary.get("kept_by_level", {})
        level_str = ", ".join(f"ESI {k}={v}" for k, v in sorted(kept_by_level.items()))
        print(f"After clean filter (outcome-confirmed): {clean_filter_summary['total_out']:,} cases ({level_str})")
    if engine_fair_summary and not engine_fair_summary.get("skipped"):
        print(f"After engine-fair filter: {engine_fair_summary['total_out']:,} cases (excluded {engine_fair_summary['excluded_unclear']} unclear)")
    print(f"Sample CSV: {sample_csv_path}")
    print(f"Summary JSON: {summary_json_path}")

    replay_summary = payload.get("replay_summary")
    if replay_summary:
        if replay_summary.get("engine_available"):
            print("")
            print(f"Exact-match accuracy: {replay_summary['exact_match_accuracy']:.2f}%")
            print(f"Within-one-level accuracy: {replay_summary['within_one_level_accuracy']:.2f}%")
            print(f"Critical under-triage: {replay_summary['critical_under_triage_count']}")
            print(f"Predictions CSV: {predictions_csv_path}")
        else:
            print("")
            print("Replay skipped: SAFE-Triage runtime is not available in this Python environment.")
            print(f"Runtime import error: {replay_summary['engine_import_error']}")
            print("The benchmark sample was still generated, so you can rerun this script inside the backend runtime later.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
