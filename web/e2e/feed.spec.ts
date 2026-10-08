import { randomUUID } from "node:crypto";

import { expect, test } from "@playwright/test";

import { postListing } from "./listings";
import { signIn } from "./sign-in";

// Tests share one database and run in parallel, and the unfiltered feed shows everyone's
// listings (the scroll test alone posts 27). So each test scopes the feed to data only it owns
// (a category no other spec uses, or a brand or size made from a random run id) and finds its
// listings by unique titles.

test("filters the feed by category, keeps filters in the URL, and opens a listing", async ({
  context,
  page,
  baseURL,
}) => {
  await signIn(context, baseURL!);
  const run = randomUUID().slice(0, 8);
  const watch = `E2E watch ${run}`;
  const textbook = `E2E textbook ${run}`;
  const brand = `E2E brand ${run}`;
  const watchId = await postListing(context, baseURL!, { title: watch, category: "accessories-watches", brand });
  await postListing(context, baseURL!, { title: textbook, category: "textbooks", brand });

  const listings = page.getByRole("list", { name: "Listings" });
  await page.goto(`/search?brand=${encodeURIComponent(brand)}`);
  await expect(listings.getByText(watch)).toBeVisible();
  await expect(listings.getByText(textbook)).toBeVisible();

  // Department tab, then a subcategory pill.
  await page.getByRole("navigation", { name: "Marketplace departments" }).getByRole("button", { name: "Accessories" }).click();
  await page.getByRole("link", { name: "Shop all Accessories" }).click();
  await expect(page).toHaveURL(/category=accessories(&|$)/);
  await page.getByRole("navigation", { name: "Accessories categories" }).getByRole("link", { name: "Watches" }).click();
  await expect(page).toHaveURL(/category=accessories-watches/);
  await expect(page.getByRole("heading", { level: 1, name: "Accessories › Watches" })).toBeVisible();
  await expect(listings.getByText(watch)).toBeVisible();
  await expect(listings.getByText(textbook)).toHaveCount(0);

  // The URL alone restores the filtered feed.
  await page.reload();
  await expect(listings.getByText(watch)).toBeVisible();
  await expect(listings.getByText(textbook)).toHaveCount(0);

  await listings.getByRole("link", { name: new RegExp(watch) }).click();
  await expect(page).toHaveURL(`/listings/${watchId}`);
  await expect(page.getByRole("heading", { level: 1, name: watch })).toBeVisible();

  // A link whose filter no longer exists says so, and clearing it shows the feed again.
  await page.goto("/search?category=no-such-category");
  await expect(page.getByRole("heading", { name: "This link’s filters don’t work" })).toBeVisible();
  await page.getByRole("button", { name: "Clear filters" }).click();
  await expect(page).toHaveURL("/search");
  await expect(page.getByRole("heading", { level: 1, name: "New at UMD" })).toBeVisible();
  await expect(listings).toBeVisible();
});

test("the Men tab's Shoes pill goes to Shoes › Men's", async ({ context, page, baseURL }) => {
  await signIn(context, baseURL!);
  const boots = `E2E boots ${randomUUID().slice(0, 8)}`;
  await postListing(context, baseURL!, { title: boots, category: "shoes-men", size: "10" });

  await page.goto("/search?category=men");
  await page.getByRole("navigation", { name: "Men categories" }).getByRole("link", { name: "Shoes", exact: true }).click();

  await expect(page).toHaveURL(/category=shoes-men/);
  await expect(page.getByRole("heading", { level: 1, name: "Shoes › Men's" })).toBeVisible();
  const departments = page.getByRole("navigation", { name: "Marketplace departments" });
  await expect(departments.getByRole("button", { name: "Shoes" })).toHaveClass(/after:bg-ink/);
  await expect(page.getByRole("list", { name: "Listings" }).getByText(boots)).toBeVisible();
});

test("scrolling loads the next page without duplicates", async ({ context, page, baseURL }) => {
  await signIn(context, baseURL!);
  const run = randomUUID().slice(0, 8);
  const count = 27; // more than one page of 24
  for (let i = 0; i < count; i++) {
    await postListing(context, baseURL!, { title: `E2E scarf ${run} #${i}`, category: "accessories-scarves", size: `E2E-${run}` });
  }

  await page.goto(`/search?category=accessories-scarves&size=E2E-${run}`);
  const cards = page.getByRole("list", { name: "Listings" }).getByRole("listitem").filter({ hasText: run });
  await expect(cards).toHaveCount(24);

  // The page loads more as the end of the grid comes into view.
  await cards.last().scrollIntoViewIfNeeded();
  await expect(cards).toHaveCount(count);
  const titles = await cards.locator("h3").allTextContents();
  expect(new Set(titles).size).toBe(count);
  await expect(page.getByText("You’ve seen everything here.")).toBeVisible();
});
