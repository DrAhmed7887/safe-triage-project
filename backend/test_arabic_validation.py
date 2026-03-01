#!/usr/bin/env python3
"""
Arabic validation suite for offline SAFE-Triage matching.

Runs three methods against the same 50 Arabic cases:
1) Exact keyword full-string match only (from ARABIC_KEYWORDS_V2)
2) EgyBERT semantic matching (EgyBertOfflineMatcher)
3) Combined (EgyBERT first, exact keyword fallback)

Outputs:
- Detailed per-case console report
- Summary table
- backend/arabic_validation_results.json
"""

from __future__ import annotations

import json
import traceback
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Sequence, Tuple


BACKEND_DIR = Path(__file__).resolve().parent
RESULTS_PATH = BACKEND_DIR / "arabic_validation_results.json"


def _normalize_text(text: str) -> str:
    return " ".join(str(text or "").strip().split()).lower()


def _safe_int(value: Any, default: int = 3) -> int:
    try:
        return int(value)
    except Exception:
        return default


@dataclass(frozen=True)
class TestCase:
    case_id: int
    group: str
    text: str
    expected_label: str
    expected_esi: int
    accepted_categories: Tuple[str, ...]


def _tc(
    case_id: int,
    group: str,
    text: str,
    expected_label: str,
    expected_esi: int,
    accepted_categories: Sequence[str],
) -> TestCase:
    return TestCase(
        case_id=case_id,
        group=group,
        text=text,
        expected_label=expected_label,
        expected_esi=expected_esi,
        accepted_categories=tuple(accepted_categories),
    )


TEST_CASES: List[TestCase] = [
    _tc(1, "Abdominal", "بطني بتولع فيا", "abdominal_pain", 2, ("abdominal_pain_moderate",)),
    _tc(2, "Abdominal", "معدتي بتقطع من الصبح", "abdominal_pain", 2, ("abdominal_pain_moderate",)),
    _tc(3, "Abdominal", "عندي مغص جامد ومش قادر أقف", "abdominal_pain", 2, ("abdominal_pain_moderate", "severe_pain")),
    _tc(4, "Abdominal", "بطني منفوخة ومتحجرة", "acute_abdomen", 2, ("abdominal_pain_moderate", "severe_pain", "mesenteric_ischemia")),
    _tc(
        5,
        "Abdominal",
        "ألم أسفل البطن على اليمين وسخونية",
        "appendicitis/rlq_pain",
        2,
        ("abdominal_pain_moderate", "high_fever_toxic", "fever_with_symptoms"),
    ),
    _tc(
        6,
        "Abdominal",
        "بطني بتوجعني وبستفرغ من إمبارح",
        "abd_pain_vomiting",
        2,
        ("abdominal_pain_moderate", "vomiting_dehydration"),
    ),
    _tc(7, "Abdominal", "مغص وإسهال من 3 أيام", "abdominal_pain", 3, ("abdominal_pain_moderate", "mild_gi")),
    _tc(8, "Abdominal", "حرقان في المعدة بعد الأكل", "heartburn", 4, ("mild_gi", "chest_pain_noncardiac")),
    _tc(9, "Abdominal", "بطني بتنغز من الجنب", "abdominal_pain", 3, ("abdominal_pain_moderate", "kidney_stone")),
    _tc(
        10,
        "Abdominal",
        "عندي مغص وسخونية عالية",
        "abd_pain_fever",
        2,
        ("abdominal_pain_moderate", "high_fever_toxic", "fever_with_symptoms"),
    ),
    _tc(11, "Dyspnea", "مش قادر أخد نفسي خالص", "dyspnea", 2, ("respiratory_distress", "moderate_dyspnea")),
    _tc(12, "Dyspnea", "بنهج من أقل مجهود", "dyspnea", 2, ("respiratory_distress", "moderate_dyspnea")),
    _tc(13, "Dyspnea", "النفس مقطوع ومش عارف أتنفس", "dyspnea", 2, ("respiratory_distress",)),
    _tc(14, "Dyspnea", "كتمة في صدري من الصبح", "dyspnea", 2, ("respiratory_distress", "moderate_dyspnea")),
    _tc(15, "Dyspnea", "بيتخنق ووشه بقى أزرق", "dyspnea", 2, ("respiratory_distress",)),
    _tc(16, "Dyspnea", "نفسي بينقطع لما بطلع السلم", "dyspnea_exertion", 3, ("moderate_dyspnea", "respiratory_distress")),
    _tc(17, "Dyspnea", "صدري بيصفر وعندي أزمة", "asthma/wheezing", 2, ("asthma_exacerbation", "respiratory_distress")),
    _tc(18, "Dyspnea", "الطفل مش بيتنفس كويس", "dyspnea", 2, ("respiratory_distress", "pediatric_distress", "pediatric_emergency")),
    _tc(19, "Fever/Infection", "سخونية جامدة ورعشة من إمبارح", "fever_rigor", 2, ("high_fever_toxic", "fever_with_symptoms")),
    _tc(20, "Fever/Infection", "جسمي نار والحرارة مش بتنزل", "high_fever", 2, ("high_fever_toxic",)),
    _tc(
        21,
        "Fever/Infection",
        "سخونية مع ألم في البطن",
        "fever_abd",
        2,
        ("high_fever_toxic", "fever_with_symptoms", "abdominal_pain_moderate"),
    ),
    _tc(
        22,
        "Fever/Infection",
        "حرارة وكحة وضيق نفس",
        "fever + cough_dyspnea",
        2,
        ("respiratory_distress", "high_fever_toxic", "fever_with_symptoms"),
    ),
    _tc(23, "Vomiting", "بستفرغ دم من الصبح", "hematemesis", 1, ("severe_bleeding", "gi_bleed")),
    _tc(24, "Vomiting", "الترجيع فيه لون بني زي البن", "hematemesis", 2, ("severe_bleeding", "gi_bleed")),
    _tc(25, "Vomiting", "كل ما بأكل حاجة بستفرغها", "intractable_vomiting", 2, ("vomiting_dehydration",)),
    _tc(
        26,
        "Vomiting",
        "ترجيع وإسهال ومش قادر أشرب ميه",
        "vomiting + diarrhea",
        2,
        ("vomiting_dehydration", "fever_with_symptoms", "mild_gi"),
    ),
    _tc(27, "Syncope/Dizziness", "أغمى عليا في الشارع ووقعت", "syncope", 2, ("altered_mental_status", "unconscious")),
    _tc(28, "Syncope/Dizziness", "عيني بتسود لما بقوم", "presyncope", 3, ("altered_mental_status",)),
    _tc(29, "Syncope/Dizziness", "دوخة جامدة والدنيا بتلف بيا", "vertigo", 3, ("altered_mental_status",)),
    _tc(30, "Syncope/Dizziness", "فقدت وعيي لمدة دقيقة", "syncope", 2, ("altered_mental_status", "unconscious")),
    _tc(31, "Weakness", "رجليا مش شايلاني وجسمي مكسر", "severe_weakness", 2, ("altered_mental_status", "severe_pain")),
    _tc(32, "Weakness", "نص جسمي الشمال مش بيتحرك فجأة", "hemiparesis", 1, ("stroke_symptoms",)),
    _tc(33, "Weakness", "هلكان ومش قادر أقوم من السرير", "severe_weakness", 2, ("altered_mental_status", "severe_pain")),
    _tc(34, "Weakness", "إيدي اليمين مش بتتحرك من الصبح", "limb_weakness", 2, ("stroke_symptoms",)),
    _tc(
        35,
        "Chest Pain/Cardiac",
        "صدري بيضغط عليا والألم واصل لدراعي الشمال",
        "chest_pain_radiation",
        2,
        ("chest_pain_cardiac",),
    ),
    _tc(36, "Chest Pain/Cardiac", "قلبي بينط وبيدق بسرعة جامدة", "palpitations", 2, ("chest_pain_cardiac",)),
    _tc(37, "Chest Pain/Cardiac", "حاسس فيه حاجة واقفة على صدري", "chest_pain", 2, ("chest_pain_cardiac", "chest_pain_noncardiac")),
    _tc(38, "Neuro/Stroke", "وشي مال فجأة ومش قادر أتكلم", "facial_droop + aphasia", 1, ("stroke_symptoms",)),
    _tc(39, "Neuro/Stroke", "أسوأ صداع في حياتي جه فجأة", "thunderclap_headache", 1, ("severe_headache",)),
    _tc(40, "Neuro/Stroke", "اتشنج ووقع على الأرض", "seizure", 2, ("active_seizure",)),
    _tc(41, "Neuro/Stroke", "لساني تقيل وكلامي مش مفهوم", "speech_disturbance", 1, ("stroke_symptoms",)),
    _tc(42, "Trauma", "حادثة عربية واتخبط في راسه", "mva + head_injury", 2, ("severe_trauma",)),
    _tc(43, "Trauma", "اتطعن بسكينة في بطنه", "stab_wound", 1, ("severe_trauma",)),
    _tc(44, "Trauma", "وقع من الدور التالت على راسه", "fall_height", 1, ("severe_trauma",)),
    _tc(45, "Trauma", "نزيف مش بيوقف من الجرح", "active_bleeding", 1, ("severe_bleeding", "moderate_bleeding")),
    _tc(46, "Diabetic Silent MI", "عندي سكر وحرقان في المعدة من الصبح", "dm_silent_mi", 2, ("silent_mi", "chest_pain_cardiac")),
    _tc(47, "Diabetic Silent MI", "السكر نازل وبترعش وبدوخ", "hypoglycemia", 2, ("diabetic_emergency",)),
    _tc(48, "Diabetic Silent MI", "غيبوبة سكر ومش بيرد", "diabetic_coma", 1, ("diabetic_emergency", "unconscious")),
    _tc(49, "Psychiatric/Poisoning", "بلعت كل الحبوب اللي في البيت عايز أموت", "overdose + suicidal", 1, ("poisoning_overdose", "suicidal_homicidal")),
    _tc(50, "Psychiatric/Poisoning", "شربت كلور ومعدتي بتولع", "poisoning", 1, ("poisoning_overdose",)),
]


def _import_keywords() -> Dict[str, Dict[str, Any]]:
    try:
        from arabic_keywords_v2 import ARABIC_KEYWORDS_V2

        return ARABIC_KEYWORDS_V2
    except Exception as primary_exc:
        print(f"[IMPORT ERROR] arabic_keywords_v2 import failed: {primary_exc}")
        print(traceback.format_exc().rstrip())
        try:
            from backend.arabic_keywords_v2 import ARABIC_KEYWORDS_V2

            return ARABIC_KEYWORDS_V2
        except Exception as fallback_exc:
            print(f"[IMPORT ERROR] backend.arabic_keywords_v2 import failed: {fallback_exc}")
            print(traceback.format_exc().rstrip())
            raise


def _import_matcher_class():
    try:
        from egybert_matcher import EgyBertOfflineMatcher

        return EgyBertOfflineMatcher
    except Exception as primary_exc:
        print(f"[IMPORT ERROR] egybert_matcher import failed: {primary_exc}")
        print(traceback.format_exc().rstrip())
        try:
            from backend.egybert_matcher import EgyBertOfflineMatcher

            return EgyBertOfflineMatcher
        except Exception as fallback_exc:
            print(f"[IMPORT ERROR] backend.egybert_matcher import failed: {fallback_exc}")
            print(traceback.format_exc().rstrip())
            raise


def _method_a_exact_keyword(text: str, keywords: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    normalized = _normalize_text(text)
    candidates: List[Tuple[int, int, str, Dict[str, Any]]] = []

    for keyword, payload in keywords.items():
        if keyword and keyword in normalized:
            base_esi = _safe_int(payload.get("base_esi"), default=3)
            # Prefer safer/higher acuity keywords (lower ESI), then longer exact phrases.
            candidates.append((base_esi, -len(keyword), keyword, payload))

    if not candidates:
        return {
            "method": "Exact Keyword Only",
            "matched": False,
            "matched_keyword": "MISS",
            "category": "unknown",
            "esi": 3,
        }

    candidates.sort(key=lambda item: (item[0], item[1], item[2]))
    best_esi, _, best_keyword, best_payload = candidates[0]

    return {
        "method": "Exact Keyword Only",
        "matched": True,
        "matched_keyword": best_keyword,
        "category": str(best_payload.get("category", "unknown")),
        "esi": best_esi,
    }


def _method_b_egybert(text: str, matcher: Any) -> Dict[str, Any]:
    try:
        raw = matcher.match(text, top_k=3)
    except Exception as exc:
        return {
            "method": "EgyBERT Semantic",
            "matched": False,
            "category": "unknown",
            "esi": 3,
            "top_keyword": "MISS",
            "top_similarity": None,
            "threshold": None,
            "error": f"{type(exc).__name__}: {exc}",
        }

    top_matches = raw.get("top_matches", []) or []
    top = top_matches[0] if top_matches else {}
    top_keyword = top.get("keyword", "MISS") if isinstance(top, dict) else "MISS"
    top_similarity = top.get("similarity") if isinstance(top, dict) else None

    return {
        "method": "EgyBERT Semantic",
        "matched": bool(raw.get("matched", False)),
        "category": str(raw.get("category", "unknown")),
        "esi": _safe_int(raw.get("base_esi"), default=3),
        "top_keyword": top_keyword,
        "top_similarity": top_similarity,
        "threshold": raw.get("threshold"),
        "semantic_keyword": raw.get("keyword"),
        "semantic_similarity": raw.get("similarity"),
        "top_matches": top_matches,
    }


def _method_c_combined(method_a: Dict[str, Any], method_b: Dict[str, Any]) -> Dict[str, Any]:
    if method_b.get("matched") and method_b.get("category") != "unknown":
        return {
            "method": "Combined (EgyBERT+KW)",
            "source": "EgyBERT",
            "category": method_b.get("category", "unknown"),
            "esi": _safe_int(method_b.get("esi"), default=3),
            "matched_keyword": method_b.get("semantic_keyword") or method_b.get("top_keyword") or "MISS",
            "similarity": method_b.get("semantic_similarity", method_b.get("top_similarity")),
        }

    return {
        "method": "Combined (EgyBERT+KW)",
        "source": "KeywordFallback",
        "category": method_a.get("category", "unknown"),
        "esi": _safe_int(method_a.get("esi"), default=3),
        "matched_keyword": method_a.get("matched_keyword", "MISS"),
        "similarity": None,
    }


def _score_category(predicted_category: str, accepted: Sequence[str]) -> bool:
    return str(predicted_category) in set(accepted)


def _score_safe_esi(predicted_esi: Any, expected_esi: int) -> bool:
    return _safe_int(predicted_esi, default=3) <= int(expected_esi)


def _pct(part: int, total: int) -> float:
    if total == 0:
        return 0.0
    return (float(part) / float(total)) * 100.0


def _print_case_result(case: TestCase, method_a: Dict[str, Any], method_b: Dict[str, Any], method_c: Dict[str, Any]) -> None:
    print("=" * 110)
    print(f"Case {case.case_id:02d} [{case.group}]")
    print(f"Input: {case.text}")
    print(f"Expected: {case.expected_label} | ESI {case.expected_esi}")

    print(
        "A) Exact Keyword: "
        f"matched_keyword={method_a['matched_keyword']} | "
        f"category={method_a['category']} | "
        f"ESI={method_a['esi']} | "
        f"category_correct={method_a['category_correct']} | "
        f"safe_esi={method_a['safe_esi']}"
    )

    print(
        "B) EgyBERT: "
        f"top_match={method_b.get('top_keyword', 'MISS')} | "
        f"similarity={method_b.get('top_similarity')} | "
        f"category={method_b['category']} | "
        f"ESI={method_b['esi']} | "
        f"matched={method_b['matched']} | "
        f"category_correct={method_b['category_correct']} | "
        f"safe_esi={method_b['safe_esi']}"
    )
    if method_b.get("error"):
        print(f"   EgyBERT error: {method_b['error']}")

    print(
        "C) Combined: "
        f"source={method_c['source']} | "
        f"matched_keyword={method_c['matched_keyword']} | "
        f"category={method_c['category']} | "
        f"ESI={method_c['esi']} | "
        f"similarity={method_c.get('similarity')} | "
        f"category_correct={method_c['category_correct']} | "
        f"safe_esi={method_c['safe_esi']}"
    )


def run_validation() -> Dict[str, Any]:
    keywords = _import_keywords()
    matcher_cls = _import_matcher_class()

    try:
        matcher = matcher_cls()
    except Exception as exc:
        print(f"[IMPORT ERROR] EgyBERT matcher initialization failed: {exc}")
        print(traceback.format_exc().rstrip())
        raise

    total_cases = len(TEST_CASES)
    method_stats: Dict[str, Dict[str, int]] = {
        "exact_keyword_only": {"category_correct": 0, "safe_esi": 0},
        "egybert_semantic": {"category_correct": 0, "safe_esi": 0},
        "combined_egybert_kw": {"category_correct": 0, "safe_esi": 0},
    }
    per_category: Dict[str, Dict[str, int]] = {}

    caught_by_egybert_not_kw = 0
    caught_by_kw_not_egybert = 0

    detailed_cases: List[Dict[str, Any]] = []

    for case in TEST_CASES:
        method_a = _method_a_exact_keyword(case.text, keywords)
        method_b = _method_b_egybert(case.text, matcher)
        method_c = _method_c_combined(method_a, method_b)

        method_a["category_correct"] = _score_category(method_a["category"], case.accepted_categories)
        method_b["category_correct"] = _score_category(method_b["category"], case.accepted_categories)
        method_c["category_correct"] = _score_category(method_c["category"], case.accepted_categories)

        method_a["safe_esi"] = _score_safe_esi(method_a["esi"], case.expected_esi)
        method_b["safe_esi"] = _score_safe_esi(method_b["esi"], case.expected_esi)
        method_c["safe_esi"] = _score_safe_esi(method_c["esi"], case.expected_esi)

        if method_a["category_correct"]:
            method_stats["exact_keyword_only"]["category_correct"] += 1
        if method_b["category_correct"]:
            method_stats["egybert_semantic"]["category_correct"] += 1
        if method_c["category_correct"]:
            method_stats["combined_egybert_kw"]["category_correct"] += 1

        if method_a["safe_esi"]:
            method_stats["exact_keyword_only"]["safe_esi"] += 1
        if method_b["safe_esi"]:
            method_stats["egybert_semantic"]["safe_esi"] += 1
        if method_c["safe_esi"]:
            method_stats["combined_egybert_kw"]["safe_esi"] += 1

        if method_b["category_correct"] and not method_a["category_correct"]:
            caught_by_egybert_not_kw += 1
        if method_a["category_correct"] and not method_b["category_correct"]:
            caught_by_kw_not_egybert += 1

        group_stats = per_category.setdefault(
            case.group,
            {"total": 0, "kw_correct": 0, "egybert_correct": 0, "combined_correct": 0},
        )
        group_stats["total"] += 1
        if method_a["category_correct"]:
            group_stats["kw_correct"] += 1
        if method_b["category_correct"]:
            group_stats["egybert_correct"] += 1
        if method_c["category_correct"]:
            group_stats["combined_correct"] += 1

        _print_case_result(case, method_a, method_b, method_c)

        detailed_cases.append(
            {
                "case_id": case.case_id,
                "group": case.group,
                "input_text": case.text,
                "expected": {
                    "category_label": case.expected_label,
                    "esi": case.expected_esi,
                    "accepted_internal_categories": list(case.accepted_categories),
                },
                "method_a_exact_keyword": method_a,
                "method_b_egybert_semantic": method_b,
                "method_c_combined": method_c,
            }
        )

    print()
    print(f"ARABIC VALIDATION RESULTS ({total_cases} test cases)")
    print(f"{'Method':<24} {'Category Accuracy':<24} {'Safe ESI Rate':<24}")

    a_cat = method_stats["exact_keyword_only"]["category_correct"]
    a_safe = method_stats["exact_keyword_only"]["safe_esi"]
    b_cat = method_stats["egybert_semantic"]["category_correct"]
    b_safe = method_stats["egybert_semantic"]["safe_esi"]
    c_cat = method_stats["combined_egybert_kw"]["category_correct"]
    c_safe = method_stats["combined_egybert_kw"]["safe_esi"]

    print(f"{'Exact Keyword Only':<24} {a_cat}/{total_cases} ({_pct(a_cat, total_cases):.1f}%)".ljust(48) + f"{a_safe}/{total_cases} ({_pct(a_safe, total_cases):.1f}%)")
    print(f"{'EgyBERT Semantic':<24} {b_cat}/{total_cases} ({_pct(b_cat, total_cases):.1f}%)".ljust(48) + f"{b_safe}/{total_cases} ({_pct(b_safe, total_cases):.1f}%)")
    print(f"{'Combined (EgyBERT+KW)':<24} {c_cat}/{total_cases} ({_pct(c_cat, total_cases):.1f}%)".ljust(48) + f"{c_safe}/{total_cases} ({_pct(c_safe, total_cases):.1f}%)")

    print(f"Cases where EgyBERT caught what keywords missed: {caught_by_egybert_not_kw}")
    print(f"Cases where keywords caught what EgyBERT missed: {caught_by_kw_not_egybert}")
    print("Per-Category Results:")
    for group in [
        "Abdominal",
        "Dyspnea",
        "Fever/Infection",
        "Vomiting",
        "Syncope/Dizziness",
        "Weakness",
        "Chest Pain/Cardiac",
        "Neuro/Stroke",
        "Trauma",
        "Diabetic Silent MI",
        "Psychiatric/Poisoning",
    ]:
        stats = per_category.get(group, {"total": 0, "kw_correct": 0, "egybert_correct": 0, "combined_correct": 0})
        total = stats["total"]
        print(
            f"{group:<22} "
            f"KW={stats['kw_correct']}/{total}  "
            f"EgyBERT={stats['egybert_correct']}/{total}  "
            f"Combined={stats['combined_correct']}/{total}"
        )

    payload = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "total_cases": total_cases,
        "summary": {
            "exact_keyword_only": {
                "category_correct": a_cat,
                "category_accuracy_percent": round(_pct(a_cat, total_cases), 2),
                "safe_esi": a_safe,
                "safe_esi_percent": round(_pct(a_safe, total_cases), 2),
            },
            "egybert_semantic": {
                "category_correct": b_cat,
                "category_accuracy_percent": round(_pct(b_cat, total_cases), 2),
                "safe_esi": b_safe,
                "safe_esi_percent": round(_pct(b_safe, total_cases), 2),
            },
            "combined_egybert_kw": {
                "category_correct": c_cat,
                "category_accuracy_percent": round(_pct(c_cat, total_cases), 2),
                "safe_esi": c_safe,
                "safe_esi_percent": round(_pct(c_safe, total_cases), 2),
            },
            "egybert_caught_when_kw_missed": caught_by_egybert_not_kw,
            "kw_caught_when_egybert_missed": caught_by_kw_not_egybert,
        },
        "per_category": per_category,
        "cases": detailed_cases,
    }

    with RESULTS_PATH.open("w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=2)

    print(f"\nSaved detailed results to: {RESULTS_PATH}")
    return payload


def main() -> int:
    try:
        run_validation()
        return 0
    except Exception as exc:
        print(f"\nValidation suite failed: {type(exc).__name__}: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
