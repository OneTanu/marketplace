import { randomUUID } from "node:crypto";

import { expect, test } from "@playwright/test";

import { postListing } from "./listings";
import { requestDeal, setMeetupPreferences } from "./meetups";
import { signIn } from "./sign-in";
import { TEST_BUYER } from "./test-user";

// A phone-sized screen. The card grid has two columns only on large screens.
test.use({ viewport: { width: 390, height: 844 } });

test("a deal for a listing with a long title doesn't widen the Deals page on a phone", async ({
  browser,
  context,
  page,
  baseURL,
}) => {
  await signIn(context, baseURL!);
  await setMeetupPreferences(context, baseURL!);
  // Titles can be 120 characters and show on one line, cut off with an ellipsis.
  const title = `E2E mini fridge ${randomUUID().slice(0, 8)}, great for dorms, freezer shelf, quiet, cleaned and defrosted, moving out`;
  const listingId = await postListing(context, baseURL!, { title, category: "electronics" });

  const buyerContext = await browser.newContext({ baseURL });
  await signIn(buyerContext, baseURL!, TEST_BUYER);
  await requestDeal(buyerContext, baseURL!, listingId);
  await buyerContext.close();

  await page.goto("/deals");
  await page.getByRole("tab", { name: /^Selling/ }).click();
  const card = page.getByRole("article").filter({ hasText: title });
  await expect(card).toBeVisible();

  const viewport = page.viewportSize()!.width;
  const cardBox = await card.boundingBox();
  expect(cardBox!.x + cardBox!.width, "the card ends inside the screen").toBeLessThanOrEqual(viewport);
  const pageWidth = await page.evaluate(() => document.documentElement.scrollWidth);
  expect(pageWidth, "the page doesn't scroll sideways").toBeLessThanOrEqual(viewport);
});
