"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { BrandWordmark } from "@/components/LogoMark";
import {
  fetchEvalCatalog,
  fetchEvalLatest,
  type EvalCatalog,
  type EvalCaseRow,
  type EvalModeSummary,
  type EvalReport,
  type RunnerMode,
} from "@/lib/api";

const MODE_ORDER: RunnerMode[] = ["custom", "llamaindex", "langchain"];
const MODE_LABEL: Record<RunnerMode, string> = {
  custom: "Custom",
  llamaindex: "LlamaIndex",
  langchain: "LangChain",
};

function pct(value: number | null | undefined): string {
  if (value == null || Number.isNaN(value)) return "-";
  return `${(value * 100).toFixed(0)}%`;
}

function ms(value: number | null | undefined): string {
  if (value == null || Number.isNaN(value)) return "-";
  return `${Math.round(value)}`;
}

function formatRunAt(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleString(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
  });
}

type MergedCase = EvalCaseRow & {
  language?: string | null;
  must_refuse?: boolean;
  scored: boolean;
};

export default function EvalPage() {
  const [catalog, setCatalog] = useState<EvalCatalog | null>(null);
  const [report, setReport] = useState<EvalReport | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [category, setCategory] = useState<string>("all");

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const [cat, latest] = await Promise.all([
          fetchEvalCatalog(),
          fetchEvalLatest(),
        ]);
        if (!cancelled) {
          setCatalog(cat);
          setReport(latest);
          setError(null);
        }
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : "Failed to load eval");
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const mergedCases = useMemo(
    () => mergeCatalogAndReport(catalog, report),
    [catalog, report],
  );

  const byCategory = useMemo(() => {
    if (report?.by_category && Object.keys(report.by_category).length > 0) {
      return report.by_category;
    }
    return computeByCategory(mergedCases.filter((c) => c.scored));
  }, [report, mergedCases]);

  const categories = catalog?.categories ?? [];
  const filtered = useMemo(() => {
    if (category === "all") return mergedCases;
    return mergedCases.filter((c) => c.category === category);
  }, [mergedCases, category]);

  const scoredCount = mergedCases.filter((c) => c.scored).length;
  const summary = useMemo(
    () => (report ? buildBenchmarkSummary(report, byCategory) : null),
    [report, byCategory],
  );

  return (
    <div className="eval-shell min-h-dvh text-[#0a0a0a]">
      <nav className="mx-auto flex h-[3.6rem] w-full max-w-5xl items-center justify-between px-5 sm:px-7">
        <Link href="/" className="inline-flex items-center">
          <BrandWordmark size={18} />
        </Link>
        <div className="flex items-center gap-5 text-[13px]">
          <Link href="/chat" className="link-quiet text-[#8f8d8a]">
            Chat
          </Link>
          <span className="font-medium tracking-[-0.01em]">Scoreboard</span>
        </div>
      </nav>

      <main className="mx-auto w-full max-w-5xl px-5 pb-20 pt-6 sm:px-7">
        <div className="eval-mark" aria-hidden />
        <p className="text-[11px] font-medium uppercase tracking-[0.18em] text-[#8f8d8a]">
          Benchmark
        </p>
        <h1 className="font-display mt-3 text-[clamp(2rem,4vw,2.75rem)] font-normal leading-[1.02] tracking-[-0.03em]">
          Eval scoreboard
        </h1>
        <p className="mt-4 max-w-[42ch] text-[15px] leading-[1.65] tracking-[-0.01em] text-[#68655e]">
          Golden-set cases by category. Same corpus; Custom, LlamaIndex, and
          LangChain scored with deterministic checks.
        </p>

        {loading && (
          <p className="mt-12 text-[14px] text-[#8f8d8a]">Loading…</p>
        )}
        {error && (
          <p className="mt-12 text-[14px] text-[#8a2f2f]">{error}</p>
        )}

        {!loading && !error && catalog && (
          <>
            <div className="mt-9 flex flex-wrap gap-2">
              <CategoryChip
                active={category === "all"}
                label={`All · ${catalog.n}`}
                onClick={() => setCategory("all")}
              />
              {categories.map((c) => (
                <CategoryChip
                  key={c.id}
                  active={category === c.id}
                  label={`${c.id} · ${c.n}`}
                  onClick={() => setCategory(c.id)}
                />
              ))}
            </div>

            {report ? (
              <>
                <div className="eval-meta mt-8">
                  <MetaItem label="Last run" value={formatRunAt(report.generated_at)} />
                  <MetaItem
                    label="Scored"
                    value={`${scoredCount} / ${catalog.n}`}
                  />
                  {report.retrieval && report.retrieval.n > 0 ? (
                    <>
                      <MetaItem
                        label={`Recall@${report.retrieval.k}`}
                        value={pct(report.retrieval.recall_at_k)}
                      />
                      <MetaItem label="MRR" value={pct(report.retrieval.mrr)} />
                    </>
                  ) : null}
                </div>

                {summary ? (
                  <aside className="eval-summary mt-4">
                    <p className="eval-summary-kicker">Takeaway</p>
                    <p className="eval-summary-lead">{summary.lead}</p>
                    <ul className="eval-summary-list">
                      {summary.bullets.map((b) => (
                        <li key={b}>{b}</li>
                      ))}
                    </ul>
                  </aside>
                ) : null}

                {scoredCount < catalog.n && (
                  <p className="mt-4 rounded-[8px] border border-[#e8e1cf] bg-[#faf6eb] px-3.5 py-2.5 text-[13px] leading-relaxed text-[#6e6658]">
                    Scoreboard is stale vs the golden set. Re-run{" "}
                    <code className="rounded-[3px] bg-[#f3eee3] px-1.5 py-0.5 font-mono text-[12px] text-[#0a0a0a]">
                      uv run python -m app.eval --mode all
                    </code>{" "}
                    to refresh.
                  </p>
                )}

                <section className="mt-10">
                  <h2 className="text-[11px] font-medium uppercase tracking-[0.16em] text-[#8f8d8a]">
                    Modes
                  </h2>
                  <div className="eval-panel mt-3 overflow-x-auto">
                    <table className="eval-table w-full min-w-[640px] text-left">
                      <thead>
                        <tr>
                          <th>Mode</th>
                          <th>Pass</th>
                          <th>Citation</th>
                          <th>Refusal</th>
                          <th>Contain</th>
                          <th>p50 ms</th>
                          <th>Avg tools</th>
                        </tr>
                      </thead>
                      <tbody>
                        {MODE_ORDER.map((mode) => {
                          const row = report.modes[mode];
                          if (!row) {
                            return (
                              <tr key={mode}>
                                <td className="font-medium">
                                  {MODE_LABEL[mode]}
                                </td>
                                <td className="text-[#9a978f]" colSpan={6}>
                                  Not in last run
                                </td>
                              </tr>
                            );
                          }
                          return (
                            <tr key={mode}>
                              <td className="font-medium">
                                {MODE_LABEL[mode]}
                              </td>
                              <td className="tabular-nums">{fmtPass(row)}</td>
                              <td className="tabular-nums">
                                {pct(row.citation_acc)}
                              </td>
                              <td className="tabular-nums">
                                {pct(row.refusal_acc)}
                              </td>
                              <td className="tabular-nums">
                                {pct(row.contain_acc)}
                              </td>
                              <td className="tabular-nums">
                                {ms(row.p50_latency_ms)}
                              </td>
                              <td className="tabular-nums">
                                {row.avg_tool_calls == null
                                  ? "-"
                                  : row.avg_tool_calls.toFixed(1)}
                              </td>
                            </tr>
                          );
                        })}
                      </tbody>
                    </table>
                  </div>
                </section>
              </>
            ) : (
              <div className="eval-panel mt-8 space-y-3 px-4 py-4 text-[14px] leading-relaxed text-[#68655e]">
                <p>Catalog loaded ({catalog.n} cases). No scored report yet.</p>
                <pre className="overflow-x-auto rounded-[6px] bg-[#f3f1eb] px-3.5 py-2.5 font-mono text-[12.5px] text-[#0a0a0a]">
                  {`uv run python -m app.eval --mode all`}
                </pre>
              </div>
            )}

            {Object.keys(byCategory).length > 0 && (
              <section className="mt-12">
                <h2 className="text-[11px] font-medium uppercase tracking-[0.16em] text-[#8f8d8a]">
                  By category
                </h2>
                <div className="eval-panel mt-3 overflow-x-auto">
                  <table className="eval-table w-full min-w-[520px] text-left">
                    <thead>
                      <tr>
                        <th>Category</th>
                        {MODE_ORDER.map((mode) => (
                          <th key={mode}>{MODE_LABEL[mode]}</th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {Object.keys(byCategory)
                        .sort()
                        .map((cat) => (
                          <tr key={cat}>
                            <td>
                              <button
                                type="button"
                                className="font-medium tracking-[-0.01em] hover:underline"
                                onClick={() => setCategory(cat)}
                              >
                                {cat}
                              </button>
                            </td>
                            {MODE_ORDER.map((mode) => {
                              const cell = byCategory[cat]?.[mode];
                              return (
                                <td
                                  key={mode}
                                  className="tabular-nums text-[#68655e]"
                                >
                                  {cell
                                    ? `${pct(cell.pass_rate)} (${cell.passed}/${cell.n})`
                                    : "-"}
                                </td>
                              );
                            })}
                          </tr>
                        ))}
                    </tbody>
                  </table>
                </div>
              </section>
            )}

            <section className="mt-12">
              <div className="flex items-baseline justify-between gap-3">
                <h2 className="text-[11px] font-medium uppercase tracking-[0.16em] text-[#8f8d8a]">
                  Cases
                </h2>
                {category !== "all" ? (
                  <span className="text-[12px] text-[#9a978f]">{category}</span>
                ) : null}
              </div>

              {groupCases(filtered).map(([cat, items]) => (
                <div key={cat} className="mt-6">
                  <h3 className="mb-2.5 flex items-center gap-2 text-[12px] font-medium tracking-[-0.01em] text-[#5f5c55]">
                    <span>{cat}</span>
                    <span className="text-[#b0ada5]">{items.length}</span>
                  </h3>
                  <ul className="eval-case-list">
                    {items.map((c) => (
                      <li key={c.id} className="eval-case">
                        <div className="flex flex-wrap items-center gap-x-2 gap-y-1">
                          <code className="rounded-[3px] bg-[#f3f1eb] px-1.5 py-0.5 font-mono text-[11px] text-[#5f5c55]">
                            {c.id}
                          </code>
                          {c.must_refuse ? (
                            <span className="rounded-[3px] bg-[#f3eee3] px-1.5 py-0.5 text-[10px] font-medium uppercase tracking-[0.06em] text-[#7a6f5c]">
                              refuse
                            </span>
                          ) : null}
                          {!c.scored ? (
                            <span className="text-[11px] text-[#b0ada5]">
                              not scored
                            </span>
                          ) : null}
                        </div>
                        <p className="mt-2 text-[14px] leading-snug tracking-[-0.01em] text-[#0a0a0a]">
                          {c.q}
                        </p>
                        {c.scored ? (
                          <div className="mt-2.5 flex flex-wrap gap-1.5">
                            {MODE_ORDER.map((mode) => {
                              const m = c.modes[mode];
                              if (!m) return null;
                              return (
                                <span
                                  key={mode}
                                  className={`eval-result ${m.passed ? "is-pass" : "is-fail"}`}
                                >
                                  {MODE_LABEL[mode]}
                                  {m.tool_calls
                                    ? ` · ${m.tool_calls} tools`
                                    : ""}
                                </span>
                              );
                            })}
                          </div>
                        ) : null}
                      </li>
                    ))}
                  </ul>
                </div>
              ))}
            </section>
          </>
        )}
      </main>
    </div>
  );
}

function MetaItem({ label, value }: { label: string; value: string }) {
  return (
    <div className="eval-meta-item">
      <span className="eval-meta-label">{label}</span>
      <span className="eval-meta-value">{value}</span>
    </div>
  );
}

function buildBenchmarkSummary(
  report: EvalReport,
  byCategory: NonNullable<EvalReport["by_category"]>,
): { lead: string; bullets: string[] } {
  const rows = MODE_ORDER.map((mode) => {
    const row = report.modes[mode];
    return row ? { mode, row } : null;
  }).filter((x): x is { mode: RunnerMode; row: EvalModeSummary } => Boolean(x));

  if (rows.length === 0) {
    return {
      lead: "No mode results in this report yet.",
      bullets: [],
    };
  }

  const ranked = [...rows].sort((a, b) => {
    const passDiff = b.row.pass_rate - a.row.pass_rate;
    if (passDiff !== 0) return passDiff;
    return (a.row.p50_latency_ms ?? 1e9) - (b.row.p50_latency_ms ?? 1e9);
  });
  const best = ranked[0];
  const worst = ranked[ranked.length - 1];
  const fastest = [...rows].sort(
    (a, b) => (a.row.p50_latency_ms ?? 1e9) - (b.row.p50_latency_ms ?? 1e9),
  )[0];

  const lead = `${MODE_LABEL[best.mode]} leads overall at ${pct(best.row.pass_rate)} pass (${best.row.passed}/${best.row.n}). ${
    best.mode !== worst.mode
      ? `${MODE_LABEL[worst.mode]} is lowest at ${pct(worst.row.pass_rate)}.`
      : "All modes scored similarly."
  }`;

  const bullets: string[] = [];

  if (report.retrieval && report.retrieval.n > 0) {
    const k = report.retrieval.k;
    bullets.push(
      `Retrieval Recall@${k} is ${pct(report.retrieval.recall_at_k)}: in that share of cases, at least one expected doc appears in the top ${k} hits.`,
    );
    bullets.push(
      `MRR is ${pct(report.retrieval.mrr)}: how high the first correct doc ranks (higher means closer to #1).`,
    );
  }

  bullets.push(
    `${MODE_LABEL[fastest.mode]} is fastest (p50 ${ms(fastest.row.p50_latency_ms)} ms)` +
      (fastest.mode !== best.mode
        ? `, while ${MODE_LABEL[best.mode]} trades a bit of latency for the best pass rate.`
        : "."),
  );

  const categoryScores = Object.entries(byCategory)
    .map(([cat, modes]) => {
      const rates = MODE_ORDER.map((m) => modes[m]?.pass_rate).filter(
        (r): r is number => typeof r === "number",
      );
      if (rates.length === 0) return null;
      const avg = rates.reduce((a, b) => a + b, 0) / rates.length;
      return { cat, avg };
    })
    .filter((x): x is { cat: string; avg: number } => Boolean(x))
    .sort((a, b) => b.avg - a.avg);

  if (categoryScores.length >= 2) {
    const strong = categoryScores[0];
    const weak = categoryScores[categoryScores.length - 1];
    bullets.push(
      `Strongest category on average: ${strong.cat} (${pct(strong.avg)}). Softest: ${weak.cat} (${pct(weak.avg)}).`,
    );
  }

  const citation = rows.map((r) => r.row.citation_acc).filter((v): v is number => v != null);
  if (citation.length > 0) {
    const avgCite = citation.reduce((a, b) => a + b, 0) / citation.length;
    bullets.push(
      `Citation accuracy averages ${pct(avgCite)} across modes: answers usually point at the right docs when citations are checked.`,
    );
  }

  return { lead, bullets };
}

function CategoryChip({
  active,
  label,
  onClick,
}: {
  active: boolean;
  label: string;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`rounded-[6px] border px-3 py-1.5 text-[12px] tracking-[-0.01em] transition ${
        active
          ? "border-[#0a0a0a] bg-[#0a0a0a] text-[#fefefc]"
          : "border-[#e4e1d9] bg-[#fefefc]/70 text-[#68655e] hover:border-[#cfcbc3] hover:text-[#0a0a0a]"
      }`}
    >
      {label}
    </button>
  );
}

function mergeCatalogAndReport(
  catalog: EvalCatalog | null,
  report: EvalReport | null,
): MergedCase[] {
  if (!catalog) return [];
  const scoreById = new Map(
    (report?.cases ?? []).map((c) => [c.id, c] as const),
  );
  return catalog.cases.map((c) => {
    const scored = scoreById.get(c.id);
    return {
      id: c.id,
      category: c.category,
      tags: c.tags,
      q: c.q,
      language: c.language,
      must_refuse: c.must_refuse,
      modes: scored?.modes ?? {},
      scored: Boolean(scored),
    };
  });
}

function computeByCategory(
  cases: MergedCase[],
): NonNullable<EvalReport["by_category"]> {
  const out: NonNullable<EvalReport["by_category"]> = {};
  for (const c of cases) {
    const cat = c.category || "other";
    for (const mode of MODE_ORDER) {
      const m = c.modes[mode];
      if (!m) continue;
      const bucket = (out[cat] ??= {});
      const cell = (bucket[mode] ??= { n: 0, passed: 0, pass_rate: 0 });
      cell.n += 1;
      if (m.passed) cell.passed += 1;
      cell.pass_rate = cell.n ? cell.passed / cell.n : 0;
    }
  }
  return out;
}

function groupCases(cases: MergedCase[]): Array<[string, MergedCase[]]> {
  const map = new Map<string, MergedCase[]>();
  for (const c of cases) {
    const key = c.category || "other";
    const list = map.get(key) ?? [];
    list.push(c);
    map.set(key, list);
  }
  return [...map.entries()].sort(([a], [b]) => a.localeCompare(b));
}

function fmtPass(row: EvalModeSummary): string {
  return `${pct(row.pass_rate)} (${row.passed}/${row.n})`;
}
