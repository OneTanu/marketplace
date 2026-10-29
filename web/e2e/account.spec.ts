import { randomUUID } from "node:crypto";

import { expect, test } from "@playwright/test";

import { postListing } from "./listings";
import { signIn } from "./sign-in";
import { TEST_BUYER, TEST_CLOSER } from "./test-user";

test("a student deactivates their account, then logging in again brings it and their listing back", async ({ browser, context, page, baseURL }) => {
  await signIn(context, baseURL!, TEST_CLOSER);
  const title = `E2E closing lamp ${randomUUID().slice(0, 8)}`;
  const listingId = await postListing(context, baseURL!, { title, category: "electronics" });

  // Account status → Deactivate: the page says what will happen, then asks for the password.
  await page.goto("/profile/standing");
  await page.getByRole("link", { name: "Deactivate account" }).click();
  await expect(page.getByRole("heading", { level: 1, name: "Deactivate your account" })).toBeVisible();
  await expect(page.getByText("Your 1 available listing is hidden")).toBeVisible();
  const deactivate = page.getByRole("button", { name: "Deactivate account" });
  await page.getByLabel("Your password").fill("not-my-password");
  await page.getByRole("checkbox", { name: /I understand/ }).check();
  await deactivate.click();
  await expect(page.getByText("That password isn't right.")).toBeVisible();
  await page.getByLabel("Your password").fill(TEST_CLOSER.password);
  await deactivate.click();
  await expect(page).toHaveURL("/account/deactivated");
  await expect(page.getByRole("heading", { level: 1, name: "Your account is deactivated" })).toBeVisible();

  // Signed out, and the listing is hidden from other students.
  expect((await context.request.get("/api/me/")).status()).toBe(403);
  const buyerContext = await browser.newContext({ baseURL });
  await signIn(buyerContext, baseURL!, TEST_BUYER);
  expect((await buyerContext.request.get(`/api/listings/${listingId}/`)).status()).toBe(404);

  // Logging in with the right password offers to reactivate.
  await page.goto("/account/login");
  await page.getByLabel("School email").fill(TEST_CLOSER.email);
  await page.getByLabel("Password").fill(TEST_CLOSER.password);
  await page.getByRole("button", { name: "Log in" }).click();
  await expect(page.getByText("This account is deactivated")).toBeVisible();
  await page.getByRole("button", { name: "Reactivate and log in" }).click();
  await expect(page).not.toHaveURL(/\/account\/login/);

  expect((await context.request.get("/api/me/")).ok()).toBe(true);
  expect((await buyerContext.request.get(`/api/listings/${listingId}/`)).ok()).toBe(true);
  await buyerContext.close();
});
