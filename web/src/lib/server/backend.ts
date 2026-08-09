/** Server-only backend URL + API key (never expose to the browser). */

const DEFAULT_API_URL = "http://localhost:8000";

export function backendBaseUrl(): string {
  const raw =
    process.env.TELCO_API_URL?.replace(/\/$/, "") ||
    process.env.API_URL?.replace(/\/$/, "") ||
    DEFAULT_API_URL;
  if (raw.startsWith("http://") || raw.startsWith("https://")) {
    return raw;
  }
  // Render fromService `host` is hostname-only.
  return `https://${raw}`;
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

export async function proxyToBackend(
  path: string,
  init?: RequestInit,
): Promise<Response> {
  const url = `${backendBaseUrl()}${path.startsWith("/") ? path : `/${path}`}`;
  const headers = backendHeaders(init?.headers);
  const res = await fetch(url, {
    ...init,
    headers,
    cache: "no-store",
  });
  const body = await res.text();
  const contentType = res.headers.get("content-type") ?? "application/json";
  return new Response(body, {
    status: res.status,
    headers: { "content-type": contentType },
  });
}
