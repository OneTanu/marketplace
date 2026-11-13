import { expect, test } from "@playwright/test";

import { AUTH, signIn } from "./sign-in";
import { TEST_USER } from "./test-user";

// Each page proves it rendered (a level-1 heading, or the signed-in username on Profile) and
// that the nav marks it current. Kept loose on purpose so page redesigns don't break it.
const SHELL_PAGES = [
  { path: "/" },
  { path: "/sell", heading: "Sell an item" },
  { path: "/deals", heading: "Deals", navLabel: "Deals" },
  { path: "/profile", text: `@${TEST_USER.username}` },
];

test("signs in through the proxy and loads the app shell", async ({ context, page, baseURL }) => {
  const api = context.request;

  expect((await api.get(`${AUTH}/auth/session`)).status()).toBe(401);

  await signIn(context, baseURL!);

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

  // Desktop: the account menu holds Profile, My listings, Saved and Log out.
  await page.goto("/deals");
  await page.getByRole("button", { name: "Account menu" }).click();
  const menu = page.getByRole("menu", { name: "Account menu" });
  await expect(menu.getByRole("menuitem")).toHaveText(["Profile", "My listings", "Saved", "Log out"]);
  await menu.getByRole("menuitem", { name: "Saved" }).click();
  await expect(page).toHaveURL("/profile/saved");
  await expect(page.getByRole("heading", { level: 1, name: "Saved" })).toBeVisible();
  await expect(menu).toHaveCount(0);

  // Saved used to be a profile tab; the old link lands on its page.
  await page.goto("/profile?tab=bookmarks");
  await expect(page).toHaveURL("/profile/saved");

  // Escape closes the menu and gives focus back to its button.
  const menuButton = page.getByRole("button", { name: "Account menu" });
  await menuButton.focus();
  await page.keyboard.press("Enter");
  await expect(menu.getByRole("menuitem", { name: "Profile" })).toBeFocused();
  await page.keyboard.press("Escape");
  await expect(menu).toHaveCount(0);
  await expect(menuButton).toBeFocused();

  await menuButton.click();
  await menu.getByRole("menuitem", { name: "Log out" }).click();
  await expect(page).toHaveURL("/");
  await expect(page.getByRole("link", { name: "Join Tanu" })).toBeVisible();
  expect((await api.get(`${AUTH}/auth/session`)).status()).toBe(401);
});
