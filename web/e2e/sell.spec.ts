import { randomUUID } from "node:crypto";
import path from "node:path";

import { expect, test } from "@playwright/test";

import { signIn } from "./sign-in";

const PHOTO = path.join(__dirname, "fixtures", "photo.jpg");

test("posts a listing with a photo and sees it in My listings", async ({ context, page, baseURL }) => {
  await signIn(context, baseURL!);

  // The test user is shared across tests and retries, so find this run's listing by a title
  // nothing else uses.
  const title = `E2E desk lamp ${randomUUID().slice(0, 8)}`;

  await page.goto("/sell");
  await expect(page.getByRole("heading", { level: 1, name: "Sell an item" })).toBeVisible();

  await page.getByLabel("Add photos").setInputFiles(PHOTO);
  await expect(page.getByRole("img", { name: "Photo 1" })).toBeVisible();

  await page.getByLabel("Title").fill(title);
  // The category list loads from the API; selecting waits for the option to appear.
  await page.getByLabel("Category", { exact: true }).selectOption({ label: "Dorm & furniture" });
  await page.getByLabel("Price").fill("24.99");
  await page.getByLabel("Condition").selectOption({ label: "Good" });
  await page.getByRole("button", { name: "Post listing" }).click();

  await expect(page).toHaveURL("/listings/mine");
  const row = page.getByRole("listitem").filter({ hasText: title });
  await expect(row).toBeVisible();
  await expect(row.getByText("$24.99", { exact: true })).toBeVisible();
  await expect(row.getByText("Available", { exact: true })).toBeVisible();

  // The cover is served by Django through the Next.js /media proxy. It's decorative (alt=""),
  // so it has no accessible name to find it by.
  const cover = row.locator("img");
  await expect(cover).toHaveAttribute("src", /^\/media\//);
  await expect
    .poll(() => cover.evaluate((img: HTMLImageElement) => img.complete && img.naturalWidth), {
      message: "cover image loaded",
    })
    .toBeGreaterThan(0);
});

test("posts jeans into Men › Jeans with a waist and length", async ({ context, page, baseURL }) => {
  await signIn(context, baseURL!);
  const title = `E2E Levi's ${randomUUID().slice(0, 8)}`;

  await page.goto("/sell");
  await page.getByLabel("Add photos").setInputFiles(PHOTO);
  await page.getByLabel("Title").fill(title);
  await page.getByLabel("Category", { exact: true }).selectOption({ label: "Men" });
  await page.getByLabel("Subcategory").selectOption({ label: "Jeans" });
  await page.getByLabel("Price").fill("26");
  await page.getByLabel("Condition").selectOption({ label: "Good" });
  // Jeans are sized by waist and length instead of the free-text size.
  await expect(page.getByLabel("Size", { exact: true })).toHaveCount(0);
  await page.getByLabel("Waist").selectOption("32");
  await page.getByLabel("Length").selectOption("30");
  await page.getByRole("button", { name: "Post listing" }).click();

  await expect(page).toHaveURL("/listings/mine");
  await page.getByRole("listitem").filter({ hasText: title }).getByRole("link", { name: "View" }).click();
  const details = page.getByRole("list", { name: "Details" });
  await expect(details).toContainText("Size 32x30");
  await expect(details).toContainText("Jeans");
});
