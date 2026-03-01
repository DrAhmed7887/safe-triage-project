#!/usr/bin/env python3
"""
Precompute EgyBERT embeddings for offline semantic keyword matching.

Build-time use:
    python backend/precompute_embeddings.py

Outputs:
    backend/keyword_embeddings.pt   (torch.Tensor [N, H], L2-normalized)
    backend/keyword_index.json      (index -> keyword metadata)
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Dict, List, Tuple

import torch
from transformers import AutoModel, AutoTokenizer

from arabic_keywords_v2 import ARABIC_KEYWORDS_V2


def _load_keywords() -> List[Tuple[str, Dict[str, object]]]:
    # Stable deterministic order so tensor/index stays reproducible.
    return sorted(ARABIC_KEYWORDS_V2.items(), key=lambda item: item[0])


def _encode_keywords(
    *,
    model: AutoModel,
    tokenizer: AutoTokenizer,
    keywords: List[str],
    batch_size: int,
) -> torch.Tensor:
    all_embeddings: List[torch.Tensor] = []
    model.eval()

    with torch.no_grad():
        for start in range(0, len(keywords), batch_size):
            batch = keywords[start : start + batch_size]
            encoded = tokenizer(
                batch,
                return_tensors="pt",
                padding=True,
                truncation=True,
                max_length=64,
            )
            outputs = model(**encoded)
            cls_embeddings = outputs.last_hidden_state[:, 0, :]
            cls_embeddings = torch.nn.functional.normalize(cls_embeddings, p=2, dim=1)
            all_embeddings.append(cls_embeddings.cpu())

    return torch.cat(all_embeddings, dim=0)


def main() -> None:
    parser = argparse.ArgumentParser(description="Precompute EgyBERT keyword embeddings")
    parser.add_argument(
        "--model-dir",
        default=None,
        help="Path to local EgyBERT model directory (default: backend/egybert_model)",
    )
    parser.add_argument(
        "--embeddings-out",
        default=None,
        help="Output .pt file path (default: backend/keyword_embeddings.pt)",
    )
    parser.add_argument(
        "--index-out",
        default=None,
        help="Output index JSON path (default: backend/keyword_index.json)",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=64,
        help="Embedding batch size",
    )
    args = parser.parse_args()

    backend_dir = Path(__file__).resolve().parent
    model_dir = Path(args.model_dir) if args.model_dir else backend_dir / "egybert_model"
    embeddings_out = Path(args.embeddings_out) if args.embeddings_out else backend_dir / "keyword_embeddings.pt"
    index_out = Path(args.index_out) if args.index_out else backend_dir / "keyword_index.json"

    if not model_dir.exists():
        raise FileNotFoundError(
            f"EgyBERT model directory not found: {model_dir}\n"
            "Download model files locally before running precompute."
        )

    keyword_items = _load_keywords()
    keywords = [keyword for keyword, _ in keyword_items]

    tokenizer = AutoTokenizer.from_pretrained(str(model_dir), local_files_only=True)
    model = AutoModel.from_pretrained(str(model_dir), local_files_only=True)

    embeddings = _encode_keywords(
        model=model,
        tokenizer=tokenizer,
        keywords=keywords,
        batch_size=args.batch_size,
    )

    if embeddings.shape[0] != len(keywords):
        raise RuntimeError(
            f"Embedding row mismatch: got {embeddings.shape[0]} rows for {len(keywords)} keywords"
        )

    index_payload = {
        str(idx): {
            "keyword": keyword,
            "snomed": metadata["snomed"],
            "category": metadata["category"],
            "base_esi": int(metadata["base_esi"]),
            "red_flag": bool(metadata["red_flag"]),
        }
        for idx, (keyword, metadata) in enumerate(keyword_items)
    }

    embeddings_out.parent.mkdir(parents=True, exist_ok=True)
    torch.save(embeddings, embeddings_out)
    with index_out.open("w", encoding="utf-8") as fh:
        json.dump(index_payload, fh, ensure_ascii=False, indent=2)

    print(
        "Precompute complete:",
        f"keywords={len(keywords)}",
        f"shape={tuple(embeddings.shape)}",
        f"embeddings={embeddings_out}",
        f"index={index_out}",
    )


if __name__ == "__main__":
    main()
