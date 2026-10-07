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

// Django checks CSRF on every unsafe request from a signed-in session: it compares the
// X-CSRFToken header with the csrftoken cookie.
const csrf: Middleware = {
  async onRequest({ request }) {
    if (SAFE_METHODS.has(request.method)) return request;
    if (!readCookie("csrftoken")) await fetch(CSRF_COOKIE_URL);
    const token = readCookie("csrftoken");
    if (token) request.headers.set("X-CSRFToken", token);
    return request;
  },
};

api.use(csrf);
