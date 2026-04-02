"""
KTAS Arabic Benchmark Runner
==============================

Runs the SAFE-Triage engine against the KTAS dataset with chief complaints
translated to Egyptian colloquial Arabic (via Gemini).

Compares Arabic vs English performance to measure Arabic parity on an
external (non-MIETIC) dataset of 1,262 Korean ED cases.

Usage:
    cd backend
    python -m benchmarks.ktas_arabic_benchmark [--data-path PATH] [--output-dir DIR]
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

_backend_dir = Path(__file__).resolve().parent.parent
if str(_backend_dir) not in sys.path:
    sys.path.insert(0, str(_backend_dir))

from benchmarks.ktas_loader import KTASCase, load_ktas_cases, ktas_summary, MENTAL_TO_ACVPU
from benchmarks.ktas_benchmark import build_patient_input as build_english_input
from benchmarks.metrics import BenchmarkMetrics, Prediction, compute_metrics, render_markdown_report
from benchmarks.safety import classify_triage_error


# ---------------------------------------------------------------------------
# Translation map
# ---------------------------------------------------------------------------

_TRANSLATION_MAP: dict[str, str] | None = None


def _load_translation_map() -> dict[str, str]:
    global _TRANSLATION_MAP
    if _TRANSLATION_MAP is not None:
        return _TRANSLATION_MAP

    map_path = Path(__file__).resolve().parent.parent.parent / "data" / "ktas" / "ktas_en_ar_map.json"
    if not map_path.exists():
        raise FileNotFoundError(
            f"Arabic translation map not found: {map_path}\n"
            f"Generate it first using Gemini CLI."
        )
    with open(map_path, encoding="utf-8") as f:
        _TRANSLATION_MAP = json.load(f)
    return _TRANSLATION_MAP


# ---------------------------------------------------------------------------
# Arabic patient builder
# ---------------------------------------------------------------------------

def build_arabic_patient_input(case: KTASCase):
    """
    Build PatientInput with Arabic chief complaint.
    Falls back to English if no translation exists.
    """
    from models import PatientInput, Vitals, Gender

    translation_map = _load_translation_map()
    arabic_complaint = translation_map.get(case.chief_complaint, case.chief_complaint)

    gender = Gender.MALE if case.sex == 1 else Gender.FEMALE
    pain_score = case.nrs_pain if case.nrs_pain is not None else 0

    vitals = Vitals(
        hr=case.hr,
        rr=case.rr,
        spo2=case.saturation,
        temp=case.bt,
        sbp=case.sbp,
        dbp=case.dbp,
        pain_score=pain_score,
    )

    consciousness = MENTAL_TO_ACVPU.get(case.mental, "A")

    # AMS override — same as English benchmark but with Arabic keywords too
    complaint_lower = case.chief_complaint.lower()
    _AMS_KEYWORDS = {
        "mental change", "altered mentality", "confuse mentality",
        "altered mental", "change in mental", "confusion",
        "loc", "loss of consciousness", "unresponsive",
    }
    if any(kw in complaint_lower for kw in _AMS_KEYWORDS):
        consciousness = "C"

    arrived_by_ambulance = case.arrival_mode in (1, 2)

    # Enrich with injury context (in Arabic)
    enriched_complaint = arabic_complaint
    if case.injury == 2 and "trauma" not in complaint_lower and "injury" not in complaint_lower:
        enriched_complaint = f"{arabic_complaint} (إصابة / حادثة)"

    patient = PatientInput(
        age=case.age,
        gender=gender,
        chief_complaint_text=enriched_complaint,
        vitals=vitals,
        consciousness=consciousness,
        arrived_by_ambulance=arrived_by_ambulance,
    )
    return patient


# ---------------------------------------------------------------------------
# Benchmark runner
# ---------------------------------------------------------------------------

def run_benchmark(
    data_path: str | Path | None = None,
    *,
    output_dir: str | Path | None = None,
    compare_english: bool = True,
) -> tuple[BenchmarkMetrics, BenchmarkMetrics | None]:
    """
    Run Arabic KTAS benchmark, optionally comparing with English.

    Returns:
        Tuple of (arabic_metrics, english_metrics or None).
    """
    os.environ["DISABLE_RAG"] = "true"

    from logic.deterministic_triage import DeterministicTriageEngine

    cases = load_ktas_cases(data_path)
    summary = ktas_summary(cases)
    print(f"Loaded {len(cases)} KTAS cases")

    engine = DeterministicTriageEngine()
    translation_map = _load_translation_map()

    # --- Arabic run ---
    ar_predictions: list[Prediction] = []
    ar_failures: list[dict] = []

    for case in cases:
        case_id = f"ktas_ar_row_{case.row_index}"
        try:
            patient = build_arabic_patient_input(case)
            result = engine.evaluate(patient)
            predicted_esi = int(getattr(result.level, "value", result.level))
            ar_predictions.append(Prediction(
                case_id=case_id,
                actual_esi=case.ktas_expert,
                predicted_esi=predicted_esi,
                chief_complaint=translation_map.get(case.chief_complaint, case.chief_complaint),
            ))
        except Exception as e:
            ar_failures.append({
                "case_id": case_id,
                "error": str(e),
                "actual_esi": case.ktas_expert,
                "chief_complaint": case.chief_complaint,
            })

    ar_metrics = compute_metrics(ar_predictions)

    print(f"\n{'='*60}")
    print(f"KTAS Arabic Benchmark Results")
    print(f"{'='*60}")
    print(f"  Exact match:           {ar_metrics.exact_match_rate:.1%} ({ar_metrics.exact_match}/{ar_metrics.total})")
    print(f"  Within-one-level:      {ar_metrics.within_one_rate:.1%} ({ar_metrics.within_one}/{ar_metrics.total})")
    print(f"  Under-triage:          {ar_metrics.under_triage_rate:.1%} ({ar_metrics.under_triage}/{ar_metrics.total})")
    print(f"  Over-triage:           {ar_metrics.over_triage_rate:.1%} ({ar_metrics.over_triage}/{ar_metrics.total})")
    print(f"  Critical under-triage: {ar_metrics.critical_under_triage_rate:.1%} ({ar_metrics.critical_under_triage}/{ar_metrics.total})")

    if ar_metrics.critical_under_triage > 0:
        print(f"\n  *** SAFETY: {ar_metrics.critical_under_triage} critical under-triage ***")
        for c in ar_metrics.critical_under_triage_cases:
            print(f"    - {c.case_id}: actual {c.actual_esi} -> predicted {c.predicted_esi} ({c.chief_complaint[:60]})")

    # --- English run for comparison ---
    en_metrics = None
    en_predictions: list[Prediction] = []

    if compare_english:
        for case in cases:
            case_id = f"ktas_en_row_{case.row_index}"
            try:
                patient = build_english_input(case)
                result = engine.evaluate(patient)
                predicted_esi = int(getattr(result.level, "value", result.level))
                en_predictions.append(Prediction(
                    case_id=case_id,
                    actual_esi=case.ktas_expert,
                    predicted_esi=predicted_esi,
                    chief_complaint=case.chief_complaint,
                ))
            except Exception:
                pass

        en_metrics = compute_metrics(en_predictions)

        print(f"\n{'='*60}")
        print(f"KTAS English Benchmark Results (for comparison)")
        print(f"{'='*60}")
        print(f"  Exact match:           {en_metrics.exact_match_rate:.1%}")
        print(f"  Within-one-level:      {en_metrics.within_one_rate:.1%}")
        print(f"  Under-triage:          {en_metrics.under_triage_rate:.1%}")
        print(f"  Over-triage:           {en_metrics.over_triage_rate:.1%}")
        print(f"  Critical under-triage: {en_metrics.critical_under_triage_rate:.1%}")

        # --- Side-by-side ---
        print(f"\n{'='*60}")
        print(f"Arabic vs English — Head-to-Head")
        print(f"{'='*60}")
        print(f"  {'Metric':<30} {'Arabic':>10} {'English':>10} {'Delta':>10}")
        print(f"  {'-'*60}")

        for name, ar_val, en_val, higher_better in [
            ("Exact match", ar_metrics.exact_match_rate, en_metrics.exact_match_rate, True),
            ("Within-one-level", ar_metrics.within_one_rate, en_metrics.within_one_rate, True),
            ("Under-triage", ar_metrics.under_triage_rate, en_metrics.under_triage_rate, False),
            ("Over-triage", ar_metrics.over_triage_rate, en_metrics.over_triage_rate, False),
            ("Critical under-triage", ar_metrics.critical_under_triage_rate, en_metrics.critical_under_triage_rate, False),
        ]:
            delta = ar_val - en_val
            sign = "+" if delta > 0 else ""
            indicator = ""
            if abs(delta) > 0.001:
                if higher_better:
                    indicator = " ✓" if delta > 0 else " ✗"
                else:
                    indicator = " ✓" if delta < 0 else " ✗"
            print(f"  {name:<30} {ar_val:>9.1%} {en_val:>9.1%} {sign}{delta:>8.1%}{indicator}")

        # Per-level comparison
        print(f"\n  {'KTAS Level':<15} {'AR Recall':>10} {'EN Recall':>10}")
        print(f"  {'-'*35}")
        for level in range(1, 6):
            ar_r = ar_metrics.per_class_recall(level)
            en_r = en_metrics.per_class_recall(level)
            print(f"  {'KTAS ' + str(level):<15} {ar_r:>9.1%} {en_r:>9.1%}")

    # Save outputs
    if output_dir is not None:
        _save_outputs(output_dir, ar_metrics, ar_predictions, ar_failures,
                      en_metrics, en_predictions, summary)

    return ar_metrics, en_metrics


# ---------------------------------------------------------------------------
# Parity analysis — per-case differences
# ---------------------------------------------------------------------------

def _find_parity_differences(
    ar_predictions: list[Prediction],
    en_predictions: list[Prediction],
) -> list[dict]:
    """Find cases where Arabic and English give different ESI levels."""
    en_by_row = {}
    for p in en_predictions:
        row = p.case_id.replace("ktas_en_row_", "")
        en_by_row[row] = p

    diffs = []
    for p in ar_predictions:
        row = p.case_id.replace("ktas_ar_row_", "")
        en_p = en_by_row.get(row)
        if en_p and p.predicted_esi != en_p.predicted_esi:
            diffs.append({
                "row": row,
                "arabic_complaint": p.chief_complaint,
                "english_complaint": en_p.chief_complaint,
                "actual_ktas": p.actual_esi,
                "arabic_esi": p.predicted_esi,
                "english_esi": en_p.predicted_esi,
                "arabic_correct": p.predicted_esi == p.actual_esi,
                "english_correct": en_p.predicted_esi == en_p.actual_esi,
            })
    return diffs


def _save_outputs(
    output_dir: str | Path,
    ar_metrics: BenchmarkMetrics,
    ar_predictions: list[Prediction],
    ar_failures: list[dict],
    en_metrics: BenchmarkMetrics | None,
    en_predictions: list[Prediction],
    dataset_summary: dict,
) -> None:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")

    # Arabic predictions CSV
    csv_path = out / "arabic_predictions.csv"
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["case_id", "actual_ktas", "predicted_esi",
                         "exact_match", "within_one", "error_type", "chief_complaint_arabic"])
        for p in ar_predictions:
            writer.writerow([
                p.case_id, p.actual_esi, p.predicted_esi,
                int(p.actual_esi == p.predicted_esi),
                int(abs(p.actual_esi - p.predicted_esi) <= 1),
                classify_triage_error(p.actual_esi, p.predicted_esi),
                p.chief_complaint,
            ])
    print(f"  Saved {csv_path}")

    # Summary JSON
    summary_data = {
        "benchmark": "KTAS_arabic",
        "description": "KTAS cases with Egyptian Arabic chief complaints (Gemini-translated)",
        "timestamp": timestamp,
        "dataset": dataset_summary,
        "arabic_metrics": ar_metrics.to_dict(),
        "english_metrics": en_metrics.to_dict() if en_metrics else None,
    }

    # Parity differences
    if en_predictions:
        diffs = _find_parity_differences(ar_predictions, en_predictions)
        summary_data["parity_differences"] = len(diffs)
        summary_data["parity_diff_details"] = diffs[:50]  # Cap at 50

    json_path = out / "arabic_summary.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(summary_data, f, indent=2, ensure_ascii=False)
    print(f"  Saved {json_path}")

    # Comparison report
    if en_metrics:
        md_path = out / "arabic_comparison.md"
        lines = [
            "# KTAS Arabic vs English — Parity Benchmark",
            "",
            f"**Date:** {timestamp}",
            f"**Cases:** {ar_metrics.total}",
            f"**Translation:** Gemini CLI (Egyptian colloquial Arabic)",
            "",
            "## Head-to-Head",
            "",
            "| Metric | Arabic | English | Delta |",
            "|--------|--------|---------|-------|",
        ]
        for name, ar_val, en_val in [
            ("Exact match", ar_metrics.exact_match_rate, en_metrics.exact_match_rate),
            ("Within-one", ar_metrics.within_one_rate, en_metrics.within_one_rate),
            ("Under-triage", ar_metrics.under_triage_rate, en_metrics.under_triage_rate),
            ("Over-triage", ar_metrics.over_triage_rate, en_metrics.over_triage_rate),
            ("Critical under-triage", ar_metrics.critical_under_triage_rate, en_metrics.critical_under_triage_rate),
        ]:
            delta = ar_val - en_val
            sign = "+" if delta > 0 else ""
            lines.append(f"| {name} | {ar_val:.1%} | {en_val:.1%} | {sign}{delta:.1%} |")

        diffs = _find_parity_differences(ar_predictions, en_predictions)
        if diffs:
            lines.extend([
                "",
                f"## Parity Differences ({len(diffs)} cases)",
                "",
                "| Row | Arabic Complaint | English | Actual | AR ESI | EN ESI | AR✓ | EN✓ |",
                "|-----|-----------------|---------|--------|--------|--------|-----|-----|",
            ])
            for d in diffs[:30]:
                ar_check = "✓" if d["arabic_correct"] else "✗"
                en_check = "✓" if d["english_correct"] else "✗"
                lines.append(
                    f"| {d['row']} | {d['arabic_complaint'][:30]} | {d['english_complaint'][:25]} "
                    f"| {d['actual_ktas']} | {d['arabic_esi']} | {d['english_esi']} "
                    f"| {ar_check} | {en_check} |"
                )

        with open(md_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")
        print(f"  Saved {md_path}")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run KTAS benchmark with Arabic chief complaints"
    )
    parser.add_argument("--data-path", default=None)
    parser.add_argument("--output-dir", default="benchmarks/outputs/ktas_arabic")
    parser.add_argument("--no-english", action="store_true",
                        help="Skip English comparison run")
    args = parser.parse_args()

    run_benchmark(
        data_path=args.data_path,
        output_dir=args.output_dir,
        compare_english=not args.no_english,
    )


if __name__ == "__main__":
    main()
