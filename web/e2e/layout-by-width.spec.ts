import { expect, test, type Page } from "@playwright/test";

import { signIn } from "./sign-in";
import { TEST_BUYER, TEST_USER } from "./test-user";

// These run in desktop Chrome, which has a mouse. The layout must follow the
// screen width anyway, so a narrow window gets the phone layout.
const bottomBarHome = (page: Page) =>
  page.getByRole("navigation", { name: "Main" }).getByRole("link", { name: "Home" });

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

  // The chat screen has a fixed height that depends on the header and the bottom bar.
  test("keeps the message box in a chat above the bottom bar", async ({ browser, context, page, baseURL }) => {
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
    const messageBox = await page.getByRole("textbox", { name: "Message" }).boundingBox();
    const bottomBar = await page.getByRole("navigation", { name: "Main" }).boundingBox();
    expect(messageBox!.y + messageBox!.height).toBeLessThanOrEqual(bottomBar!.y);
  });
});
