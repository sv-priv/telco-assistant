"""Chat LLM clients (OpenAI + fake)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Protocol, runtime_checkable

from openai import AsyncOpenAI


@dataclass(frozen=True)
class ChatMessage:
    role: Literal["user", "assistant"]
    content: str


@runtime_checkable
class ChatClient(Protocol):
    async def complete(self, *, system: str, user: str) -> str:
        """Return the assistant text for a single-turn chat."""
        ...


class OpenAIChatClient:
    def __init__(self, api_key: str, *, model: str = "gpt-4o-mini") -> None:
        if not api_key:
            raise ValueError("OPENAI_API_KEY is required for OpenAIChatClient")
        self._client = AsyncOpenAI(api_key=api_key)
        self._model = model

    async def complete(self, *, system: str, user: str) -> str:
        response = await self._client.chat.completions.create(
            model=self._model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            temperature=0.2,
        )
        content = response.choices[0].message.content
        return (content or "").strip()


class FakeChatClient:
    """Deterministic replies for tests."""

    def __init__(self, reply: str = "Based on the sources: answer.") -> None:
        self._reply = reply
        self.last_system: str | None = None
        self.last_user: str | None = None

    async def complete(self, *, system: str, user: str) -> str:
        self.last_system = system
        self.last_user = user
        return self._reply
