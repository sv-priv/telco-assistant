# Corpus sources and licensing

## Language note (product)

- **Operator corpus:** bilingual MK + EN (primary product language for chat).
- **EU / WB6:** English-first. Ingested as `language: en`. The UI may still ask
  in Macedonian; retrieval can surface EN regulation docs when relevant.
  Prefer asking regulation questions in English for best matches.

## EU (real)

From EUR-Lex, CC BY 4.0 (Commission Decision 2011/833/EU).

> © European Union, 1998–2026
> https://eur-lex.europa.eu/content/legal-notice/legal-notice.html

| File | CELEX | Instrument | Status |
|------|-------|------------|--------|
| `eu/32022R0612-en.md` | 32022R0612 | Roaming (recast) | in force |
| `eu/32012R0531-en.md` | 32012R0531 | Roaming | repealed 30 Jun 2022 |
| `eu/32018L1972-en.md` | 32018L1972 | EECC | in force |
| `eu/32015R2120-en.md` | 32015R2120 | Open internet | in force |

HTML → markdown via `scripts/convert_eurlex.py`. `ARTICLE-INDEX.md` is a lookup
aid, not ingested. 531/2012 is kept on purpose (superseded law / `status` metadata).

## WB6 (real)

Regional roaming agreement and related public texts under `wb6/`.

## Operator (synthetic)

Built from `data/scripts/catalog.py` via `data/scripts/generate_corpus.py`.
**Vardar Mobile does not exist.** Prices and promos are invented; no real
operator text or personal data.
