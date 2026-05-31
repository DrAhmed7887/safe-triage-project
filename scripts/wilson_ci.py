#!/usr/bin/env python3
"""Compute 95% Wilson score confidence intervals for SAFE-Triage metrics."""

from __future__ import annotations

from dataclasses import dataclass
from math import sqrt


Z_95 = 1.959963984540054


@dataclass(frozen=True)
class Metric:
    name: str
    numerator: int
    denominator: int


METRICS = [
    Metric("MIETIC English exact ESI agreement", 35, 36),
    Metric("MIETIC English within-one agreement", 36, 36),
    Metric("MIETIC English critical under-triage", 0, 36),
    Metric("MIETIC English over-triage", 1, 36),
    Metric("MIETIC Arabic mirror exact ESI agreement", 35, 36),
    Metric("MIETIC Arabic mirror within-one agreement", 36, 36),
    Metric("MIETIC Arabic mirror critical under-triage", 0, 36),
    Metric("MIETIC Arabic mirror over-triage", 1, 36),
    Metric("KTAS exact agreement", 477, 1262),
    Metric("KTAS within-one agreement", 1030, 1262),
    Metric("KTAS critical under-triage", 16, 1262),
    Metric("KTAS over-triage", 708, 1262),
    Metric("KTAS all under-triage", 77, 1262),
    Metric("KTAS hard-case Gemma 4 resolution", 6, 17),
    Metric("KTAS hard-case MedGemma flagging", 12, 17),
    Metric("KTAS Arabic exact agreement", 459, 1262),
    Metric("KTAS Arabic within-one agreement", 1037, 1262),
    Metric("KTAS Arabic critical under-triage", 13, 1262),
    Metric("KTAS Arabic over-triage", 671, 1262),
    Metric("KTAS Arabic all under-triage", 132, 1262),
]


def wilson_interval(successes: int, total: int, z: float = Z_95) -> tuple[float, float]:
    if total <= 0:
        raise ValueError("total must be positive")

    p_hat = successes / total
    denominator = 1 + (z * z / total)
    center = (p_hat + (z * z / (2 * total))) / denominator
    margin = (z * sqrt((p_hat * (1 - p_hat) + (z * z / (4 * total))) / total)) / denominator
    return max(0.0, center - margin), min(1.0, center + margin)


def pct(value: float) -> str:
    return f"{value * 100:.1f}%"


def main() -> None:
    print("| Metric | Count | Point estimate | 95% Wilson CI |")
    print("|---|---:|---:|---:|")
    for metric in METRICS:
        estimate = metric.numerator / metric.denominator
        lo, hi = wilson_interval(metric.numerator, metric.denominator)
        print(
            f"| {metric.name} | {metric.numerator}/{metric.denominator} | "
            f"{pct(estimate)} | {pct(lo)} to {pct(hi)} |"
        )


if __name__ == "__main__":
    main()
