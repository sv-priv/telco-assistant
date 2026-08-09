import { proxyToBackend } from "@/lib/server/backend";

export async function GET() {
  return proxyToBackend("/v1/eval/catalog", { method: "GET" });
}
