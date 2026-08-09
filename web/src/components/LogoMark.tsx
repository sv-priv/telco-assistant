/** Vardar — minimal “V” monogram. */
export function LogoMark({
  size = 22,
  tight = false,
}: {
  size?: number;
  tight?: boolean;
}) {
  return (
    <svg
      width={size}
      height={size}
      viewBox={tight ? "6 6 20 22" : "0 0 32 32"}
      fill="none"
      aria-hidden
      className="shrink-0"
    >
      <path
        d="M8 8L16 25.5L24 8"
        stroke="currentColor"
        strokeWidth="2.4"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

/** Logo V + “ardar Mobile” as one wordmark. */
export function BrandWordmark({
  size = 18,
  className = "",
}: {
  size?: number;
  className?: string;
}) {
  return (
    <span
      className={`inline-flex items-center text-[13px] font-medium tracking-tight text-current ${className}`}
      aria-label="Vardar Mobile"
    >
      <LogoMark size={size} tight />
      <span className="-ml-[0.08em] translate-y-[0.5px]">ardar&nbsp;Mobile</span>
    </span>
  );
}
