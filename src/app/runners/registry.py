"""Resolve a runner by mode."""

from __future__ import annotations

from app.chat.llm import ChatClient
from app.errors import AppError
from app.retrieve.service import Retriever
from app.runners.custom.runner import CustomRunner
from app.runners.langchain.runner import LangChainRunner
from app.runners.llamaindex.runner import LlamaIndexRunner
from app.runners.protocol import Runner, RunnerMode


def get_runner(mode: RunnerMode, *, retriever: Retriever, llm: ChatClient) -> Runner:
    if mode == "custom":
        return CustomRunner(retriever, llm)
    if mode == "llamaindex":
        return LlamaIndexRunner(retriever, llm)
    if mode == "langchain":
        return LangChainRunner(retriever, llm)
    raise AppError(
        title="Unknown runner",
        status=400,
        detail=f"Unsupported mode: {mode}",
    )
