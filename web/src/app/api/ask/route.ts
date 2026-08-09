import { backendHostForLogs, proxyToBackend } from "@/lib/server/backend";

/** Safe diagnostics for Render misconfig (no secrets). */
export async function GET() {
  return Response.json({
    ok: true,
    backend_host: backendHostForLogs(),
    telco_api_url_set: Boolean(
      process.env.TELCO_API_URL?.trim() || process.env.API_URL?.trim(),
    ),
    telco_api_key_set: Boolean(process.env.TELCO_API_KEY?.trim()),
  });
}

export async function POST(request: Request) {
  const body = await request.text();
  return proxyToBackend("/v1/ask", {
    method: "POST",
    headers: { "content-type": "application/json" },
    body,
  });
}
