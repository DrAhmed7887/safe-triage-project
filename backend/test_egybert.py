from __future__ import annotations

import json
from pathlib import Path

import pytest
import torch

try:
    from arabic_keywords_v2 import ARABIC_KEYWORDS_V2
    from egybert_matcher import EgyBertOfflineMatcher
except ImportError:
    from backend.arabic_keywords_v2 import ARABIC_KEYWORDS_V2
    from backend.egybert_matcher import EgyBertOfflineMatcher


BACKEND_DIR = Path(__file__).resolve().parent
MODEL_DIR = BACKEND_DIR / "egybert_model"
MODEL_CONFIG_PATH = MODEL_DIR / "config.json"
MODEL_WEIGHTS_CANDIDATES = (
    MODEL_DIR / "model.safetensors",
    MODEL_DIR / "pytorch_model.bin",
)
EMBEDDINGS_PATH = BACKEND_DIR / "keyword_embeddings.pt"
INDEX_PATH = BACKEND_DIR / "keyword_index.json"


def _has_model_weights() -> bool:
    return any(candidate.exists() for candidate in MODEL_WEIGHTS_CANDIDATES)


def _require_assets() -> None:
    if not MODEL_DIR.exists() or not MODEL_CONFIG_PATH.exists() or not _has_model_weights():
        pytest.skip("EgyBERT model weights are not downloaded (run backend/download_egybert.py)")
    if not EMBEDDINGS_PATH.exists() or not INDEX_PATH.exists():
        pytest.skip("Precomputed embedding assets are missing (run precompute_embeddings.py)")


def _matcher() -> EgyBertOfflineMatcher:
    _require_assets()
    return EgyBertOfflineMatcher(
        model_dir=str(MODEL_DIR),
        embeddings_path=str(EMBEDDINGS_PATH),
        index_path=str(INDEX_PATH),
        similarity_threshold=0.7,
    )


def test_abdominal_variation_matches_abdominal_category() -> None:
    matcher = _matcher()
    result = matcher.match("بطني بتولع فيا")
    assert result["category"] == "abdominal_pain_moderate"


def test_dyspnea_variation_matches_respiratory_distress() -> None:
    matcher = _matcher()
    result = matcher.match("مش قادر أخد نفسي خالص")
    assert result["category"] == "respiratory_distress"


def test_severe_headache_phrase_matches_headache_category() -> None:
    matcher = _matcher()
    result = matcher.match("راسي هتنفجر")
    assert result["category"] == "severe_headache"


def test_non_arabic_noise_returns_conservative_unknown_default() -> None:
    matcher = _matcher()
    result = matcher.match("random english text xyz")
    assert result["category"] == "unknown"
    assert int(result["base_esi"]) == 3


def test_all_keywords_have_precomputed_embeddings() -> None:
    _require_assets()
    embeddings = torch.load(EMBEDDINGS_PATH, map_location="cpu")
    with INDEX_PATH.open("r", encoding="utf-8") as fh:
        keyword_index = json.load(fh)

    keyword_count = len(ARABIC_KEYWORDS_V2)
    assert keyword_count >= 1800
    assert isinstance(embeddings, torch.Tensor)
    assert int(embeddings.shape[0]) == keyword_count
    assert len(keyword_index) == keyword_count
