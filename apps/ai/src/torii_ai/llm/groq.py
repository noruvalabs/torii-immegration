"""Groq chat client (OpenAI-compatible API)."""

from __future__ import annotations

from typing import Any, Protocol

from openai import AsyncOpenAI

from torii_ai.config import Settings


class ChatClient(Protocol):
    async def complete(self, *, system: str, user: str) -> str: ...


class GroqChatClient:
    """Thin wrapper around the OpenAI SDK pointed at Groq with fallback support."""

    def __init__(
        self,
        settings: Settings,
        model: str | None = None,
        fallback: ChatClient | None = None,
        max_tokens: int | None = None,
    ) -> None:
        self._settings = settings
        self._model = model or settings.groq_model
        # Groq counts the reserved output budget toward the tokens-per-minute allowance, so
        # a caller whose reply is short says so here rather than reserving the account's
        # whole minute and being refused with a 413.
        self._max_tokens = max_tokens or settings.groq_max_tokens
        self._fallback = fallback
        self._client = AsyncOpenAI(
            api_key=settings.groq_api_key or "missing",
            base_url=settings.groq_base_url,
            timeout=settings.groq_timeout_seconds,
            max_retries=0,
        )

    async def complete(self, *, system: str, user: str) -> str:
        if not self._settings.groq_api_key:
            if self._fallback:
                return await self._fallback.complete(system=system, user=user)
            raise RuntimeError("TORII_AI_GROQ_API_KEY is not configured")
        try:
            response = await self._client.chat.completions.create(
                model=self._model,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                temperature=0.2,
                max_tokens=self._max_tokens,
            )
            content = response.choices[0].message.content
            return content or ""
        except Exception:
            if self._fallback:
                return await self._fallback.complete(system=system, user=user)
            raise


class FakeChatClient:
    """Deterministic stand-in for tests."""

    def __init__(self, reply: str = "Test reply.") -> None:
        self.reply = reply
        self.calls: list[dict[str, Any]] = []

    async def complete(self, *, system: str, user: str) -> str:
        self.calls.append({"system": system, "user": user})
        return self.reply
