import { expect, test, type Page } from "@playwright/test";

import { postListing } from "./listings";
import { signIn } from "./sign-in";
import { TEST_BUYER, TEST_USER } from "./test-user";

// These run in desktop Chrome, which has a mouse. The layout must follow the
// screen width anyway, so a narrow window gets the phone layout.
const bottomBar = (page: Page) => page.getByRole("navigation", { name: "Main" });
const bottomBarHome = (page: Page) => bottomBar(page).getByRole("link", { name: "Home" });
const siteSearch = (page: Page) => page.getByRole("searchbox", { name: "Search listings" });

test.describe("a narrow window with a mouse", () => {
  test.use({ viewport: { width: 760, height: 820 } });

  test("gets the phone layout with the bottom bar", async ({ page }) => {
    await page.goto("/");
    await expect(bottomBarHome(page)).toBeVisible();
  });
});

test.describe("a wide touchscreen", () => {
  test.use({ viewport: { width: 1180, height: 820 }, hasTouch: true, isMobile: true });

  test("gets the desktop header and no bottom bar", async ({ page }) => {
    await page.goto("/");
    await expect(page.getByRole("navigation", { name: "Main" }).getByRole("link", { name: "Deals" })).toBeVisible();
    await expect(bottomBarHome(page)).toHaveCount(0);
  });
});

test.describe("a phone", () => {
  test.use({ viewport: { width: 390, height: 844 }, hasTouch: true, isMobile: true });

  // iPhones zoom the page when a focused field has text smaller than 16px.
  for (const path of ["/", "/account/signup"]) {
    test(`shows every typing field on ${path} at 16px or larger`, async ({ page }) => {
      await page.goto(path);
      const fields = page.locator("input, select, textarea");
      await expect(fields.first()).toBeVisible();
      const sizes = await fields.evaluateAll((all) => all.map((field) => parseFloat(getComputedStyle(field).fontSize)));
      expect(Math.min(...sizes)).toBeGreaterThanOrEqual(16);
    });
  }

  test("has a one-row header and Sell in the middle of the bottom bar", async ({ context, page, baseURL }) => {
    await signIn(context, baseURL!);
    await page.goto("/deals");
    // Inbox may carry an unread count after its name, so it is matched by its start.
    await expect(bottomBar(page).getByRole("link")).toHaveText([/^Home$/, /^Deals$/, /^Sell$/, /^Inbox/, /^Profile$/]);

    // Logo, search and bell share one row; Log out and the school switcher are gone.
    const logo = await page.getByRole("link", { name: "Tanu home" }).boundingBox();
    const search = await siteSearch(page).boundingBox();
    const bell = await page.getByRole("link", { name: /^Notifications/ }).boundingBox();
    const middle = (box: { y: number; height: number } | null) => box!.y + box!.height / 2;
    expect(Math.abs(middle(search) - middle(logo))).toBeLessThan(4);
    expect(Math.abs(middle(bell) - middle(logo))).toBeLessThan(4);
    await expect(page.getByRole("button", { name: "Log out" })).toHaveCount(0);
    await expect(page.getByRole("combobox", { name: "School marketplace" })).toHaveCount(0);

    // Log out lives on Profile.
    await bottomBar(page).getByRole("link", { name: "Profile" }).click();
    await expect(page.getByRole("button", { name: "Log out" })).toBeVisible();
  });

  test("shows Sell, Edit listing and Meetup preferences as focused screens", async ({ context, page, baseURL }) => {
    await signIn(context, baseURL!);
    const listingId = await postListing(context, baseURL!, { title: "E2E focused screen lamp", category: "electronics" });
    for (const [path, title, back] of [
      ["/sell", "Sell an item", "/"],
      [`/listings/${listingId}/edit`, "Edit listing", "/listings/mine"],
      ["/profile/meetup", "Meetup preferences", "/profile"],
      ["/profile/edit", "Edit profile", "/profile"],
    ]) {
      await page.goto(path);
      await expect(page.getByRole("heading", { level: 1, name: title })).toBeVisible();
      await expect(page.getByRole("link", { name: /^Back to/ })).toHaveAttribute("href", back);
      await expect(siteSearch(page)).toBeHidden();
      await expect(bottomBar(page)).toHaveCount(0);
      await expect(page.getByRole("contentinfo")).toHaveCount(0);
    }
  });

  // A chat is a focused screen: it fills the phone screen, with the message box at the bottom.
  test("fills the screen with a chat and keeps the message box in view", async ({ browser, context, page, baseURL }) => {
    const buyerContext = await browser.newContext({ baseURL });
    await signIn(buyerContext, baseURL!, TEST_BUYER);
    const csrf = (await buyerContext.cookies()).find((c) => c.name === "csrftoken")?.value;
    const headers = { "X-CSRFToken": csrf!, Origin: baseURL! };
    const started = await buyerContext.request.post("/api/conversations/", { data: { username: TEST_USER.username }, headers });
    const conversationId = ((await started.json()) as { id: number }).id;
    expect((await buyerContext.request.post(`/api/conversations/${conversationId}/messages/`, { data: { body: "Is this still available?" }, headers })).ok()).toBe(true);
    await buyerContext.close();

    await signIn(context, baseURL!);
    await page.goto(`/inbox/${conversationId}`);
    await expect(page.getByRole("link", { name: "Back to inbox" })).toBeVisible();
    await expect(siteSearch(page)).toBeHidden();
    await expect(bottomBar(page)).toHaveCount(0);
    const messageBox = await page.getByRole("textbox", { name: "Message" }).boundingBox();
    expect(messageBox!.y + messageBox!.height).toBeLessThanOrEqual(844);
    // The page itself doesn't scroll; only the message list does.
    expect(await page.evaluate(() => document.documentElement.scrollHeight)).toBeLessThanOrEqual(844);
  });

  test("shows a branded 404 with a way back Home", async ({ page }) => {
    const response = await page.goto("/no-such-page");
    expect(response!.status()).toBe(404);
    await expect(page).toHaveTitle("Page not found · Tanu");
    await expect(page.getByRole("heading", { level: 1, name: "This page isn’t here" })).toBeVisible();
    await page.getByRole("link", { name: "Back to Home" }).click();
    await expect(page).toHaveURL("/");
  });
});
