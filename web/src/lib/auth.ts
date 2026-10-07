export type AuthError = { message: string; field?: string };

type AllauthError = { message?: string; code?: string; param?: string };
type AllauthResponse = {
  status?: number;
  data?: { user?: { email?: string }; flows?: { id: string; is_pending?: boolean }[] };
  errors?: AllauthError[];
  meta?: { is_authenticated?: boolean };
};

function cookie(name: string) {
  return document.cookie.split("; ").find((part) => part.startsWith(`${name}=`))?.split("=").slice(1).join("=");
}

async function csrfToken() {
  let token = cookie("csrftoken");
  if (!token) {
    await fetch("/api/auth/browser/v1/config", { credentials: "same-origin" });
    token = cookie("csrftoken");
  }
  return token;
}

export async function authRequest(path: string, init: RequestInit = {}) {
  const method = init.method?.toUpperCase() ?? "GET";
  const headers = new Headers(init.headers);
  if (method !== "GET" && method !== "HEAD") {
    const csrf = await csrfToken();
    if (csrf) headers.set("X-CSRFToken", decodeURIComponent(csrf));
  }
  if (init.body) headers.set("Content-Type", "application/json");
  const response = await fetch(`/api/auth/browser/v1/${path}`, { ...init, headers, credentials: "same-origin" });
  const body = (await response.json().catch(() => ({}))) as AllauthResponse;
  return { response, body };
}

export function errorsFrom(body: AllauthResponse, fallback: string): AuthError[] {
  if (!body.errors?.length) return [{ message: fallback }];
  return body.errors.map((error) => ({ message: error.message ?? fallback, field: error.param }));
}

export function pendingFlow(body: AllauthResponse, id: string) {
  return body.data?.flows?.some((flow) => flow.id === id && flow.is_pending);
}
