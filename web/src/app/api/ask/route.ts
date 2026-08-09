import { proxyToBackend } from "@/lib/server/backend";

export async function POST(request: Request) {
  const body = await request.text();
  return proxyToBackend("/v1/ask", {
    method: "POST",
    headers: { "content-type": "application/json" },
    body,
  });
}
