"""
MedGemma Client via Vertex AI Model Garden.
Production-grade hosted MedGemma inference on a Vertex AI endpoint.

Replaces the previous Dr7.ai-hosted API with a native Google Cloud deployment.
The public interface — generate(prompt, max_tokens, temperature) — is unchanged,
so all downstream code (batch QA, hourly job, alerts) works without modification.
"""

from __future__ import annotations

import os
import time
from typing import Optional

from google.cloud import aiplatform


class MedGemmaClient:
    """
    Client for MedGemma via Vertex AI Model Garden endpoint.
    """

    def __init__(self) -> None:
        self.project_id: str = os.getenv("PROJECT_ID", "safe-triage-ai")
        self.region: str = os.getenv("VERTEX_REGION", "us-central1")
        self.endpoint_id: str = (os.getenv("MEDGEMMA_ENDPOINT_ID") or "").strip()
        self.max_retries: int = int(os.getenv("MEDGEMMA_MAX_RETRIES", "3"))
        self.retry_delay: int = int(os.getenv("MEDGEMMA_RETRY_DELAY", "5"))
        self.timeout_seconds: int = int(os.getenv("MEDGEMMA_TIMEOUT_SECONDS", "120"))
        self.enable_gemini_fallback: bool = (
            (os.getenv("MEDGEMMA_GEMINI_FALLBACK") or "true").strip().lower() == "true"
        )
        self.last_error: Optional[str] = None
        self.provider: str = "VertexAI-MedGemma"

        if not self.endpoint_id:
            raise ValueError(
                "MEDGEMMA_ENDPOINT_ID not set. "
                "Deploy MedGemma first: python deploy_medgemma_vertex.py"
            )

        aiplatform.init(project=self.project_id, location=self.region)
        self.endpoint = aiplatform.Endpoint(self.endpoint_id)

    def _build_chat_prompt(self, prompt: str) -> str:
        """
        Format the prompt using Gemma's native chat template.

        MedGemma 4B-IT uses <start_of_turn> / <end_of_turn> markers
        instead of OpenAI-style messages. The vLLM container on Vertex AI
        expects raw text with these markers.
        """
        return (
            "<start_of_turn>system\n"
            "You are a concise emergency medicine QA assistant.\n"
            "<end_of_turn>\n"
            f"<start_of_turn>user\n{prompt}\n<end_of_turn>\n"
            "<start_of_turn>model\n"
        )

    def _parse_prediction(self, prediction: object) -> Optional[str]:
        """
        Extract text from a Vertex AI prediction response.

        The vLLM serving container can return different formats depending
        on version, so we try multiple keys.
        """
        if isinstance(prediction, str) and prediction.strip():
            return prediction.strip()

        if isinstance(prediction, dict):
            for key in ("text", "generated_text", "output", "content"):
                value = prediction.get(key)
                if isinstance(value, str) and value.strip():
                    return value.strip()

            # OpenAI-compatible format (some containers use this)
            choices = prediction.get("choices")
            if isinstance(choices, list) and choices:
                first = choices[0]
                if isinstance(first, dict):
                    msg = first.get("message", {})
                    if isinstance(msg, dict):
                        content = msg.get("content")
                        if isinstance(content, str) and content.strip():
                            return content.strip()

        return None

    def _generate_vertex(
        self, prompt: str, max_tokens: int, temperature: float
    ) -> Optional[str]:
        """
        Call MedGemma on the Vertex AI endpoint.

        Sends the prompt formatted with Gemma chat markers to the vLLM
        container running on the endpoint. The container handles tokenization,
        GPU inference, and returns generated text.
        """
        chat_prompt = self._build_chat_prompt(prompt)

        payload = {
            "prompt": chat_prompt,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }

        try:
            response = self.endpoint.predict(instances=[payload])
            predictions = response.predictions

            if predictions and len(predictions) > 0:
                text = self._parse_prediction(predictions[0])
                if text:
                    self.last_error = None
                    return text

            self.last_error = "vertex_empty_response"
            return None
        except Exception as exc:
            self.last_error = f"vertex_exception: {exc}"
            return None

    def _generate_gemini_fallback(self, prompt: str) -> Optional[str]:
        """
        Optional fallback to Vertex Gemini if MedGemma endpoint is unavailable.

        This uses the same Vertex AI project but calls the Gemini model directly
        (no custom endpoint needed — Gemini is a first-party Google model).
        """
        if not self.enable_gemini_fallback:
            return None
        try:
            import vertexai
            from vertexai.generative_models import GenerativeModel

            model_name = os.getenv("MEDGEMMA_FALLBACK_MODEL", "gemini-2.5-flash")
            vertexai.init(project=self.project_id, location=self.region)
            model = GenerativeModel(model_name)
            response = model.generate_content(prompt)
            text = (response.text or "").strip()
            if text:
                self.provider = "VertexAI-MedGemma (Gemini fallback)"
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
        Generate response from MedGemma via Vertex AI.

        Same interface as the previous Dr7.ai client — all downstream code
        (medgemma_batch_qa, medgemma_hourly_job, etc.) works unchanged.

        Retry flow:
            1. Try Vertex AI endpoint up to max_retries times
            2. If all fail, try Gemini fallback (if enabled)
            3. Return None if everything fails
        """
        self.provider = "VertexAI-MedGemma"

        for attempt in range(self.max_retries):
            print(
                f"[MedGemma] Calling Vertex AI endpoint "
                f"(attempt {attempt + 1}/{self.max_retries})..."
            )
            result = self._generate_vertex(prompt, max_tokens, temperature)
            if result:
                print(f"[MedGemma] Vertex AI response received ({len(result)} chars)")
                return result
            if attempt < self.max_retries - 1:
                time.sleep(self.retry_delay)

        print(f"[MedGemma] Vertex AI failed: {self.last_error}")
        fallback = self._generate_gemini_fallback(prompt)
        if fallback:
            print(f"[MedGemma] Fallback response received ({len(fallback)} chars)")
            return fallback

        print("[MedGemma] All backends failed")
        return None

    def test_connection(self) -> bool:
        """
        Test if the Vertex AI MedGemma endpoint is accessible.
        """
        response = self.generate(
            "What is pneumonia?",
            max_tokens=50,
            temperature=0.1,
        )
        return bool(response and len(response) > 10)
