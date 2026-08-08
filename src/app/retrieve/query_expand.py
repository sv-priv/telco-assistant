"""Deterministic query expansion for plan / package questions.

Dense retrieval alone often maps colloquial «XL пакетот» onto addon
«Додатен интернет пакет…» docs. Expanding toward «тарифен план / ценовник»
pulls price-list chunks into the candidate set.
"""

from __future__ import annotations

import re

_TIER_RE = re.compile(r"(?<![A-Za-zА-Яа-я])(S|M|L|XL)(?![A-Za-zА-Яа-я])", re.I)

_PLAN_HINT_RE = re.compile(
    r"пакет|paket|план|plan|тариф|tarif|ценовник|cenovnik|"
    r"вклучува|vklucuva|included?|inclusion|"
    r"што\s+има|sto\s+ima|what\s+is\s+in|what's\s+in",
    re.I,
)

_LIST_HINT_RE = re.compile(
    r"какви|kakvi|кои\s+пакет|koi\s+paket|which\s+plan|what\s+plan|"
    r"packages?|пакети|paketi|понуд|ponud|листа|lista|"
    r"има(?:те)?\s+пакет|ima(?:te)?\s+paket",
    re.I,
)

_ABOUT_HINT_RE = re.compile(
    r"(?:за|za|about|more about|повеќе|povekje|nesto povekje|нешто повеќе).*"
    r"(?:вардар|vardar)|"
    r"(?:who is|what is)\s+vardar|"
    r"(?:што е|sto e)\s+вардар|"
    r"оператор(?:от)?|operator",
    re.I,
)


def plan_tiers(query: str) -> list[str]:
    found: list[str] = []
    seen: set[str] = set()
    for match in _TIER_RE.finditer(query):
        tier = match.group(1).upper()
        if tier not in seen:
            seen.add(tier)
            found.append(tier)
    return found


def is_plan_query(query: str) -> bool:
    text = query.strip()
    if not text:
        return False
    if _ABOUT_HINT_RE.search(text) and not plan_tiers(text):
        return False
    return bool(
        _LIST_HINT_RE.search(text)
        or (_PLAN_HINT_RE.search(text) and plan_tiers(text))
        or (_PLAN_HINT_RE.search(text) and _LIST_HINT_RE.search(text))
    )


def expand_search_query(query: str) -> str:
    """Append retrieval-friendly plan terms; leave unrelated queries unchanged."""
    text = query.strip()
    if not text:
        return query

    # Already in price-list vocabulary — don't dilute the embedding further.
    if re.search(r"тарифен\s+план|ценовник", text, re.I):
        return text

    tiers = plan_tiers(text)
    extras: list[str] = []

    if _ABOUT_HINT_RE.search(text) and not tiers:
        extras.append(
            "за Вардар Мобиле оператор преглед услуги што нуди тарифни планови роаминг FAQ about"
        )
    elif tiers and _PLAN_HINT_RE.search(text):
        for tier in tiers:
            extras.append(
                f"тарифен план {tier} ценовник Вардар Мобилен {tier} што вклучува месечна претплата"
            )
    elif _LIST_HINT_RE.search(text) or (_PLAN_HINT_RE.search(text) and "план" in text.lower()):
        extras.append(
            "тарифни планови S M L XL ценовник Вардар Мобилен "
            "што вклучува месечна претплата интернет"
        )

    if not extras:
        return text
    return f"{text} {' '.join(extras)}"
