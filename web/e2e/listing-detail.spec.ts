import { randomUUID } from "node:crypto";

import { expect, test } from "@playwright/test";

import { postListing } from "./listings";
import { signIn } from "./sign-in";
import { TEST_BUYER, TEST_USER } from "./test-user";

test("the seller and another student see different actions on a listing", async ({
  browser,
  context,
  page,
  baseURL,
}) => {
  await signIn(context, baseURL!);
  const title = `E2E calculator ${randomUUID().slice(0, 8)}`;
  const id = await postListing(context, baseURL!, {
    title,
    category: "electronics",
    priceCents: 6000,
    condition: "like_new",
  });

  // The seller: Edit and Remove, no buyer actions.
  await page.goto(`/listings/${id}`);
  await expect(page.getByRole("heading", { level: 1, name: title })).toBeVisible();
  await expect(page.getByText("$60", { exact: true })).toBeVisible();
  await expect(page.getByRole("list", { name: "Details" })).toContainText("Like new");
  await expect(page.getByRole("link", { name: "Edit listing" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Message" })).toHaveCount(0);

  // My listings links to the page.
  await page.goto("/listings/mine");
  await page.getByRole("listitem").filter({ hasText: title }).getByRole("link", { name: "View" }).click();
  await expect(page).toHaveURL(`/listings/${id}`);

  // Another student: Message works; offers wait for Deals.
  const buyerContext = await browser.newContext({ baseURL });
  const buyerPage = await buyerContext.newPage();
  await signIn(buyerContext, baseURL!, TEST_BUYER);
  await buyerPage.goto(`/listings/${id}`);
  await expect(buyerPage.getByRole("heading", { level: 1, name: title })).toBeVisible();
  await expect(buyerPage.getByRole("link", { name: `@${TEST_USER.username}` })).toBeVisible();
  await expect(buyerPage.getByRole("button", { name: "Make offer" })).toBeDisabled();
  await expect(buyerPage.getByRole("button", { name: "Buy now" })).toBeDisabled();
  await expect(buyerPage.getByRole("link", { name: "Edit listing" })).toHaveCount(0);
  await buyerPage.getByRole("button", { name: "Message" }).click();
  await expect(buyerPage).toHaveURL(/\/inbox\/\d+$/);

  // The seller removes it from the page; it's then gone for the other student.
  await page.getByRole("button", { name: "Remove" }).click();
  await page.getByRole("button", { name: "Remove listing" }).click();
  await expect(page.getByText("You removed this listing. Buyers can't see it.")).toBeVisible();
  await expect(page.getByText("Removed", { exact: true })).toBeVisible();

  await buyerPage.goto(`/listings/${id}`);
  await expect(buyerPage.getByRole("heading", { level: 1, name: "Listing not found" })).toBeVisible();
  await buyerContext.close();
});
