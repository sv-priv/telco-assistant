export type Citation = {
  doc_id: string;
  chunk_index: number;
  title: string;
  section: string | null;
  source: string;
  language: string;
  score: number | null;
};

export type HistoryMessage = {
  role: "user" | "assistant";
  content: string;
};

export type RunnerMode = "custom" | "llamaindex" | "langchain";

export type ChatResponse = {
  question: string;
  answer: string;
  citations: Citation[];
};

export type AskResponse = {
  mode: RunnerMode;
  question: string;
  answer: string;
  citations: Citation[];
  trace: Record<string, unknown>[];
  latency_ms: number;
};

export type EvalModeSummary = {
  n: number;
  passed: number;
  pass_rate: number;
  citation_acc: number | null;
  refusal_acc: number | null;
  contain_acc: number | null;
  p50_latency_ms: number | null;
  p95_latency_ms: number | null;
  avg_tool_calls: number | null;
};

export type EvalCaseModeScore = {
  passed: boolean;
  latency_ms: number;
  cited_doc_ids: string[];
  tool_calls: number;
  answer_preview: string;
  error: string | null;
};

export type EvalCaseRow = {
  id: string;
  category?: string;
  tags: string[];
  q: string;
  modes: Partial<Record<RunnerMode, EvalCaseModeScore>>;
};

export type EvalReport = {
  generated_at: string;
  golden_path: string;
  modes: Partial<Record<RunnerMode, EvalModeSummary>>;
  by_category?: Record<
    string,
    Partial<Record<RunnerMode, { n: number; passed: number; pass_rate: number }>>
  >;
  retrieval: {
    n: number;
    k: number;
    recall_at_k: number | null;
    mrr: number | null;
  } | null;
  cases: EvalCaseRow[];
};

export type EvalCatalog = {
  golden_path: string;
  n: number;
  categories: Array<{ id: string; n: number }>;
  cases: Array<{
    id: string;
    category: string;
    tags: string[];
    q: string;
    language: string | null;
    must_refuse: boolean;
  }>;
};

/** Browser calls same-origin Next proxies — API key stays on the server. */
const PROXY = "";

async function readBodyText(res: Response): Promise<string> {
  try {
    return (await res.text()).trim();
  } catch {
    return "";
  }
}

async function readProblem(res: Response): Promise<string> {
  const text = await readBodyText(res);
  if (!text) {
    return `Request failed (${res.status || "network"}) — empty response from API`;
  }
  try {
    const data = JSON.parse(text) as { detail?: string; title?: string };
    return data.detail || data.title || `Request failed (${res.status})`;
  } catch {
    return text.slice(0, 200) || `Request failed (${res.status})`;
  }
}

export async function fetchEvalCatalog(): Promise<EvalCatalog> {
  const res = await fetch(`${PROXY}/api/eval/catalog`);
  if (!res.ok) throw new Error(await readProblem(res));
  const text = await readBodyText(res);
  if (!text) throw new Error("Empty eval catalog response");
  return JSON.parse(text) as EvalCatalog;
}

export async function fetchEvalLatest(): Promise<EvalReport | null> {
  const res = await fetch(`${PROXY}/api/eval/latest`);
  if (res.status === 404) return null;
  if (!res.ok) throw new Error(await readProblem(res));
  const text = await readBodyText(res);
  if (!text) return null;
  return JSON.parse(text) as EvalReport;
}

export async function askChat(input: {
  question: string;
  language?: string;
  limit?: number;
  history?: HistoryMessage[];
  mode?: RunnerMode;
}): Promise<AskResponse> {
  const res = await fetch(`${PROXY}/api/ask`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({
      question: input.question,
      mode: input.mode ?? "custom",
      language: input.language || undefined,
      limit: input.limit ?? 8,
      history: input.history ?? [],
    }),
  });

  if (!res.ok) throw new Error(await readProblem(res));
  const text = await readBodyText(res);
  if (!text) {
    throw new Error(
      "Empty response from API (service may be waking up — retry in ~30s)",
    );
  }
  return JSON.parse(text) as AskResponse;
}
