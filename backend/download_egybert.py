#!/usr/bin/env python3
"""
Download and cache faisalq/EgyBERT locally for offline inference.

Usage:
    python backend/download_egybert.py
"""

from __future__ import annotations

import argparse
from pathlib import Path

from transformers import AutoModel, AutoTokenizer


MODEL_ID = "faisalq/EgyBERT"


def main() -> None:
    parser = argparse.ArgumentParser(description="Download EgyBERT model files locally")
    parser.add_argument(
        "--output-dir",
        default=None,
        help="Target model directory (default: backend/egybert_model)",
    )
    args = parser.parse_args()

    backend_dir = Path(__file__).resolve().parent
    output_dir = Path(args.output_dir) if args.output_dir else backend_dir / "egybert_model"
    output_dir.mkdir(parents=True, exist_ok=True)

    tokenizer = AutoTokenizer.from_pretrained(MODEL_ID)
    model = AutoModel.from_pretrained(MODEL_ID)

    tokenizer.save_pretrained(str(output_dir))
    model.save_pretrained(str(output_dir))

    print(f"EgyBERT downloaded and saved to: {output_dir}")


if __name__ == "__main__":
    main()
