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
DEFAULT_OUTPUT_DIR = Path(__file__).resolve().parent / "benchmark_outputs"
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

    gender_value = Gender.MALE if default_gender == "male" else Gender.FEMALE

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
        "notes": [
            "Replay used complaint text and triage vitals from MIMIC-IV-ED.",
            "Age/gender were neutral placeholders because the local ED extract does not include demographics.",
            "This is suitable for retrospective replay benchmarking, not for claiming prospective clinical validation.",
        ],
        "failures_preview": failures[:20],
    }
    return {
        "summary": result_summary,
        "predictions": predictions,
        "failures": failures,
    }


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

    prefix = make_output_prefix(args.output_dir, args.tag, args.target_cases)
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
