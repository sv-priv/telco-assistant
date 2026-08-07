"""Document and Chunk models."""

from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field

Source = Literal["operator", "eu", "wb6"]


class Document(BaseModel):
    """One corpus markdown file."""

    doc_id: str
    title: str
    source: Source
    authority: str
    family: str
    language: str
    effective_date: date | None
    status: str
    path: Path
    body: str
    extras: dict[str, str] = Field(default_factory=dict)

    @property
    def char_count(self) -> int:
        return len(self.body)


class Chunk(BaseModel):
    """One retrieval chunk."""

    doc_id: str
    title: str
    source: Source
    authority: str
    family: str
    language: str
    effective_date: date | None
    status: str
    path: Path
    chunk_index: int
    section: str | None
    text: str
    extras: dict[str, str] = Field(default_factory=dict)

    @property
    def char_count(self) -> int:
        return len(self.text)
