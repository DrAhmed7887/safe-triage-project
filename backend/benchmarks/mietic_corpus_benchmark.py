"""
MIETIC Corpus Benchmark
========================

Benchmarks the SAFE-Triage engine against the full MIETIC corpus (9,630 cases).

Unlike MIETIC-validate-samples.csv (36 expert-reviewed cases), the main corpus
contains LLM-generated clinical vignettes based on real MIMIC-IV-ED cases.
Each vignette includes age, gender, vitals, chief complaint, and clinical
narrative — making them richer than raw MIMIC triage rows.

ESI level is derived from:
  - ESI 1: instruction contains "immediate life-saving interventions"
  - ESI 2: instruction contains "ESI Level 2"
  - ESI 3: instruction contains "resources likely required" + output says 2+ resources
  - ESI 4: instruction contains "resources likely required" + output says 1 resource
  - ESI 5: instruction contains "resources likely required" + output says 0 resources

Vitals are extracted from the vignette text via regex.

Usage:
    cd backend
    python -m benchmarks.mietic_corpus_benchmark [--target-per-level 200]
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import random
import re
import sys
from collections import Counter
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

_backend_dir = Path(__file__).resolve().parent.parent
if str(_backend_dir) not in sys.path:
    sys.path.insert(0, str(_backend_dir))

DEFAULT_MIETIC_DIR = Path(__file__).resolve().parents[2] / "mimic-iv-ext-triage-instruction-corpus-1.0.0"
DEFAULT_OUTPUT_DIR = Path(__file__).resolve().parent / "outputs" / "mietic_corpus"


@dataclass
class CorpusCase:
    row_index: int
    esi_level: int
    vignette: str            # Full clinical narrative (input field)
    age: Optional[float]
    gender: Optional[str]
    vitals: Dict[str, Any]   # Extracted from text: hr, rr, spo2, sbp, dbp, temp
    chief_complaint: str     # First sentence or chief complaint phrase


def _extract_vitals(text: str) -> Dict[str, Any]:
    """Extract structured vitals from a clinical vignette."""
    v: Dict[str, Any] = {}

    m = re.search(r'(?:heart rate|HR|pulse)\s*(?:of\s*|:\s*|is\s*)?(\d{2,3})\b', text, re.I)
    if m:
        v['hr'] = int(m.group(1))

    m = re.search(r'(?:respiratory rate|RR|resp(?:iration)?\s*rate)\s*(?:of\s*|:\s*|is\s*)?(\d{1,2})\b', text, re.I)
    if m:
        v['rr'] = int(m.group(1))

    m = re.search(r'(?:oxygen saturation|SpO2|O2\s*sat(?:uration)?)\s*(?:of\s*|:\s*|is\s*|at\s*)?(\d{2,3})%?', text, re.I)
    if m:
        v['spo2'] = float(m.group(1))

    m = re.search(r'(?:blood pressure|BP)\s*(?:of\s*|:\s*|is\s*)?(\d{2,3})\s*/\s*(\d{2,3})', text, re.I)
    if m:
        v['sbp'] = int(m.group(1))
        v['dbp'] = int(m.group(2))

    m = re.search(r'(?:temperature|temp)\s*(?:of\s*|:\s*|is\s*)?(\d{2,3}(?:\.\d)?)(?:\s*°?\s*F)?', text, re.I)
    if m:
        v['temp'] = float(m.group(1))

    m = re.search(r'pain\s*(?:score|scale|rating|level)?\s*(?:of\s*|:\s*|is\s*|rated\s*(?:at\s*)?)?(\d{1,2})(?:\s*/\s*10|\s*out\s*of\s*10)?', text, re.I)
    if m:
        v['pain_score'] = min(10, max(0, int(m.group(1))))

    return v


def _extract_age(text: str) -> Optional[float]:
    m = re.search(r'(\d{1,3})\s*-?\s*year\s*-?\s*old', text, re.I)
    return float(m.group(1)) if m else None


def _extract_gender(text: str) -> Optional[str]:
    if re.search(r'\bfemale\b', text, re.I):
        return 'female'
    if re.search(r'\bmale\b', text, re.I):
        return 'male'
    return None


def _extract_chief_complaint(text: str) -> str:
    """Extract chief complaint phrase from vignette."""
    m = re.search(r'(?:chief complaint|presenting complaint|presents? (?:to|with|for))\s*(?:of\s*|:\s*|is\s*)?([^.]+)', text, re.I)
    if m:
        return m.group(1).strip()[:200]
    # Fallback: first sentence
    first_sentence = text.split('.')[0].strip()
    return first_sentence[:200] if first_sentence else text[:200]


def _resolve_esi(instruction: str, output: str) -> Optional[int]:
    """Resolve ESI level from instruction band + output resource count."""
    if 'immediate life-saving' in instruction:
        return 1
    if 'ESI Level 2' in instruction:
        return 2
    if 'resources likely required' in instruction:
        # Check resource count in output
        if re.search(r'(?:no|zero|0)\s+resource', output, re.I):
            return 5
        m = re.search(r'(\d+)\s*resource', output, re.I)
        if m:
            count = int(m.group(1))
            if count == 1:
                return 4
            if count >= 2:
                return 3
        return None  # Can't determine
    return None


def load_corpus_cases(mietic_dir: Path) -> List[CorpusCase]:
    """Load and parse all MIETIC corpus cases with resolved ESI levels."""
    path = mietic_dir / "MIETIC.csv"
    if not path.exists():
        raise FileNotFoundError(f"MIETIC corpus not found: {path}")

    cases: List[CorpusCase] = []

    with open(path, encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for i, row in enumerate(reader):
            instruction = row.get('instruction', '')
            vignette = row.get('input', '').strip()
            output = row.get('output', '')

            if not vignette:
                continue

            esi = _resolve_esi(instruction, output)
            if esi is None:
                continue

            vitals = _extract_vitals(vignette)
            age = _extract_age(vignette)
            gender = _extract_gender(vignette)
            cc = _extract_chief_complaint(vignette)

            cases.append(CorpusCase(
                row_index=i,
                esi_level=esi,
                vignette=vignette,
                age=age,
                gender=gender,
                vitals=vitals,
                chief_complaint=cc,
            ))

    return cases


def sample_balanced(
    cases: List[CorpusCase],
    target_per_level: int,
    seed: int = 42,
    require_vitals: int = 3,
) -> Tuple[List[CorpusCase], Dict[str, Any]]:
    """Sample up to target_per_level cases per ESI level.

    Only cases with at least `require_vitals` core vitals (HR,RR,SpO2,SBP,Temp)
    are included — ensures fair comparison against the NEWS2 engine.
    """
    core_keys = ('hr', 'rr', 'spo2', 'sbp', 'temp')

    by_level: Dict[int, List[CorpusCase]] = {1: [], 2: [], 3: [], 4: [], 5: []}
    skipped_no_vitals = 0

    for case in cases:
        core_count = sum(1 for k in core_keys if k in case.vitals)
        if core_count < require_vitals:
            skipped_no_vitals += 1
            continue
        by_level[case.esi_level].append(case)

    rng = random.Random(seed)
    selected: List[CorpusCase] = []
    selected_by_level: Dict[int, int] = {}

    for level in [1, 2, 3, 4, 5]:
        pool = by_level[level]
        rng.shuffle(pool)
        n = min(target_per_level, len(pool))
        selected.extend(pool[:n])
        selected_by_level[level] = n

    summary = {
        "total_corpus": len(cases),
        "eligible_with_vitals": len(cases) - skipped_no_vitals,
        "skipped_no_vitals": skipped_no_vitals,
        "target_per_level": target_per_level,
        "selected_by_level": selected_by_level,
        "total_selected": len(selected),
    }
    return selected, summary


def run_replay(cases: List[CorpusCase]) -> Dict[str, Any]:
    """Run cases through the deterministic engine."""
    from logic.deterministic_triage import DeterministicTriageEngine
    from models import PatientInput, Vitals, Gender

    os.environ.setdefault("DISABLE_RAG", "true")
    engine = DeterministicTriageEngine(use_ai=False)

    predictions: List[Dict[str, Any]] = []
    failures: List[Dict[str, Any]] = []
    confusion: Dict[int, Counter] = {i: Counter() for i in range(1, 6)}
    exact = 0
    within_one = 0
    over_triage = 0
    under_triage = 0
    critical_ut = 0

    for case in cases:
        try:
            gender = Gender.FEMALE if case.gender == 'female' else Gender.MALE
            age = case.age if case.age is not None else 40.0

            # Temperature: MIETIC vignettes use Fahrenheit
            temp = case.vitals.get('temp')
            if temp is not None and temp > 50:
                temp = round((temp - 32) * 5 / 9, 1)

            vitals = Vitals(
                hr=case.vitals.get('hr'),
                rr=case.vitals.get('rr'),
                spo2=case.vitals.get('spo2'),
                temp=temp,
                sbp=case.vitals.get('sbp'),
                dbp=case.vitals.get('dbp'),
                pain_score=case.vitals.get('pain_score', 0),
            )

            patient = PatientInput(
                age=age,
                gender=gender,
                chief_complaint_text=case.vignette,
                vitals=vitals,
                consciousness='A',
            )

            result = engine.evaluate(patient)
            predicted = int(getattr(result.level, 'value', result.level))
            actual = case.esi_level

            is_exact = predicted == actual
            is_within_one = abs(predicted - actual) <= 1
            is_critical_ut = actual <= 2 and predicted > actual
            is_over = predicted < actual
            is_under = predicted > actual

            if is_exact:
                exact += 1
            if is_within_one:
                within_one += 1
            if is_over:
                over_triage += 1
            if is_under:
                under_triage += 1
            if is_critical_ut:
                critical_ut += 1
            confusion[actual][predicted] += 1

            predictions.append({
                'row_index': case.row_index,
                'actual_esi': actual,
                'predicted_esi': predicted,
                'exact_match': is_exact,
                'within_one': is_within_one,
                'critical_under_triage': is_critical_ut,
                'chief_complaint': case.chief_complaint[:100],
                'label_en': getattr(result, 'label_en', ''),
            })

        except Exception as e:
            failures.append({
                'row_index': case.row_index,
                'actual_esi': case.esi_level,
                'error': f"{type(e).__name__}: {e}",
            })

    valid = len(predictions)
    summary = {
        'total_attempted': valid + len(failures),
        'valid_predictions': valid,
        'failed_predictions': len(failures),
        'exact_match_accuracy': round(100 * exact / valid, 2) if valid else 0,
        'within_one_level_accuracy': round(100 * within_one / valid, 2) if valid else 0,
        'over_triage_rate': round(100 * over_triage / valid, 2) if valid else 0,
        'under_triage_rate': round(100 * under_triage / valid, 2) if valid else 0,
        'critical_under_triage_rate': round(100 * critical_ut / valid, 4) if valid else 0,
        'critical_under_triage_count': critical_ut,
        'confusion_matrix': {
            str(actual): {str(pred): count for pred, count in sorted(counter.items())}
            for actual, counter in sorted(confusion.items()) if counter
        },
    }
    return {
        'summary': summary,
        'predictions': predictions,
        'failures': failures,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="MIETIC corpus benchmark")
    parser.add_argument('--mietic-dir', type=Path, default=DEFAULT_MIETIC_DIR)
    parser.add_argument('--target-per-level', type=int, default=200)
    parser.add_argument('--seed', type=int, default=42)
    parser.add_argument('--require-vitals', type=int, default=3)
    parser.add_argument('--output-dir', type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument('--tag', default=None)
    args = parser.parse_args()

    print("Loading MIETIC corpus...")
    cases = load_corpus_cases(args.mietic_dir)
    level_counts = Counter(c.esi_level for c in cases)
    print(f"  Loaded {len(cases)} cases with resolved ESI: {dict(sorted(level_counts.items()))}")

    selected, sample_summary = sample_balanced(
        cases, args.target_per_level, args.seed, args.require_vitals,
    )
    print(f"  Selected {sample_summary['total_selected']} cases: {sample_summary['selected_by_level']}")
    print(f"  Skipped {sample_summary['skipped_no_vitals']} with <{args.require_vitals} core vitals")

    print("\nRunning engine replay...")
    result = run_replay(selected)
    rs = result['summary']

    # Save outputs
    args.output_dir.mkdir(parents=True, exist_ok=True)
    tag = args.tag or f"{args.target_per_level}per"
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")

    payload = {
        'benchmark': 'MIETIC_corpus',
        'timestamp': timestamp,
        'sample_summary': sample_summary,
        'replay_summary': rs,
        'failures': result['failures'][:20],
    }
    json_path = args.output_dir / f"corpus_{tag}_{timestamp}.json"
    json_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False))

    pred_path = args.output_dir / f"corpus_{tag}_{timestamp}_predictions.csv"
    if result['predictions']:
        with open(pred_path, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=result['predictions'][0].keys())
            writer.writeheader()
            writer.writerows(result['predictions'])

    # Print results
    print(f"\n{'='*60}")
    print("MIETIC Corpus Benchmark Results")
    print(f"{'='*60}")
    print(f"  Cases:                 {rs['valid_predictions']}")
    print(f"  Exact match:           {rs['exact_match_accuracy']:.1f}%")
    print(f"  Within-one-level:      {rs['within_one_level_accuracy']:.1f}%")
    print(f"  Over-triage:           {rs['over_triage_rate']:.1f}%")
    print(f"  Under-triage:          {rs['under_triage_rate']:.1f}%")
    print(f"  Critical under-triage: {rs['critical_under_triage_count']} ({rs['critical_under_triage_rate']:.2f}%)")
    print(f"{'='*60}")

    cm = rs['confusion_matrix']
    print(f"\n{'':>12}", end='')
    for p in ['1', '2', '3', '4', '5']:
        print(f"{'pred '+p:>8}", end='')
    print()
    for actual in sorted(cm):
        print(f"  actual {actual}:", end='')
        for p in ['1', '2', '3', '4', '5']:
            print(f"{cm[actual].get(p, 0):>8}", end='')
        total = sum(cm[actual].values())
        correct = cm[actual].get(actual, 0)
        print(f"  | {correct}/{total} ({100*correct/total:.0f}%)")

    if rs['critical_under_triage_count'] == 0:
        print(f"\n  SAFETY GATE PASSED: Zero critical under-triage")
    else:
        print(f"\n  Critical under-triage: {rs['critical_under_triage_count']} cases")

    print(f"\n  Outputs: {json_path}")
    print(f"           {pred_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
