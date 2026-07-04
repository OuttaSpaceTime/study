import { NextResponse, type NextRequest } from "next/server";

// Host allowlist duplicated from lib/security.ts ALLOWED_HOSTS as literals —
// proxy runs isolated from app modules and must not rely on shared state.
// This gate covers pages too, so a DNS-rebound origin can never read the CSRF
// token out of /study HTML or pull /api/index.
const ALLOWED_HOSTS = new Set(["localhost:4777", "127.0.0.1:4777", "[::1]:4777"]);

export function proxy(request: NextRequest) {
  const host = request.headers.get("host") ?? "";
  if (!ALLOWED_HOSTS.has(host)) {
    return new NextResponse("Forbidden", { status: 403 });
  }
  return NextResponse.next();
}
