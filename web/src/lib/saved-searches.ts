// Saved searches: the feed's URL filters (lib/discovery.ts), stored by the API. Running one
// rebuilds the /search URL, so it's the same search, not a separate implementation.

import { api, requestFailed } from "@/lib/api/client";
import type { components } from "@/lib/api/schema";
import { feedQueryString, priceLabel, type FeedParams } from "@/lib/discovery";
import { COLORS, CONDITIONS } from "@/lib/listing-options";

export type SavedSearch = components["schemas"]["SavedSearch"];
export type SavedSearchFilters = components["schemas"]["SavedSearchFiltersRequest"];

export const MAX_NAME_LENGTH = 80;

/** Whether the feed has anything worth saving: keywords or a filter (a school scope alone isn't). */
export function hasSearchFilters(feed: FeedParams) {
  return Boolean(feed.search || feed.category || feed.brand || feed.condition || feed.color || feed.size || feed.minPrice || feed.maxPrice);
}

/** The feed's URL filters as a saved search's filters. A school page's school wins over the URL. */
export function toSavedFilters(feed: FeedParams, fixedSchool?: string): SavedSearchFilters {
  const cents = (dollars: string) => (dollars ? Number(dollars) * 100 : null);
  return {
    q: feed.search.slice(0, 100),
    school: fixedSchool ?? feed.school,
    category: feed.category || null,
    brand: feed.brand,
    min_price: cents(feed.minPrice),
    max_price: cents(feed.maxPrice),
    size: feed.size,
    condition: feed.condition,
    color: feed.color,
    sort: feed.sort,
  };
}

/** The /search URL that runs a saved search. */
export function savedSearchHref(filters: SavedSearch["filters"]) {
  // The URL holds whole dollars, and searches are saved from it, so prices are whole dollars.
  const dollars = (cents: number | null | undefined) => (cents == null ? "" : String(Math.floor(cents / 100)));
  const feed: FeedParams = {
    search: filters.q,
    school: filters.school,
    category: filters.category ?? "",
    brand: filters.brand,
    minPrice: dollars(filters.min_price),
    maxPrice: dollars(filters.max_price),
    size: filters.size,
    condition: filters.condition || "",
    color: filters.color || "",
    sort: filters.sort ?? "newest",
  };
  return `/search${feedQueryString(feed)}`;
}

/** What makes two saved searches the same search (as the API sees it): every filter after the
 * API's whitespace cleanup, but not the sort. */
export function filtersKey(filters: SavedSearchFilters | SavedSearch["filters"]) {
  const squash = (text: string | undefined) => (text ?? "").split(/\s+/).filter(Boolean).join(" ");
  return JSON.stringify([
    squash(filters.q),
    filters.school ?? "",
    filters.category ?? "",
    squash(filters.brand),
    filters.min_price ?? null,
    filters.max_price ?? null,
    (filters.size ?? "").trim(),
    filters.condition ?? "",
    filters.color ?? "",
  ]);
}

/** A readable default name, e.g. “denim” · Men › Jeans · Levi's · Under $40. */
export function defaultSearchName(feed: FeedParams, { category, school }: { category?: string; school?: string }) {
  const parts = [
    feed.search && `“${feed.search.split(/\s+/).filter(Boolean).join(" ")}”`,
    category,
    feed.brand,
    feed.size,
    COLORS.find((c) => c.value === feed.color)?.label,
    CONDITIONS.find((c) => c.value === feed.condition)?.label,
    feed.minPrice && feed.maxPrice
      ? `${priceLabel(Number(feed.minPrice) * 100)}–${priceLabel(Number(feed.maxPrice) * 100)}`
      : feed.maxPrice ? `Under ${priceLabel(Number(feed.maxPrice) * 100)}` : feed.minPrice ? `${priceLabel(Number(feed.minPrice) * 100)}+` : "",
    school,
  ].filter(Boolean);
  const name = parts.join(" · ") || "Saved search";
  return name.length <= MAX_NAME_LENGTH ? name : `${name.slice(0, MAX_NAME_LENGTH - 1)}…`;
}

/** The viewer's saved searches, or null when signed out. */
export async function listSavedSearches() {
  const { data, error, response } = await api.GET("/api/saved-searches/");
  if (response.status === 401 || response.status === 403) return null;
  return data ?? requestFailed(error, response);
}

export async function createSavedSearch(body: { name: string; filters: SavedSearchFilters; alerts_enabled: boolean }) {
  const { data, error, response } = await api.POST("/api/saved-searches/", { body });
  return data ?? requestFailed(error, response);
}

export async function updateSavedSearch(id: number, body: { name?: string; alerts_enabled?: boolean }) {
  const { data, error, response } = await api.PATCH("/api/saved-searches/{id}/", { params: { path: { id } }, body });
  return data ?? requestFailed(error, response);
}

export async function deleteSavedSearch(id: number) {
  const { error, response } = await api.DELETE("/api/saved-searches/{id}/", { params: { path: { id } } });
  if (!response.ok) requestFailed(error, response);
}
