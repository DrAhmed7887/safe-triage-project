"""
Real MedGemma Model Client
Accesses Google's Gemma-2B via Hugging Face Inference API.
"""

from __future__ import annotations

import os
import time
from typing import Optional

import requests


class MedGemmaClient:
    """Client for Google's smallest Gemma model over Hugging Face inference."""

    def __init__(self):
        self.model_id = os.getenv("MEDGEMMA_MODEL_ID", "google/gemma-2-2b-it")
        self.api_url = f"https://api-inference.huggingface.co/models/{self.model_id}"
        self.api_token = os.getenv("HUGGINGFACE_API_TOKEN", "").strip()
        if not self.api_token:
            raise ValueError(
                "HUGGINGFACE_API_TOKEN not set. Get token from https://huggingface.co/settings/tokens"
            )

        self.headers = {
            "Authorization": f"Bearer {self.api_token}",
            "Content-Type": "application/json",
        }
        self.max_retries = int(os.getenv("MEDGEMMA_MAX_RETRIES", "3"))
        self.retry_delay = int(os.getenv("MEDGEMMA_RETRY_DELAY", "5"))
        self.timeout_seconds = int(os.getenv("MEDGEMMA_TIMEOUT_SECONDS", "60"))

    def generate(
        self,
        prompt: str,
        max_tokens: int = 4096,
        temperature: float = 0.1,
    ) -> Optional[str]:
        """
        Send prompt to Gemma-2B and return generated text.
        Returns None on repeated failures.
        """
        payload = {
            "inputs": prompt,
            "parameters": {
                "max_new_tokens": max_tokens,
                "temperature": temperature,
                "do_sample": bool(temperature > 0),
                "return_full_text": False,
            },
        }

        for attempt in range(self.max_retries):
            try:
                print(
                    f"[MedGemma] Calling HF model {self.model_id} "
                    f"(attempt {attempt + 1}/{self.max_retries})"
                )
                response = requests.post(
                    self.api_url,
                    headers=self.headers,
                    json=payload,
                    timeout=self.timeout_seconds,
                )

                if response.status_code == 200:
                    result = response.json()
                    if isinstance(result, list) and result:
                        text = result[0].get("generated_text", "")
                    elif isinstance(result, dict):
                        text = result.get("generated_text", "")
                    else:
                        text = str(result)
                    print(f"[MedGemma] Response received ({len(text)} chars)")
                    return text

                if response.status_code == 503:
                    print("[MedGemma] Model loading (503), retrying...")
                    time.sleep(self.retry_delay)
                    continue

                if response.status_code == 429:
                    print("[MedGemma] Rate-limited (429), backing off...")
                    time.sleep(self.retry_delay * 2)
                    continue

                print(f"[MedGemma] API error {response.status_code}: {response.text}")
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay)
                    continue
                return None
            except requests.exceptions.Timeout:
                print("[MedGemma] Request timeout")
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay)
                    continue
                return None
            except Exception as exc:
                print(f"[MedGemma] Unexpected error: {exc}")
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay)
                    continue
                return None
        return None

    def test_connection(self) -> bool:
        response = self.generate("What is 2+2? Respond with one number.", max_tokens=16, temperature=0.0)
        return bool(response)
