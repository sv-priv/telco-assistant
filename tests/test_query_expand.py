"""Plan query expansion + ranking helpers."""

from __future__ import annotations

from app.ingest.store import StoredChunk
from app.retrieve.query_expand import expand_search_query, is_plan_query
from app.retrieve.ranking import rerank_hits


def test_expand_xl_paket_adds_cenovnik_terms() -> None:
    q = expand_search_query("Што има во XL пакетот?")
    assert "тарифен план XL" in q
    assert "ценовник" in q


def test_expand_list_packages() -> None:
    q = expand_search_query("kakvi paketi ima?")
    assert "тарифни планови" in q
    assert "S M L XL" in q


def test_expand_leaves_roaming_alone() -> None:
    q = "Колку чини роаминг во Турција?"
    assert expand_search_query(q) == q
    assert not is_plan_query(q)


def test_expand_about_operator() -> None:
    q = expand_search_query("a mozes da mi kazes nesto povekje za vardar mobile")
    assert "преглед" in q or "about" in q.lower()
    assert not is_plan_query(q)


def test_rerank_prefers_cenovnik_over_addon() -> None:
    hits = [
        StoredChunk(
            doc_id="op-addon-1gb-2026",
            chunk_index=0,
            language="mk",
            source="operator",
            title="Додатен интернет пакет 1 GB",
            section=None,
            family="addon",
            text="додаток",
            score=0.50,
        ),
        StoredChunk(
            doc_id="op-cenovnik-xl-2026",
            chunk_index=0,
            language="mk",
            source="operator",
            title="Ценовник — Вардар Мобилен XL",
            section=None,
            family="price",
            text="XL план",
            score=0.37,
        ),
    ]
    ranked = rerank_hits("Што има во XL пакетот? тарифен план XL", hits, limit=2)
    assert ranked[0].doc_id == "op-cenovnik-xl-2026"
