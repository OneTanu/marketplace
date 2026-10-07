import { expect, test } from "@playwright/test";

import { TEST_USER } from "./test-user";

// allauth headless browser API, reached through the Next.js /api proxy. No trailing slashes.
const AUTH = "/api/auth/browser/v1";

// Each page proves it rendered (a level-1 heading, or the signed-in username on Profile) and
// that the nav marks it current. Kept loose on purpose so page redesigns don't break it.
const SHELL_PAGES = [
  { path: "/", navLabel: "Home" },
  { path: "/sell", heading: "Sell an item", navLabel: "Sell" },
  { path: "/profile", text: `@${TEST_USER.username}` },
];

test("signs in through the proxy and loads the app shell", async ({ context, page, baseURL }) => {
  // context.request shares the browser context's cookie jar, so the session cookie set by
  // login is sent by the pages loaded afterwards.
  const api = context.request;

  expect((await api.get(`${AUTH}/config`)).ok()).toBe(true);
  const csrfToken = (await context.cookies()).find((c) => c.name === "csrftoken")?.value;
  expect(csrfToken, "csrftoken cookie set by /config").toBeTruthy();

  expect((await api.get(`${AUTH}/auth/session`)).status()).toBe(401);

  const login = await api.post(`${AUTH}/auth/login`, {
    data: { email: TEST_USER.email, password: TEST_USER.password },
    // A browser sends its Origin on POST; Django checks it against CSRF_TRUSTED_ORIGINS.
    headers: { "X-CSRFToken": csrfToken!, Origin: baseURL! },
  });
  expect(login.status(), await login.text()).toBe(200);

  const session = await api.get(`${AUTH}/auth/session`);
  expect(session.status()).toBe(200);
  expect((await session.json()).data.user.email).toBe(TEST_USER.email);

  for (const { path, heading, navLabel, text } of SHELL_PAGES) {
    await page.goto(path);
    await expect(page.getByRole("heading", { level: 1, name: heading }).first()).toBeVisible();
    if (text) await expect(page.getByText(text, { exact: true }).first()).toBeVisible();

    if (navLabel) {
      const nav = page.getByRole("navigation", { name: "Main" });
      await expect(nav.getByRole("link", { name: navLabel, exact: true })).toHaveAttribute(
        "aria-current",
        "page",
      );
    }

    // The page itself (not just the test's request context) is signed in through the proxy.
    const status = await page.evaluate(async (url) => (await fetch(url)).status, `${AUTH}/auth/session`);
    expect(status, `session status from ${path}`).toBe(200);
  }
});
