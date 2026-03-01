"""
Offline semantic matcher powered by local EgyBERT embeddings.

Design notes:
- 100% offline: `local_files_only=True`, no runtime network calls.
- Lazy loading: model/index/tensors load on first `match()` call.
- Uses cosine similarity over L2-normalized [CLS] embeddings.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from threading import Lock
from typing import Dict, List, Optional

import torch

ARABIC_CHAR_PATTERN = re.compile(r"[\u0600-\u06FF]")


class EgyBertOfflineMatcher:
    def __init__(
        self,
        *,
        model_dir: Optional[str] = None,
        embeddings_path: Optional[str] = None,
        index_path: Optional[str] = None,
        similarity_threshold: float = 0.70,
    ) -> None:
        backend_dir = Path(__file__).resolve().parent
        self.model_dir = Path(model_dir) if model_dir else backend_dir / "egybert_model"
        self.embeddings_path = Path(embeddings_path) if embeddings_path else backend_dir / "keyword_embeddings.pt"
        self.index_path = Path(index_path) if index_path else backend_dir / "keyword_index.json"
        self.similarity_threshold = float(similarity_threshold)

        self._tokenizer = None
        self._model = None
        self._keyword_embeddings: Optional[torch.Tensor] = None
        self._keyword_index: Dict[int, Dict[str, object]] = {}
        self._loaded = False
        self._load_error: Optional[Exception] = None
        self._lock = Lock()

    def _ensure_loaded(self) -> None:
        if self._loaded:
            return
        if self._load_error is not None:
            raise RuntimeError("EgyBERT assets are unavailable") from self._load_error

        with self._lock:
            if self._loaded:
                return
            if self._load_error is not None:
                raise RuntimeError("EgyBERT assets are unavailable") from self._load_error

            try:
                if not self.model_dir.exists():
                    raise FileNotFoundError(f"Model directory not found: {self.model_dir}")
                if not self.embeddings_path.exists():
                    raise FileNotFoundError(f"Embeddings file not found: {self.embeddings_path}")
                if not self.index_path.exists():
                    raise FileNotFoundError(f"Keyword index file not found: {self.index_path}")

                # Deferred import to keep module import fast for non-offline paths.
                from transformers import AutoModel, AutoTokenizer

                self._tokenizer = AutoTokenizer.from_pretrained(
                    str(self.model_dir), local_files_only=True
                )
                self._model = AutoModel.from_pretrained(str(self.model_dir), local_files_only=True)
                self._model.eval()

                loaded = torch.load(self.embeddings_path, map_location="cpu")
                if isinstance(loaded, dict) and "embeddings" in loaded:
                    loaded = loaded["embeddings"]
                if not isinstance(loaded, torch.Tensor):
                    raise TypeError("keyword_embeddings.pt must contain a torch.Tensor")

                self._keyword_embeddings = torch.nn.functional.normalize(
                    loaded.float(), p=2, dim=1
                )

                with self.index_path.open("r", encoding="utf-8") as fh:
                    raw_index = json.load(fh)
                self._keyword_index = {int(idx): value for idx, value in raw_index.items()}

                if len(self._keyword_index) != int(self._keyword_embeddings.shape[0]):
                    raise ValueError(
                        f"Index/embedding mismatch: {len(self._keyword_index)} != "
                        f"{int(self._keyword_embeddings.shape[0])}"
                    )

                self._loaded = True
            except Exception as exc:  # pragma: no cover - guarded runtime failure path
                self._load_error = exc
                raise

    def _embed_text(self, text: str) -> torch.Tensor:
        encoded = self._tokenizer(
            [text],
            return_tensors="pt",
            padding=True,
            truncation=True,
            max_length=64,
        )
        with torch.no_grad():
            outputs = self._model(**encoded)
            cls_embedding = outputs.last_hidden_state[:, 0, :]
            cls_embedding = torch.nn.functional.normalize(cls_embedding, p=2, dim=1)
            return cls_embedding.squeeze(0).cpu()

    def match(self, text: str, top_k: int = 3) -> Dict[str, object]:
        cleaned_text = " ".join(str(text or "").strip().split())
        if not cleaned_text:
            return {
                "category": "unknown",
                "base_esi": 3,
                "red_flag": False,
                "matched": False,
                "top_matches": [],
                "threshold": self.similarity_threshold,
            }
        if not ARABIC_CHAR_PATTERN.search(cleaned_text):
            return {
                "category": "unknown",
                "base_esi": 3,
                "red_flag": False,
                "matched": False,
                "top_matches": [],
                "threshold": self.similarity_threshold,
            }

        self._ensure_loaded()
        if self._keyword_embeddings is None:
            raise RuntimeError("Keyword embeddings failed to load")

        query_embedding = self._embed_text(cleaned_text)
        scores = torch.mv(self._keyword_embeddings, query_embedding)

        k = min(max(int(top_k), 1), int(scores.shape[0]))
        values, indices = torch.topk(scores, k=k)

        top_matches: List[Dict[str, object]] = []
        for score, idx in zip(values.tolist(), indices.tolist()):
            metadata = dict(self._keyword_index[int(idx)])
            top_matches.append(
                {
                    "keyword": metadata.get("keyword", ""),
                    "category": metadata.get("category", "unknown"),
                    "snomed": metadata.get("snomed", ""),
                    "base_esi": int(metadata.get("base_esi", 3)),
                    "red_flag": bool(metadata.get("red_flag", False)),
                    "similarity": round(float(score), 6),
                }
            )

        matches_above_threshold = [
            candidate
            for candidate in top_matches
            if float(candidate["similarity"]) >= self.similarity_threshold
        ]

        if not matches_above_threshold:
            return {
                "category": "unknown",
                "base_esi": 3,
                "red_flag": False,
                "matched": False,
                "top_matches": top_matches,
                "threshold": self.similarity_threshold,
            }

        best = matches_above_threshold[0]
        return {
            "category": best["category"],
            "base_esi": int(best["base_esi"]),
            "snomed": best["snomed"],
            "red_flag": bool(best["red_flag"]),
            "keyword": best["keyword"],
            "similarity": float(best["similarity"]),
            "matched": True,
            "threshold": self.similarity_threshold,
            "top_matches": top_matches,
            "matches_above_threshold": matches_above_threshold,
        }
