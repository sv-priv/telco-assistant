"""LangChain tool-calling agent over our Retriever.

Agent loop (model → tools → model) with search_docs / get_plan / list_plans
against the shared pgvector index.
"""

from __future__ import annotations

import time
from typing import Any, cast

from langchain.agents import create_agent
from langchain_openai import ChatOpenAI
from pydantic import SecretStr

from app.chat.llm import ChatClient, ChatMessage
from app.chat.service import Citation
from app.config import get_settings
from app.errors import AppError
from app.ingest.models import Source
from app.language import answer_language_rule
from app.retrieve.service import Retriever
from app.runners.langchain.tools import build_tools
from app.runners.protocol import AskResult, RunnerMode


def _system_prompt(language: str | None) -> str:
    return (
        "You are a support agent for Vardar Mobile (Вардар Мобиле), a "
        "Macedonian mobile operator.\n\n"
        "You have tools. Use them to gather evidence before answering:\n"
        "- get_plan(tier) for S/M/L/XL inclusions and prices\n"
        "- list_plans() for an overview of available plans\n"
        "- search_docs(query) for roaming, bills, FAQ, policies, or anything else\n\n"
        "Rules:\n"
        "- Prefer tools over guessing. Call multiple tools if comparing plans.\n"
        "- Answer using ONLY tool results. If tools lack the info, say you don't "
        "have enough information.\n"
        "- Plan names are exact: only S, M, L, XL exist. Never treat XXL as XL, "
        "XS as S, or any similar name as a real plan. If the user asks for "
        "XXL/XS/etc., call get_plan with that exact string (or list_plans) and "
        "report that it is not offered — do NOT substitute another tier's details.\n"
        "- Do not invent prices or policies.\n"
        "- Cite sources inline like [doc_id].\n"
        f"- {answer_language_rule(language)}\n"
        "- Keep answers concise and practical.\n"
    )


class LangChainRunner:
    mode: RunnerMode = "langchain"

    def __init__(self, retriever: Retriever, llm: ChatClient) -> None:
        self._retriever = retriever
        self._llm = llm  # reserved; agent uses ChatOpenAI directly

    async def ask(
        self,
        question: str,
        *,
        limit: int = 8,
        language: str | None = None,
        source: Source | None = None,
        history: list[ChatMessage] | None = None,
    ) -> AskResult:
        _ = self._llm
        history = history or []
        started = time.perf_counter()
        settings = get_settings()
        if not settings.openai_api_key:
            raise AppError(
                title="Missing API key",
                status=503,
                detail="OPENAI_API_KEY is not configured",
            )

        citations: list[Citation] = []
        tool_trace: list[dict[str, Any]] = []

        def on_tool(event: dict[str, Any]) -> None:
            tool_trace.append({"step": "tool_call", **event})

        tools = build_tools(
            self._retriever,
            language=language,
            source=source,
            limit=limit,
            citations=citations,
            on_tool=on_tool,
        )

        model = ChatOpenAI(
            model=settings.chat_model,
            api_key=SecretStr(settings.openai_api_key),
            temperature=0.0,
        )
        agent = create_agent(
            model=model,
            tools=tools,
            system_prompt=_system_prompt(language),
        )

        messages = _history_to_messages(history)
        messages.append({"role": "user", "content": question})

        raw = await agent.ainvoke(  # type: ignore[call-overload]
            {"messages": messages},
            config={"recursion_limit": 12},
        )
        result = cast(dict[str, Any], raw)
        answer = _final_answer(result)
        trace: list[dict[str, Any]] = [
            {
                "step": "agent_start",
                "status": "ok",
                "framework": "langchain_create_agent",
            },
            *tool_trace,
            {
                "step": "agent_finish",
                "status": "ok",
                "tools_used": len(tool_trace),
                "citations": len(citations),
            },
        ]
        return AskResult(
            mode=self.mode,
            question=question,
            answer=answer,
            citations=citations,
            trace=trace,
            latency_ms=(time.perf_counter() - started) * 1000,
        )


def _history_to_messages(history: list[ChatMessage]) -> list[dict[str, str]]:
    out: list[dict[str, str]] = []
    for msg in history[-8:]:
        if msg.role in ("user", "assistant"):
            out.append({"role": msg.role, "content": msg.content})
    return out


def _final_answer(result: dict[str, Any]) -> str:
    messages = result.get("messages") or []
    for msg in reversed(messages):
        content = getattr(msg, "content", None)
        if content is None and isinstance(msg, dict):
            content = msg.get("content")
        if isinstance(content, str) and content.strip():
            # Skip empty / tool-only AI messages
            tool_calls = getattr(msg, "tool_calls", None)
            if tool_calls:
                continue
            return content.strip()
        if isinstance(content, list):
            texts = [
                block.get("text", "")
                for block in content
                if isinstance(block, dict) and block.get("type") == "text"
            ]
            joined = "".join(texts).strip()
            if joined:
                return joined
    return "I don't have enough information to answer that."
