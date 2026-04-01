"""
KTAS Nurse Comparison
=====================

Compares SAFE-Triage engine performance vs Korean nurses,
both measured against the expert gold standard (KTAS_expert).

This is a high-value analysis for the paper: if SAFE matches or
exceeds nurse performance on an external dataset, it demonstrates
real-world clinical competitiveness.

Usage:
    cd backend
    python -m benchmarks.ktas_nurse_comparison [--data-path PATH] [--output-dir DIR]

Outputs:
    - comparison.md        Side-by-side Markdown report
    - comparison.json      Machine-readable comparison data
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

# Ensure backend/ is on sys.path for imports
_backend_dir = Path(__file__).resolve().parent.parent
if str(_backend_dir) not in sys.path:
    sys.path.insert(0, str(_backend_dir))

from benchmarks.ktas_loader import KTASCase, load_ktas_cases, ktas_summary
from benchmarks.ktas_benchmark import build_patient_input
from benchmarks.metrics import BenchmarkMetrics, Prediction, compute_metrics


def run_comparison(
    data_path: str | Path | None = None,
    *,
    output_dir: str | Path | None = None,
) -> tuple[BenchmarkMetrics, BenchmarkMetrics]:
    """
    Run side-by-side comparison: SAFE engine vs Korean nurse.

    Returns:
        Tuple of (engine_metrics, nurse_metrics).
    """
    os.environ["DISABLE_RAG"] = "true"

    from logic.deterministic_triage import DeterministicTriageEngine

    cases = load_ktas_cases(data_path)
    summary = ktas_summary(cases)
    print(f"Loaded {len(cases)} KTAS cases for comparison")

    engine = DeterministicTriageEngine()

    engine_predictions: list[Prediction] = []
    nurse_predictions: list[Prediction] = []
    failures: list[dict] = []

    for case in cases:
        case_id = f"ktas_row_{case.row_index}"

        # Nurse prediction (always available)
        nurse_predictions.append(Prediction(
            case_id=case_id,
            actual_esi=case.ktas_expert,
            predicted_esi=case.ktas_rn,
            chief_complaint=case.chief_complaint,
        ))

        # Engine prediction
        try:
            patient = build_patient_input(case)
            result = engine.evaluate(patient)
            predicted_esi = int(
                getattr(result.level, "value", result.level)
            )
            engine_predictions.append(Prediction(
                case_id=case_id,
                actual_esi=case.ktas_expert,
                predicted_esi=predicted_esi,
                chief_complaint=case.chief_complaint,
            ))
        except Exception as e:
            failures.append({"case_id": case_id, "error": str(e)})

    engine_metrics = compute_metrics(engine_predictions)
    nurse_metrics = compute_metrics(nurse_predictions)

    # Print comparison
    print(f"\n{'='*70}")
    print(f"SAFE Engine vs Korean Nurse — KTAS External Validation")
    print(f"{'='*70}")
    print(f"{'Metric':<30} {'SAFE Engine':>15} {'Korean Nurse':>15}")
    print(f"{'-'*70}")
    print(f"{'Cases evaluated':<30} {engine_metrics.total:>15} {nurse_metrics.total:>15}")
    print(f"{'Exact match':<30} {engine_metrics.exact_match_rate:>14.1%} {nurse_metrics.exact_match_rate:>14.1%}")
    print(f"{'Within-one-level':<30} {engine_metrics.within_one_rate:>14.1%} {nurse_metrics.within_one_rate:>14.1%}")
    print(f"{'Under-triage':<30} {engine_metrics.under_triage_rate:>14.1%} {nurse_metrics.under_triage_rate:>14.1%}")
    print(f"{'Over-triage':<30} {engine_metrics.over_triage_rate:>14.1%} {nurse_metrics.over_triage_rate:>14.1%}")
    print(f"{'Critical under-triage':<30} {engine_metrics.critical_under_triage_rate:>14.1%} {nurse_metrics.critical_under_triage_rate:>14.1%}")
    print(f"{'='*70}")

    print(f"\nPer-class recall:")
    print(f"{'ESI Level':<15} {'SAFE Engine':>15} {'Korean Nurse':>15}")
    print(f"{'-'*45}")
    for esi in range(1, 6):
        print(f"{'KTAS ' + str(esi):<15} {engine_metrics.per_class_recall(esi):>14.1%} {nurse_metrics.per_class_recall(esi):>14.1%}")

    if failures:
        print(f"\nEngine failures: {len(failures)}")

    if output_dir is not None:
        _save_comparison(output_dir, engine_metrics, nurse_metrics, summary, failures)

    return engine_metrics, nurse_metrics


def _save_comparison(
    output_dir: str | Path,
    engine_metrics: BenchmarkMetrics,
    nurse_metrics: BenchmarkMetrics,
    dataset_summary: dict,
    failures: list[dict],
) -> None:
    """Save comparison outputs."""
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")

    # comparison.json
    json_path = out / "comparison.json"
    data = {
        "benchmark": "KTAS_nurse_comparison",
        "timestamp": timestamp,
        "dataset": dataset_summary,
        "engine_metrics": engine_metrics.to_dict(),
        "nurse_metrics": nurse_metrics.to_dict(),
        "engine_failures": len(failures),
    }
    with open(json_path, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"\n  Saved {json_path}")

    # comparison.md
    md_path = out / "comparison.md"
    report = _render_comparison_report(engine_metrics, nurse_metrics, dataset_summary, timestamp)
    with open(md_path, "w") as f:
        f.write(report)
    print(f"  Saved {md_path}")


def _render_comparison_report(
    engine: BenchmarkMetrics,
    nurse: BenchmarkMetrics,
    dataset: dict,
    timestamp: str,
) -> str:
    """Render side-by-side comparison as Markdown."""
    lines: list[str] = []

    lines.append("# SAFE Engine vs Korean Nurse — KTAS External Validation")
    lines.append("")
    lines.append("## Dataset")
    lines.append(f"- **Source**: Kaggle (ilkeryildiz/emergency-service-triage-application)")
    lines.append(f"- **Design**: Cross-sectional retrospective, two Korean EDs")
    lines.append(f"- **Gold standard**: KTAS_expert (3 triage experts consensus)")
    lines.append(f"- **Total cases**: {dataset['total']}")
    lines.append(f"- **KTAS distribution**: {dataset['ktas_expert_distribution']}")
    lines.append(f"- **Timestamp**: {timestamp}")
    lines.append("")

    lines.append("## Head-to-Head Comparison")
    lines.append("")
    lines.append("| Metric | SAFE Engine | Korean Nurse | Winner |")
    lines.append("|--------|-----------|------------|--------|")

    def _winner(e_val: float, n_val: float, higher_is_better: bool = True) -> str:
        if abs(e_val - n_val) < 0.005:
            return "Tie"
        if higher_is_better:
            return "SAFE" if e_val > n_val else "Nurse"
        return "SAFE" if e_val < n_val else "Nurse"

    rows = [
        ("Exact match", engine.exact_match_rate, nurse.exact_match_rate, True),
        ("Within-one-level", engine.within_one_rate, nurse.within_one_rate, True),
        ("Under-triage", engine.under_triage_rate, nurse.under_triage_rate, False),
        ("Over-triage", engine.over_triage_rate, nurse.over_triage_rate, False),
        ("Critical under-triage", engine.critical_under_triage_rate, nurse.critical_under_triage_rate, False),
    ]
    for label, e_val, n_val, higher_better in rows:
        winner = _winner(e_val, n_val, higher_better)
        lines.append(f"| {label} | {e_val:.1%} | {n_val:.1%} | {winner} |")

    lines.append("")

    lines.append("## Per-Class Recall")
    lines.append("")
    lines.append("| KTAS Level | SAFE Engine | Korean Nurse | Winner |")
    lines.append("|------------|-----------|------------|--------|")
    for esi in range(1, 6):
        e_r = engine.per_class_recall(esi)
        n_r = nurse.per_class_recall(esi)
        winner = _winner(e_r, n_r, True)
        lines.append(f"| KTAS {esi} | {e_r:.1%} | {n_r:.1%} | {winner} |")
    lines.append("")

    # Engine confusion matrix
    lines.append("## SAFE Engine Confusion Matrix")
    lines.append("")
    lines.append("Rows = Actual KTAS, Columns = Predicted ESI")
    lines.append("")
    header = "| | " + " | ".join(f"Pred {i}" for i in range(1, 6)) + " |"
    sep = "|---|" + "|".join("---" for _ in range(5)) + "|"
    lines.append(header)
    lines.append(sep)
    for actual in range(1, 6):
        cells = " | ".join(str(engine.confusion[actual][p]) for p in range(1, 6))
        lines.append(f"| **KTAS {actual}** | {cells} |")
    lines.append("")

    # Nurse confusion matrix
    lines.append("## Korean Nurse Confusion Matrix")
    lines.append("")
    lines.append("Rows = Actual KTAS expert, Columns = Nurse KTAS_RN")
    lines.append("")
    lines.append(header)
    lines.append(sep)
    for actual in range(1, 6):
        cells = " | ".join(str(nurse.confusion[actual][p]) for p in range(1, 6))
        lines.append(f"| **KTAS {actual}** | {cells} |")
    lines.append("")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Compare SAFE-Triage engine vs Korean nurses on KTAS dataset"
    )
    parser.add_argument("--data-path", default=None, help="Path to KTAS CSV file")
    parser.add_argument(
        "--output-dir",
        default="benchmarks/outputs/ktas",
        help="Output directory (default: benchmarks/outputs/ktas)",
    )
    args = parser.parse_args()

    engine_m, nurse_m = run_comparison(
        data_path=args.data_path,
        output_dir=args.output_dir,
    )

    if engine_m.critical_under_triage > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
