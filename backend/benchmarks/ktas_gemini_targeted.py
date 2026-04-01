"""
KTAS Gemini Targeted Benchmark
===============================

Runs ONLY the 63 critical under-triage cases through the Gemini-enhanced
engine (use_ai=True) and compares against the deterministic-only results.

This isolates the AI value: same cases, same engine, but with Gemini
classification instead of keyword matching.

Usage:
    cd backend
    python -m benchmarks.ktas_gemini_targeted [--data-path PATH]
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

_backend_dir = Path(__file__).resolve().parent.parent
if str(_backend_dir) not in sys.path:
    sys.path.insert(0, str(_backend_dir))

from benchmarks.ktas_loader import KTASCase, load_ktas_cases, MENTAL_TO_ACVPU
from benchmarks.ktas_benchmark import build_patient_input
from benchmarks.metrics import BenchmarkMetrics, Prediction, compute_metrics
from benchmarks.safety import classify_triage_error


def load_critical_case_ids(predictions_path: str | Path) -> set[str]:
    """Load case IDs that were critical under-triage in the deterministic run."""
    case_ids = set()
    with open(predictions_path) as f:
        for row in csv.DictReader(f):
            if row["error_type"] == "critical_under_triage":
                case_ids.add(row["case_id"])
    return case_ids


def run_targeted_benchmark(
    data_path: str | Path | None = None,
    *,
    output_dir: str | Path | None = None,
) -> None:
    """Run the 63 critical cases through both deterministic and Gemini engines."""
    from dotenv import load_dotenv
    load_dotenv()

    from logic.deterministic_triage import DeterministicTriageEngine

    # Load all cases, then filter to just the critical ones
    all_cases = load_ktas_cases(data_path)
    cases_by_id = {f"ktas_row_{c.row_index}": c for c in all_cases}

    # Load critical case IDs from previous deterministic run
    det_predictions_path = Path("benchmarks/outputs/ktas/predictions.csv")
    if not det_predictions_path.exists():
        print("ERROR: Run ktas_benchmark.py first to generate deterministic predictions.")
        sys.exit(1)

    critical_ids = load_critical_case_ids(det_predictions_path)
    print(f"Loaded {len(critical_ids)} critical under-triage case IDs from deterministic run")

    critical_cases = [(cid, cases_by_id[cid]) for cid in sorted(critical_ids) if cid in cases_by_id]
    print(f"Matched {len(critical_cases)} cases in KTAS dataset")

    # Load deterministic predictions for comparison
    det_preds = {}
    with open(det_predictions_path) as f:
        for row in csv.DictReader(f):
            if row["case_id"] in critical_ids:
                det_preds[row["case_id"]] = int(row["predicted_esi"])

    # Run through Gemini-enhanced engine
    print("\nInitializing Gemini-enhanced engine...")
    engine_ai = DeterministicTriageEngine(use_ai=True)

    ai_predictions: list[Prediction] = []
    failures: list[dict] = []
    improvements = []
    regressions = []

    for i, (case_id, case) in enumerate(critical_cases):
        patient = build_patient_input(case)
        try:
            result = engine_ai.evaluate(patient)
            predicted_esi = int(getattr(result.level, "value", result.level))

            ai_predictions.append(Prediction(
                case_id=case_id,
                actual_esi=case.ktas_expert,
                predicted_esi=predicted_esi,
                chief_complaint=case.chief_complaint,
            ))

            det_esi = det_preds.get(case_id, 0)
            actual = case.ktas_expert

            if predicted_esi < det_esi:
                improvements.append({
                    "case_id": case_id,
                    "complaint": case.chief_complaint,
                    "actual": actual,
                    "det_esi": det_esi,
                    "ai_esi": predicted_esi,
                    "extraction": getattr(result, "extraction_method", "unknown"),
                })
            elif predicted_esi > det_esi:
                regressions.append({
                    "case_id": case_id,
                    "complaint": case.chief_complaint,
                    "actual": actual,
                    "det_esi": det_esi,
                    "ai_esi": predicted_esi,
                })

            status = "IMPROVED" if predicted_esi <= actual else ("SAME" if predicted_esi == det_esi else "WORSE")
            print(f"  [{i+1}/{len(critical_cases)}] {case.chief_complaint:<35} "
                  f"KTAS {actual} | det->ESI {det_esi} | ai->ESI {predicted_esi} {status}")

            # Rate limit: Gemini has quotas
            time.sleep(0.3)

        except Exception as e:
            failures.append({"case_id": case_id, "error": str(e)})
            print(f"  [{i+1}/{len(critical_cases)}] FAILED {case_id}: {e}")

    # Compute metrics for AI predictions
    if not ai_predictions:
        print("No predictions generated.")
        return

    ai_metrics = compute_metrics(ai_predictions)

    # Build deterministic metrics for the same subset
    det_subset_preds = [
        Prediction(
            case_id=cid,
            actual_esi=cases_by_id[cid].ktas_expert,
            predicted_esi=det_preds[cid],
            chief_complaint=cases_by_id[cid].chief_complaint,
        )
        for cid in sorted(critical_ids)
        if cid in cases_by_id and cid in det_preds
    ]
    det_metrics = compute_metrics(det_subset_preds)

    # Print comparison
    print(f"\n{'='*70}")
    print(f"Gemini vs Deterministic — 63 Critical Under-Triage Cases")
    print(f"{'='*70}")
    print(f"{'Metric':<30} {'Deterministic':>15} {'Gemini':>15}")
    print(f"{'-'*70}")
    print(f"{'Cases':<30} {det_metrics.total:>15} {ai_metrics.total:>15}")
    print(f"{'Exact match':<30} {det_metrics.exact_match_rate:>14.1%} {ai_metrics.exact_match_rate:>14.1%}")
    print(f"{'Within-one-level':<30} {det_metrics.within_one_rate:>14.1%} {ai_metrics.within_one_rate:>14.1%}")
    print(f"{'Under-triage':<30} {det_metrics.under_triage_rate:>14.1%} {ai_metrics.under_triage_rate:>14.1%}")
    print(f"{'Over-triage':<30} {det_metrics.over_triage_rate:>14.1%} {ai_metrics.over_triage_rate:>14.1%}")
    print(f"{'Critical under-triage':<30} {det_metrics.critical_under_triage_rate:>14.1%} {ai_metrics.critical_under_triage_rate:>14.1%}")
    print(f"{'='*70}")

    print(f"\nImprovements (AI more accurate): {len(improvements)}")
    for imp in improvements:
        print(f"  {imp['complaint']:<35} KTAS {imp['actual']} | det ESI {imp['det_esi']} -> ai ESI {imp['ai_esi']}")

    print(f"\nRegressions (AI worse): {len(regressions)}")
    for reg in regressions:
        print(f"  {reg['complaint']:<35} KTAS {reg['actual']} | det ESI {reg['det_esi']} -> ai ESI {reg['ai_esi']}")

    remaining_critical = ai_metrics.critical_under_triage
    print(f"\nCritical under-triage: {det_metrics.critical_under_triage} -> {remaining_critical} "
          f"({det_metrics.critical_under_triage - remaining_critical} fixed by Gemini)")

    if failures:
        print(f"\nFailures: {len(failures)}")

    # Save outputs
    if output_dir:
        out = Path(output_dir)
        out.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")

        # Save detailed results
        results = {
            "benchmark": "KTAS_gemini_targeted",
            "timestamp": timestamp,
            "total_critical_cases": len(critical_cases),
            "deterministic_metrics": det_metrics.to_dict(),
            "gemini_metrics": ai_metrics.to_dict(),
            "improvements": improvements,
            "regressions": regressions,
            "failures": failures,
            "critical_reduction": {
                "before": det_metrics.critical_under_triage,
                "after": ai_metrics.critical_under_triage,
                "fixed": det_metrics.critical_under_triage - ai_metrics.critical_under_triage,
            },
        }
        json_path = out / "gemini_targeted.json"
        with open(json_path, "w") as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        print(f"\nSaved {json_path}")

        # Save per-case CSV
        csv_path = out / "gemini_targeted_predictions.csv"
        with open(csv_path, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow([
                "case_id", "actual_ktas", "det_esi", "ai_esi",
                "det_error", "ai_error", "chief_complaint",
            ])
            for p in ai_predictions:
                det_esi = det_preds.get(p.case_id, 0)
                writer.writerow([
                    p.case_id, p.actual_esi, det_esi, p.predicted_esi,
                    classify_triage_error(p.actual_esi, det_esi),
                    classify_triage_error(p.actual_esi, p.predicted_esi),
                    p.chief_complaint,
                ])
        print(f"Saved {csv_path}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run 63 critical under-triage cases through Gemini-enhanced engine"
    )
    parser.add_argument("--data-path", default=None, help="Path to KTAS CSV file")
    parser.add_argument(
        "--output-dir", default="benchmarks/outputs/ktas",
        help="Output directory (default: benchmarks/outputs/ktas)",
    )
    args = parser.parse_args()

    run_targeted_benchmark(data_path=args.data_path, output_dir=args.output_dir)


if __name__ == "__main__":
    main()
