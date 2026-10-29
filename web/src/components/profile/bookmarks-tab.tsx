"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { ListingCard } from "@/components/discovery/listing-card";
import { BOOKMARK_FAILURES, listBookmarks, setBookmarked, type Bookmark } from "@/lib/bookmarks";

type Page =
  | { state: "loading" }
  | { state: "error" }
  | { state: "ready"; bookmarks: Bookmark[]; next: string | null; loadingMore: boolean; moreFailed: boolean };

const GONE: Record<string, { title: string; note: string }> = {
  removed: { title: "Listing removed", note: "This listing isn’t on Tanu anymore." },
  unavailable: { title: "Not available right now", note: "This seller’s listings are hidden for now." },
};

/** A saved listing that can't be shown any more, with a way to unsave it. */
function GoneCard({ bookmark, onRemoved }: { bookmark: Bookmark; onRemoved: () => void }) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const gone = GONE[bookmark.availability] ?? GONE.removed;

  async function remove() {
    setBusy(true);
    setError("");
    const failure = await setBookmarked(bookmark.listing_id, false, true);
    setBusy(false);
    if (failure) setError(failure === "signed-out" ? "Log in again to change your saved listings." : BOOKMARK_FAILURES[failure]);
    else onRemoved();
  }

  return <article className="flex aspect-[4/5] flex-col items-center justify-center rounded-md border border-dashed border-line bg-surface/60 p-4 text-center">
    <p className="text-sm font-bold">{gone.title}</p>
    <p className="mt-1 text-xs leading-5 text-muted">{gone.note}</p>
    <button type="button" onClick={remove} disabled={busy} className="btn btn-quiet btn-sm mt-3">{busy ? "Removing…" : "Remove from saved"}</button>
    {error && <p role="alert" className="mt-2 text-xs text-[var(--danger)]">{error}</p>}
  </article>;
}

/** The profile's Bookmarks tab: saved listings, most recently saved first, a page at a time.
 * Pending and Sold ones show their stamp; removed ones show a placeholder. */
export function BookmarksTab() {
  const [page, setPage] = useState<Page>({ state: "loading" });
  // Bumped by "Try again", to load the first page again.
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    let active = true;
    listBookmarks()
      .then(({ data }) => active && setPage(data ? { state: "ready", bookmarks: data.results, next: data.next_cursor, loadingMore: false, moreFailed: false } : { state: "error" }))
      .catch(() => active && setPage({ state: "error" }));
    return () => { active = false; };
  }, [attempt]);

  function retry() {
    setPage({ state: "loading" });
    setAttempt((n) => n + 1);
  }

  function loadMore() {
    if (page.state !== "ready" || !page.next || page.loadingMore) return;
    const cursor = page.next;
    setPage({ ...page, loadingMore: true, moreFailed: false });
    listBookmarks(cursor)
      .then(({ data }) => setPage((latest) => {
        if (latest.state !== "ready") return latest;
        if (!data) return { ...latest, loadingMore: false, moreFailed: true };
        const seen = new Set(latest.bookmarks.map((b) => b.listing_id));
        return { ...latest, bookmarks: [...latest.bookmarks, ...data.results.filter((b) => !seen.has(b.listing_id))], next: data.next_cursor, loadingMore: false };
      }))
      .catch(() => setPage((latest) => latest.state === "ready" ? { ...latest, loadingMore: false, moreFailed: true } : latest));
  }

  if (page.state === "loading") {
    return <div aria-busy="true" aria-label="Loading saved listings" className="grid grid-cols-2 gap-x-3 gap-y-6 sm:grid-cols-3 sm:gap-x-4 lg:grid-cols-4">{Array.from({ length: 4 }).map((_, index) => <div key={index} className="aspect-[4/5] animate-pulse rounded-md bg-surface" />)}</div>;
  }
  if (page.state === "error") {
    return <div role="alert" className="rounded-2xl bg-surface p-6 text-center"><p className="font-bold">Couldn’t load your saved listings</p><p className="mt-1 text-sm text-muted">Check your connection and try again.</p><button type="button" onClick={retry} className="btn btn-secondary mt-4">Try again</button></div>;
  }
  if (!page.bookmarks.length) {
    return <div className="grid min-h-64 place-items-center rounded-3xl border border-dashed border-line bg-white/45 px-6 text-center">
      <div className="max-w-sm py-10">
        <div className="mx-auto mb-4 grid size-12 place-items-center rounded-2xl bg-[var(--ink-soft)] text-xl text-ink" aria-hidden="true">♡</div>
        <h2 className="text-lg font-bold">No saved listings yet</h2>
        <p className="mt-2 text-sm leading-6 text-muted">Tap the heart on a listing while browsing and it will be collected here.</p>
        <div className="mt-5"><Link href="/search" className="btn btn-secondary">Browse listings</Link></div>
      </div>
    </div>;
  }
  return <>
    <ul aria-label="Saved listings" className="grid grid-cols-2 gap-x-3 gap-y-6 sm:grid-cols-3 sm:gap-x-4 sm:gap-y-8 lg:grid-cols-4">
      {page.bookmarks.map((bookmark) => <li key={bookmark.listing_id}>
        {bookmark.listing
          ? <ListingCard listing={bookmark.listing} showBookmark />
          : <GoneCard bookmark={bookmark} onRemoved={() => setPage((latest) => latest.state === "ready" ? { ...latest, bookmarks: latest.bookmarks.filter((b) => b.listing_id !== bookmark.listing_id) } : latest)} />}
      </li>)}
    </ul>
    {(page.next || page.moreFailed) && <div className="mt-8 flex justify-center">
      <button type="button" onClick={loadMore} disabled={page.loadingMore} className="btn btn-secondary">{page.loadingMore ? "Loading…" : page.moreFailed ? "Couldn’t load more. Try again" : "Load more"}</button>
    </div>}
  </>;
}
