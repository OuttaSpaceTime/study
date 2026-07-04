// Server-only gate for mutating routes. This app executes code on POST, so
// every mutating handler calls assertLocalMutation first. Threat model:
// drive-by CSRF from malicious websites and DNS rebinding — not the local user.
import crypto from "node:crypto";

// Per-boot token. Stashed on globalThis because Next dev compiles routes as
// separate entrypoints that may re-instantiate this module.
const g = globalThis as typeof globalThis & { __studyCsrf?: string };
export const CSRF_TOKEN: string = (g.__studyCsrf ??= crypto
  .randomBytes(16)
  .toString("hex"));

const PORT = process.env.PORT ?? "3000";

// Duplicated as literals in proxy.ts (proxy cannot share module state).
export const ALLOWED_HOSTS = new Set([
  `localhost:${PORT}`,
  `127.0.0.1:${PORT}`,
  `[::1]:${PORT}`,
]);

const ALLOWED_ORIGINS = new Set([...ALLOWED_HOSTS].map((h) => `http://${h}`));

function forbidden(reason: string): Response {
  return new Response(`Forbidden: ${reason}`, { status: 403 });
}

/** Returns a 403 Response to send back, or null if the request may proceed.
 *  Origin "null" (sandboxed iframes have an opaque origin) counts as present
 *  and invalid — that plus the unreadable token is what keeps rendered
 *  challenge output from calling back into the API. Absent Origin is allowed
 *  so curl and the study skill's scripts keep working. */
export function assertLocalMutation(req: Request): Response | null {
  const host = req.headers.get("host") ?? "";
  if (!ALLOWED_HOSTS.has(host)) return forbidden("host");
  const origin = req.headers.get("origin");
  if (origin !== null && !ALLOWED_ORIGINS.has(origin)) return forbidden("origin");
  if (req.headers.get("x-study-csrf") !== CSRF_TOKEN) return forbidden("token");
  return null;
}
