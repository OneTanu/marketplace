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
  await page.getByLabel("Category").selectOption({ label: "Dorm & furniture" });
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
