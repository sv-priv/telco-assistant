/** Server-only backend URL + API key (never expose to the browser). */

const DEFAULT_API_URL = "http://localhost:8000";

export function backendBaseUrl(): string {
  const raw =
    process.env.TELCO_API_URL?.trim().replace(/\/$/, "") ||
    process.env.API_URL?.trim().replace(/\/$/, "") ||
    DEFAULT_API_URL;
  if (raw.startsWith("http://") || raw.startsWith("https://")) {
    return raw;
  }
  // Render fromService host / RENDER_EXTERNAL_HOSTNAME is hostname-only.
  return `https://${raw}`;
}

/** Hostname only — safe to show in error messages. */
export function backendHostForLogs(): string {
  try {
    return new URL(backendBaseUrl()).host;
  } catch {
    return "(invalid TELCO_API_URL)";
  }
}

export function backendHeaders(
  init?: HeadersInit,
): Record<string, string> {
  const headers: Record<string, string> = {
    accept: "application/json",
  };
  if (init) {
    const incoming = new Headers(init);
    incoming.forEach((value, key) => {
      headers[key] = value;
    });
  }
  const key = process.env.TELCO_API_KEY;
  if (key) {
    headers["X-API-Key"] = key;
  }
  return headers;
}

function problemResponse(status: number, detail: string): Response {
  return new Response(
    JSON.stringify({
      type: "about:blank",
      title: status >= 500 ? "Bad Gateway" : "Request Error",
      status,
      detail,
    }),
    {
      status,
      headers: { "content-type": "application/problem+json" },
    },
  );
}

export async function proxyToBackend(
  path: string,
  init?: RequestInit,
): Promise<Response> {
  const base = backendBaseUrl();
  const host = backendHostForLogs();
  const url = `${base}${path.startsWith("/") ? path : `/${path}`}`;
  const headers = backendHeaders(init?.headers);
  const hasKey = Boolean(process.env.TELCO_API_KEY);

  let res: Response;
  try {
    res = await fetch(url, {
      ...init,
      headers,
      cache: "no-store",
    });
  } catch (err) {
    const message = err instanceof Error ? err.message : "fetch failed";
    return problemResponse(
      502,
      `Cannot reach API host "${host}" (${message}). Set TELCO_API_URL to the telco-api public URL (https://telco-api-….onrender.com), not the web URL. Key set: ${hasKey}.`,
    );
  }

  const body = await res.text();
  const contentType = res.headers.get("content-type") ?? "";

  // Upstream returned HTML (wrong host, Next 404, Render error page).
  if (
    body.trimStart().startsWith("<!") ||
    contentType.includes("text/html")
  ) {
    return problemResponse(
      502,
      `API host "${host}" returned HTML instead of JSON for ${path} (status ${res.status}). TELCO_API_URL is probably the web app or a dead service — use the telco-api public URL. Key set: ${hasKey}.`,
    );
  }

  if (!body && res.status >= 400) {
    return problemResponse(
      res.status,
      `API host "${host}" returned empty ${res.status} for ${path}. Key set: ${hasKey}.`,
    );
  }

  return new Response(body, {
    status: res.status,
    headers: {
      "content-type": contentType || "application/json",
    },
  });
}
