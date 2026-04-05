"""
Boundary Clarification Mode — A/B Benchmark
=============================================

Compares triage accuracy across three modes:
  (a) no_questions   — current baseline
  (b) 1_question     — boundary mode capped at 1 question
  (c) up_to_3        — full boundary mode (0-3 questions)

Simulates patient answers from ground-truth ESI:
  - If actual ESI is MORE acute than predicted → "yes" to upgrade questions
  - Otherwise → "no"

Usage:
    cd backend
    python -m benchmarks.boundary_benchmark [--output-dir DIR]
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

_backend_dir = Path(__file__).resolve().parent.parent
if str(_backend_dir) not in sys.path:
    sys.path.insert(0, str(_backend_dir))

from benchmarks.metrics import BenchmarkMetrics, Prediction, compute_metrics
from benchmarks.mietic_loader import MIETICValidatedCase, load_mietic_validated
from benchmarks.mietic_benchmark import build_patient_input

from logic.esi_v5_engine import (
    PatientFeatures,
    VitalSigns,
    NEWS2Result,
    triage_patient as esi_triage_patient,
)
from logic.boundary_clarification import (
    BoundaryZone,
    detect_boundary_zone,
    select_questions,
    apply_answers,
    FALLBACK_QUESTIONS,
)


@dataclass
class BoundaryBenchmarkStats:
    mode: str
    total_cases: int = 0
    questions_triggered: int = 0
    esi_changed: int = 0
    questions_by_type: Counter = field(default_factory=Counter)
    metrics: BenchmarkMetrics | None = None


def _simulate_answers(
    actual_esi: int,
    predicted_esi: int,
    selected_questions: list[dict],
) -> list[dict]:
    """Simulate patient answers based on ground truth."""
    should_upgrade = actual_esi < predicted_esi
    return [
        {"question_id": f"q{i}", "response": "yes" if should_upgrade else "no"}
        for i in range(len(selected_questions))
    ]


def _get_esi_v5_metadata(patient_input, det_result):
    """
    Run ESI v5 engine through the same path as the MIETIC benchmark
    and return the metadata needed for boundary zone detection.
    """
    # Import here to avoid circular imports at module level
    try:
        from main import _run_esi_v5_for_patient, _severity_from_level, _deterministic_confidence
    except ImportError:
        # If main.py can't be imported (e.g., missing env vars), return None
        return None

    det_confidence, det_offline = _deterministic_confidence(
        det_result, force_offline=True,
    )
    esi_v5_result = _run_esi_v5_for_patient(
        patient_input,
        body_system=det_result.category,
        news2_score=det_result.news2_score,
        news2_level=det_result.news2_level,
        severity=_severity_from_level(det_result.final_level),
        ai_confidence=det_confidence,
        is_offline=det_offline,
    )
    return esi_v5_result, det_confidence


def run_mode(
    cases: list[MIETICValidatedCase],
    mode: str,
    max_questions: int,
) -> tuple[list[Prediction], BoundaryBenchmarkStats]:
    """Run one mode of the benchmark using the full deterministic pipeline."""
    from logic.deterministic_triage import DeterministicTriageEngine

    stats = BoundaryBenchmarkStats(mode=mode)
    predictions: list[Prediction] = []
    engine = DeterministicTriageEngine()

    for case in cases:
        case_id = f"stay_{case.stay_id}"
        stats.total_cases += 1

        try:
            patient_input = build_patient_input(case)

            # Phase 1: Full pipeline triage (same as MIETIC benchmark)
            result = engine.evaluate(patient_input)
            initial_esi = int(getattr(result.level, "value", result.level))

            if mode == "no_questions" or max_questions == 0:
                predicted_esi = initial_esi
            else:
                # Get ESI v5 metadata for boundary detection
                det_result = engine.triage(patient_input.model_dump())
                body_system = det_result.category or "unclear_needs_evaluation"
                news2_total = int(det_result.news2_score or 0)

                # Try to get ESI v5 stage info; if unavailable, use heuristic
                stage_reached = "stage3_resource_estimation"  # default assumption
                resources_estimated = 2  # moderate default
                safety_floors_applied: list[str] = []
                ai_confidence = 0.75

                try:
                    esi_meta = _get_esi_v5_metadata(patient_input, det_result)
                    if esi_meta is not None:
                        esi_v5_result, ai_conf = esi_meta
                        stage_reached = esi_v5_result.stage_reached or stage_reached
                        resources_estimated = int(esi_v5_result.resources_estimated or 2)
                        safety_floors_applied = list(esi_v5_result.safety_floors_applied or [])
                        ai_confidence = float(ai_conf)
                except Exception:
                    pass  # Use defaults if ESI v5 metadata unavailable

                severity = "severe" if initial_esi <= 2 else ("moderate" if initial_esi == 3 else "mild")

                zone = detect_boundary_zone(
                    esi_level=initial_esi,
                    stage_reached=stage_reached,
                    ai_confidence=ai_confidence,
                    body_system=body_system,
                    severity=severity,
                    age=int(case.age),
                    gender="male" if case.gender == "M" else "female",
                    news2_total=news2_total,
                    resources_estimated=resources_estimated,
                    safety_floors_applied=safety_floors_applied,
                )

                # Cap questions by mode
                effective_questions = min(zone.questions, max_questions)
                effective_types = zone.selected_types[:effective_questions]
                capped_zone = BoundaryZone(
                    zone=zone.zone,
                    questions=effective_questions,
                    selected_types=effective_types,
                )

                if capped_zone.questions > 0:
                    stats.questions_triggered += 1
                    selected = select_questions(
                        capped_zone, [],
                        body_system=body_system,
                        chief_complaint=case.triage_case or case.chief_complaint,
                    )
                    for q in selected:
                        stats.questions_by_type[q["type"]] += 1

                    simulated = _simulate_answers(case.acuity, initial_esi, selected)

                    # Build PatientFeatures for re-triage
                    temp_c = None
                    if case.temperature is not None:
                        temp_c = round((case.temperature - 32) * 5 / 9, 1) if case.temperature > 50 else case.temperature
                    pain_score = 0
                    if case.pain is not None:
                        try:
                            pain_score = min(10, max(0, int(float(case.pain))))
                        except (ValueError, TypeError):
                            pain_score = 10 if str(case.pain).lower() in ("critical", "severe") else 0

                    features = PatientFeatures(
                        chief_complaint=case.triage_case if case.triage_case else case.chief_complaint,
                        snomed_codes=[],
                        body_system=body_system,
                        severity=severity,
                        onset="unknown",
                        red_flags=list(getattr(det_result, "alerts_en", []) or []),
                        age=int(case.age),
                        gender="male" if case.gender == "M" else "female",
                        comorbidities=[],
                        mental_status="alert",
                        pain_score=pain_score,
                        ai_confidence=ai_confidence,
                        is_offline=True,
                    )
                    vitals = VitalSigns(
                        heart_rate=int(case.heartrate) if case.heartrate is not None else None,
                        systolic_bp=int(case.sbp) if case.sbp is not None else None,
                        diastolic_bp=int(case.dbp) if case.dbp is not None else None,
                        respiratory_rate=int(case.resprate) if case.resprate is not None else None,
                        spo2=case.o2sat,
                        temperature=temp_c,
                        gcs=None,
                    )
                    news2 = NEWS2Result(
                        total_score=news2_total,
                        risk_level="HIGH" if news2_total >= 7 else ("MEDIUM" if news2_total >= 5 else "LOW"),
                        parameter_scores={},
                        single_param_3=news2_total >= 7,
                    )

                    clarification_result = apply_answers(simulated, selected, features)
                    if clarification_result.aborted or not clarification_result.modifications:
                        # No modifications = no re-triage needed
                        predicted_esi = initial_esi
                    else:
                        new_result = esi_triage_patient(clarification_result.features, vitals, news2)
                        # Safety: boundary clarification can only upgrade (lower ESI), never downgrade
                        predicted_esi = min(initial_esi, new_result.final_esi)
                        if predicted_esi != initial_esi:
                            stats.esi_changed += 1
                else:
                    predicted_esi = initial_esi

            predictions.append(Prediction(
                case_id=case_id,
                actual_esi=case.acuity,
                predicted_esi=predicted_esi,
                chief_complaint=case.chief_complaint,
            ))

        except Exception as e:
            print(f"  FAILED {case_id}: {e}")

    stats.metrics = compute_metrics(predictions) if predictions else None
    return predictions, stats


def run_benchmark(
    mietic_dir: str | Path | None = None,
    output_dir: str | Path | None = None,
) -> dict[str, BoundaryBenchmarkStats]:
    """Run the full A/B boundary benchmark."""
    cases = load_mietic_validated(mietic_dir, retain_only=True)
    print(f"Loaded {len(cases)} MIETIC RETAIN cases for boundary benchmark\n")

    modes = [
        ("no_questions", 0),
        ("1_question", 1),
        ("up_to_3", 3),
    ]

    all_stats: dict[str, BoundaryBenchmarkStats] = {}

    for mode_name, max_q in modes:
        print(f"--- Mode: {mode_name} (max {max_q} questions) ---")
        predictions, stats = run_mode(cases, mode_name, max_q)
        all_stats[mode_name] = stats

        if stats.metrics:
            m = stats.metrics
            print(f"  Exact match:     {m.exact_match_rate:.1%} ({m.exact_match}/{m.total})")
            print(f"  Within-one:      {m.within_one_rate:.1%}")
            print(f"  Under-triage:    {m.under_triage_rate:.1%}")
            print(f"  Over-triage:     {m.over_triage_rate:.1%}")
            print(f"  Crit under-tri:  {m.critical_under_triage_rate:.1%}")
            print(f"  Questions asked:  {stats.questions_triggered}/{stats.total_cases}")
            print(f"  ESI changed:     {stats.esi_changed}/{stats.questions_triggered or 1}")
            print(f"  Question types:  {dict(stats.questions_by_type)}")
        print()

    # Print comparison table
    print("=" * 80)
    print("BOUNDARY CLARIFICATION A/B COMPARISON")
    print("=" * 80)
    header = f"{'Metric':<25} {'no_questions':>15} {'1_question':>15} {'up_to_3':>15}"
    print(header)
    print("-" * 80)

    for metric_name, getter in [
        ("Exact Match", lambda s: f"{s.metrics.exact_match_rate:.1%}"),
        ("Within-One", lambda s: f"{s.metrics.within_one_rate:.1%}"),
        ("Under-Triage", lambda s: f"{s.metrics.under_triage_rate:.1%}"),
        ("Over-Triage", lambda s: f"{s.metrics.over_triage_rate:.1%}"),
        ("Crit Under-Triage", lambda s: f"{s.metrics.critical_under_triage_rate:.1%}"),
        ("Questions Triggered", lambda s: f"{s.questions_triggered}/{s.total_cases}"),
        ("ESI Changed", lambda s: f"{s.esi_changed}/{max(s.questions_triggered, 1)}"),
    ]:
        vals = []
        for mode_name, _ in modes:
            s = all_stats[mode_name]
            if s.metrics:
                vals.append(getter(s))
            else:
                vals.append("N/A")
        print(f"{metric_name:<25} {vals[0]:>15} {vals[1]:>15} {vals[2]:>15}")

    print("=" * 80)

    # Safety gate check
    for mode_name, _ in modes:
        s = all_stats[mode_name]
        if s.metrics and s.metrics.critical_under_triage > 0:
            print(f"\n*** SAFETY GATE FAILED in {mode_name}: "
                  f"{s.metrics.critical_under_triage} critical under-triage cases ***")
        elif s.metrics:
            print(f"  {mode_name}: SAFETY GATE PASSED (0% critical under-triage)")

    # Save outputs
    if output_dir:
        out = Path(output_dir)
        out.mkdir(parents=True, exist_ok=True)
        summary = {}
        for mode_name, _ in modes:
            s = all_stats[mode_name]
            if s.metrics:
                summary[mode_name] = {
                    "exact_match": s.metrics.exact_match_rate,
                    "within_one": s.metrics.within_one_rate,
                    "under_triage": s.metrics.under_triage_rate,
                    "over_triage": s.metrics.over_triage_rate,
                    "critical_under_triage": s.metrics.critical_under_triage_rate,
                    "questions_triggered": s.questions_triggered,
                    "esi_changed": s.esi_changed,
                    "question_types": dict(s.questions_by_type),
                }
        (out / "boundary_comparison.json").write_text(
            json.dumps(summary, indent=2, ensure_ascii=False)
        )
        print(f"\nResults saved to {out / 'boundary_comparison.json'}")

    return all_stats


def main():
    parser = argparse.ArgumentParser(description="Boundary Clarification A/B Benchmark")
    parser.add_argument("--output-dir", type=str, default=None)
    parser.add_argument("--mietic-dir", type=str, default=None)
    args = parser.parse_args()
    run_benchmark(mietic_dir=args.mietic_dir, output_dir=args.output_dir)


if __name__ == "__main__":
    main()
