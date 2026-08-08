"use client";

import Link from "next/link";
import { useEffect, useRef, useState, type FormEvent } from "react";
import { LogoMark } from "@/components/LogoMark";
import { askChat, type Citation, type HistoryMessage } from "@/lib/api";

type Role = "user" | "assistant" | "error";

type Message = {
  id: string;
  role: Role;
  content: string;
  pending?: boolean;
};

const SUGGESTIONS_MK = [
  { label: "Роаминг во Турција", q: "Колку чини роаминг во Турција?" },
  { label: "XL план", q: "Што има во тарифен план XL?" },
  { label: "Читање на сметка", q: "Како да ја читам месечната сметка?" },
];

const SUGGESTIONS_EN = [
  { label: "Roaming in Turkey", q: "How much is roaming in Turkey?" },
  { label: "XL plan", q: "What is included in the XL plan?" },
  { label: "Read my bill", q: "How do I read my monthly bill?" },
];

function suggestionsFor(language: string) {
  return language === "en" ? SUGGESTIONS_EN : SUGGESTIONS_MK;
}

const COPY = {
  mk: {
    eyebrow: "Асистент",
    title: "Што ти треба?",
    subtitle:
      "Прашај на македонски. Одговорите се од операторските документи — изворите се на таблата.",
    disclaimer: "Демо · фиктивен оператор · не е вистински телеком",
    placeholder: "Прашај за роаминг, планови, сметки…",
    send: "Испрати",
    thinking: "Размислува",
    sources: "Извори",
    sourcesEmpty:
      "Документите за последниот одговор се појавуваат овде — намерно надвор од разговорот.",
    match: "Поклопување",
    sourceLabels: { operator: "оператор", eu: "ЕУ", wb6: "ЗБ6" } as Record<
      string,
      string
    >,
  },
  en: {
    eyebrow: "Assistant",
    title: "What do you need?",
    subtitle:
      "Ask in English. Answers are grounded in operator docs — sources land on the board.",
    disclaimer: "Demo · fictional operator · not a real carrier",
    placeholder: "Ask about roaming, plans, bills…",
    send: "Send",
    thinking: "Thinking",
    sources: "Sources",
    sourcesEmpty:
      "Docs used for the latest answer show up here — kept out of the chat on purpose.",
    match: "Match",
    sourceLabels: { operator: "operator", eu: "EU", wb6: "WB6" } as Record<
      string,
      string
    >,
  },
} as const;

function SendIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" aria-hidden>
      <path
        d="M5 12h14M13 6l6 6-6 6"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

function splitRow(line: string): string[] {
  return line
    .trim()
    .replace(/^\|/, "")
    .replace(/\|$/, "")
    .split("|")
    .map((c) => c.trim());
}

function MarkdownAnswer({ text }: { text: string }) {
  const blocks = text.trim().split(/\n{2,}/);
  return (
    <div className="prose-answer">
      {blocks.map((block, i) => {
        const lines = block.split("\n");
        const isTable =
          lines.length >= 2 &&
          lines[0].includes("|") &&
          /^\s*\|?\s*:?-+:?\s*(\|\s*:?-+:?\s*)+\|?\s*$/.test(lines[1]);
        if (isTable) {
          const [header, , ...rows] = lines;
          return (
            <table key={i}>
              <thead>
                <tr>
                  {splitRow(header).map((cell) => (
                    <th key={cell}>{cell}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {rows
                  .filter((row) => row.includes("|"))
                  .map((row) => (
                    <tr key={row}>
                      {splitRow(row).map((cell) => (
                        <td key={`${row}-${cell}`}>{cell}</td>
                      ))}
                    </tr>
                  ))}
              </tbody>
            </table>
          );
        }
        return <p key={i}>{block}</p>;
      })}
    </div>
  );
}

function relevance(score: number | null): number {
  if (typeof score !== "number") return 0;
  return Math.max(0, Math.min(1, score));
}

export default function ChatPage() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [question, setQuestion] = useState("");
  const [language, setLanguage] = useState("mk");
  const [busy, setBusy] = useState(false);
  const [board, setBoard] = useState<Citation[]>([]);
  const threadRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    const el = threadRef.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [messages]);

  function historyForApi(nextMessages: Message[]): HistoryMessage[] {
    return nextMessages
      .filter((m) => !m.pending && (m.role === "user" || m.role === "assistant"))
      .slice(-8)
      .map((m) => ({
        role: m.role as "user" | "assistant",
        content: m.content,
      }));
  }

  async function send(text: string) {
    const q = text.trim();
    if (!q || busy) return;

    const pendingId = crypto.randomUUID();
    const userMsg: Message = {
      id: crypto.randomUUID(),
      role: "user",
      content: q,
    };
    const history = historyForApi(messages);

    setMessages((prev) => [
      ...prev,
      userMsg,
      { id: pendingId, role: "assistant", content: "", pending: true },
    ]);
    setQuestion("");
    setBusy(true);

    try {
      const data = await askChat({
        question: q,
        language: language || undefined,
        history,
      });
      setMessages((prev) =>
        prev.map((m) =>
          m.id === pendingId
            ? { ...m, pending: false, content: data.answer }
            : m,
        ),
      );
      setBoard(data.citations ?? []);
    } catch (err) {
      const detail = err instanceof Error ? err.message : "Request failed";
      setMessages((prev) =>
        prev.map((m) =>
          m.id === pendingId
            ? { ...m, role: "error", pending: false, content: detail }
            : m,
        ),
      );
    } finally {
      setBusy(false);
      inputRef.current?.focus();
    }
  }

  function onSubmit(e: FormEvent) {
    e.preventDefault();
    void send(question);
  }

  const empty = messages.length === 0;
  const suggestions = suggestionsFor(language);
  const t = language === "en" ? COPY.en : COPY.mk;

  return (
    <div className="flex h-dvh bg-[#fefefc] text-[#0a0a0a]">
      <div className="flex min-w-0 flex-1 flex-col">
        <header className="flex h-14 shrink-0 items-center justify-between gap-3 border-b border-[#e1dfda]/80 px-5">
          <Link href="/" className="flex min-w-0 items-center gap-2.5 text-[#0a0a0a]">
            <LogoMark />
            <span className="truncate text-[14px] font-medium tracking-tight">
              Vardar Mobile
            </span>
          </Link>
          <p className="hidden text-[11px] text-[#8f8d8a] sm:block">{t.disclaimer}</p>
          <div className="flex items-center gap-1 rounded-[2px] border border-[#e1dfda] bg-[#fbfbf9] p-0.5">
            {(
              [
                ["mk", "MK"],
                ["en", "EN"],
              ] as const
            ).map(([value, label]) => (
              <button
                key={label}
                type="button"
                disabled={busy}
                onClick={() => setLanguage(value)}
                className={`rounded-[2px] px-2.5 py-1 text-[12px] font-medium transition ${
                  language === value
                    ? "bg-[#fefefc] text-[#0a0a0a] shadow-sm"
                    : "text-[#68655e] hover:text-[#0a0a0a]"
                }`}
              >
                {label}
              </button>
            ))}
          </div>
        </header>

        <div ref={threadRef} className="min-h-0 flex-1 overflow-auto">
          <div
            className={`mx-auto w-full max-w-[680px] px-5 ${
              empty ? "flex h-full flex-col justify-center" : "py-8"
            }`}
          >
            {empty ? (
              <div className="animate-rise">
                <p className="text-[12px] font-medium uppercase tracking-[0.16em] text-[#68655e]">
                  {t.eyebrow}
                </p>
                <h1 className="font-display mt-3 text-[2rem] font-normal tracking-[-0.02em] text-[#0a0a0a] sm:text-[2.35rem]">
                  {t.title}
                </h1>
                <p className="mt-3 max-w-md text-[15px] leading-relaxed tracking-[-0.01em] text-[#68655e]">
                  {t.subtitle}
                </p>
                <div className="mt-7 flex flex-wrap gap-2">
                  {suggestions.map((s) => (
                    <button
                      key={`${language}-${s.label}`}
                      type="button"
                      onClick={() => void send(s.q)}
                      className="rounded-[2px] border border-[#e1dfda] bg-[#fefefc] px-4 py-2 text-[13px] font-medium text-[#444] transition hover:border-[#d0cdc8] hover:bg-[#ebf5ed] hover:text-[#0a0a0a]"
                    >
                      {s.label}
                    </button>
                  ))}
                </div>
              </div>
            ) : (
              <div className="space-y-6">
                {messages.map((m) => (
                  <div key={m.id} className="msg-enter">
                    {m.role === "user" ? (
                      <div className="flex justify-end">
                        <div className="max-w-[80%] rounded-2xl bg-[#0a0a0a] px-4 py-2.5 text-[14px] leading-relaxed tracking-[-0.01em] text-[#fefefc]">
                          {m.content}
                        </div>
                      </div>
                    ) : (
                      <div className="flex gap-3">
                        <div className="mt-1 flex h-7 w-7 shrink-0 items-center justify-center rounded-[2px] bg-[#0a0a0a] text-[11px] font-medium text-[#fefefc]">
                          V
                        </div>
                        <div
                          className={`min-w-0 flex-1 pt-0.5 ${
                            m.role === "error" ? "text-[14px] text-red-600" : ""
                          }`}
                        >
                          {m.pending ? (
                            <span className="typing" aria-label={t.thinking}>
                              <i />
                              <i />
                              <i />
                            </span>
                          ) : m.role === "assistant" ? (
                            <MarkdownAnswer text={m.content} />
                          ) : (
                            m.content
                          )}
                        </div>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        <div className="shrink-0 px-5 pb-5 pt-2">
          <form
            onSubmit={onSubmit}
            className="mx-auto flex max-w-[680px] items-end gap-2 rounded-lg border border-[#e1dfda] bg-[#fbfbf9]/80 p-2 shadow-[0_1px_2px_rgba(0,0,0,0.04)] transition focus-within:border-[#d0cdc8] focus-within:bg-[#fefefc] focus-within:shadow-[0_8px_24px_rgba(13,16,22,0.06)]"
          >
            <textarea
              ref={inputRef}
              value={question}
              onChange={(e) => {
                setQuestion(e.target.value);
                e.currentTarget.style.height = "auto";
                e.currentTarget.style.height = `${Math.min(e.currentTarget.scrollHeight, 140)}px`;
              }}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault();
                  void send(question);
                }
              }}
              rows={1}
              placeholder={t.placeholder}
              required
              disabled={busy}
              className="max-h-[140px] min-h-[44px] flex-1 resize-none bg-transparent px-3 py-2.5 text-[14px] tracking-[-0.01em] outline-none placeholder:text-[#8f8d8a]"
            />
            <button
              type="submit"
              disabled={busy || !question.trim()}
              aria-label={t.send}
              className="mb-0.5 inline-flex h-11 w-11 shrink-0 items-center justify-center rounded-[2px] bg-[#0a0a0a] text-[#fefefc] transition hover:bg-[#222] disabled:opacity-35"
            >
              <SendIcon />
            </button>
          </form>
        </div>
      </div>

      <aside className="hidden w-[320px] shrink-0 flex-col border-l border-[#e1dfda] bg-[#ebf5ed] xl:flex">
        <div className="flex h-14 items-center justify-between px-5">
          <span className="text-[12px] font-medium uppercase tracking-[0.14em] text-[#8f8d8a]">
            {t.sources}
          </span>
          {board.length > 0 ? (
            <span className="rounded-[2px] bg-[#fefefc] px-2 py-0.5 text-[11px] font-medium text-[#68655e] ring-1 ring-[#e1dfda]">
              {board.length}
            </span>
          ) : null}
        </div>
        <div className="min-h-0 flex-1 overflow-auto px-3 pb-4">
          {board.length === 0 ? (
            <p className="px-2 pt-1 text-[13px] leading-relaxed text-[#8f8d8a]">
              {t.sourcesEmpty}
            </p>
          ) : (
            <ol className="space-y-2">
              {board.map((c, i) => {
                const pct = Math.round(relevance(c.score) * 100);
                return (
                  <li
                    key={`${c.doc_id}-${c.chunk_index}-${c.language}`}
                    className="msg-enter rounded-lg border border-[#e1dfda]/80 bg-[#fefefc] p-3 shadow-[0_1px_2px_rgba(0,0,0,0.03)]"
                  >
                    <div className="flex items-start justify-between gap-2">
                      <span className="font-mono text-[11px] text-[#d0cdc8]">
                        {String(i + 1).padStart(2, "0")}
                      </span>
                      <span className="rounded-[2px] bg-[#f3f2ed] px-1.5 py-0.5 text-[10px] font-medium uppercase tracking-wide text-[#68655e]">
                        {t.sourceLabels[c.source] ?? c.source}
                      </span>
                    </div>
                    <p className="mt-2 text-[13px] font-medium leading-snug tracking-tight text-[#0a0a0a]">
                      {c.title || c.doc_id}
                    </p>
                    <p className="mt-1 truncate font-mono text-[11px] text-[#8f8d8a]">
                      {c.doc_id}
                    </p>
                    {typeof c.score === "number" ? (
                      <div className="mt-3">
                        <div className="mb-1 flex items-center justify-between text-[11px] text-[#8f8d8a]">
                          <span>{t.match}</span>
                          <span className="font-mono text-[#005032]">
                            {pct}%
                          </span>
                        </div>
                        <div className="h-1 overflow-hidden rounded-full bg-[#e1dfda]">
                          <div
                            className="h-full rounded-full bg-[#005032] transition-all"
                            style={{ width: `${pct}%` }}
                          />
                        </div>
                      </div>
                    ) : null}
                  </li>
                );
              })}
            </ol>
          )}
        </div>
      </aside>
    </div>
  );
}
