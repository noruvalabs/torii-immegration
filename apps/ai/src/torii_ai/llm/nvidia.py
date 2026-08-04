"""NVIDIA NIM chat client (OpenAI-compatible API)."""

from __future__ import annotations

from openai import AsyncOpenAI

from torii_ai.config import Settings


class NvidiaChatClient:
    """Thin wrapper around the OpenAI SDK pointed at NVIDIA NIM."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._model = settings.nvidia_model
        self._client = AsyncOpenAI(
            api_key=settings.nvidia_api_key,
            base_url=settings.nvidia_base_url,
            timeout=settings.nvidia_timeout_seconds,
        )

    async def complete(self, *, system: str, user: str) -> str:
        if not self._settings.nvidia_api_key:
            raise RuntimeError("TORII_AI_NVIDIA_API_KEY is not configured")
        response = await self._client.chat.completions.create(
            model=self._model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            temperature=0.2,
            max_tokens=self._settings.nvidia_max_tokens,
        )
        content = response.choices[0].message.content
        return content or ""
