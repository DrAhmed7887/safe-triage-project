"""
MedGemma Client via Dr7.ai API
Production-grade hosted MedGemma inference.
"""

from __future__ import annotations

import os
import time
from typing import Optional

import requests


class MedGemmaClient:
    """
    Client for MedGemma via Dr7.ai hosted API.
    """

    def __init__(self):
        self.dr7_api_key = (os.getenv("DR7_API_KEY") or "").strip()
        self.model = os.getenv("DR7_MODEL", "medgemma-4b-it")
        self.max_retries = int(os.getenv("MEDGEMMA_MAX_RETRIES", "3"))
        self.retry_delay = int(os.getenv("MEDGEMMA_RETRY_DELAY", "5"))
        self.timeout_seconds = int(os.getenv("MEDGEMMA_TIMEOUT_SECONDS", "120"))
        self.enable_gemini_fallback = (
            (os.getenv("MEDGEMMA_GEMINI_FALLBACK") or "true").strip().lower() == "true"
        )
        self.last_error: Optional[str] = None
        self.provider = "Dr7.ai"

        if not self.dr7_api_key:
            raise ValueError(
                "DR7_API_KEY not set. Get API key from https://dr7.ai/dashboard"
            )

        self.headers = {
            "Authorization": f"Bearer {self.dr7_api_key}",
            "Content-Type": "application/json",
        }

        # Dr7.ai official endpoint (from docs: https://dr7.ai/docs)
        endpoint_override = (os.getenv("DR7_API_URL") or "").strip()
        if endpoint_override:
            self.endpoints = [endpoint_override]
        else:
            self.endpoints = [
                "https://dr7.ai/api/v1/medical/chat/completions",
            ]

    def _parse_response_text(self, body: object) -> Optional[str]:
        if isinstance(body, dict):
            choices = body.get("choices")
            if isinstance(choices, list) and choices:
                first = choices[0]
                if isinstance(first, dict):
                    msg = first.get("message")
                    if isinstance(msg, dict):
                        content = msg.get("content")
                        if isinstance(content, str) and content.strip():
                            return content.strip()
                    text = first.get("text")
                    if isinstance(text, str) and text.strip():
                        return text.strip()
            for key in ("generated_text", "text", "output"):
                value = body.get(key)
                if isinstance(value, str) and value.strip():
                    return value.strip()
        return None

    def _generate_dr7(self, prompt: str, max_tokens: int, temperature: float) -> Optional[str]:
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": "You are a concise emergency medicine QA assistant."},
                {"role": "user", "content": prompt},
            ],
            "max_tokens": max_tokens,
            "temperature": temperature,
            "stream": False,
        }

        for endpoint in self.endpoints:
            try:
                response = requests.post(
                    endpoint,
                    headers=self.headers,
                    json=payload,
                    timeout=self.timeout_seconds,
                )
            except Exception as exc:
                self.last_error = f"dr7_exception: {exc}"
                continue

            if response.status_code == 200:
                try:
                    body = response.json()
                except Exception:
                    body = {"text": response.text}
                text = self._parse_response_text(body)
                if text:
                    self.last_error = None
                    return text
                self.last_error = "dr7_empty_response"
                continue

            if response.status_code in (429, 503):
                self.last_error = f"dr7_http_{response.status_code}: transient"
                time.sleep(self.retry_delay * (2 if response.status_code == 429 else 1))
                continue

            self.last_error = f"dr7_http_{response.status_code}: {response.text[:500]}"

        return None

    def _generate_gemini_fallback(self, prompt: str) -> Optional[str]:
        """
        Optional fallback to Vertex Gemini if Dr7 is unavailable.
        """
        if not self.enable_gemini_fallback:
            return None
        try:
            import vertexai
            from vertexai.generative_models import GenerativeModel

            project = os.getenv("PROJECT_ID", "safe-triage-ai")
            region = os.getenv("VERTEX_REGION", "us-central1")
            model_name = os.getenv("MEDGEMMA_FALLBACK_MODEL", "gemini-2.0-flash-001")
            vertexai.init(project=project, location=region)
            model = GenerativeModel(model_name)
            response = model.generate_content(prompt)
            text = (response.text or "").strip()
            if text:
                self.provider = "Dr7.ai (Gemini fallback)"
                self.last_error = None
                return text
            self.last_error = "gemini_fallback_empty_response"
            return None
        except Exception as exc:
            self.last_error = f"gemini_fallback_error: {exc}"
            return None

    def generate(
        self,
        prompt: str,
        max_tokens: int = 4096,
        temperature: float = 0.1,
    ) -> Optional[str]:
        """
        Generate response from MedGemma via Dr7.ai.
        """
        self.provider = "Dr7.ai"

        for attempt in range(self.max_retries):
            print(
                f"[MedGemma] Calling Dr7.ai (attempt {attempt + 1}/{self.max_retries})..."
            )
            result = self._generate_dr7(prompt, max_tokens, temperature)
            if result:
                print(f"[MedGemma] Dr7.ai response received ({len(result)} chars)")
                return result
            if attempt < self.max_retries - 1:
                time.sleep(self.retry_delay)

        print(f"[MedGemma] Dr7.ai failed: {self.last_error}")
        fallback = self._generate_gemini_fallback(prompt)
        if fallback:
            print(f"[MedGemma] Fallback response received ({len(fallback)} chars)")
            return fallback

        print("[MedGemma] All backends failed")
        return None

    def test_connection(self) -> bool:
        """
        Test if Dr7.ai API is accessible.
        """
        response = self.generate(
            "What is pneumonia?",
            max_tokens=50,
            temperature=0.1,
        )
        return bool(response and len(response) > 10)
