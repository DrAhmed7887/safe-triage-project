"""
Benchmark Metrics for SAFE-Triage
=================================

Computes triage performance metrics from a list of (actual, predicted) ESI pairs.
All safety logic is delegated to safety.py — this module only aggregates.

Metrics computed:
  - Exact ESI match rate
  - Within-one-level accuracy
  - Under-triage rate (all levels)
  - Over-triage rate (all levels)
  - Critical under-triage count and rate
  - Per-class recall for ESI 1-5
  - Confusion matrix (5x5)
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field

from .safety import (
    classify_triage_error,
    is_critical_under_triage,
    is_over_triage,
    is_under_triage,
    is_within_one_level,
)


@dataclass(frozen=True)
class Prediction:
    """A single triage prediction with metadata."""
    case_id: str
    actual_esi: int
    predicted_esi: int
    chief_complaint: str = ""


@dataclass
class BenchmarkMetrics:
    """Aggregated benchmark metrics."""
    total: int = 0
    exact_match: int = 0
    within_one: int = 0
    under_triage: int = 0
    over_triage: int = 0
    critical_under_triage: int = 0

    # Per-class: how many of each actual ESI level were predicted correctly
    per_class_correct: dict[int, int] = field(default_factory=lambda: {i: 0 for i in range(1, 6)})
    per_class_total: dict[int, int] = field(default_factory=lambda: {i: 0 for i in range(1, 6)})

    # Confusion matrix: confusion[actual][predicted] = count
    confusion: dict[int, dict[int, int]] = field(
        default_factory=lambda: {
            a: {p: 0 for p in range(1, 6)} for a in range(1, 6)
        }
    )

    # Lists of critical under-triage cases for review
    critical_under_triage_cases: list[Prediction] = field(default_factory=list)

    @property
    def exact_match_rate(self) -> float:
        return self.exact_match / self.total if self.total else 0.0

    @property
    def within_one_rate(self) -> float:
        return self.within_one / self.total if self.total else 0.0

    @property
    def under_triage_rate(self) -> float:
        return self.under_triage / self.total if self.total else 0.0

    @property
    def over_triage_rate(self) -> float:
        return self.over_triage / self.total if self.total else 0.0

    @property
    def critical_under_triage_rate(self) -> float:
        return self.critical_under_triage / self.total if self.total else 0.0

    def per_class_recall(self, esi: int) -> float:
        """Recall for a specific ESI level: correct / total for that level."""
        total = self.per_class_total.get(esi, 0)
        correct = self.per_class_correct.get(esi, 0)
        return correct / total if total else 0.0

    def to_dict(self) -> dict:
        """Serialize to a JSON-compatible dict."""
        return {
            "total": self.total,
            "exact_match": self.exact_match,
            "exact_match_rate": round(self.exact_match_rate, 4),
            "within_one": self.within_one,
            "within_one_rate": round(self.within_one_rate, 4),
            "under_triage": self.under_triage,
            "under_triage_rate": round(self.under_triage_rate, 4),
            "over_triage": self.over_triage,
            "over_triage_rate": round(self.over_triage_rate, 4),
            "critical_under_triage": self.critical_under_triage,
            "critical_under_triage_rate": round(self.critical_under_triage_rate, 4),
            "per_class_recall": {
                esi: round(self.per_class_recall(esi), 4) for esi in range(1, 6)
            },
            "confusion_matrix": self.confusion,
            "critical_under_triage_cases": [
                {
                    "case_id": c.case_id,
                    "actual_esi": c.actual_esi,
                    "predicted_esi": c.predicted_esi,
                    "chief_complaint": c.chief_complaint,
                }
                for c in self.critical_under_triage_cases
            ],
        }


def compute_metrics(predictions: list[Prediction]) -> BenchmarkMetrics:
    """
    Compute all benchmark metrics from a list of predictions.

    Args:
        predictions: List of Prediction objects with actual and predicted ESI.

    Returns:
        BenchmarkMetrics with all aggregated statistics.

    Raises:
        ValueError: If predictions list is empty.
    """
    if not predictions:
        raise ValueError("Cannot compute metrics from empty predictions list.")

    m = BenchmarkMetrics(total=len(predictions))

    for pred in predictions:
        actual = pred.actual_esi
        predicted = pred.predicted_esi

        # Confusion matrix
        m.confusion[actual][predicted] += 1

        # Per-class counts
        m.per_class_total[actual] += 1
        if actual == predicted:
            m.exact_match += 1
            m.per_class_correct[actual] += 1

        if is_within_one_level(actual, predicted):
            m.within_one += 1

        if is_under_triage(actual, predicted):
            m.under_triage += 1

        if is_over_triage(actual, predicted):
            m.over_triage += 1

        if is_critical_under_triage(actual, predicted):
            m.critical_under_triage += 1
            m.critical_under_triage_cases.append(pred)

    return m


def render_markdown_report(
    metrics: BenchmarkMetrics,
    *,
    title: str = "MIETIC Benchmark Report",
    dataset_info: dict | None = None,
) -> str:
    """
    Render a human-readable Markdown report from benchmark metrics.

    Args:
        metrics: Computed BenchmarkMetrics.
        title: Report title.
        dataset_info: Optional dict with dataset metadata.

    Returns:
        Markdown string.
    """
    lines: list[str] = []
    lines.append(f"# {title}")
    lines.append("")

    if dataset_info:
        lines.append("## Dataset")
        for k, v in dataset_info.items():
            lines.append(f"- **{k}**: {v}")
        lines.append("")

    lines.append("## Summary Metrics")
    lines.append("")
    lines.append(f"| Metric | Value |")
    lines.append(f"|--------|-------|")
    lines.append(f"| Total cases | {metrics.total} |")
    lines.append(f"| Exact ESI match | {metrics.exact_match} ({metrics.exact_match_rate:.1%}) |")
    lines.append(f"| Within-one-level | {metrics.within_one} ({metrics.within_one_rate:.1%}) |")
    lines.append(f"| Under-triage (all) | {metrics.under_triage} ({metrics.under_triage_rate:.1%}) |")
    lines.append(f"| Over-triage (all) | {metrics.over_triage} ({metrics.over_triage_rate:.1%}) |")
    lines.append(f"| **Critical under-triage** | **{metrics.critical_under_triage} ({metrics.critical_under_triage_rate:.1%})** |")
    lines.append("")

    # Safety gate
    if metrics.critical_under_triage == 0:
        lines.append("> SAFETY GATE: PASSED (zero critical under-triage)")
    else:
        lines.append(f"> SAFETY GATE: **FAILED** ({metrics.critical_under_triage} critical under-triage cases)")
    lines.append("")

    # Per-class recall
    lines.append("## Per-Class Recall")
    lines.append("")
    lines.append("| ESI Level | Recall | Correct / Total |")
    lines.append("|-----------|--------|-----------------|")
    for esi in range(1, 6):
        total = metrics.per_class_total[esi]
        correct = metrics.per_class_correct[esi]
        recall = metrics.per_class_recall(esi)
        lines.append(f"| ESI {esi} | {recall:.1%} | {correct} / {total} |")
    lines.append("")

    # Confusion matrix
    lines.append("## Confusion Matrix")
    lines.append("")
    lines.append("Rows = Actual ESI, Columns = Predicted ESI")
    lines.append("")
    header = "| | " + " | ".join(f"Pred {i}" for i in range(1, 6)) + " |"
    sep = "|---|" + "|".join("---" for _ in range(5)) + "|"
    lines.append(header)
    lines.append(sep)
    for actual in range(1, 6):
        cells = " | ".join(
            str(metrics.confusion[actual][pred]) for pred in range(1, 6)
        )
        lines.append(f"| **Actual {actual}** | {cells} |")
    lines.append("")

    # Critical under-triage details
    if metrics.critical_under_triage_cases:
        lines.append("## Critical Under-Triage Cases")
        lines.append("")
        lines.append("| Case ID | Actual | Predicted | Complaint |")
        lines.append("|---------|--------|-----------|-----------|")
        for c in metrics.critical_under_triage_cases:
            complaint = c.chief_complaint[:60]
            lines.append(f"| {c.case_id} | ESI {c.actual_esi} | ESI {c.predicted_esi} | {complaint} |")
        lines.append("")

    return "\n".join(lines)
