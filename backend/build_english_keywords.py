#!/usr/bin/env python3
"""Build an English clinical keyword database from MIMIC-IV-ED triage data."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

import pandas as pd

SPLIT_PATTERN = r"[,;&+]|\s+w/|\s+and\s+|\s+with\s+"

ABBREVIATIONS = {
    "cp": "chest pain",
    "sob": "shortness of breath",
    "n/v": "nausea vomiting",
    "n+v": "nausea vomiting",
    "ams": "altered mental status",
    "etoh": "alcohol intoxication",
    "mvc": "motor vehicle collision",
    "mva": "motor vehicle accident",
    "abd pain": "abdominal pain",
    "abd": "abdominal",
    "h/a": "headache",
    "ha": "headache",
    "sz": "seizure",
    "si": "suicidal ideation",
    "uti": "urinary tract infection",
    "uri": "upper respiratory infection",
    "lbp": "low back pain",
    "gi bleed": "gastrointestinal bleeding",
    "fb": "foreign body",
    "lac": "laceration",
    "fx": "fracture",
    "inj": "injury",
    "lle": "left lower extremity pain",
    "rle": "right lower extremity pain",
}

STOP_WORDS = {
    "pt",
    "patient",
    "c/o",
    "complains",
    "of",
    "states",
    "reports",
    "s/p",
    "hx",
    "the",
    "a",
    "an",
    "for",
    "to",
    "er",
    "ed",
    "eval",
    "evaluation",
    "follow",
    "up",
    "f/u",
}

MANUAL_KEYWORD_OVERRIDES = {
    "back pain": {"base_esi": 4, "is_red_flag": False, "resource_estimate": 1, "risk_tier": "low"},
    "lower back pain": {"base_esi": 4, "is_red_flag": False, "resource_estimate": 1, "risk_tier": "low"},
    "low back pain": {"base_esi": 4, "is_red_flag": False, "resource_estimate": 1, "risk_tier": "low"},
}


def atomize(text: object) -> List[str]:
    if pd.isna(text):
        return []
    parts = re.split(SPLIT_PATTERN, str(text).lower().strip())
    return [p.strip() for p in parts if len(p.strip()) > 1]


def _expand_abbreviations(text: str) -> str:
    expanded = f" {text} "
    for src, dst in sorted(ABBREVIATIONS.items(), key=lambda item: len(item[0]), reverse=True):
        pattern = re.compile(rf"\b{re.escape(src)}\b")
        expanded = pattern.sub(dst, expanded)
    return expanded.strip()


def normalize_fragment(fragment: str) -> Optional[str]:
    text = _expand_abbreviations(str(fragment).lower().strip())
    text = re.sub(r"[^a-z0-9\s/+.-]", " ", text)
    text = text.replace("/", " ").replace("+", " ").replace("-", " ")
    tokens = [tok for tok in re.split(r"\s+", text) if tok]
    cleaned_tokens = [tok for tok in tokens if tok not in STOP_WORDS]
    normalized = " ".join(cleaned_tokens).strip()
    if len(normalized) < 2:
        return None
    return normalized


def _mode_esi(counts: Dict[int, int]) -> int:
    ranked = sorted(((cnt, -esi) for esi, cnt in counts.items()), reverse=True)
    return -ranked[0][1]


def _map_base_esi(haf: float, mode_esi: int) -> Tuple[int, bool, str]:
    if haf >= 0.40:
        return 2, True, "high"
    if haf >= 0.25:
        return 3, False, "moderate"
    # For lower HAF terms, use the observed modal ESI directly.
    mode = int(mode_esi)
    if mode < 1:
        mode = 1
    elif mode > 5:
        mode = 5
    return mode, False, "mode_based"


def _resource_estimate_for_base_esi(base_esi: int) -> int:
    if base_esi <= 2:
        return 3
    if base_esi == 3:
        return 2
    if base_esi == 4:
        return 1
    return 0


def _discover_mimic_paths() -> Tuple[Optional[Path], Optional[Path]]:
    candidates = [
        Path("/Users/ahmedzayed/Downloads/mimic-iv-ed-2.2"),
        Path("/Users/ahmedzayed/Downloads/mimic-iv-ed"),
        Path("/Users/ahmedzayed/Documents/mimic-iv-ed"),
        Path("/Users/ahmedzayed/Downloads/mietic"),
    ]
    for base in candidates:
        if not base.exists():
            continue
        triage = next(iter(base.rglob("triage.csv.gz")), None)
        edstays = next(iter(base.rglob("edstays.csv.gz")), None)
        if triage and edstays:
            return triage, edstays
    return None, None


def _load_mimic(triage_path: Path, edstays_path: Path) -> pd.DataFrame:
    triage = pd.read_csv(
        triage_path,
        compression="gzip",
        usecols=["stay_id", "chiefcomplaint", "acuity"],
    )
    edstays = pd.read_csv(
        edstays_path,
        compression="gzip",
        usecols=["stay_id", "disposition"],
    )
    merged = triage.merge(edstays, on="stay_id", how="left")
    return merged


def _extract_keyword_records(df: pd.DataFrame) -> pd.DataFrame:
    rows: List[Tuple[str, int]] = []
    scoped = df[df["chiefcomplaint"].notna() & df["acuity"].notna()].copy()
    for _, row in scoped.iterrows():
        try:
            acuity = int(float(row["acuity"]))
        except Exception:
            continue
        if acuity < 1 or acuity > 5:
            continue
        fragments = atomize(row["chiefcomplaint"])
        normalized_fragments = {
            normalized
            for fragment in fragments
            for normalized in [normalize_fragment(fragment)]
            if normalized
        }
        for keyword in normalized_fragments:
            rows.append((keyword, acuity))
    return pd.DataFrame(rows, columns=["keyword_text", "acuity"])


def build_keyword_tables(data: pd.DataFrame, top_n: int, min_samples: int) -> Tuple[pd.DataFrame, pd.DataFrame]:
    extracted = _extract_keyword_records(data)
    if extracted.empty:
        return pd.DataFrame(), pd.DataFrame()

    counts = extracted.groupby(["keyword_text", "acuity"]).size().unstack(fill_value=0)
    for acuity in [1, 2, 3, 4, 5]:
        if acuity not in counts.columns:
            counts[acuity] = 0
    counts = counts[[1, 2, 3, 4, 5]].rename(
        columns={1: "esi_1_count", 2: "esi_2_count", 3: "esi_3_count", 4: "esi_4_count", 5: "esi_5_count"}
    )
    counts["sample_size"] = counts.sum(axis=1)
    counts["haf"] = (counts["esi_1_count"] + counts["esi_2_count"]) / counts["sample_size"]
    counts["mode_esi_raw"] = [
        _mode_esi({1: int(r["esi_1_count"]), 2: int(r["esi_2_count"]), 3: int(r["esi_3_count"]), 4: int(r["esi_4_count"]), 5: int(r["esi_5_count"])})
        for _, r in counts.iterrows()
    ]

    base_esi: List[int] = []
    red_flag: List[bool] = []
    risk_tier: List[str] = []
    for _, row in counts.iterrows():
        b, rf, tier = _map_base_esi(float(row["haf"]), int(row["mode_esi_raw"]))
        base_esi.append(b)
        red_flag.append(rf)
        risk_tier.append(tier)
    counts["base_esi"] = base_esi
    counts["is_red_flag"] = red_flag
    counts["risk_tier"] = risk_tier
    counts["resource_estimate"] = counts["base_esi"].map(_resource_estimate_for_base_esi)
    counts["high_acuity_pct"] = (counts["haf"] * 100.0).round(2)

    full_stats = counts.reset_index().sort_values("sample_size", ascending=False)
    selected = (
        full_stats[full_stats["sample_size"] >= int(min_samples)]
        .sort_values("sample_size", ascending=False)
        .head(int(top_n))
        .copy()
    )

    full_by_keyword = full_stats.set_index("keyword_text", drop=False)
    for keyword_text, override in MANUAL_KEYWORD_OVERRIDES.items():
        if keyword_text in selected["keyword_text"].values:
            selected.loc[selected["keyword_text"] == keyword_text, "base_esi"] = int(override["base_esi"])
            selected.loc[selected["keyword_text"] == keyword_text, "is_red_flag"] = bool(override["is_red_flag"])
            selected.loc[selected["keyword_text"] == keyword_text, "resource_estimate"] = int(override["resource_estimate"])
            selected.loc[selected["keyword_text"] == keyword_text, "risk_tier"] = str(override["risk_tier"])
        elif keyword_text in full_by_keyword.index:
            forced_row = full_by_keyword.loc[keyword_text].copy()
            forced_row["base_esi"] = int(override["base_esi"])
            forced_row["is_red_flag"] = bool(override["is_red_flag"])
            forced_row["resource_estimate"] = int(override["resource_estimate"])
            forced_row["risk_tier"] = str(override["risk_tier"])
            selected = pd.concat([selected, pd.DataFrame([forced_row])], ignore_index=True)

    if len(selected) > int(top_n):
        override_keywords = set(MANUAL_KEYWORD_OVERRIDES.keys())
        selected = selected.sort_values(["keyword_text"]).reset_index(drop=True)
        protected = selected[selected["keyword_text"].isin(override_keywords)]
        non_protected = selected[~selected["keyword_text"].isin(override_keywords)]
        non_protected = non_protected.sort_values("sample_size", ascending=False)
        keep_non_protected = max(0, int(top_n) - len(protected))
        selected = pd.concat([protected, non_protected.head(keep_non_protected)], ignore_index=True)
        selected = selected.sort_values("sample_size", ascending=False).reset_index(drop=True)
    selected = selected[
        [
            "keyword_text",
            "base_esi",
            "is_red_flag",
            "resource_estimate",
            "risk_tier",
            "high_acuity_pct",
            "sample_size",
            "esi_1_count",
            "esi_2_count",
            "esi_3_count",
            "esi_4_count",
            "esi_5_count",
            "mode_esi_raw",
        ]
    ]
    return selected, full_stats.reset_index()


def main() -> None:
    parser = argparse.ArgumentParser(description="Build English keyword DB from MIMIC-IV-ED triage data")
    parser.add_argument("--triage", type=Path, default=None, help="Path to triage.csv.gz")
    parser.add_argument("--edstays", type=Path, default=None, help="Path to edstays.csv.gz")
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=Path(__file__).resolve().parent / "logic",
        help="Output directory for keyword artifacts",
    )
    parser.add_argument("--top-n", type=int, default=500, help="Top-N keywords by frequency to keep")
    parser.add_argument("--min-samples", type=int, default=50, help="Minimum sample size per keyword")
    args = parser.parse_args()

    triage_path = args.triage
    edstays_path = args.edstays
    if not triage_path or not edstays_path:
        discovered_triage, discovered_edstays = _discover_mimic_paths()
        triage_path = triage_path or discovered_triage
        edstays_path = edstays_path or discovered_edstays
    if not triage_path or not edstays_path:
        raise FileNotFoundError("Could not locate MIMIC-IV-ED triage/edstays files")

    print(f"Using triage file: {triage_path}")
    print(f"Using edstays file: {edstays_path}")
    data = _load_mimic(triage_path, edstays_path)
    print(f"Total merged rows: {len(data):,}")
    print(f"Non-null chiefcomplaint: {int(data['chiefcomplaint'].notna().sum()):,}")
    print("Acuity distribution:")
    print(data["acuity"].value_counts(dropna=False).sort_index().to_string())

    selected, full_stats = build_keyword_tables(data, top_n=args.top_n, min_samples=args.min_samples)
    args.out_dir.mkdir(parents=True, exist_ok=True)

    json_path = args.out_dir / "english_clinical_keywords.json"
    csv_path = args.out_dir / "english_clinical_keywords.csv"
    full_stats_path = args.out_dir / "mimic_complaint_full_statistics.csv"

    payload = selected[
        [
            "keyword_text",
            "base_esi",
            "is_red_flag",
            "resource_estimate",
            "risk_tier",
            "high_acuity_pct",
            "sample_size",
        ]
    ].to_dict(orient="records")
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2))
    selected.to_csv(csv_path, index=False)
    full_stats.to_csv(full_stats_path, index=False)

    print("\nBuild summary:")
    print(f"  Output keywords: {len(selected):,}")
    print(f"  JSON: {json_path}")
    print(f"  CSV: {csv_path}")
    print(f"  Full stats CSV: {full_stats_path}")

    if not selected.empty:
        print("\nTop 20 keywords by frequency:")
        print(selected[["keyword_text", "sample_size", "base_esi", "high_acuity_pct"]].head(20).to_string(index=False))

        red_flags = selected[selected["is_red_flag"]].sort_values("sample_size", ascending=False).head(10)
        print("\nTop 10 red-flag keywords:")
        if red_flags.empty:
            print("  (none)")
        else:
            print(red_flags[["keyword_text", "sample_size", "high_acuity_pct", "base_esi"]].to_string(index=False))

        print("\nFinal DB base_esi distribution:")
        print(selected["base_esi"].value_counts().sort_index().to_string())


if __name__ == "__main__":
    main()
