"""Deterministic query expansion for plan / package / country questions.

Dense retrieval alone often maps colloquial «XL пакетот» onto addon
«Додатен интернет пакет…» docs. Expanding toward «тарифен план / ценовник»
pulls price-list chunks into the candidate set.

Country aliases (England → United Kingdom) keep EN queries aligned with
corpus titles that use official names.
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

# Colloquial / alternate names → corpus wording (official country titles).
_COUNTRY_ALIASES: list[tuple[re.Pattern[str], str]] = [
    (
        re.compile(r"\b(england|britain|great\s+britain|uk)\b", re.I),
        "United Kingdom GB roaming",
    ),
    (re.compile(r"\b(holland|the\s+netherlands)\b", re.I), "Netherlands NL roaming"),
    (re.compile(r"\b(uae|dubai)\b", re.I), "United Arab Emirates AE roaming"),
    (re.compile(r"\b(usa|u\.s\.a\.|united\s+states)\b", re.I), "United States US roaming"),
    (re.compile(r"\b(czechia|czech\s+republic)\b", re.I), "Czechia CZ roaming"),
]


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


def expand_country_aliases(query: str) -> str:
    """Append official country names used in corpus titles."""
    text = query.strip()
    if not text:
        return query
    extras: list[str] = []
    for pattern, expansion in _COUNTRY_ALIASES:
        if pattern.search(text):
            extras.append(expansion)
    if not extras:
        return text
    return f"{text} {' '.join(extras)}"


def expand_search_query(query: str) -> str:
    """Append retrieval-friendly plan/country terms; leave unrelated queries unchanged."""
    text = expand_country_aliases(query.strip())
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
