"""
KTAS External Benchmark Runner
===============================

Runs the SAFE-Triage deterministic engine against the KTAS external dataset
(1,267 expert-validated Korean ED cases) and produces benchmark outputs.

This is an EXTERNAL VALIDATION benchmark — non-MIMIC, non-US data.

Usage:
    cd backend
    python -m benchmarks.ktas_benchmark [--data-path PATH] [--output-dir DIR]

Outputs:
    - predictions.csv      Row-level predictions
    - summary.json         Machine-readable metrics
    - report.md            Human-readable Markdown report
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

# Ensure backend/ is on sys.path for imports
_backend_dir = Path(__file__).resolve().parent.parent
if str(_backend_dir) not in sys.path:
    sys.path.insert(0, str(_backend_dir))

from benchmarks.ktas_loader import KTASCase, load_ktas_cases, ktas_summary, MENTAL_TO_ACVPU
from benchmarks.metrics import BenchmarkMetrics, Prediction, compute_metrics, render_markdown_report
from benchmarks.safety import classify_triage_error


def build_patient_input(case: KTASCase):
    """
    Convert a KTASCase to a PatientInput for the triage engine.

    Key mapping decisions:
    - Temperature: already Celsius (no conversion)
    - SpO2: 54% missing, passed as None
    - Pain: NRS if available, else 0
    - Mental→ACVPU: 1→A, 2→C, 3→A, 4→V
    - Ambulance: arrival_mode == 2
    """
    from models import PatientInput, Vitals, Gender

    gender = Gender.MALE if case.sex == 1 else Gender.FEMALE

    pain_score = case.nrs_pain if case.nrs_pain is not None else 0

    vitals = Vitals(
        hr=case.hr,
        rr=case.rr,
        spo2=case.saturation,
        temp=case.bt,  # Already Celsius
        sbp=case.sbp,
        dbp=case.dbp,
        pain_score=pain_score,
    )

    consciousness = MENTAL_TO_ACVPU.get(case.mental, "A")

    # Override consciousness when chief complaint indicates altered mental status
    # The KTAS Mental field codes baseline psychiatric history, NOT current
    # consciousness. A patient presenting with "mental change" is coded
    # Mental=1 (normal baseline) but is clinically confused NOW.
    complaint_lower = case.chief_complaint.lower()
    _AMS_KEYWORDS = {
        "mental change", "altered mentality", "confuse mentality",
        "altered mental", "change in mental", "confusion",
        "loc", "loss of consciousness", "unresponsive",
    }
    if any(kw in complaint_lower for kw in _AMS_KEYWORDS):
        consciousness = "C"  # Confusion on ACVPU

    # Ambulance arrival: mode 2 = ambulance, mode 1 = 119 (Korean emergency)
    arrived_by_ambulance = case.arrival_mode in (1, 2)

    # Enrich complaint with injury context when available
    # KTAS Injury=2 means the presentation is injury/trauma-related
    enriched_complaint = case.chief_complaint
    if case.injury == 2 and "trauma" not in complaint_lower and "injury" not in complaint_lower:
        enriched_complaint = f"{case.chief_complaint} (trauma/injury)"

    patient = PatientInput(
        age=case.age,
        gender=gender,
        chief_complaint_text=enriched_complaint,
        vitals=vitals,
        consciousness=consciousness,
        arrived_by_ambulance=arrived_by_ambulance,
    )
    return patient


def run_benchmark(
    data_path: str | Path | None = None,
    *,
    output_dir: str | Path | None = None,
) -> BenchmarkMetrics:
    """
    Run the KTAS benchmark end-to-end (deterministic engine only).

    Args:
        data_path: Path to the KTAS CSV file.
        output_dir: Where to save outputs. None = don't save.

    Returns:
        BenchmarkMetrics with all results.
    """
    # Disable AI features for deterministic-only benchmark
    os.environ["DISABLE_RAG"] = "true"

    from logic.deterministic_triage import DeterministicTriageEngine

    # Load cases
    cases = load_ktas_cases(data_path)
    summary = ktas_summary(cases)
    print(f"Loaded {len(cases)} KTAS cases")
    print(f"  KTAS expert distribution: {summary['ktas_expert_distribution']}")
    print(f"  Missing SpO2: {summary['missing_spo2']}")
    print(f"  Missing pain: {summary['missing_pain']}")

    # Initialize engine
    engine = DeterministicTriageEngine()

    # Run predictions
    predictions: list[Prediction] = []
    failures: list[dict] = []

    for case in cases:
        case_id = f"ktas_row_{case.row_index}"
        try:
            patient = build_patient_input(case)
            result = engine.evaluate(patient)
            predicted_esi = int(
                getattr(result.level, "value", result.level)
            )

            predictions.append(Prediction(
                case_id=case_id,
                actual_esi=case.ktas_expert,
                predicted_esi=predicted_esi,
                chief_complaint=case.chief_complaint,
            ))
        except Exception as e:
            failures.append({
                "case_id": case_id,
                "error": str(e),
                "actual_esi": case.ktas_expert,
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
    print(f"KTAS External Benchmark Results (Deterministic Only)")
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
            print(f"    - {c.case_id}: actual KTAS {c.actual_esi} -> predicted ESI {c.predicted_esi} ({c.chief_complaint[:50]})")
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
            "case_id", "actual_ktas", "predicted_esi",
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
        "benchmark": "KTAS_external",
        "source": "Kaggle: ilkeryildiz/emergency-service-triage-application",
        "description": "1,267 ED patients from two Korean hospitals, expert-validated KTAS levels",
        "gold_standard": "KTAS_expert (3 triage experts consensus)",
        "engine_mode": "deterministic_only (no Gemini/MedGemma)",
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
        title="KTAS External Benchmark Report",
        dataset_info={
            "Source": "Kaggle: ilkeryildiz/emergency-service-triage-application",
            "Design": "Cross-sectional retrospective, two Korean EDs (Oct 2016 - Sep 2017)",
            "Gold standard": "KTAS_expert (3 triage experts consensus)",
            "Engine mode": "Deterministic only (no Gemini/MedGemma)",
            "Total cases": dataset_summary["total"],
            "KTAS distribution": str(dataset_summary["ktas_expert_distribution"]),
            "Missing SpO2": f"{dataset_summary['missing_spo2']} ({dataset_summary['missing_spo2']/dataset_summary['total']:.0%})",
            "Missing pain score": f"{dataset_summary['missing_pain']} ({dataset_summary['missing_pain']/dataset_summary['total']:.0%})",
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
        description="Run SAFE-Triage against KTAS external dataset (deterministic only)"
    )
    parser.add_argument(
        "--data-path",
        default=None,
        help="Path to KTAS CSV file",
    )
    parser.add_argument(
        "--output-dir",
        default="benchmarks/outputs/ktas",
        help="Output directory for results (default: benchmarks/outputs/ktas)",
    )
    args = parser.parse_args()

    metrics = run_benchmark(
        data_path=args.data_path,
        output_dir=args.output_dir,
    )

    # Exit with non-zero if critical under-triage found
    if metrics.critical_under_triage > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
