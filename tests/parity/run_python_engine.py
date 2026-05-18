"""
tests/parity/run_python_engine.py — run the canonical SAFE-Triage Python
engine against the shared parity fixtures and emit a JSON report.

    python tests/parity/run_python_engine.py
        → writes tests/parity/python_results.json + prints a summary.

The canonical engine is `DeterministicTriageEngine` from
`backend.logic.deterministic_triage` — the same one that
`backend/main.py` uses for the `/triage` endpoint and that the project's
benchmarks (MIETIC, MIETIC-Arabic, KTAS, NHAMCS) validate.

Why this exists:
    Hospital Lite mode keeps a JS fallback engine in the browser for
    when the backend is unreachable. This script + its Node companion
    (`run_js_engine.mjs --compare`) keep that fallback honest by failing
    loudly if it ever produces a *less acute* suggestion than the
    canonical engine on a critical case.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND_DIR = REPO_ROOT / "backend"
sys.path.insert(0, str(BACKEND_DIR))

# Quiet down heavy modules during import for this lightweight harness.
os.environ.setdefault("SAFE_TRIAGE_MODE", "hospital_lite")

from logic.deterministic_triage import DeterministicTriageEngine  # noqa: E402

FIXTURE_PATH = Path(__file__).with_name("critical_cases.json")
OUTPUT_PATH = Path(__file__).with_name("python_results.json")


def _to_backend_payload(case_input: dict) -> dict:
    """Map the shared fixture's input into the dict shape the canonical
    deterministic engine accepts (mirrors `PatientInput.model_dump()`)."""
    vitals = dict(case_input.get("vitals") or {})
    # Ensure every key the engine reads exists, even if None.
    for key in ("hr", "rr", "spo2", "temp", "sbp", "dbp"):
        vitals.setdefault(key, None)

    return {
        "patient_id": case_input.get("patient_id") or "PARITY",
        "patient_name": case_input.get("patient_name"),
        "age": float(case_input["age"]),
        "gender": case_input.get("gender", "male"),
        "chief_complaint_text": case_input.get("chief_complaint_text", "").strip(),
        "vitals": vitals,
        "history_cardiac": bool(case_input.get("history_cardiac", False)),
        "history_stroke": bool(case_input.get("history_stroke", False)),
        "immuno_compromised": bool(case_input.get("is_immunocompromised", False)),
        "is_immunocompromised": bool(case_input.get("is_immunocompromised", False)),
        "consciousness": (case_input.get("consciousness") or "A").upper(),
        "on_supplemental_o2": bool(case_input.get("on_supplemental_o2", False)),
        "is_copd": bool(case_input.get("is_copd", False)),
        "is_pregnant": bool(case_input.get("is_pregnant", False)),
        "gestational_weeks": case_input.get("gestational_weeks"),
        "pregnancy_complaint": case_input.get("pregnancy_complaint"),
        "pain_scale": case_input.get("pain_scale"),
        "pain_context": case_input.get("pain_context"),
    }


def _result_level(result) -> int:
    """Pull the integer level out of a DeterministicTriageEngine result."""
    for attr in ("final_level", "level", "esi_safe", "esi_level"):
        if hasattr(result, attr):
            value = getattr(result, attr)
            if value is None:
                continue
            try:
                return int(value)
            except (TypeError, ValueError):
                continue
    if isinstance(result, dict):
        for key in ("final_level", "level"):
            if result.get(key) is not None:
                return int(result[key])
    raise RuntimeError(f"Could not extract level from {result!r}")


def main() -> int:
    fixture = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    tolerance = int(fixture.get("tolerance", 0))
    engine = DeterministicTriageEngine(use_ai=False)

    results = []
    exit_code = 0

    print("Python canonical engine results:")
    for case in fixture["cases"]:
        payload = _to_backend_payload(case["input"])
        det_result = engine.triage(payload)
        level = _result_level(det_result)
        category = getattr(det_result, "category", None) or getattr(det_result, "label_en", "")
        expected_max = case.get("expected_max_level")

        results.append(
            {
                "name": case["name"],
                "level": level,
                "category": category,
                "expected_max_level": expected_max,
            }
        )

        marker = " "
        if expected_max is not None and level > expected_max:
            marker = "✗"
            exit_code = 1
        print(f"  {marker} {case['name']:<40} → L{level}  ({category})")
        if marker == "✗":
            print(f"     ✗ exceeds expected_max_level {expected_max}")

    OUTPUT_PATH.write_text(
        json.dumps({"tolerance": tolerance, "results": results}, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    print(f"\nWrote {OUTPUT_PATH.relative_to(REPO_ROOT)}")
    print("Next: run  node tests/parity/run_js_engine.mjs --compare")
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
