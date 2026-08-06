#!/usr/bin/env bash
# Download the four EU instruments in EN and NL from EUR-Lex.
# Run from the repository root:  bash scripts_fetch_eu_corpus.sh
set -euo pipefail

OUT="data/corpus/eu"
mkdir -p "$OUT"

CELEX=(32022R0612 32012R0531 32018L1972 32015R2120)
NAME=("roaming, current" "roaming, repealed" "EECC" "open internet")
LANGS=(EN NL)

fail=0
for i in "${!CELEX[@]}"; do
  for lang in "${LANGS[@]}"; do
    id="${CELEX[$i]}"
    low=$(echo "$lang" | tr '[:upper:]' '[:lower:]')
    f="$OUT/${id}-${low}.html"
    curl -sL --compressed \
      -A "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0 Safari/537.36" \
      -H "Accept: text/html,application/xhtml+xml" \
      -H "Accept-Language: en-GB,en;q=0.9" \
      "https://eur-lex.europa.eu/legal-content/${lang}/TXT/HTML/?uri=CELEX:${id}" \
      -o "$f" || true
    size=$(wc -c < "$f" 2>/dev/null || echo 0)
    if [ "$size" -lt 50000 ]; then
      printf "  ✗ %-12s %s  %8s bytes  TOO SMALL — download manually\n" "$id" "$lang" "$size"
      fail=1
    else
      printf "  ✓ %-12s %s  %8s bytes  (%s)\n" "$id" "$lang" "$size" "${NAME[$i]}"
    fi
  done
done

echo
if [ "$fail" -eq 1 ]; then
  cat <<'MSG'
Some files failed. EUR-Lex sometimes rejects non-browser clients.
Fallback: open each URL in a browser and use File > Save As, choosing
format "Page Source" (not "Web Archive"), saving as <CELEX>-<lang>.html
into data/corpus/eu/

  https://eur-lex.europa.eu/legal-content/EN/TXT/HTML/?uri=CELEX:32022R0612
  https://eur-lex.europa.eu/legal-content/EN/TXT/HTML/?uri=CELEX:32012R0531
  https://eur-lex.europa.eu/legal-content/EN/TXT/HTML/?uri=CELEX:32018L1972
  https://eur-lex.europa.eu/legal-content/EN/TXT/HTML/?uri=CELEX:32015R2120

Swap EN for NL for the Dutch parallel versions.
MSG
else
  echo "All eight files downloaded. Corpus layer 1 complete."
fi
