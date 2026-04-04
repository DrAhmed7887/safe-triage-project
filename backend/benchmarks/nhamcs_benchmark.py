"""
NHAMCS Benchmark Runner
========================

Runs the SAFE-Triage deterministic engine against the National Hospital
Ambulatory Medical Care Survey (NHAMCS) 2021 Emergency Department data.

NHAMCS is a nationally representative US ED survey from the CDC.
IMMEDR field maps directly to ESI 1-5 (Immediate/Emergent/Urgent/Semi-urgent/Nonurgent).

Source: https://ftp.cdc.gov/pub/Health_Statistics/NCHS/Datasets/NHAMCS/
Data use: statistical reporting and analysis only per CDC terms.

Usage:
    cd backend
    python -m benchmarks.nhamcs_benchmark --data-path /tmp/ed2021

Outputs saved to benchmarks/outputs/nhamcs/
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import sys
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

_backend_dir = Path(__file__).resolve().parent.parent
if str(_backend_dir) not in sys.path:
    sys.path.insert(0, str(_backend_dir))

DEFAULT_DATA_PATH = Path("/tmp/ed2021")
DEFAULT_OUTPUT_DIR = Path(__file__).resolve().parent / "outputs" / "nhamcs"
RFV_CODES_PATH = Path("/tmp/nhamcs_rfv_codes.json")

# ── Column positions (SAS 1-based → Python 0-based) ─────────────────
# From ed21inp.txt SAS input statement
COLS = {
    "age":       (15, 18),   # @16 AGE 3.
    "sex":       (24, 25),   # @25 SEX 1.  (1=Female, 2=Male)
    "arrems":    (32, 34),   # @33 ARREMS 2.  (01=Yes ambulance)
    "tempf":     (47, 51),   # @48 TEMPF 4.  (implied decimal: 0983=98.3°F)
    "pulse":     (51, 54),   # @52 PULSE 3.
    "respr":     (54, 57),   # @55 RESPR 3.
    "bpsys":     (57, 60),   # @58 BPSYS 3.
    "bpdias":    (60, 63),   # @61 BPDIAS 3.
    "popct":     (63, 66),   # @64 POPCT 3.  (pulse oximetry %)
    "immedr":    (66, 68),   # @67 IMMEDR 2. (1-5 = ESI levels)
    "painscale": (68, 70),   # @69 PAINSCALE 2.
    "rfv1":      (72, 77),   # @73 RFV1 5.
    "rfv2":      (77, 82),   # @78 RFV2 5.
    "rfv3":      (82, 87),   # @83 RFV3 5.
}


@dataclass
class NHAMCSCase:
    row_index: int
    age: Optional[float]
    sex: Optional[str]         # "M" or "F"
    ambulance: bool
    temp_f: Optional[float]
    hr: Optional[int]
    rr: Optional[int]
    sbp: Optional[int]
    dbp: Optional[int]
    spo2: Optional[float]
    immedr: int                # 1-5 (ESI equivalent)
    pain_score: Optional[int]
    chief_complaint: str       # from RFV codes


def _safe_int(raw: str) -> Optional[int]:
    raw = raw.strip()
    if not raw or raw.startswith("-"):
        return None
    try:
        v = int(raw)
        return v if v > 0 else None
    except ValueError:
        return None


def _safe_float(raw: str) -> Optional[float]:
    raw = raw.strip()
    if not raw or raw.startswith("-"):
        return None
    try:
        v = float(raw)
        return v if v > 0 else None
    except ValueError:
        return None


def load_rfv_codes(path: Path = RFV_CODES_PATH) -> dict[str, str]:
    with open(path) as f:
        return json.load(f)


def parse_nhamcs(
    data_path: Path,
    rfv_map: dict[str, str],
) -> list[NHAMCSCase]:
    """Parse NHAMCS fixed-width file into structured cases."""
    cases: list[NHAMCSCase] = []

    with open(data_path) as f:
        for i, line in enumerate(f):
            # Extract raw fields
            raw = {k: line[c[0]:c[1]] for k, c in COLS.items()}

            # Filter: only keep valid triage levels 1-5
            immedr = _safe_int(raw["immedr"])
            if immedr is None or immedr < 1 or immedr > 5:
                continue

            # Age
            age = _safe_float(raw["age"])
            if age is not None and age > 120:
                age = None

            # Sex: NHAMCS 1=Female, 2=Male
            sex_raw = raw["sex"].strip()
            sex = "F" if sex_raw == "1" else ("M" if sex_raw == "2" else None)

            # Ambulance: ARREMS 01=Yes
            ambulance = raw["arrems"].strip() == "01"

            # Temperature: stored as integer with implied decimal (0983=98.3°F)
            temp_raw = _safe_int(raw["tempf"])
            temp_f = temp_raw / 10.0 if temp_raw and temp_raw > 90 else None

            # Vitals
            hr = _safe_int(raw["pulse"])
            rr = _safe_int(raw["respr"])
            sbp = _safe_int(raw["bpsys"])
            dbp = _safe_int(raw["bpdias"])
            spo2 = _safe_float(raw["popct"])

            # Pain
            pain = _safe_int(raw["painscale"])
            if pain is not None and (pain < 0 or pain > 10):
                pain = None

            # Chief complaint from RFV codes
            complaints = []
            for rfv_key in ("rfv1", "rfv2", "rfv3"):
                code = raw[rfv_key].strip()
                if code and not code.startswith("-"):
                    text = rfv_map.get(code)
                    if text:
                        complaints.append(text)
            chief_complaint = "; ".join(complaints) if complaints else "Unknown"

            # Require at least chief complaint or vitals
            has_vitals = sum(1 for v in [hr, rr, spo2, sbp] if v is not None)
            if chief_complaint == "Unknown" and has_vitals < 2:
                continue

            cases.append(NHAMCSCase(
                row_index=i,
                age=age,
                sex=sex,
                ambulance=ambulance,
                temp_f=temp_f,
                hr=hr,
                rr=rr,
                sbp=sbp,
                dbp=dbp,
                spo2=spo2,
                immedr=immedr,
                pain_score=pain,
                chief_complaint=chief_complaint,
            ))

    return cases


def run_benchmark(cases: list[NHAMCSCase]) -> dict[str, Any]:
    """Run cases through the SAFE-Triage deterministic engine."""
    from logic.deterministic_triage import DeterministicTriageEngine
    from models import PatientInput, Vitals, Gender

    os.environ.setdefault("DISABLE_RAG", "true")
    engine = DeterministicTriageEngine(use_ai=False)

    predictions: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []
    confusion: dict[int, Counter] = {i: Counter() for i in range(1, 6)}
    exact = within_one = over = under = critical_ut = 0

    for idx, case in enumerate(cases):
        if (idx + 1) % 500 == 0:
            print(f"  {idx + 1}/{len(cases)}...")

        try:
            gender = Gender.FEMALE if case.sex == "F" else Gender.MALE
            age = case.age if case.age is not None else 40.0

            # Convert temperature F → C
            temp_c = None
            if case.temp_f is not None and case.temp_f > 50:
                temp_c = round((case.temp_f - 32) * 5 / 9, 1)

            vitals = Vitals(
                hr=case.hr,
                rr=case.rr,
                spo2=case.spo2,
                temp=temp_c,
                sbp=case.sbp,
                dbp=case.dbp,
                pain_score=case.pain_score or 0,
            )

            patient = PatientInput(
                age=age,
                gender=gender,
                chief_complaint_text=case.chief_complaint,
                vitals=vitals,
                consciousness="A",
                arrived_by_ambulance=case.ambulance,
            )

            result = engine.evaluate(patient)
            predicted = int(getattr(result.level, "value", result.level))
            actual = case.immedr

            is_exact = predicted == actual
            is_within = abs(predicted - actual) <= 1
            is_crit_ut = actual <= 2 and predicted > actual
            is_over = predicted < actual
            is_under = predicted > actual

            if is_exact:
                exact += 1
            if is_within:
                within_one += 1
            if is_over:
                over += 1
            if is_under:
                under += 1
            if is_crit_ut:
                critical_ut += 1
            confusion[actual][predicted] += 1

            predictions.append({
                "row_index": case.row_index,
                "actual_esi": actual,
                "predicted_esi": predicted,
                "exact_match": is_exact,
                "within_one": is_within,
                "critical_under_triage": is_crit_ut,
                "chief_complaint": case.chief_complaint[:100],
            })

        except Exception as e:
            failures.append({
                "row_index": case.row_index,
                "actual_esi": case.immedr,
                "error": f"{type(e).__name__}: {e}",
            })

    valid = len(predictions)
    summary = {
        "total_attempted": valid + len(failures),
        "valid_predictions": valid,
        "failed_predictions": len(failures),
        "exact_match_accuracy": round(100 * exact / valid, 2) if valid else 0,
        "within_one_level_accuracy": round(100 * within_one / valid, 2) if valid else 0,
        "over_triage_rate": round(100 * over / valid, 2) if valid else 0,
        "under_triage_rate": round(100 * under / valid, 2) if valid else 0,
        "critical_under_triage_rate": round(100 * critical_ut / valid, 4) if valid else 0,
        "critical_under_triage_count": critical_ut,
        "esi1_recall": _recall(confusion, 1),
        "esi2_recall": _recall(confusion, 2),
        "confusion_matrix": {
            str(a): {str(p): c for p, c in sorted(ct.items())}
            for a, ct in sorted(confusion.items()) if ct
        },
    }
    return {
        "summary": summary,
        "predictions": predictions,
        "failures": failures[:20],
    }


def _recall(confusion: dict[int, Counter], level: int) -> float:
    total = sum(confusion[level].values())
    correct = confusion[level].get(level, 0)
    return round(100 * correct / total, 1) if total else 0.0


def main() -> int:
    parser = argparse.ArgumentParser(description="NHAMCS 2021 ED benchmark")
    parser.add_argument("--data-path", type=Path, default=DEFAULT_DATA_PATH)
    parser.add_argument("--rfv-codes", type=Path, default=RFV_CODES_PATH)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    args = parser.parse_args()

    print("Loading RFV codes...")
    rfv_map = load_rfv_codes(args.rfv_codes)
    print(f"  {len(rfv_map)} RFV code mappings")

    print("Parsing NHAMCS 2021 ED data...")
    cases = parse_nhamcs(args.data_path, rfv_map)
    dist = Counter(c.immedr for c in cases)
    print(f"  Parsed {len(cases)} cases with valid triage levels")
    print(f"  ESI distribution: {dict(sorted(dist.items()))}")

    print("\nRunning engine...")
    result = run_benchmark(cases)
    rs = result["summary"]

    # Save outputs
    args.output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")

    payload = {
        "benchmark": "NHAMCS_2021_ED",
        "timestamp": timestamp,
        "source": "National Hospital Ambulatory Medical Care Survey 2021 (CDC/NCHS)",
        "dataset": {
            "total_rows": len(cases),
            "esi_distribution": dict(sorted(dist.items())),
        },
        "metrics": rs,
        "failures": result["failures"],
    }
    json_path = args.output_dir / "summary.json"
    json_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False))

    pred_path = args.output_dir / "predictions.csv"
    if result["predictions"]:
        with open(pred_path, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=result["predictions"][0].keys())
            writer.writeheader()
            writer.writerows(result["predictions"])

    # Print results
    print(f"\n{'='*60}")
    print("NHAMCS 2021 ED Benchmark Results")
    print(f"{'='*60}")
    print(f"  Cases:                 {rs['valid_predictions']}")
    print(f"  Exact match:           {rs['exact_match_accuracy']:.1f}%")
    print(f"  Within-one-level:      {rs['within_one_level_accuracy']:.1f}%")
    print(f"  Over-triage:           {rs['over_triage_rate']:.1f}%")
    print(f"  Under-triage:          {rs['under_triage_rate']:.1f}%")
    print(f"  Critical under-triage: {rs['critical_under_triage_count']} ({rs['critical_under_triage_rate']:.2f}%)")
    print(f"  ESI-1 recall:          {rs['esi1_recall']:.1f}%")
    print(f"  ESI-2 recall:          {rs['esi2_recall']:.1f}%")

    cm = rs["confusion_matrix"]
    print(f"\n{'':>12}", end="")
    for p in ["1", "2", "3", "4", "5"]:
        print(f"{'pred '+p:>8}", end="")
    print()
    for actual in sorted(cm):
        print(f"  actual {actual}:", end="")
        for p in ["1", "2", "3", "4", "5"]:
            print(f"{cm[actual].get(p, 0):>8}", end="")
        total = sum(cm[actual].values())
        correct = cm[actual].get(actual, 0)
        print(f"  | {correct}/{total} ({100*correct/total:.0f}%)")

    if rs["critical_under_triage_count"] == 0:
        print(f"\n  SAFETY GATE PASSED: Zero critical under-triage")
    else:
        print(f"\n  Critical under-triage: {rs['critical_under_triage_count']} cases")

    print(f"\n  Saved: {json_path}")
    print(f"         {pred_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
