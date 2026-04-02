"""
Arabic MIETIC Benchmark Runner
==============================

Runs the SAFE-Triage deterministic engine against physician-authored Arabic
mirror vignettes for the MIETIC expert-validated RETAIN set.

This scaffold-only runner expects Arabic text to be filled in later by a
physician. Empty Arabic vignettes are warned and skipped.

Usage:
    cd backend
    python -m benchmarks.mietic_arabic_benchmark [--fixture PATH] [--output-dir DIR]

Outputs:
    - predictions.csv
    - summary.json
    - report.md
    - comparison.md
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from dataclasses import dataclass, replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_backend_dir = Path(__file__).resolve().parent.parent
if str(_backend_dir) not in sys.path:
    sys.path.insert(0, str(_backend_dir))

from benchmarks.metrics import BenchmarkMetrics, Prediction, compute_metrics, render_markdown_report
from benchmarks.mietic_benchmark import build_patient_input, run_benchmark as run_english_benchmark
from benchmarks.mietic_loader import MIETICValidatedCase, load_mietic_validated, validated_summary
from benchmarks.safety import classify_triage_error


DEFAULT_FIXTURE_PATH = "benchmarks/mietic_arabic_fixture.json"
DEFAULT_OUTPUT_DIR = "benchmarks/outputs/mietic_ar"
DEFAULT_ENGLISH_SUMMARY_PATH = "benchmarks/outputs/mietic/summary.json"
REQUIRED_DIALECT = "egyptian_arabic"


class ArabicFixtureError(Exception):
    """Raised when the Arabic fixture is malformed."""


@dataclass(frozen=True)
class ArabicFixtureCase:
    """One Arabic mirror row paired to a MIETIC RETAIN case."""

    stay_id: int
    acuity: int
    chief_complaint_en: str
    triage_case_en: str
    triage_case_ar: str
    dialect: str


def load_arabic_fixture(fixture_path: str | Path) -> tuple[dict[str, Any], list[ArabicFixtureCase]]:
    """Load and validate the Arabic MIETIC mirror fixture."""
    path = Path(fixture_path)
    if not path.exists():
        raise FileNotFoundError(f"Arabic MIETIC fixture not found: {path}")

    with open(path, encoding="utf-8") as f:
        payload = json.load(f)

    if not isinstance(payload, dict):
        raise ArabicFixtureError("Fixture root must be a JSON object.")

    meta = payload.get("meta")
    if not isinstance(meta, dict):
        raise ArabicFixtureError("Fixture must include a top-level 'meta' object.")

    required_meta_fields = {
        "description",
        "source",
        "arabic_status",
        "dialect_requirement",
        "cases",
    }
    missing_meta = required_meta_fields - set(meta)
    if missing_meta:
        raise ArabicFixtureError(f"Fixture meta missing fields: {sorted(missing_meta)}")

    cases_raw = meta.get("cases")
    if not isinstance(cases_raw, list):
        raise ArabicFixtureError("Fixture meta must include a 'cases' array.")

    cases: list[ArabicFixtureCase] = []
    seen_stay_ids: set[int] = set()
    required_case_fields = {
        "stay_id",
        "acuity",
        "chief_complaint_en",
        "triage_case_en",
        "triage_case_ar",
        "dialect",
    }

    for index, raw in enumerate(cases_raw, start=1):
        if not isinstance(raw, dict):
            raise ArabicFixtureError(f"Fixture case #{index} must be an object.")
        missing_case_fields = required_case_fields - set(raw)
        if missing_case_fields:
            raise ArabicFixtureError(
                f"Fixture case #{index} missing fields: {sorted(missing_case_fields)}"
            )

        stay_id = int(raw["stay_id"])
        if stay_id in seen_stay_ids:
            raise ArabicFixtureError(f"Duplicate stay_id in fixture: {stay_id}")
        seen_stay_ids.add(stay_id)

        cases.append(
            ArabicFixtureCase(
                stay_id=stay_id,
                acuity=int(raw["acuity"]),
                chief_complaint_en=str(raw["chief_complaint_en"]),
                triage_case_en=str(raw["triage_case_en"]),
                triage_case_ar=str(raw["triage_case_ar"]),
                dialect=str(raw["dialect"]),
            )
        )

    cases.sort(key=lambda case: case.stay_id)
    return meta, cases


def merge_arabic_cases(
    english_cases: list[MIETICValidatedCase],
    fixture_cases: list[ArabicFixtureCase],
) -> tuple[list[MIETICValidatedCase], int]:
    """Merge Arabic vignette text onto the original structured MIETIC cases."""
    english_by_stay = {case.stay_id: case for case in english_cases}
    expected_stay_ids = sorted(english_by_stay)
    fixture_stay_ids = sorted(case.stay_id for case in fixture_cases)

    if fixture_stay_ids != expected_stay_ids:
        missing = sorted(set(expected_stay_ids) - set(fixture_stay_ids))
        extra = sorted(set(fixture_stay_ids) - set(expected_stay_ids))
        raise ArabicFixtureError(
            f"Fixture stay_id mismatch. Missing={missing[:5]} Extra={extra[:5]}"
        )

    runnable_cases: list[MIETICValidatedCase] = []
    filled_cases = 0

    for fixture_case in fixture_cases:
        english_case = english_by_stay[fixture_case.stay_id]

        if fixture_case.acuity != english_case.acuity:
            raise ArabicFixtureError(
                f"Fixture acuity mismatch for stay_id {fixture_case.stay_id}: "
                f"{fixture_case.acuity} != {english_case.acuity}"
            )

        if fixture_case.dialect != REQUIRED_DIALECT:
            print(
                f"[WARN] stay_id {fixture_case.stay_id}: dialect="
                f"{fixture_case.dialect!r} (expected {REQUIRED_DIALECT!r})"
            )

        if fixture_case.triage_case_ar == "":
            print(f"[WARN] stay_id {fixture_case.stay_id}: empty triage_case_ar, skipping")
            continue

        filled_cases += 1
        runnable_cases.append(
            replace(english_case, triage_case=fixture_case.triage_case_ar)
        )

    return runnable_cases, filled_cases


def load_english_baseline_metrics(summary_path: str | Path = DEFAULT_ENGLISH_SUMMARY_PATH) -> BenchmarkMetrics:
    """Load cached English MIETIC metrics, falling back to a live benchmark run."""
    path = Path(summary_path)
    if path.exists():
        with open(path, encoding="utf-8") as f:
            payload = json.load(f)
        metrics_data = payload.get("metrics", {})
        if metrics_data:
            return BenchmarkMetrics(
                total=int(metrics_data.get("total", 0)),
                exact_match=int(metrics_data.get("exact_match", 0)),
                within_one=int(metrics_data.get("within_one", 0)),
                under_triage=int(metrics_data.get("under_triage", 0)),
                over_triage=int(metrics_data.get("over_triage", 0)),
                critical_under_triage=int(metrics_data.get("critical_under_triage", 0)),
            )

    return run_english_benchmark(output_dir=None)


def run_arabic_predictions(
    cases: list[MIETICValidatedCase],
) -> tuple[list[Prediction], list[dict[str, Any]]]:
    """Run deterministic predictions on Arabic mirror cases."""
    from logic.deterministic_triage import DeterministicTriageEngine

    engine = DeterministicTriageEngine()
    predictions: list[Prediction] = []
    failures: list[dict[str, Any]] = []

    for case in cases:
        case_id = f"stay_{case.stay_id}"
        try:
            patient = build_patient_input(case)
            result = engine.evaluate(patient)
            predicted_esi = int(getattr(result.level, "value", result.level))
            predictions.append(
                Prediction(
                    case_id=case_id,
                    actual_esi=case.acuity,
                    predicted_esi=predicted_esi,
                    chief_complaint=case.chief_complaint,
                )
            )
        except Exception as exc:
            failures.append(
                {
                    "case_id": case_id,
                    "error": str(exc),
                    "actual_esi": case.acuity,
                    "chief_complaint": case.chief_complaint,
                }
            )
            print(f"  FAILED case {case_id}: {exc}")

    return predictions, failures


def write_predictions_csv(output_dir: Path, predictions: list[Prediction]) -> None:
    """Write row-level predictions CSV."""
    csv_path = output_dir / "predictions.csv"
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(
            [
                "case_id",
                "actual_esi",
                "predicted_esi",
                "exact_match",
                "within_one",
                "error_type",
                "chief_complaint",
            ]
        )
        for prediction in predictions:
            writer.writerow(
                [
                    prediction.case_id,
                    prediction.actual_esi,
                    prediction.predicted_esi,
                    int(prediction.actual_esi == prediction.predicted_esi),
                    int(abs(prediction.actual_esi - prediction.predicted_esi) <= 1),
                    classify_triage_error(
                        prediction.actual_esi,
                        prediction.predicted_esi,
                    ),
                    prediction.chief_complaint,
                ]
            )


def write_summary_json(
    output_dir: Path,
    *,
    timestamp: str,
    fixture_meta: dict[str, Any],
    dataset_summary: dict[str, Any],
    predictions: list[Prediction],
    failures: list[dict[str, Any]],
    filled_cases: int,
    status: str,
    metrics: Any | None = None,
) -> None:
    """Write machine-readable summary JSON."""
    fixture_meta_summary = {
        key: value for key, value in fixture_meta.items() if key != "cases"
    }
    summary_data: dict[str, Any] = {
        "benchmark": "MIETIC Arabic Mirror",
        "timestamp": timestamp,
        "status": status,
        "fixture_meta": fixture_meta_summary,
        "dataset": dataset_summary,
        "filled_cases": filled_cases,
        "predictions_count": len(predictions),
        "failures": failures,
    }
    if metrics is not None:
        summary_data["metrics"] = metrics.to_dict()

    json_path = output_dir / "summary.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(summary_data, f, indent=2, ensure_ascii=False)


def write_report_md(
    output_dir: Path,
    *,
    timestamp: str,
    dataset_summary: dict[str, Any],
    filled_cases: int,
    metrics: Any | None = None,
) -> None:
    """Write Markdown report or pending scaffold note."""
    report_path = output_dir / "report.md"
    if metrics is None:
        lines = [
            "# MIETIC Arabic Mirror Benchmark Report",
            "",
            "> STATUS: PENDING (fewer than 10 Arabic cases are filled in the fixture)",
            "",
            "## Dataset",
            "- **Source**: Arabic MIETIC mirror fixture",
            f"- **Total fixture cases**: {dataset_summary['total']}",
            f"- **Filled Arabic cases**: {filled_cases}",
            f"- **Timestamp**: {timestamp}",
            "",
            "No Arabic benchmark metrics were computed yet.",
            "",
        ]
        report_path.write_text("\n".join(lines), encoding="utf-8")
        return

    report = render_markdown_report(
        metrics,
        title="MIETIC Arabic Mirror Benchmark Report",
        dataset_info={
            "Source": "Arabic MIETIC mirror fixture",
            "Subset": "Expert-validated RETAIN cases with physician-filled Arabic vignette",
            "Total fixture cases": dataset_summary["total"],
            "Runnable Arabic cases": filled_cases,
            "Acuity distribution": str(dataset_summary["acuity_distribution"]),
            "Cases with missing vitals": dataset_summary["has_missing_vitals"],
            "Timestamp": timestamp,
        },
    )
    report_path.write_text(report, encoding="utf-8")


def format_comparison_value(value: str | int | float | None) -> str:
    """Format comparison table cell values."""
    if value is None:
        return "pending"
    return str(value)


def build_comparison_md(
    english_metrics: Any,
    *,
    arabic_metrics: Any | None,
    fixture_total: int,
    filled_cases: int,
) -> str:
    """Render side-by-side comparison table."""
    english_total = english_metrics.total

    if arabic_metrics is None:
        arabic_total = format_comparison_value(None)
        arabic_exact = format_comparison_value(None)
        arabic_within_one = format_comparison_value(None)
        arabic_over = format_comparison_value(None)
        arabic_critical = format_comparison_value(None)
        status_note = (
            f"Arabic mirror benchmark is pending: {filled_cases}/{fixture_total} "
            "fixture cases currently contain Arabic text."
        )
    else:
        arabic_total = arabic_metrics.total
        arabic_exact = (
            f"{arabic_metrics.exact_match} ({arabic_metrics.exact_match_rate:.1%})"
        )
        arabic_within_one = (
            f"{arabic_metrics.within_one} ({arabic_metrics.within_one_rate:.1%})"
        )
        arabic_over = (
            f"{arabic_metrics.over_triage} ({arabic_metrics.over_triage_rate:.1%})"
        )
        arabic_critical = (
            f"{arabic_metrics.critical_under_triage} "
            f"({arabic_metrics.critical_under_triage_rate:.1%})"
        )
        status_note = (
            f"Arabic mirror benchmark ran on {filled_cases}/{fixture_total} "
            "fixture cases with non-empty Arabic vignette text."
        )

    lines = [
        "# English vs Arabic MIETIC Comparison",
        "",
        f"> {status_note}",
        "",
        "| Metric | English MIETIC | Arabic MIETIC mirror |",
        "|--------|----------------|----------------------|",
        f"| Total cases | {english_total} | {arabic_total} |",
        (
            f"| Exact ESI match | {english_metrics.exact_match} "
            f"({english_metrics.exact_match_rate:.1%}) | {arabic_exact} |"
        ),
        (
            f"| Within-one-level | {english_metrics.within_one} "
            f"({english_metrics.within_one_rate:.1%}) | {arabic_within_one} |"
        ),
        (
            f"| Over-triage | {english_metrics.over_triage} "
            f"({english_metrics.over_triage_rate:.1%}) | {arabic_over} |"
        ),
        (
            f"| Critical under-triage | {english_metrics.critical_under_triage} "
            f"({english_metrics.critical_under_triage_rate:.1%}) | {arabic_critical} |"
        ),
        "",
    ]
    return "\n".join(lines)


def write_comparison_md(
    output_dir: Path,
    english_metrics: Any,
    *,
    arabic_metrics: Any | None,
    fixture_total: int,
    filled_cases: int,
) -> None:
    """Write side-by-side comparison Markdown."""
    comparison_path = output_dir / "comparison.md"
    comparison_path.write_text(
        build_comparison_md(
            english_metrics,
            arabic_metrics=arabic_metrics,
            fixture_total=fixture_total,
            filled_cases=filled_cases,
        ),
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run SAFE-Triage against Arabic MIETIC mirror cases"
    )
    parser.add_argument(
        "--fixture",
        default=DEFAULT_FIXTURE_PATH,
        help="Path to Arabic MIETIC fixture JSON",
    )
    parser.add_argument(
        "--output-dir",
        default=DEFAULT_OUTPUT_DIR,
        help="Output directory for Arabic benchmark results",
    )
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    fixture_meta, fixture_cases = load_arabic_fixture(args.fixture)
    english_cases = sorted(load_mietic_validated(retain_only=True), key=lambda case: case.stay_id)

    if len(fixture_cases) != len(english_cases):
        raise ArabicFixtureError(
            f"Fixture case count mismatch: {len(fixture_cases)} != {len(english_cases)}"
        )

    english_metrics = load_english_baseline_metrics()
    runnable_cases, filled_cases = merge_arabic_cases(english_cases, fixture_cases)
    dataset_summary = validated_summary(english_cases)

    if filled_cases < 10:
        write_predictions_csv(output_dir, [])
        write_summary_json(
            output_dir,
            timestamp=timestamp,
            fixture_meta=fixture_meta,
            dataset_summary=dataset_summary,
            predictions=[],
            failures=[],
            filled_cases=filled_cases,
            status="pending_physician_fill",
        )
        write_report_md(
            output_dir,
            timestamp=timestamp,
            dataset_summary=dataset_summary,
            filled_cases=filled_cases,
            metrics=None,
        )
        write_comparison_md(
            output_dir,
            english_metrics,
            arabic_metrics=None,
            fixture_total=len(fixture_cases),
            filled_cases=filled_cases,
        )
        print(
            f"[PENDING] Only {filled_cases} Arabic cases are filled. "
            "Need at least 10 to run benchmark."
        )
        sys.exit(2)

    predictions, failures = run_arabic_predictions(runnable_cases)
    if not predictions:
        raise RuntimeError("All runnable Arabic cases failed. Cannot compute metrics.")

    metrics = compute_metrics(predictions)

    write_predictions_csv(output_dir, predictions)
    write_summary_json(
        output_dir,
        timestamp=timestamp,
        fixture_meta=fixture_meta,
        dataset_summary=dataset_summary,
        predictions=predictions,
        failures=failures,
        filled_cases=filled_cases,
        status="completed",
        metrics=metrics,
    )
    write_report_md(
        output_dir,
        timestamp=timestamp,
        dataset_summary=dataset_summary,
        filled_cases=filled_cases,
        metrics=metrics,
    )
    write_comparison_md(
        output_dir,
        english_metrics,
        arabic_metrics=metrics,
        fixture_total=len(fixture_cases),
        filled_cases=filled_cases,
    )

    if metrics.critical_under_triage > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
