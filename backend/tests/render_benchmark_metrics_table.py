#!/usr/bin/env python3
"""
Render a SAFE-Triage replay summary JSON into presentation-friendly tables.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Render benchmark summary JSON into Markdown and compact text tables."
    )
    parser.add_argument("summary_json", type=Path, help="Path to mimic_replay_*.summary.json")
    parser.add_argument(
        "--output-md",
        type=Path,
        default=None,
        help="Optional explicit output markdown path",
    )
    return parser.parse_args()


def format_percent(value: Any) -> str:
    if value is None:
        return "N/A"
    return f"{float(value):.2f}%"


def format_int(value: Any) -> str:
    if value is None:
        return "N/A"
    return f"{int(value):,}"


def list_to_rows(items: Iterable[Tuple[Any, Any]]) -> List[str]:
    rows: List[str] = []
    for key, value in items:
        rows.append(f"| `{key}` | {value} |")
    return rows


def render_markdown(payload: Dict[str, Any], summary_path: Path) -> str:
    dataset = payload.get("dataset_summary", {})
    sample = payload.get("sample_summary", {})
    replay = payload.get("replay_summary", {})
    artifacts = payload.get("artifacts", {})

    lines: List[str] = []
    lines.append(f"# SAFE-Triage MIMIC Replay Metrics")
    lines.append("")
    lines.append(f"Source summary: `{summary_path}`")
    lines.append("")
    lines.append("## Core Metrics")
    lines.append("")
    lines.append("| Metric | Value |")
    lines.append("| --- | --- |")
    lines.append(f"| Usable MIMIC-IV-ED rows | {format_int(dataset.get('usable_rows'))} |")
    lines.append(f"| Unique complaint buckets | {format_int(dataset.get('unique_complaint_buckets'))} |")
    lines.append(f"| Sample selected | {format_int(sample.get('selected_cases'))} |")
    lines.append(f"| Valid predictions | {format_int(replay.get('valid_predictions'))} |")
    lines.append(f"| Failed predictions | {format_int(replay.get('failed_predictions'))} |")
    lines.append(f"| Exact-match accuracy | {format_percent(replay.get('exact_match_accuracy'))} |")
    lines.append(f"| Within-one-level accuracy | {format_percent(replay.get('within_one_level_accuracy'))} |")
    lines.append(f"| Over-triage rate | {format_percent(replay.get('over_triage_rate'))} |")
    lines.append(f"| Under-triage rate | {format_percent(replay.get('under_triage_rate'))} |")
    lines.append(f"| Critical under-triage rate | {format_percent(replay.get('critical_under_triage_rate'))} |")
    lines.append(f"| Critical under-triage count | {format_int(replay.get('critical_under_triage_count'))} |")
    lines.append("")
    lines.append("## Sample Composition")
    lines.append("")
    lines.append("| ESI Level | Target | Selected |")
    lines.append("| --- | --- | --- |")
    level_targets = sample.get("level_targets", {})
    level_selected = sample.get("level_selected", {})
    for level in ["1", "2", "3", "4", "5"]:
        lines.append(
            f"| {level} | {format_int(level_targets.get(level, 0))} | {format_int(level_selected.get(level, 0))} |"
        )
    lines.append("")
    lines.append("## Top Complaint Buckets In Sample")
    lines.append("")
    lines.append("| Complaint bucket | Count |")
    lines.append("| --- | --- |")
    lines.extend(list_to_rows(sample.get("top_complaint_buckets", [])[:15]))
    lines.append("")
    lines.append("## Top Miss Buckets")
    lines.append("")
    lines.append("| Complaint bucket | Count |")
    lines.append("| --- | --- |")
    lines.extend(list_to_rows(replay.get("top_miss_buckets", [])[:15]))
    lines.append("")
    lines.append("## Notes")
    lines.append("")
    for note in replay.get("notes", []):
        lines.append(f"- {note}")
    if artifacts:
        lines.append("")
        lines.append("## Artifacts")
        lines.append("")
        lines.append(f"- Sample CSV: `{artifacts.get('sample_csv')}`")
        lines.append(f"- Predictions CSV: `{artifacts.get('predictions_csv')}`")
    lines.append("")
    lines.append("## Slide-Safe One-Liner")
    lines.append("")
    lines.append(
        f"`Retrospective replay on {format_int(sample.get('selected_cases')).replace(',', '')} stratified MIMIC-IV-ED triage cases "
        f"yielded {format_percent(replay.get('within_one_level_accuracy'))} within-one-level accuracy, "
        f"with {format_int(replay.get('critical_under_triage_count'))} critical under-triage cases in this run.`"
    )
    return "\n".join(lines) + "\n"


def main() -> int:
    args = parse_args()
    payload = json.loads(args.summary_json.read_text(encoding="utf-8"))
    output_path = args.output_md or args.summary_json.with_suffix(".metrics.md")
    output_path.write_text(render_markdown(payload, args.summary_json), encoding="utf-8")
    print(output_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
