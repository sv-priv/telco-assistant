"""Golden-set eval models (deterministic scoreboard inputs)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

from app.chat.llm import ChatMessage
from app.runners.protocol import RunnerMode

CheckName = Literal[
    "citation",
    "refusal",
    "must_contain",
    "must_not_contain",
    "must_not_cite",
]

EvalCategory = Literal[
    "plan",
    "refuse",
    "roaming",
    "billing",
    "about",
    "followup",
    "network",
    "devices",
    "contract",
    "security",
    "addon",
    "support",
]

EVAL_CATEGORIES: frozenset[str] = frozenset(
    {
        "plan",
        "refuse",
        "roaming",
        "billing",
        "about",
        "followup",
        "network",
        "devices",
        "contract",
        "security",
        "addon",
        "support",
    }
)


@dataclass(frozen=True)
class GoldenCase:
    id: str
    question: str
    category: EvalCategory
    language: str | None = None
    source: Literal["operator", "eu", "wb6"] | None = "operator"
    tags: tuple[str, ...] = ()
    expect_doc_ids: tuple[str, ...] = ()
    must_contain: tuple[str, ...] = ()
    must_not_contain: tuple[str, ...] = ()
    must_not_cite: tuple[str, ...] = ()
    must_refuse: bool = False
    history: tuple[ChatMessage, ...] = ()


@dataclass(frozen=True)
class CheckResult:
    name: CheckName
    passed: bool
    detail: str = ""


@dataclass(frozen=True)
class CaseScore:
    case_id: str
    mode: RunnerMode
    passed: bool
    checks: list[CheckResult]
    latency_ms: float
    cited_doc_ids: list[str]
    tool_calls: int
    answer_preview: str
    error: str | None = None


@dataclass
class ModeSummary:
    mode: RunnerMode
    n: int = 0
    passed: int = 0
    pass_rate: float = 0.0
    citation_n: int = 0
    citation_ok: int = 0
    citation_acc: float | None = None
    refusal_n: int = 0
    refusal_ok: int = 0
    refusal_acc: float | None = None
    contain_n: int = 0
    contain_ok: int = 0
    contain_acc: float | None = None
    p50_latency_ms: float | None = None
    p95_latency_ms: float | None = None
    avg_tool_calls: float | None = None


@dataclass
class RetrievalSummary:
    n: int = 0
    recall_at_k: float | None = None
    mrr: float | None = None
    k: int = 8


@dataclass
class EvalReport:
    generated_at: str
    golden_path: str
    modes: dict[str, ModeSummary] = field(default_factory=dict)
    by_category: dict[str, dict[str, dict[str, float | int]]] = field(default_factory=dict)
    retrieval: RetrievalSummary | None = None
    cases: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        modes_out: dict[str, Any] = {}
        for mode, summary in self.modes.items():
            modes_out[mode] = {
                "n": summary.n,
                "passed": summary.passed,
                "pass_rate": summary.pass_rate,
                "citation_acc": summary.citation_acc,
                "refusal_acc": summary.refusal_acc,
                "contain_acc": summary.contain_acc,
                "p50_latency_ms": summary.p50_latency_ms,
                "p95_latency_ms": summary.p95_latency_ms,
                "avg_tool_calls": summary.avg_tool_calls,
            }
        retrieval_out: dict[str, Any] | None = None
        if self.retrieval is not None:
            retrieval_out = {
                "n": self.retrieval.n,
                "k": self.retrieval.k,
                "recall_at_k": self.retrieval.recall_at_k,
                "mrr": self.retrieval.mrr,
            }
        return {
            "generated_at": self.generated_at,
            "golden_path": self.golden_path,
            "modes": modes_out,
            "by_category": self.by_category,
            "retrieval": retrieval_out,
            "cases": self.cases,
        }
