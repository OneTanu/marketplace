import { expect, type BrowserContext } from "@playwright/test";

import { TEST_USER, type TestUser } from "./test-user";

// allauth headless browser API, reached through the Next.js /api proxy. No trailing slashes.
export const AUTH = "/api/auth/browser/v1";

/**
 * Signs a test user (TEST_USER unless given) in through the proxy. Uses context.request, which
 * shares the browser context's cookie jar, so pages loaded afterwards send the session cookie.
 */
export async function signIn(context: BrowserContext, baseURL: string, user: TestUser = TEST_USER) {
  const api = context.request;

  expect((await api.get(`${AUTH}/config`)).ok()).toBe(true);
  const csrfToken = (await context.cookies()).find((c) => c.name === "csrftoken")?.value;
  expect(csrfToken, "csrftoken cookie set by /config").toBeTruthy();

  const login = await api.post(`${AUTH}/auth/login`, {
    data: { email: user.email, password: user.password },
    // A browser sends its Origin on POST; Django checks it against CSRF_TRUSTED_ORIGINS.
    headers: { "X-CSRFToken": csrfToken!, Origin: baseURL },
  });
  expect(login.status(), await login.text()).toBe(200);
}
