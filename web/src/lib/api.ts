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

export type ChatResponse = {
  question: string;
  answer: string;
  citations: Citation[];
};

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export async function askChat(input: {
  question: string;
  language?: string;
  limit?: number;
  history?: HistoryMessage[];
}): Promise<ChatResponse> {
  const res = await fetch(`${API_URL}/v1/chat`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({
      question: input.question,
      language: input.language || undefined,
      limit: input.limit ?? 8,
      history: input.history ?? [],
    }),
  });

  const data = (await res.json()) as ChatResponse & {
    detail?: string;
    title?: string;
  };

  if (!res.ok) {
    throw new Error(data.detail || data.title || `Request failed (${res.status})`);
  }
  return data;
}
