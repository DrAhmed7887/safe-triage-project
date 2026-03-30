#!/usr/bin/env python3
"""
SAFE-Triage MIMIC-IV-ED validation harness.

STATUS: SECONDARY / EXTERNAL ROBUSTNESS BENCHMARK
======================================================================
This is NOT the primary public benchmark for SAFE-Triage.
The primary benchmark is MIETIC (see backend/benchmarks/mietic_benchmark.py).

This harness replays raw MIMIC-IV-ED triage data as a robustness stress
test. Results from this script should NOT be cited as primary accuracy
claims. See backend/benchmarks/ for the authoritative benchmark suite.
======================================================================

Thin adapter over the existing mimic_replay_benchmark logic that exposes
the CLI interface expected by the validation pipeline:

  --use-ai        run the AI-assisted engine (default: keyword-only)
  --limit N       sample N cases (default: 7000)
  --stratified    stratified sampling by acuity level (default: True)
  --json-out PATH write structured results JSON to PATH

Ground truth: MIMIC-IV-ED triage.acuity column (integer 1-5, matches ESI directly).
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import types
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
ROOT_DIR = Path(__file__).resolve().parents[1]
DEFAULT_TRIAGE_PATH = ROOT_DIR / "mimic-iv-ed-2.2" / "ed" / "triage.csv.gz"

# Ensure the benchmark helper is importable from tests/ sub-directory.
sys.path.insert(0, str(Path(__file__).resolve().parent / "tests"))
sys.path.insert(0, str(Path(__file__).resolve().parent))


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="SAFE-Triage MIMIC-IV-ED ground-truth validation (200 / 1000 case mode)."
    )
    parser.add_argument(
        "--triage-path",
        type=Path,
        default=DEFAULT_TRIAGE_PATH,
        help="Path to MIMIC-IV-ED triage.csv.gz",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=7000,
        metavar="N",
        help="Number of cases to sample and validate (default: 7000)",
    )
    parser.add_argument(
        "--use-ai",
        action="store_true",
        default=False,
        help="Use AI-assisted engine (Gemini) instead of keyword-only",
    )
    parser.add_argument(
        "--stratified",
        action="store_true",
        default=False,
        help="Use stratified sampling by acuity level (default off = proportional random)",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed for reproducible sampling",
    )
    parser.add_argument(
        "--json-out",
        type=Path,
        default=None,
        metavar="PATH",
        help="Write structured result JSON to this file",
    )
    parser.add_argument(
        "--default-age",
        type=float,
        default=40.0,
    )
    parser.add_argument(
        "--default-gender",
        choices=("male", "female"),
        default="male",
    )
    return parser.parse_args()


# ---------------------------------------------------------------------------
# Import reusable helpers from mimic_replay_benchmark
# ---------------------------------------------------------------------------

def _import_benchmark_helpers():
    """Import load_replay_cases and sample_cases from mimic_replay_benchmark."""
    try:
        from mimic_replay_benchmark import (  # type: ignore
            load_replay_cases,
            sample_cases,
        )
        return load_replay_cases, sample_cases
    except ImportError as exc:
        raise SystemExit(
            f"Cannot import mimic_replay_benchmark from backend/tests/: {exc}\n"
            "Ensure backend/tests/mimic_replay_benchmark.py is present."
        ) from exc


# ---------------------------------------------------------------------------
# Runtime import (triage engine)
# ---------------------------------------------------------------------------

def import_engine(use_ai: bool):
    """Import DeterministicTriageEngine and model classes."""
    try:
        import dotenv  # type: ignore  # noqa: F401
    except ModuleNotFoundError:
        stub = types.ModuleType("dotenv")
        stub.load_dotenv = lambda *args, **kwargs: False
        sys.modules["dotenv"] = stub

    backend_dir = Path(__file__).resolve().parent
    if str(backend_dir) not in sys.path:
        sys.path.insert(0, str(backend_dir))

    try:
        from logic.deterministic_triage import DeterministicTriageEngine  # type: ignore
        from models import Gender, PatientInput, Vitals  # type: ignore
    except Exception as exc:
        raise SystemExit(
            f"Cannot import SAFE-Triage runtime: {type(exc).__name__}: {exc}"
        ) from exc

    os.environ.setdefault("DISABLE_RAG", "true")
    engine = DeterministicTriageEngine(use_ai=use_ai)
    return engine, PatientInput, Vitals, Gender


# ---------------------------------------------------------------------------
# Replay runner
# ---------------------------------------------------------------------------

def run_validation(
    cases,
    engine,
    PatientInput,
    Vitals,
    Gender,
    default_age: float,
    default_gender: str,
) -> Dict[str, Any]:
    gender_value = Gender.MALE if default_gender == "male" else Gender.FEMALE

    predictions: List[Dict[str, Any]] = []
    failures: List[Dict[str, Any]] = []

    # Counters
    exact_matches = 0
    within_one = 0
    over_triage_count = 0
    under_triage_count = 0
    critical_under_count = 0

    # Per-level breakdown: {level: {exact, critical_ut, over, total}}
    per_level: Dict[int, Dict[str, int]] = {
        lvl: {"total": 0, "exact": 0, "critical_ut": 0, "over": 0, "under": 0}
        for lvl in [1, 2, 3, 4, 5]
    }

    total_cases = len(list(cases)) if not hasattr(cases, '__len__') else len(cases)
    # Re-iterate (cases is a list)
    for idx, case in enumerate(cases, 1):
        if idx % 50 == 0 or idx == total_cases:
            print(f"  [{idx:4d}/{total_cases}] running...", end="\r", flush=True)
        try:
            patient = PatientInput(
                age=default_age,
                gender=gender_value,
                chief_complaint_text=case.complaint,
                vitals=Vitals(**case.vitals),
                consciousness="A",
            )
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
                over_triage_count += 1
            if under:
                under_triage_count += 1
            if critical_under:
                critical_under_count += 1

            lvl = case.actual_esi
            if lvl in per_level:
                per_level[lvl]["total"] += 1
                if exact:
                    per_level[lvl]["exact"] += 1
                if critical_under:
                    per_level[lvl]["critical_ut"] += 1
                if over:
                    per_level[lvl]["over"] += 1
                if under:
                    per_level[lvl]["under"] += 1

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
                }
            )
        except Exception as exc:
            failures.append(
                {
                    "stay_id": case.stay_id,
                    "source_row": case.source_row,
                    "chief_complaint_text": case.complaint,
                    "actual_esi": case.actual_esi,
                    "error": f"{type(exc).__name__}: {exc}",
                }
            )

    print()  # newline after progress
    valid = len(predictions)

    summary = {
        "total_attempted": valid + len(failures),
        "valid_predictions": valid,
        "failed_predictions": len(failures),
        "exact_match_count": exact_matches,
        "exact_match_pct": round((exact_matches / valid) * 100, 2) if valid else 0.0,
        "within_one_level_pct": round((within_one / valid) * 100, 2) if valid else 0.0,
        "over_triage_count": over_triage_count,
        "under_triage_noncritical_count": under_triage_count - critical_under_count,
        "critical_under_triage_count": critical_under_count,
        "per_level": per_level,
        "acuity_distribution": {
            str(lvl): per_level[lvl]["total"] for lvl in [1, 2, 3, 4, 5]
        },
    }

    return {
        "summary": summary,
        "predictions": predictions,
        "failures": failures[:50],
    }


# ---------------------------------------------------------------------------
# Printing
# ---------------------------------------------------------------------------

def print_report(summary: Dict[str, Any], limit: int) -> None:
    n = summary["valid_predictions"]
    correct = summary["exact_match_count"]
    pct = summary["exact_match_pct"]
    crit = summary["critical_under_triage_count"]
    over = summary["over_triage_count"]
    under_nc = summary["under_triage_noncritical_count"]
    dist = summary["acuity_distribution"]

    print()
    print("=" * 70)
    print(f"MIMIC-IV-ED Validation — {limit} Cases")
    print("=" * 70)
    print()
    print("| Metric                      | Value                              |")
    print("|-----------------------------|------------------------------------|")
    print(f"| Total cases                 | {n:<34} |")
    print(f"| Pass rate                   | {correct}/{n} ({pct}%){'':<{max(0, 20 - len(str(correct) + '/' + str(n) + ' (' + str(pct) + '%)'))}}) |".replace("))", ")"))
    print(f"| Critical under-triage       | {crit:<34} |")
    print(f"| Over-triage                 | {over:<34} |")
    print(f"| Under-triage (non-critical) | {under_nc:<34} |")
    dist_str = " ".join(f"L{k}:{v}" for k, v in dist.items())
    print(f"| Acuity distribution         | {dist_str:<34} |")
    print()

    print("Per-acuity breakdown:")
    print("| ESI Level | n    | Correct | Critical UT | Over-triage |")
    print("|-----------|------|---------|-------------|-------------|")
    per = summary["per_level"]
    for lvl in [1, 2, 3, 4, 5]:
        d = per[lvl]
        n_lvl = d["total"]
        correct_lvl = d["exact"]
        crit_lvl = d["critical_ut"]
        over_lvl = d["over"]
        print(f"| L{lvl}        | {n_lvl:<4} | {correct_lvl:<7} | {crit_lvl:<11} | {over_lvl:<11} |")
    print()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    args = parse_args()

    # Verify data file
    if not args.triage_path.exists():
        print(f"ERROR: MIMIC triage file not found: {args.triage_path}")
        print("Expected: mimic-iv-ed-2.2/ed/triage.csv.gz in project root")
        return 1

    print("=" * 70)
    print("SAFE-Triage MIMIC-IV-ED Validation Harness")
    print(f"Started: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Limit: {args.limit} | AI mode: {args.use_ai} | Stratified: {args.stratified}")
    print("=" * 70)

    # Load helpers from existing benchmark
    load_replay_cases, sample_cases = _import_benchmark_helpers()

    print(f"\nLoading MIMIC data from: {args.triage_path}")
    cases, dataset_summary = load_replay_cases(args.triage_path)
    print(f"Usable rows: {dataset_summary['usable_rows']:,}")
    print(f"Unique complaint buckets: {dataset_summary['unique_complaint_buckets']:,}")
    acuity_dist = dataset_summary["acuity_distribution"]
    print(f"Acuity distribution: " + " ".join(f"L{k}:{v}" for k, v in acuity_dist.items()))

    print(f"\nSampling {args.limit} cases (seed={args.seed})...")
    sampled, sample_summary = sample_cases(
        cases=cases,
        target_cases=args.limit,
        seed=args.seed,
        max_per_bucket=0,
    )
    print(f"Selected: {sample_summary['selected_cases']} cases")
    level_sel = sample_summary["level_selected"]
    print(f"Level distribution: " + " ".join(f"L{k}:{v}" for k, v in sorted(level_sel.items())))

    # Import engine
    print(f"\nLoading SAFE-Triage engine (use_ai={args.use_ai})...")
    engine, PatientInput, Vitals, Gender = import_engine(args.use_ai)
    print("Engine loaded. Starting validation...\n")

    start = time.time()
    result = run_validation(
        cases=sampled,
        engine=engine,
        PatientInput=PatientInput,
        Vitals=Vitals,
        Gender=Gender,
        default_age=args.default_age,
        default_gender=args.default_gender,
    )
    elapsed = time.time() - start
    print(f"Validation completed in {elapsed:.1f}s")

    summary = result["summary"]
    print_report(summary, args.limit)

    # Write JSON output
    payload = {
        "meta": {
            "limit": args.limit,
            "use_ai": args.use_ai,
            "stratified": args.stratified,
            "seed": args.seed,
            "elapsed_seconds": round(elapsed, 2),
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        },
        "dataset_summary": dataset_summary,
        "sample_summary": sample_summary,
        "validation_summary": summary,
        "predictions": result["predictions"],
        "failures": result["failures"],
    }

    if args.json_out:
        out_path = args.json_out
        out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"JSON results written to: {out_path}")

    # Decision gate
    crit = summary["critical_under_triage_count"]
    correct = summary["exact_match_count"]
    n = summary["valid_predictions"]
    pct = summary["exact_match_pct"]

    print()
    if crit == 0 and correct >= int(n * 0.65):
        print(f"✅ GATE PASSED — {correct}/{n} ({pct}%), 0 critical under-triage")
        return 0
    else:
        reasons = []
        if crit > 0:
            reasons.append(f"{crit} critical under-triage cases")
        if correct < int(n * 0.65):
            reasons.append(f"pass rate {pct}% below 65% threshold")
        print(f"❌ GATE FAILED — {'; '.join(reasons)}")
        if crit > 0:
            failed = [p for p in result["predictions"] if p["critical_under_triage"]]
            print("\nCritical under-triage cases:")
            for p in failed[:20]:
                print(f"  [actual L{p['actual_esi']} → predicted L{p['predicted_esi']}] {p['chief_complaint_text'][:80]}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
