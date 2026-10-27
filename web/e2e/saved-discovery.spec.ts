import { randomUUID } from "node:crypto";

import { expect, test, type BrowserContext } from "@playwright/test";

import { postListing } from "./listings";
import { signIn } from "./sign-in";
import { TEST_BUYER, TEST_USER } from "./test-user";

type Notification = { kind: string; title: string; link: string };

async function notifications(context: BrowserContext) {
  const response = await context.request.get("/api/notifications/");
  expect(response.ok()).toBe(true);
  return (await response.json()) as Notification[];
}

/** A word no other test's listing contains, so only this test's listings match its searches. */
const token = () => `zz${randomUUID().slice(0, 8)}`;

test("bookmarks a listing, saves a search, and is alerted once to a new match", async ({ browser, page, context, baseURL }) => {
  const sellerContext = await browser.newContext({ baseURL });
  await signIn(sellerContext, baseURL!, TEST_USER);
  await signIn(context, baseURL!, TEST_BUYER);

  // 1. Bookmark a listing from its page.
  const lampTitle = `E2E lamp ${token()}`;
  const lampId = await postListing(sellerContext, baseURL!, { title: lampTitle, category: "electronics" });
  await page.goto(`/listings/${lampId}`);
  const save = page.getByRole("button", { name: "Save listing" });
  await expect(save).toHaveAttribute("aria-pressed", "false");
  await save.click();
  await expect(page.getByRole("button", { name: "Remove saved listing" })).toHaveAttribute("aria-pressed", "true");

  // The feed shows it saved too.
  await page.goto(`/search?search=${encodeURIComponent(lampTitle)}`);
  const card = page.getByRole("list", { name: "Listings" }).getByRole("article").filter({ hasText: lampTitle });
  await expect(card.getByRole("button", { name: "Remove saved listing" })).toBeVisible();

  // 2. It's in the profile's Bookmarks tab.
  await page.goto("/profile");
  await page.getByRole("tab", { name: "Bookmarks" }).click();
  await expect(page.getByRole("list", { name: "Saved listings" }).getByText(lampTitle)).toBeVisible();

  // 3. Save a filtered search.
  const word = token();
  await page.goto(`/search?search=${word}&category=men-jeans&max_price=40`);
  await page.getByRole("button", { name: "Save this search" }).click();
  const name = page.getByLabel("Name");
  await expect(name).toHaveValue(`“${word}” · Men › Jeans · Under $40`);
  await name.fill(`Jeans ${word}`);
  await expect(page.getByLabel("Notify me about new listings")).toBeChecked();
  await page.getByRole("button", { name: "Save search", exact: true }).click();
  await expect(page.getByRole("status").filter({ hasText: `Saved as “Jeans ${word}”` })).toBeVisible();
  // Reloading still knows it's saved.
  await page.reload();
  await expect(page.getByText(`Saved as “Jeans ${word}”`)).toBeVisible();

  // 4. Another student posts a matching listing (and one that doesn't match).
  const jeansTitle = `Levi's ${word} jeans`;
  const jeansId = await postListing(sellerContext, baseURL!, { title: jeansTitle, category: "men-jeans", priceCents: 3500, size: "32x30" });
  await postListing(sellerContext, baseURL!, { title: `Pricey ${word} jeans`, category: "men-jeans", priceCents: 9000 });

  // 5. Exactly one alert, from the background job, linking to the listing.
  const alertsFor = async () => (await notifications(context)).filter((n) => n.kind === "saved_search" && n.title.includes(word));
  await expect.poll(async () => (await alertsFor()).length, { timeout: 20_000 }).toBe(1);
  const [alert] = await alertsFor();
  expect(alert.title).toBe(`New match for “Jeans ${word}”`);
  expect(alert.link).toBe(`/listings/${jeansId}`);
  await page.goto("/notifications");
  await page.getByRole("link").filter({ hasText: `New match for “Jeans ${word}”` }).click();
  await expect(page).toHaveURL(`/listings/${jeansId}`);

  // 6. No price-drop alerts: lowering the price sends nothing.
  const csrf = (await sellerContext.cookies()).find((c) => c.name === "csrftoken")!.value;
  const edit = await sellerContext.request.patch(`/api/listings/${jeansId}/`, {
    data: { price_cents: 2000 },
    headers: { "X-CSRFToken": csrf, Origin: baseURL! },
  });
  expect(edit.ok(), await edit.text()).toBe(true);
  await page.waitForTimeout(2_000); // give a (non-existent) job time to run
  const about = (await notifications(context)).filter((n) => n.link === `/listings/${jeansId}`);
  expect(about.map((n) => n.kind)).toEqual(["saved_search"]);
  expect((await notifications(context)).some((n) => /price/i.test(n.kind))).toBe(false);

  await sellerContext.close();
});

test("runs, renames, switches alerts for, and deletes a saved search", async ({ page, context, baseURL }) => {
  await signIn(context, baseURL!, TEST_BUYER);
  const word = token();
  await page.goto(`/search?search=${word}&color=blue`);
  await page.getByRole("button", { name: "Save this search" }).click();
  await page.getByLabel("Name").fill(`Blue ${word}`);
  await page.getByRole("button", { name: "Save search", exact: true }).click();
  await page.getByRole("link", { name: "Manage saved searches" }).click();

  await expect(page).toHaveURL("/profile/searches");
  const row = page.getByRole("listitem", { name: `Blue ${word}` });
  await expect(row).toContainText(`“${word}” · Blue · Your school`);

  // Rename.
  await row.getByRole("button", { name: "Rename" }).click();
  await page.getByLabel("Search name").fill(`Navy ${word}`);
  await page.getByRole("button", { name: "Save name" }).click();
  const renamed = page.getByRole("listitem", { name: `Navy ${word}` });
  await expect(renamed).toBeVisible();

  // Alerts off, and it stays off after a reload.
  const alerts = renamed.getByRole("switch", { name: "New-listing alerts" });
  await expect(alerts).toBeChecked();
  await alerts.click();
  await expect(alerts).not.toBeChecked();
  await page.reload();
  await expect(page.getByRole("listitem", { name: `Navy ${word}` }).getByRole("switch", { name: "New-listing alerts" })).not.toBeChecked();

  // Run it: the same /search URL it was saved from.
  await page.getByRole("listitem", { name: `Navy ${word}` }).getByRole("link", { name: "Run search" }).click();
  await expect(page).toHaveURL(`/search?color=blue&search=${word}`);
  await expect(page.getByText(`Saved as “Navy ${word}”`)).toBeVisible();

  // Delete.
  await page.goto("/profile/searches");
  const row2 = page.getByRole("listitem", { name: `Navy ${word}` });
  await row2.getByRole("button", { name: "Delete" }).click();
  await row2.getByRole("group").getByRole("button", { name: "Delete" }).click();
  await expect(page.getByRole("listitem", { name: `Navy ${word}` })).toHaveCount(0);
  await page.reload();
  await expect(page.getByRole("listitem", { name: `Navy ${word}` })).toHaveCount(0);
});

test("a failed bookmark puts the heart back", async ({ page, context, baseURL }) => {
  const sellerContext = await page.context().browser()!.newContext({ baseURL });
  await signIn(sellerContext, baseURL!, TEST_USER);
  const id = await postListing(sellerContext, baseURL!, { title: `E2E rollback ${token()}`, category: "electronics" });
  await sellerContext.close();

  await signIn(context, baseURL!, TEST_BUYER);
  await page.route(`**/api/listings/${id}/bookmark/`, (route) => route.fulfill({ status: 500, body: "{}" }));
  await page.goto(`/listings/${id}`);
  await page.getByRole("button", { name: "Save listing" }).click();

  await expect(page.getByRole("alert").filter({ hasText: "Couldn’t update your saved listings" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Save listing" })).toHaveAttribute("aria-pressed", "false");
  expect((await context.request.get("/api/bookmarks/")).ok()).toBe(true);
  const saved = (await (await context.request.get("/api/bookmarks/")).json()) as { results: { listing_id: number }[] };
  expect(saved.results.some((b) => b.listing_id === id)).toBe(false);
});

test("signed-out students are sent to log in", async ({ page, context, baseURL }) => {
  // The pages say so.
  await page.goto("/profile/searches");
  await expect(page.getByText("Log in to see your saved searches")).toBeVisible();
  expect((await context.request.get("/api/bookmarks/")).status()).toBe(403);

  // A session that ends while a listing is open: saving goes to the login page.
  const sellerContext = await page.context().browser()!.newContext({ baseURL });
  await signIn(sellerContext, baseURL!, TEST_USER);
  const id = await postListing(sellerContext, baseURL!, { title: `E2E signed out ${token()}`, category: "electronics" });
  await sellerContext.close();
  await signIn(context, baseURL!, TEST_BUYER);
  await page.goto(`/listings/${id}`);
  await context.clearCookies();
  await page.getByRole("button", { name: "Save listing" }).click();
  await expect(page).toHaveURL(/\/account\/login$/);
});
