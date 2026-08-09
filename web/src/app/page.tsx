import Link from "next/link";
import { BrandWordmark } from "@/components/LogoMark";
import { NetworkCanvas } from "@/components/NetworkCanvas";

const TOPICS = [
  {
    title: "Plans & pricing",
    body: "S, M, L, and XL: what’s included, monthly price, speed, and fair-use limits.",
  },
  {
    title: "Roaming",
    body: "Country zones, daily rates, and roaming packs for EU and world travel.",
  },
  {
    title: "Bills & add-ons",
    body: "How to read a monthly invoice, extra data packs, and common charges.",
  },
  {
    title: "Devices & network",
    body: "Handsets, coverage basics, and day-to-day support procedures.",
  },
];

export default function HomePage() {
  return (
    <div className="landing relative min-h-dvh bg-[#fefefc] text-[#0a0a0a]">
      <nav className="relative z-20 mx-auto flex h-16 w-full max-w-6xl items-center justify-between px-6 sm:px-10">
        <Link href="/" className="inline-flex items-center">
          <BrandWordmark size={18} />
        </Link>
        <div className="flex items-center gap-6 text-[13px]">
          <a
            href="#covers"
            className="link-quiet hidden text-[#68655e] sm:inline"
          >
            Coverage
          </a>
          <Link href="/eval" className="link-quiet hidden text-[#68655e] sm:inline">
            Scoreboard
          </Link>
          <Link href="/chat" className="link-quiet font-medium text-[#0a0a0a]">
            Open chat
          </Link>
        </div>
      </nav>

      <main>
        {/* Full-viewport hero + Three.js field */}
        <section className="landing-hero relative flex min-h-[calc(100dvh-4rem)] flex-col justify-center overflow-hidden">
          <div className="pointer-events-none absolute inset-0">
            <NetworkCanvas />
            <div className="absolute inset-0 bg-[linear-gradient(105deg,#fefefc_0%,#fefefc_32%,rgba(254,254,252,0.55)_52%,rgba(254,254,252,0.08)_100%)]" />
          </div>

          <div className="relative z-10 mx-auto w-full max-w-6xl px-6 py-16 sm:px-10 sm:py-20">
            <div className="max-w-xl">
              <h1 className="font-display text-[clamp(2.75rem,7vw,4.75rem)] font-normal leading-[0.95] tracking-[-0.02em]">
                <span className="block text-[#0a0a0a]">Ask me.</span>
                <span className="mt-2 block text-[#68655e]">
                  Find out what you need.
                </span>
              </h1>
              <p className="mt-7 max-w-md text-[16px] leading-[1.55] tracking-[-0.01em] text-[#68655e]">
                Plans, roaming, bills: answered from operator docs, with
                citations you can open and check.
              </p>
              <div className="mt-10 flex flex-wrap items-center gap-x-6 gap-y-3">
                <Link
                  href="/chat"
                  className="cta inline-flex items-center gap-2 rounded-[2px] bg-[#0a0a0a] px-4 py-2.5 text-[13px] font-medium text-[#fefefc]"
                >
                  Start asking
                  <span aria-hidden className="cta-arrow">
                    →
                  </span>
                </Link>
                <a
                  href="#covers"
                  className="link-quiet text-[13px] text-[#68655e]"
                >
                  See what it covers
                </a>
              </div>
            </div>
          </div>
        </section>

        <section
          id="covers"
          className="landing-section border-y border-[#e1dfda] bg-[#fbfbf9]"
        >
          <div className="mx-auto max-w-6xl px-6 py-16 sm:px-10 sm:py-20">
            <h2 className="font-display max-w-[14ch] text-[1.65rem] font-normal tracking-[-0.01em] sm:text-[1.9rem]">
              What customers ask about.
            </h2>

            <ul className="mt-12 grid gap-3 sm:grid-cols-2 sm:gap-4">
              {TOPICS.map((topic) => (
                <li key={topic.title}>
                  <Link href="/chat" className="topic-card group">
                    <h3 className="text-[15px] font-medium tracking-tight text-[#0a0a0a] transition-colors duration-200 sm:text-[16px]">
                      {topic.title}
                    </h3>
                    <p className="mt-2 text-[13px] leading-relaxed tracking-[-0.01em] text-[#68655e] sm:text-[14px]">
                      {topic.body}
                    </p>
                    <span
                      aria-hidden
                      className="mt-5 inline-flex items-center gap-1 text-[12px] font-medium text-[#0a0a0a]"
                    >
                      Ask about this
                      <span className="topic-card-arrow">→</span>
                    </span>
                  </Link>
                </li>
              ))}
            </ul>
          </div>
        </section>

        <section className="landing-section mx-auto max-w-6xl px-6 py-16 sm:px-10 sm:py-20">
          <div className="max-w-xl">
            <h2 className="font-display max-w-[12ch] text-[1.65rem] font-normal tracking-[-0.01em] sm:text-[1.9rem]">
              Answers you can verify.
            </h2>
            <p className="mt-4 max-w-[36ch] text-[15px] leading-relaxed tracking-[-0.01em] text-[#68655e]">
              Every reply shows the documents it used. If the docs don’t cover
              the question, it says so instead of inventing a price.
            </p>
            <div className="mt-8">
              <Link
                href="/chat"
                className="cta inline-flex items-center gap-2 rounded-[2px] bg-[#0a0a0a] px-4 py-2.5 text-[13px] font-medium text-[#fefefc]"
              >
                Try the assistant
                <span aria-hidden className="cta-arrow">
                  →
                </span>
              </Link>
            </div>
          </div>
        </section>

        <footer className="border-t border-[#e1dfda]">
          <div className="mx-auto flex max-w-6xl flex-col gap-3 px-6 py-7 text-[12px] text-[#8f8d8a] sm:flex-row sm:items-center sm:justify-between sm:px-10">
            <BrandWordmark size={16} />
            <p className="max-w-md text-[11px] leading-relaxed sm:text-right">
              Demo operator with synthetic product data.
            </p>
          </div>
        </footer>
      </main>
    </div>
  );
}
