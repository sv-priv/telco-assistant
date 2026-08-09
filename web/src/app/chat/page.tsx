"use client";

import Link from "next/link";
import { useEffect, useRef, useState, type FormEvent } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { BrandWordmark } from "@/components/LogoMark";
import {
  askChat,
  type Citation,
  type HistoryMessage,
  type RunnerMode,
} from "@/lib/api";

type Role = "user" | "assistant" | "error";

type Message = {
  id: string;
  role: Role;
  content: string;
  pending?: boolean;
  mode?: RunnerMode;
  trace?: Record<string, unknown>[];
};

const RUNNERS: {
  id: RunnerMode;
  label: string;
  hintMk: string;
  hintEn: string;
}[] = [
  {
    id: "custom",
    label: "Custom",
    hintMk: "Наш RAG pipeline: retrieve, па одговор.",
    hintEn: "Our RAG pipeline: retrieve, then answer.",
  },
  {
    id: "llamaindex",
    label: "LlamaIndex",
    hintMk: "QueryEngine над истиот retriever.",
    hintEn: "QueryEngine on the same retriever.",
  },
  {
    id: "langchain",
    label: "LangChain",
    hintMk: "Agent со tools (search / get_plan).",
    hintEn: "Agent with tools (search / get_plan).",
  },
];

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
      "Прашај на македонски. Одговорите се од операторските документи. Изворите се на таблата.",
    runnerLabel: "Начин на одговор",
    placeholder: "Прашај за роаминг, планови, сметки…",
    send: "Испрати",
    thinking: "Размислува",
    sources: "Извори",
    sourcesEmpty: "Документите за последниот одговор се појавуваат овде.",
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
      "Ask in English. Answers are grounded in operator docs. Sources land on the board.",
    runnerLabel: "Answer mode",
    placeholder: "Ask about roaming, plans, bills…",
    send: "Send",
    thinking: "Thinking",
    sources: "Sources",
    sourcesEmpty: "Docs used for the latest answer show up here.",
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

function MarkdownAnswer({ text }: { text: string }) {
  return (
    <div className="prose-answer">
      <ReactMarkdown remarkPlugins={[remarkGfm]}>{text}</ReactMarkdown>
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
  const [mode, setMode] = useState<RunnerMode>("custom");
  const [busy, setBusy] = useState(false);
  const [board, setBoard] = useState<Citation[]>([]);
  const threadRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    const el = threadRef.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [messages]);

  useEffect(() => {
    document.documentElement.lang = language === "en" ? "en" : "mk";
  }, [language]);

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
      {
        id: pendingId,
        role: "assistant",
        content: "",
        pending: true,
        mode,
      },
    ]);
    setQuestion("");
    setBusy(true);

    try {
      const data = await askChat({
        question: q,
        language: language || undefined,
        history,
        mode,
      });
      setMessages((prev) =>
        prev.map((m) =>
          m.id === pendingId
            ? {
                ...m,
                pending: false,
                content: data.answer,
                mode: data.mode,
                trace: data.trace ?? [],
              }
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
  const activeRunner = RUNNERS.find((r) => r.id === mode) ?? RUNNERS[0];

  return (
    <div className="chat-shell flex h-dvh text-[#0a0a0a]">
      <div className="chat-main relative flex min-w-0 flex-1 flex-col">
        <header className="flex h-[3.6rem] shrink-0 items-center justify-between gap-3 px-5 sm:px-7">
          <Link
            href="/"
            className="group inline-flex min-w-0 items-center opacity-100 transition-opacity duration-200 hover:opacity-65"
          >
            <BrandWordmark size={18} className="text-[14px]" />
          </Link>
          <div className="flex items-center gap-3">
            <Link
              href="/eval"
              className="link-quiet hidden text-[12px] text-[#8f8d8a] sm:inline"
            >
              Scoreboard
            </Link>
            <div className="flex items-center gap-0.5 rounded-[7px] border border-[#e4e1d9] bg-white/55 p-[3px] shadow-[inset_0_1px_0_rgba(255,255,255,0.7)] backdrop-blur-sm">
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
                  className={`rounded-[4px] px-2.5 py-1 text-[11px] font-medium tracking-[0.06em] transition ${
                    language === value
                      ? "bg-[#0a0a0a] text-[#fefefc]"
                      : "text-[#8f8d8a] hover:text-[#0a0a0a]"
                  }`}
                >
                  {label}
                </button>
              ))}
            </div>
          </div>
        </header>

        <div className="shrink-0 px-5 pb-1 sm:px-7">
          <div className="mx-auto flex w-full max-w-[680px] flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
            <div
              className="chat-runner-group"
              role="radiogroup"
              aria-label={t.runnerLabel}
            >
              {RUNNERS.map((runner) => {
                const selected = mode === runner.id;
                return (
                  <button
                    key={runner.id}
                    type="button"
                    role="radio"
                    aria-checked={selected}
                    disabled={busy}
                    onClick={() => setMode(runner.id)}
                    className="chat-runner"
                  >
                    {runner.label}
                  </button>
                );
              })}
            </div>
            <p className="hidden max-w-[260px] truncate text-right text-[11px] leading-snug tracking-[-0.01em] text-[#9a978f] sm:block">
              {language === "en" ? activeRunner.hintEn : activeRunner.hintMk}
            </p>
          </div>
        </div>

        <div ref={threadRef} className="min-h-0 flex-1 overflow-auto">
          <div
            className={`mx-auto w-full max-w-[680px] px-5 sm:px-7 ${
              empty ? "flex h-full flex-col justify-center pb-10" : "py-10"
            }`}
          >
            {empty ? (
              <div>
                <div className="chat-empty-mark" aria-hidden />
                <p className="chat-empty-copy text-[11px] font-medium uppercase tracking-[0.2em] text-[#8f8d8a]">
                  {t.eyebrow}
                </p>
                <h1 className="chat-empty-title font-display mt-3 text-[clamp(2.35rem,5vw,3.1rem)] font-normal leading-[0.98] tracking-[-0.03em] text-[#0a0a0a]">
                  {t.title}
                </h1>
                <p className="chat-empty-copy mt-5 max-w-[32ch] text-[15px] leading-[1.65] tracking-[-0.01em] text-[#68655e]">
                  {t.subtitle}
                </p>
                <p className="mt-2 text-[12px] text-[#a8a59e] sm:hidden">
                  {language === "en" ? activeRunner.hintEn : activeRunner.hintMk}
                </p>
                <div className="mt-9 flex flex-wrap gap-2.5">
                  {suggestions.map((s) => (
                    <button
                      key={`${language}-${s.label}`}
                      type="button"
                      onClick={() => void send(s.q)}
                      className="chat-chip rounded-[6px] px-4 py-2 text-[13px] font-medium tracking-[-0.01em] text-[#3f3d38]"
                    >
                      {s.label}
                    </button>
                  ))}
                </div>
              </div>
            ) : (
              <div className="space-y-7">
                {messages.map((m) => (
                  <div key={m.id} className="msg-enter">
                    {m.role === "user" ? (
                      <div className="flex justify-end">
                        <div className="max-w-[78%] rounded-[20px] rounded-br-[5px] bg-[#0a0a0a] px-4 py-2.5 text-[14px] leading-relaxed tracking-[-0.01em] text-[#fefefc] shadow-[0_8px_20px_rgba(10,10,10,0.12)]">
                          {m.content}
                        </div>
                      </div>
                    ) : (
                      <div className="flex gap-3">
                        <div className="mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-[6px] bg-[#0a0a0a] text-[10px] font-semibold tracking-[0.04em] text-[#fefefc]">
                          V
                        </div>
                        <div
                          className={`min-w-0 flex-1 pt-0.5 ${
                            m.role === "error" ? "text-[14px] text-[#8a2f2f]" : ""
                          }`}
                        >
                          {m.mode ? (
                            <p className="mb-1.5 text-[10px] font-medium uppercase tracking-[0.14em] text-[#b0ada5]">
                              {RUNNERS.find((r) => r.id === m.mode)?.label ?? m.mode}
                            </p>
                          ) : null}
                          {m.trace && m.trace.some((t) => t.step === "tool_call") ? (
                            <ul className="mb-2 space-y-0.5 font-mono text-[11px] text-[#9a978f]">
                              {m.trace
                                .filter((t) => t.step === "tool_call")
                                .map((t, i) => (
                                  <li key={`${m.id}-tool-${i}`}>
                                    {String(t.tool)}
                                    {t.args
                                      ? ` ${JSON.stringify(t.args)}`
                                      : ""}
                                  </li>
                                ))}
                            </ul>
                          ) : null}
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

        <div className="chat-composer-wrap shrink-0 px-5 pb-6 pt-2 sm:px-7">
          <form
            onSubmit={onSubmit}
            className="chat-composer mx-auto flex max-w-[680px] items-end gap-2 rounded-[18px] p-2.5"
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
              className="max-h-[140px] min-h-[46px] flex-1 resize-none bg-transparent px-3.5 py-2.5 text-[14.5px] tracking-[-0.01em] outline-none placeholder:text-[#a8a59e]"
            />
            <button
              type="submit"
              disabled={busy || !question.trim()}
              aria-label={t.send}
              className="chat-send mb-0.5 inline-flex h-11 w-11 shrink-0 items-center justify-center rounded-[8px] bg-[#0a0a0a] text-[#fefefc] disabled:opacity-30"
            >
              <SendIcon />
            </button>
          </form>
          <div className="mx-auto mt-2.5 flex max-w-[680px] justify-end px-1 text-[11px] sm:hidden">
            <Link href="/eval" className="link-quiet text-[#8f8d8a]">
              Scoreboard
            </Link>
          </div>
        </div>
      </div>

      <aside className="chat-aside hidden w-[340px] shrink-0 flex-col border-l border-[#d5e3d9] xl:flex">
        <div className="flex h-[3.6rem] items-center justify-between gap-3 px-5">
          <span className="text-[11px] font-medium uppercase tracking-[0.18em] text-[#6d8072]">
            {t.sources}
          </span>
          {board.length > 0 ? (
            <span className="rounded-[5px] bg-[#fefefc]/85 px-2.5 py-0.5 text-[11px] font-medium tabular-nums text-[#5f7264] ring-1 ring-[#d0dfd4]">
              {board.length}
            </span>
          ) : null}
        </div>
        <div className="min-h-0 flex-1 overflow-auto px-3.5 pb-5">
          {board.length === 0 ? (
            <div className="chat-aside-empty">
              <div className="chat-aside-empty-icon" aria-hidden>
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
                  <path
                    d="M7 4h7l3 3v13H7V4Z"
                    stroke="currentColor"
                    strokeWidth="1.6"
                  />
                  <path
                    d="M14 4v3h3"
                    stroke="currentColor"
                    strokeWidth="1.6"
                  />
                  <path
                    d="M10 12h4M10 15h4"
                    stroke="currentColor"
                    strokeWidth="1.6"
                    strokeLinecap="round"
                  />
                </svg>
              </div>
              <p className="max-w-[24ch] text-[13px] leading-relaxed tracking-[-0.01em] text-[#6d8072]">
                {t.sourcesEmpty}
              </p>
            </div>
          ) : (
            <ol className="space-y-2.5">
              {board.map((c, i) => {
                const pct = Math.round(relevance(c.score) * 100);
                return (
                  <li
                    key={`${c.doc_id}-${c.chunk_index}-${c.language}`}
                    className="chat-source-card msg-enter rounded-[12px] border border-[#d5e3d9] bg-[#fefefc]/88 p-3.5 shadow-[0_1px_2px_rgba(13,16,22,0.03)] backdrop-blur-sm"
                  >
                    <div className="flex items-start justify-between gap-2">
                      <span className="font-mono text-[11px] tabular-nums text-[#b4c4b8]">
                        {String(i + 1).padStart(2, "0")}
                      </span>
                      <span className="rounded-[4px] bg-[#e8f1eb] px-2 py-0.5 text-[10px] font-medium uppercase tracking-[0.06em] text-[#5f7264]">
                        {t.sourceLabels[c.source] ?? c.source}
                      </span>
                    </div>
                    <p className="mt-2.5 text-[13px] font-medium leading-snug tracking-tight text-[#0a0a0a]">
                      {c.title || c.doc_id}
                    </p>
                    <p className="mt-1 truncate font-mono text-[11px] text-[#839589]">
                      {c.doc_id}
                    </p>
                    {typeof c.score === "number" ? (
                      <div className="mt-3.5">
                        <div className="mb-1 flex items-center justify-between text-[11px] text-[#839589]">
                          <span>{t.match}</span>
                          <span className="font-mono tabular-nums text-[#005032]">
                            {pct}%
                          </span>
                        </div>
                        <div className="h-[3px] overflow-hidden rounded-full bg-[#d9e6dd]">
                          <div
                            className="h-full rounded-full bg-[#005032] transition-[width] duration-500 ease-out"
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
