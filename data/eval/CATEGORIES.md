# Golden-set categories

Each case in `golden.jsonl` has a required `category` (primary bucket) plus optional `tags`.

| Category | What it tests |
|----------|----------------|
| `plan` | S/M/L/XL inclusions, prices, FUP, compare |
| `refuse` | Non-existent tiers (XXL, XS, …) — must not alias |
| `roaming` | Zones, country rates, roaming packs |
| `billing` | Invoices, FUP on bill, plan-change lines |
| `about` | Operator overview / “who are you” |
| `followup` | Short replies that need conversation history |
| `network` | Coverage, 5G, network FAQ |
| `devices` | Phones / catalog / device FAQ |
| `contract` | Contracts, cancellation, portability |
| `security` | Lost SIM, fraud |
| `addon` | Extra data packs (AD-*) |
| `support` | SIM activation, account FAQ, procedures |

Scoreboard rolls up pass rate **by category × mode** in `latest.json` → `by_category`.
