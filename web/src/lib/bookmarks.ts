// Saved listings ("bookmarks"). Each listing from the API says whether the viewer saved it
// (`is_bookmarked`); this store remembers every change made in this tab, so the feed, a
// listing page and the profile's Bookmarks tab agree without refetching.

import { useSyncExternalStore } from "react";

import { api } from "@/lib/api/client";
import type { components } from "@/lib/api/schema";

export type Bookmark = components["schemas"]["Bookmark"];

const changed = new Map<number, boolean>();
const listeners = new Set<() => void>();

function publish(listingId: number, saved: boolean) {
  changed.set(listingId, saved);
  listeners.forEach((listener) => listener());
}

function subscribe(listener: () => void) {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

/** Whether the viewer has saved the listing: the latest change in this tab, else what the API
 * said when the listing loaded. */
export function useIsBookmarked(listingId: number, fromApi: boolean) {
  return useSyncExternalStore(
    subscribe,
    () => changed.get(listingId) ?? fromApi,
    () => fromApi,
  );
}

export type BookmarkFailure = "signed-out" | "unavailable" | "own" | "error";

/** Save or unsave a listing. The new state shows at once everywhere; if the request fails it's
 * put back and the reason returned. */
export async function setBookmarked(listingId: number, saved: boolean, previous: boolean): Promise<BookmarkFailure | null> {
  publish(listingId, saved);
  try {
    const path = { params: { path: { id: listingId } } };
    const { response } = saved
      ? await api.PUT("/api/listings/{id}/bookmark/", path)
      : await api.DELETE("/api/listings/{id}/bookmark/", path);
    if (response.ok) return null;
    publish(listingId, previous);
    if (response.status === 401 || response.status === 403) return "signed-out";
    if (response.status === 404 || response.status === 409) return "unavailable";
    if (response.status === 400) return "own";
    return "error";
  } catch {
    publish(listingId, previous);
    return "error";
  }
}

export const BOOKMARK_FAILURES: Record<Exclude<BookmarkFailure, "signed-out">, string> = {
  unavailable: "This listing can’t be saved anymore.",
  own: "You can’t save your own listing.",
  error: "Couldn’t update your saved listings. Try again.",
};

/** A page of the viewer's saved listings, most recently saved first. */
export async function listBookmarks(cursor?: string) {
  return api.GET("/api/bookmarks/", { params: { query: cursor ? { cursor } : {} } });
}
