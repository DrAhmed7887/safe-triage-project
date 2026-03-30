"""
MIETIC Benchmark Runner
=======================

Runs the SAFE-Triage deterministic engine against MIETIC expert-validated
cases and produces reproducible benchmark outputs.

This is the PRIMARY public benchmark for SAFE-Triage.

Usage:
    cd backend
    python -m benchmarks.mietic_benchmark [--output-dir DIR] [--all-cases]

Outputs:
    - predictions.csv      Row-level predictions
    - summary.json         Machine-readable metrics
    - report.md            Human-readable Markdown report
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

# Ensure backend/ is on sys.path for imports
_backend_dir = Path(__file__).resolve().parent.parent
if str(_backend_dir) not in sys.path:
    sys.path.insert(0, str(_backend_dir))

from benchmarks.metrics import BenchmarkMetrics, Prediction, compute_metrics, render_markdown_report
from benchmarks.mietic_loader import (
    MIETICValidatedCase,
    load_mietic_validated,
    validated_summary,
)
from benchmarks.safety import classify_triage_error, is_critical_under_triage


def build_patient_input(case: MIETICValidatedCase):
    """
    Convert a MIETIC validated case to a PatientInput for the triage engine.

    Uses the clinical vignette (tiragecase) as the chief complaint text,
    which contains the full narrative including demographics, vitals, and
    history — giving the engine the richest possible input.

    Falls back to the raw chief_complaint field if tiragecase is empty.
    """
    from models import PatientInput, Vitals, Gender

    # Use clinical vignette if available, else raw chief complaint
    complaint_text = case.triage_case if case.triage_case else case.chief_complaint

    # Parse pain score from the pain field
    pain_score = 0
    if case.pain is not None:
        try:
            pain_score = min(10, max(0, int(float(case.pain))))
        except (ValueError, TypeError):
            # Non-numeric pain values like "Critical", "uta" -> high pain
            if case.pain.lower() in ("critical", "severe"):
                pain_score = 10
            else:
                pain_score = 0

    # Map gender
    gender = Gender.MALE if case.gender == "M" else Gender.FEMALE

    # Temperature: MIETIC uses Fahrenheit, engine expects Celsius
    temp_c = None
    if case.temperature is not None:
        if case.temperature > 50:  # Clearly Fahrenheit
            temp_c = round((case.temperature - 32) * 5 / 9, 1)
        else:
            temp_c = case.temperature

    vitals = Vitals(
        hr=int(case.heartrate) if case.heartrate is not None else None,
        rr=int(case.resprate) if case.resprate is not None else None,
        spo2=case.o2sat,
        temp=temp_c,
        sbp=int(case.sbp) if case.sbp is not None else None,
        dbp=int(case.dbp) if case.dbp is not None else None,
        pain_score=pain_score,
    )

    patient = PatientInput(
        age=case.age,
        gender=gender,
        chief_complaint_text=complaint_text,
        vitals=vitals,
        consciousness="A",  # MIETIC does not provide ACVPU
        arrived_by_ambulance=(case.arrival_transport == "AMBULANCE"),
    )
    return patient


def run_benchmark(
    mietic_dir: str | Path | None = None,
    *,
    retain_only: bool = True,
    output_dir: str | Path | None = None,
) -> BenchmarkMetrics:
    """
    Run the MIETIC benchmark end-to-end.

    Args:
        mietic_dir: Path to MIETIC dataset directory.
        retain_only: Only use expert-RETAIN cases (default True).
        output_dir: Where to save outputs. None = don't save.

    Returns:
        BenchmarkMetrics with all results.
    """
    from logic.deterministic_triage import DeterministicTriageEngine

    # Load cases
    cases = load_mietic_validated(mietic_dir, retain_only=retain_only)
    summary = validated_summary(cases)
    print(f"Loaded {len(cases)} MIETIC validated cases")
    print(f"  Acuity distribution: {summary['acuity_distribution']}")
    print(f"  Cases with missing vitals: {summary['has_missing_vitals']}")

    # Validate minimum expectations
    if retain_only and len(cases) < 20:
        raise RuntimeError(
            f"Expected at least 20 RETAIN cases, got {len(cases)}. "
            "Dataset may be corrupted or filtered incorrectly."
        )

    # Initialize engine
    engine = DeterministicTriageEngine()

    # Run predictions
    predictions: list[Prediction] = []
    failures: list[dict] = []

    for i, case in enumerate(cases):
        case_id = f"stay_{case.stay_id}"
        try:
            patient = build_patient_input(case)
            result = engine.evaluate(patient)
            predicted_esi = int(
                getattr(result.level, "value", result.level)
            )

            predictions.append(Prediction(
                case_id=case_id,
                actual_esi=case.acuity,
                predicted_esi=predicted_esi,
                chief_complaint=case.chief_complaint,
            ))
        except Exception as e:
            failures.append({
                "case_id": case_id,
                "error": str(e),
                "actual_esi": case.acuity,
                "chief_complaint": case.chief_complaint,
            })
            print(f"  FAILED case {case_id}: {e}")

    print(f"\nPredictions: {len(predictions)}, Failures: {len(failures)}")

    if not predictions:
        raise RuntimeError("All cases failed. Cannot compute metrics.")

    # Compute metrics
    metrics = compute_metrics(predictions)

    # Print summary
    print(f"\n{'='*60}")
    print(f"MIETIC Benchmark Results")
    print(f"{'='*60}")
    print(f"  Exact match:           {metrics.exact_match_rate:.1%} ({metrics.exact_match}/{metrics.total})")
    print(f"  Within-one-level:      {metrics.within_one_rate:.1%} ({metrics.within_one}/{metrics.total})")
    print(f"  Under-triage:          {metrics.under_triage_rate:.1%} ({metrics.under_triage}/{metrics.total})")
    print(f"  Over-triage:           {metrics.over_triage_rate:.1%} ({metrics.over_triage}/{metrics.total})")
    print(f"  Critical under-triage: {metrics.critical_under_triage_rate:.1%} ({metrics.critical_under_triage}/{metrics.total})")
    print(f"{'='*60}")

    if metrics.critical_under_triage > 0:
        print(f"\n  *** SAFETY GATE FAILED: {metrics.critical_under_triage} critical under-triage cases ***")
        for c in metrics.critical_under_triage_cases:
            print(f"    - {c.case_id}: actual ESI {c.actual_esi} -> predicted ESI {c.predicted_esi} ({c.chief_complaint[:50]})")
    else:
        print(f"\n  SAFETY GATE PASSED: Zero critical under-triage")

    # Save outputs
    if output_dir is not None:
        _save_outputs(output_dir, metrics, predictions, failures, summary)

    return metrics


def _save_outputs(
    output_dir: str | Path,
    metrics: BenchmarkMetrics,
    predictions: list[Prediction],
    failures: list[dict],
    dataset_summary: dict,
) -> None:
    """Save benchmark outputs to disk."""
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")

    # predictions.csv
    csv_path = out / "predictions.csv"
    with open(csv_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([
            "case_id", "actual_esi", "predicted_esi",
            "exact_match", "within_one", "error_type", "chief_complaint",
        ])
        for p in predictions:
            writer.writerow([
                p.case_id,
                p.actual_esi,
                p.predicted_esi,
                int(p.actual_esi == p.predicted_esi),
                int(abs(p.actual_esi - p.predicted_esi) <= 1),
                classify_triage_error(p.actual_esi, p.predicted_esi),
                p.chief_complaint,
            ])
    print(f"  Saved {csv_path}")

    # summary.json
    json_path = out / "summary.json"
    summary_data = {
        "benchmark": "MIETIC",
        "timestamp": timestamp,
        "dataset": dataset_summary,
        "metrics": metrics.to_dict(),
        "failures": failures,
    }
    with open(json_path, "w") as f:
        json.dump(summary_data, f, indent=2, ensure_ascii=False)
    print(f"  Saved {json_path}")

    # report.md
    md_path = out / "report.md"
    report = render_markdown_report(
        metrics,
        title="MIETIC Benchmark Report",
        dataset_info={
            "Source": "MIMIC-IV-ED Triage Instruction Corpus (MIETIC)",
            "Subset": "Expert-validated RETAIN cases",
            "Total cases": dataset_summary["total"],
            "Acuity distribution": str(dataset_summary["acuity_distribution"]),
            "Cases with missing vitals": dataset_summary["has_missing_vitals"],
            "Timestamp": timestamp,
        },
    )
    with open(md_path, "w") as f:
        f.write(report)
    print(f"  Saved {md_path}")


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run SAFE-Triage against MIETIC validated cases"
    )
    parser.add_argument(
        "--mietic-dir",
        default=None,
        help="Path to MIETIC dataset directory",
    )
    parser.add_argument(
        "--output-dir",
        default="benchmarks/outputs/mietic",
        help="Output directory for results (default: benchmarks/outputs/mietic)",
    )
    parser.add_argument(
        "--all-cases",
        action="store_true",
        help="Include all cases, not just expert-RETAIN",
    )
    args = parser.parse_args()

    metrics = run_benchmark(
        mietic_dir=args.mietic_dir,
        retain_only=not args.all_cases,
        output_dir=args.output_dir,
    )

    # Exit with non-zero if critical under-triage found
    if metrics.critical_under_triage > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
