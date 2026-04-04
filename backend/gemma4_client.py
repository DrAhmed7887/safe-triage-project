"""
Gemma 4 Client via Vertex AI Model Garden.

Drop-in replacement for the Gemini GenerativeModel interface, backed by
a Gemma 4 27B-IT vLLM endpoint on Vertex AI.

The public interface mirrors GenerativeModel so ai_service.py can swap
between Gemini and Gemma 4 with minimal code changes:

    client = Gemma4VertexModel()
    response = client.generate_content("Analyze this patient...")
    print(response.text)
"""

from __future__ import annotations

import logging
import os
import time
from types import SimpleNamespace
from typing import Any, Optional

from google.cloud import aiplatform

logger = logging.getLogger(__name__)


class Gemma4VertexModel:
    """
    Vertex AI endpoint wrapper that mimics the GenerativeModel interface.

    Talks to a Gemma 4 27B-IT model served by vLLM on a Model Garden endpoint.
    The ``generate_content(prompt)`` method returns an object with a ``.text``
    attribute, matching the Gemini SDK response shape.
    """

    def __init__(
        self,
        endpoint_id: str = "",
        project_id: str = "",
        region: str = "",
        max_tokens: int = 2048,
        temperature: float = 0.1,
    ) -> None:
        self.project_id = project_id or os.getenv("PROJECT_ID", "safe-triage-ai")
        self.region = region or os.getenv("VERTEX_REGION", "us-central1")
        self.endpoint_id = (
            endpoint_id or os.getenv("GEMMA4_ENDPOINT_ID", "")
        ).strip()
        self.max_tokens = max_tokens
        self.temperature = temperature

        if not self.endpoint_id:
            raise ValueError(
                "GEMMA4_ENDPOINT_ID not set. "
                "Deploy Gemma 4 first: python deploy_gemma4_vertex.py"
            )

        aiplatform.init(project=self.project_id, location=self.region)
        self.endpoint = aiplatform.Endpoint(self.endpoint_id)
        logger.info(
            "Gemma 4 client initialized (endpoint=%s, region=%s)",
            self.endpoint_id,
            self.region,
        )

    def _format_prompt(self, prompt: str) -> str:
        """
        Wrap the prompt in Gemma's chat template.

        Gemma 4 IT uses <start_of_turn>/<end_of_turn> markers.
        We set a system turn for the clinical extraction role, then
        pass the user prompt.
        """
        return (
            "<start_of_turn>user\n"
            f"{prompt}\n"
            "<end_of_turn>\n"
            "<start_of_turn>model\n"
        )

    @staticmethod
    def _parse_prediction(prediction: Any) -> Optional[str]:
        """Extract text from a vLLM prediction response."""
        if isinstance(prediction, str) and prediction.strip():
            return prediction.strip()

        if isinstance(prediction, dict):
            # vLLM returns various formats depending on version
            for key in ("text", "generated_text", "output", "content"):
                value = prediction.get(key)
                if isinstance(value, str) and value.strip():
                    return value.strip()

            # OpenAI-compatible format
            choices = prediction.get("choices")
            if isinstance(choices, list) and choices:
                first = choices[0]
                if isinstance(first, dict):
                    msg = first.get("message") or first.get("text") or {}
                    if isinstance(msg, dict):
                        content = msg.get("content", "")
                        if content:
                            return content.strip()
                    elif isinstance(msg, str):
                        return msg.strip()

        if isinstance(prediction, list) and prediction:
            return Gemma4VertexModel._parse_prediction(prediction[0])

        return None

    def generate_content(self, prompt: str) -> SimpleNamespace:
        """
        Send prompt to the Gemma 4 endpoint and return a response
        with a ``.text`` attribute (matching the Gemini SDK shape).

        Raises RuntimeError if the endpoint returns no usable text.
        """
        formatted = self._format_prompt(prompt)
        started = time.perf_counter()

        response = self.endpoint.predict(
            instances=[
                {
                    "prompt": formatted,
                    "max_tokens": self.max_tokens,
                    "temperature": self.temperature,
                }
            ]
        )

        elapsed = time.perf_counter() - started
        logger.info("Gemma 4 inference: %.3fs", elapsed)

        # response.predictions is a list of prediction objects
        predictions = getattr(response, "predictions", None) or []
        for pred in predictions:
            text = self._parse_prediction(pred)
            if text:
                # Strip the Gemma turn markers if echoed back
                text = text.replace("<end_of_turn>", "").strip()
                return SimpleNamespace(text=text)

        raise RuntimeError(
            f"Gemma 4 endpoint returned no usable text. "
            f"Raw predictions: {predictions!r}"
        )

    def generate(
        self,
        prompt: str,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
    ) -> Optional[str]:
        """Convenience method returning raw text (used by benchmarks)."""
        original_max = self.max_tokens
        original_temp = self.temperature
        try:
            if max_tokens is not None:
                self.max_tokens = max_tokens
            if temperature is not None:
                self.temperature = temperature
            result = self.generate_content(prompt)
            return result.text
        finally:
            self.max_tokens = original_max
            self.temperature = original_temp
