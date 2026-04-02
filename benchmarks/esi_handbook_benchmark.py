"""
ESI Handbook Benchmark
======================
Runs SAFE-Triage deterministic engine against the official ESI v4
Implementation Handbook vignettes (via TriageAgent dataset).

These are the cleanest possible labels — expert cases from the official
AHRQ handbook used to train triage nurses. Zero label noise.

3 test sets × 70 cases = 210 cases total.

Usage:
    cd /Users/ahmedzayed/Projects/safe-triage-project
    source .venv/bin/activate
    python benchmarks/esi_handbook_benchmark.py
"""
from __future__ import annotations

import csv
import json
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

_backend = Path(__file__).resolve().parent.parent / "backend"
if str(_backend) not in sys.path:
    sys.path.insert(0, str(_backend))

# ── Dataset loading ────────────────────────────────────────────────────────────

BENCHMARKS_DIR = Path(__file__).resolve().parent
TEST_FILES = [
    BENCHMARKS_DIR / "esi_handbook_test1.tsv",
    BENCHMARKS_DIR / "esi_handbook_test2.tsv",
    BENCHMARKS_DIR / "esi_handbook_test3.tsv",
]


def _parse_esi_label(raw: str) -> int | None:
    """Extract integer ESI level. '4 or 5' → 4 (conservative)."""
    raw = raw.strip()
    m = re.match(r"^([1-5])", raw)
    return int(m.group(1)) if m else None


def load_handbook_cases() -> list[dict]:
    cases = []
    for path in TEST_FILES:
        with open(path, encoding="utf-8") as f:
            lines = f.readlines()
        for line in lines[1:]:          # skip header row
            parts = line.rstrip("\n").split("\t")
            if len(parts) < 2:
                continue
            vignette = parts[0].strip()
            label_raw = parts[-1].strip()
            label = _parse_esi_label(label_raw)
            if vignette and label:
                cases.append({
                    "vignette": vignette,
                    "actual_esi": label,
                    "source_file": path.name,
                    "raw_label": label_raw,
                })
    return cases


# ── Age/vitals extraction from vignette text ──────────────────────────────────

def _extract_age(text: str) -> float:
    """Extract age from vignette. Returns 35 if not found."""
    # "8-month-old" → 0.5, "7-year-old" → 7
    m = re.search(r"(\d+)[- ]month[- ]old", text, re.IGNORECASE)
    if m:
        return int(m.group(1)) / 12
    m = re.search(r"(\d+)[- ](?:year|yr)[- ]old", text, re.IGNORECASE)
    if m:
        return float(m.group(1))
    m = re.search(r"(?:age[d]?|a)\s+(\d+)", text, re.IGNORECASE)
    if m:
        return float(m.group(1))
    return 35.0


def _extract_vitals(text: str) -> dict:
    """Best-effort vital sign extraction from free text."""
    vitals: dict[str, float | None] = {
        "hr": None, "rr": None, "spo2": None,
        "temp_f": None, "sbp": None, "dbp": None,
    }
    # HR
    m = re.search(r"HR[:\s]+(\d+)", text, re.IGNORECASE)
    if m:
        vitals["hr"] = float(m.group(1))
    # RR
    m = re.search(r"RR[:\s]+(\d+)", text, re.IGNORECASE)
    if m:
        vitals["rr"] = float(m.group(1))
    # SpO2
    m = re.search(r"(?:SpO2|O2 sat|oxygen sat)[:\s]+(\d+)", text, re.IGNORECASE)
    if m:
        vitals["spo2"] = float(m.group(1))
    # Temp
    m = re.search(r"T(?:emp)?[:\s]+([\d.]+)[°\s]*[FC]?", text, re.IGNORECASE)
    if m:
        t = float(m.group(1))
        vitals["temp_f"] = t if t > 50 else t * 9/5 + 32  # treat <50 as C
    # BP
    m = re.search(r"BP[:\s]+(\d+)[/\\](\d+)", text, re.IGNORECASE)
    if m:
        vitals["sbp"] = float(m.group(1))
        vitals["dbp"] = float(m.group(2))
    return vitals


# ── Engine integration ────────────────────────────────────────────────────────

def _run_engine(vignette: str) -> int | None:
    """Run deterministic engine on vignette text. Returns ESI int or None."""
    try:
        from logic.deterministic_triage import DeterministicTriageEngine
    except ImportError:
        return None

    age = _extract_age(vignette)
    vitals = _extract_vitals(vignette)

    engine = _get_engine()

    patient_data = {
        "chief_complaint_text": vignette,
        "age": age,
        "gender": "male",  # neutral default
        "vitals": {
            "hr": vitals.get("hr"),
            "rr": vitals.get("rr"),
            "spo2": vitals.get("spo2"),
            "temp": ((vitals["temp_f"] - 32) * 5/9) if vitals.get("temp_f") else None,
            "sbp": vitals.get("sbp"),
            "dbp": vitals.get("dbp"),
        },
        "arrived_by_ambulance": bool(re.search(r"\bEMS\b|\bambulance\b", vignette, re.IGNORECASE)),
    }

    result = engine.triage(patient_data)
    return result.final_level if result else None


_engine_instance = None

def _get_engine():
    global _engine_instance
    if _engine_instance is None:
        from logic.deterministic_triage import DeterministicTriageEngine
        _engine_instance = DeterministicTriageEngine(use_ai=False)
    return _engine_instance


# ── Metrics ───────────────────────────────────────────────────────────────────

def compute_metrics(predictions: list[dict]) -> dict:
    valid = [p for p in predictions if p["predicted_esi"] is not None]
    total = len(valid)
    if total == 0:
        return {}

    exact = sum(1 for p in valid if p["actual_esi"] == p["predicted_esi"])
    within1 = sum(1 for p in valid if abs(p["actual_esi"] - p["predicted_esi"]) <= 1)
    over = sum(1 for p in valid if p["predicted_esi"] < p["actual_esi"])
    under = sum(1 for p in valid if p["predicted_esi"] > p["actual_esi"])
    # Critical under-triage: actual ESI 1 or 2, predicted 3+
    crit_under = sum(
        1 for p in valid
        if p["actual_esi"] <= 2 and p["predicted_esi"] > p["actual_esi"]
    )

    # Per-class recall
    by_actual: dict[int, list] = defaultdict(list)
    for p in valid:
        by_actual[p["actual_esi"]].append(p["predicted_esi"])
    per_class_recall = {
        lvl: sum(1 for x in preds if x == lvl) / len(preds)
        for lvl, preds in sorted(by_actual.items())
    }

    # Confusion matrix
    confusion: dict[str, dict[str, int]] = {}
    for p in valid:
        a, pr = str(p["actual_esi"]), str(p["predicted_esi"])
        confusion.setdefault(a, {})
        confusion[a][pr] = confusion[a].get(pr, 0) + 1

    return {
        "total": total,
        "exact_match": exact,
        "exact_match_rate": round(exact / total, 4),
        "within_one": within1,
        "within_one_rate": round(within1 / total, 4),
        "over_triage": over,
        "over_triage_rate": round(over / total, 4),
        "under_triage": under,
        "under_triage_rate": round(under / total, 4),
        "critical_under_triage": crit_under,
        "critical_under_triage_rate": round(crit_under / total, 4),
        "per_class_recall": {k: round(v, 4) for k, v in per_class_recall.items()},
        "confusion_matrix": confusion,
    }


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    print("Loading ESI handbook cases...")
    cases = load_handbook_cases()
    print(f"  Loaded {len(cases)} cases from {len(TEST_FILES)} test sets")

    dist = Counter(c["actual_esi"] for c in cases)
    print(f"  ESI distribution: {dict(sorted(dist.items()))}")

    print("\nRunning engine...")
    predictions = []
    failed = 0
    for i, case in enumerate(cases):
        pred = _run_engine(case["vignette"])
        if pred is None:
            failed += 1
        is_crit = case["actual_esi"] <= 2 and pred is not None and pred > case["actual_esi"]
        predictions.append({
            **case,
            "predicted_esi": pred,
            "exact_match": pred == case["actual_esi"],
            "within_one": pred is not None and abs(pred - case["actual_esi"]) <= 1,
            "critical_under_triage": is_crit,
        })
        if (i + 1) % 50 == 0:
            print(f"  {i+1}/{len(cases)}...")

    print(f"  Done. Failed: {failed}")

    metrics = compute_metrics(predictions)

    # ── Print report ──
    print()
    print("=" * 60)
    print("ESI HANDBOOK BENCHMARK (TriageAgent — 3 Test Sets)")
    print("=" * 60)
    print(f"  Cases:             {metrics['total']}")
    print(f"  Exact match:       {metrics['exact_match_rate']*100:.1f}%  ({metrics['exact_match']}/{metrics['total']})")
    print(f"  Within-1 level:    {metrics['within_one_rate']*100:.1f}%  ({metrics['within_one']}/{metrics['total']})")
    print(f"  Over-triage:       {metrics['over_triage_rate']*100:.1f}%  ({metrics['over_triage']})")
    print(f"  Under-triage:      {metrics['under_triage_rate']*100:.1f}%  ({metrics['under_triage']})")
    print(f"  Critical under:    {metrics['critical_under_triage_rate']*100:.1f}%  ({metrics['critical_under_triage']})")
    print()
    print("  Per-class recall:")
    for lvl, rec in metrics["per_class_recall"].items():
        bar = "█" * int(rec * 20)
        print(f"    ESI {lvl}: {rec*100:5.1f}%  {bar}")
    print()
    print("  Confusion matrix (rows=actual, cols=predicted):")
    print(f"  {'':8}", end="")
    for col in range(1, 6):
        print(f"  P{col}", end="")
    print()
    for actual in range(1, 6):
        row = metrics["confusion_matrix"].get(str(actual), {})
        print(f"  A{actual}      ", end="")
        for pred in range(1, 6):
            val = row.get(str(pred), 0)
            print(f"  {val:2}", end="")
        print()

    safety = "PASSED" if metrics["critical_under_triage"] == 0 else "FAILED"
    print()
    print(f"  SAFETY GATE (0% critical under-triage): {safety}")
    print("=" * 60)

    # ── Save outputs ──
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_dir = BENCHMARKS_DIR / "outputs" / "esi_handbook"
    out_dir.mkdir(parents=True, exist_ok=True)

    summary = {
        "benchmark": "ESI_Handbook_TriageAgent",
        "timestamp": ts,
        "source": "ESI v4 Implementation Handbook via TriageAgent (EMNLP 2024)",
        "test_sets": [p.name for p in TEST_FILES],
        "dataset": {"total": len(cases), "acuity_distribution": {str(k): v for k, v in sorted(dist.items())}},
        "metrics": metrics,
        "failures": failed,
    }
    (out_dir / "summary.json").write_text(json.dumps(summary, indent=2))

    with open(out_dir / "predictions.csv", "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "source_file", "actual_esi", "predicted_esi",
            "exact_match", "within_one", "critical_under_triage", "raw_label", "vignette"
        ])
        writer.writeheader()
        writer.writerows(predictions)

    print(f"\n  Saved: {out_dir}/summary.json")
    print(f"  Saved: {out_dir}/predictions.csv")

    return metrics


if __name__ == "__main__":
    main()
