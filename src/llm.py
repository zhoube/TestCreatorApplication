from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Sequence

from dotenv import load_dotenv


class LLMError(RuntimeError):
    pass


class LLMClient:
    def __init__(self, model: str = "gpt-4.1-mini") -> None:
        load_dotenv(Path(__file__).resolve().parents[1] / ".env", override=True)
        self.model = model
        api_key = os.getenv("OPENAI_API_KEY", "").strip()
        self.enabled = bool(api_key and api_key != "PASTE_YOUR_OPENAI_API_KEY_HERE")
        self._client = None

    def _ensure_client(self):
        if not self.enabled:
            raise LLMError("OPENAI_API_KEY is missing or still set to the placeholder value.")
        if self._client is None:
            from openai import OpenAI

            self._client = OpenAI()
        return self._client

    def json(self, system: str, user: str) -> Any:
        return self.json_messages(
            [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ]
        )

    def json_messages(self, messages: Sequence[dict[str, str]]) -> Any:
        client = self._ensure_client()
        try:
            response = client.responses.create(
                model=self.model,
                input=list(messages),
                text={"format": {"type": "json_object"}},
            )
            return json.loads(response.output_text)
        except Exception as exc:
            raise LLMError(f"LLM JSON generation failed: {exc}") from exc

    def text(self, system: str, user: str) -> str:
        client = self._ensure_client()
        try:
            response = client.responses.create(
                model=self.model,
                input=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
            )
            return response.output_text
        except Exception as exc:
            raise LLMError(f"LLM text generation failed: {exc}") from exc
