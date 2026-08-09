"""App language contract (mk | en) and localized copy for grounded answers."""

from __future__ import annotations

from typing import Literal

AppLanguage = Literal["mk", "en"]

NO_HIT_ANSWER: dict[AppLanguage, str] = {
    "mk": (
        "Немам доволно информации во базата на знаење за да одговорам. "
        "Пробајте поконкретно прашање за планови, роаминг или сметки."
    ),
    "en": (
        "I don't have enough information in the knowledge base to answer that. "
        "Try a more concrete question about plans, roaming, or bills."
    ),
}

_ANSWER_LANG_RULE: dict[AppLanguage, str] = {
    "mk": "Answer in Macedonian (македонски).",
    "en": "Answer in English.",
}


def normalize_language(language: str | None) -> AppLanguage | None:
    if language is None:
        return None
    value = language.strip().lower()
    if value in ("mk", "en"):
        return value  # type: ignore[return-value]
    return None


def no_hit_answer(language: str | None) -> str:
    lang = normalize_language(language) or "en"
    return NO_HIT_ANSWER[lang]


def answer_language_rule(language: str | None) -> str:
    lang = normalize_language(language)
    if lang is None:
        return "Prefer the customer's language when clear from the question."
    return _ANSWER_LANG_RULE[lang]


def grounding_system_prompt(language: str | None) -> str:
    """Shared grounding rules for Custom (and as a base for other runners)."""
    return (
        "You are a support assistant for Vardar Mobile (Вардар Мобиле), a "
        "Macedonian mobile operator. Answer using ONLY the provided context snippets.\n\n"
        "Rules:\n"
        '- Resolve follow-ups using the conversation history (e.g. "and in L?" means '
        "the L plan after discussing XL).\n"
        "- If the user asks broadly about Vardar Mobile / the operator and the context "
        "has product or FAQ snippets, give a short grounded overview of what those "
        "docs cover (plans, roaming, support). Do not invent company history, HQ, "
        "ownership, or unstated marketing claims.\n"
        "- If the context is insufficient for the specific ask, say you don't have "
        "enough information and suggest a more concrete question (plans, roaming, bills).\n"
        "- Do not invent prices, policies, or legal text.\n"
        f"- {answer_language_rule(language)}\n"
        "- Cite sources inline like [doc_id] using the doc_id from each snippet.\n"
        "- When context includes superseded/repealed law, prefer in-force sources.\n"
    )
