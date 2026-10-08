import createClient, { type Middleware } from "openapi-fetch";

import type { paths } from "./schema";

// Typed API client. Paths and response types come from contracts/openapi.yaml
// (regenerate with `pnpm api:types`). Requests are relative ("/api/..."), so they go
// through the Next.js proxy; use this from client components.
export const api = createClient<paths>({ baseUrl: "" });

const SAFE_METHODS = new Set(["GET", "HEAD", "OPTIONS", "TRACE"]);
// allauth's config endpoint sets the csrftoken cookie if the browser doesn't have one yet.
const CSRF_COOKIE_URL = "/api/auth/browser/v1/config";

function readCookie(name: string): string | undefined {
  const prefix = `${name}=`;
  const cookie = document.cookie.split("; ").find((c) => c.startsWith(prefix));
  return cookie ? decodeURIComponent(cookie.slice(prefix.length)) : undefined;
}

/** The CSRF token for an unsafe request, fetching the cookie first if the browser has none.
 * Also used by lib/auth.ts, whose allauth endpoints aren't in the contract. */
export async function csrfToken(): Promise<string | undefined> {
  if (!readCookie("csrftoken")) await fetch(CSRF_COOKIE_URL);
  return readCookie("csrftoken");
}

// Django checks CSRF on every unsafe request from a signed-in session: it compares the
// X-CSRFToken header with the csrftoken cookie.
const csrf: Middleware = {
  async onRequest({ request }) {
    if (SAFE_METHODS.has(request.method)) return request;
    const token = await csrfToken();
    if (token) request.headers.set("X-CSRFToken", token);
    return request;
  },
};

api.use(csrf);

/** The first message under `key` in a DRF error body ({"key": "..."} or {"key": ["..."]}). */
export function errorMessage(body: unknown, key: string): string | undefined {
  if (!body || typeof body !== "object") return undefined;
  const value = (body as Record<string, unknown>)[key];
  if (Array.isArray(value)) return String(value[0]);
  return typeof value === "string" ? value : undefined;
}
