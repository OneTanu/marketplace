import { readFileSync } from "node:fs";
import path from "node:path";

import { expect, type BrowserContext } from "@playwright/test";

export const PHOTO = path.join(__dirname, "fixtures", "photo.jpg");

type NewListing = {
  title: string;
  /** Category slug, e.g. "electronics" or "men-jeans". */
  category: string;
  priceCents?: number;
  condition?: string;
  size?: string;
  color?: string;
};

/**
 * Posts a listing through the API as whoever is signed in to `context` (see signIn), and returns
 * its id. Faster than the Sell form, which sell.spec.ts covers.
 */
export async function postListing(context: BrowserContext, baseURL: string, listing: NewListing) {
  const api = context.request;
  const categories = await api.get("/api/categories/?kind=item");
  expect(categories.ok()).toBe(true);
  const category = ((await categories.json()) as { id: number; slug: string }[]).find(
    (c) => c.slug === listing.category,
  );
  expect(category, `category ${listing.category}`).toBeTruthy();

  const csrfToken = (await context.cookies()).find((c) => c.name === "csrftoken")?.value;
  const response = await api.post("/api/listings/", {
    multipart: {
      title: listing.title,
      category: String(category!.id),
      price_cents: String(listing.priceCents ?? 2500),
      condition: listing.condition ?? "good",
      size: listing.size ?? "",
      color: listing.color ?? "",
      photos: { name: "photo.jpg", mimeType: "image/jpeg", buffer: readFileSync(PHOTO) },
    },
    headers: { "X-CSRFToken": csrfToken!, Origin: baseURL },
  });
  expect(response.status(), await response.text()).toBe(201);
  return ((await response.json()) as { id: number }).id;
}
