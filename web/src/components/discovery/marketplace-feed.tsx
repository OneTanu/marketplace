"use client";

import Link from "next/link";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { type ReactNode, useCallback, useEffect, useRef, useState } from "react";

import { api } from "@/lib/api/client";
import type { components } from "@/lib/api/schema";
import { categoryTree, loadItemCategories, SHOE_SHORTCUTS, type CategoryTree } from "@/lib/categories";
import {
  feedApiQuery,
  feedQueryString,
  readFeedParams,
  type FeedParams,
  type ListingCard as Card,
} from "@/lib/discovery";
import { getCurrentUser, getSchools } from "@/lib/platform";
import { hasSearchFilters } from "@/lib/saved-searches";
import { ListingCard } from "./listing-card";
import { MarketplaceFilterBar } from "./marketplace-filter-bar";
import { SaveSearch } from "./save-search";

type School = components["schemas"]["School"];

// One feed request's results. `key` is the API query it was for, so a response that arrives
// after the filters changed is recognized and dropped.
type Feed =
  | { key: string; state: "loading" }
  | { key: string; state: "signed-out" | "error" | "invalid" }
  | { key: string; state: "ready"; listings: Card[]; next: string | null; loadingMore: boolean; moreFailed: boolean };

async function fetchPage(query: ReturnType<typeof feedApiQuery>, cursor?: string) {
  return api.GET("/api/listings/", { params: { query: cursor ? { ...query, cursor } : query } });
}

/** The marketplace feed for /search (the viewer's school unless the URL widens it), for a
 * school page (that school), and for a signed-in student's Home (`variant="home"`: no filter
 * row, a Filters link to Search instead, and `above` shown over the title). Filters live in the
 * URL; listings load a page at a time as the reader scrolls. */
export function MarketplaceFeed({ school, variant = "browse", above }: { school?: School; variant?: "browse" | "home"; above?: ReactNode }) {
  const home = variant === "home";
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const feed = readFeedParams(searchParams);
  const query = feedApiQuery(feed, school?.slug);
  const key = JSON.stringify(query);

  const [tree, setTree] = useState<CategoryTree | null>(null);
  const [schools, setSchools] = useState<School[]>(school ? [school] : []);
  const [homeSchool, setHomeSchool] = useState<School | null>(null);
  const [viewerId, setViewerId] = useState<number>();
  const [result, setResult] = useState<Feed>({ key, state: "loading" });
  // Bumped by "Try again", to refetch the same query.
  const [attempt, setAttempt] = useState(0);
  const sentinel = useRef<HTMLDivElement>(null);

  const update = useCallback((patch: Partial<FeedParams>) => {
    const next = feedQueryString({ ...readFeedParams(new URLSearchParams(window.location.search)), ...patch });
    router.replace(`${pathname}${next}`, { scroll: false });
  }, [pathname, router]);

  useEffect(() => {
    loadItemCategories().then((categories) => setTree(categories ? categoryTree(categories) : null));
    getCurrentUser().then((user) => { setHomeSchool(user?.school ?? null); setViewerId(user?.id); }).catch(() => setHomeSchool(null));
    if (!school) getSchools().then((items) => setSchools(items.filter((item) => item.marketplace_status === "open"))).catch(() => setSchools([]));
  }, [school]);

  // The first page, again whenever the filters change.
  useEffect(() => {
    let active = true;
    const apiQuery = JSON.parse(key) as typeof query;
    fetchPage(apiQuery)
      .then(({ data, response }) => {
        if (!active) return;
        if (data) setResult({ key, state: "ready", listings: data.results, next: data.next_cursor, loadingMore: false, moreFailed: false });
        else if (response.status === 403 || response.status === 401) setResult({ key, state: "signed-out" });
        // A link with a filter the API refuses (an unknown category, min above max).
        else setResult({ key, state: response.status === 400 ? "invalid" : "error" });
      })
      .catch(() => active && setResult({ key, state: "error" }));
    return () => { active = false; };
  }, [key, attempt]);

  const current: Feed = result.key === key ? result : { key, state: "loading" };

  function retry() {
    setResult({ key, state: "loading" });
    setAttempt((n) => n + 1);
  }

  function loadMore() {
    if (current.state !== "ready" || !current.next || current.loadingMore) return;
    const cursor = current.next;
    setResult({ ...current, loadingMore: true, moreFailed: false });
    fetchPage(JSON.parse(key), cursor)
      .then(({ data }) => setResult((latest) => {
        if (latest.key !== key || latest.state !== "ready") return latest;
        if (!data) return { ...latest, loadingMore: false, moreFailed: true };
        // Keyset paging doesn't repeat listings; deduping keeps React keys unique regardless.
        const seen = new Set(latest.listings.map((listing) => listing.id));
        return { ...latest, listings: [...latest.listings, ...data.results.filter((l) => !seen.has(l.id))], next: data.next_cursor, loadingMore: false };
      }))
      .catch(() => setResult((latest) => latest.key === key && latest.state === "ready" ? { ...latest, loadingMore: false, moreFailed: true } : latest));
  }

  // Infinite scroll: load the next page when the end of the grid comes near. The observer
  // calls the latest loadMore through a ref, so it's only re-created when the cursor changes.
  const loadMoreRef = useRef(loadMore);
  useEffect(() => { loadMoreRef.current = loadMore; });
  const nextCursor = current.state === "ready" && !current.moreFailed ? current.next : null;
  useEffect(() => {
    const element = sentinel.current;
    if (!element || !nextCursor) return;
    const observer = new IntersectionObserver((entries) => { if (entries.some((e) => e.isIntersecting)) loadMoreRef.current(); }, { rootMargin: "800px 0px" });
    observer.observe(element);
    return () => observer.disconnect();
  }, [nextCursor]);

  const category = tree?.bySlug.get(feed.category);
  const department = category && tree?.departmentOf(category);
  const subcategories = department ? tree?.children.get(department.id) ?? [] : [];
  const shoeShortcut = department ? SHOE_SHORTCUTS[department.slug] : undefined;
  const scopeName = school?.name ?? (feed.school === "all" ? "All schools" : schools.find((s) => s.slug === feed.school)?.name ?? homeSchool?.name ?? "");
  const scopeShort = school?.short_name ?? (feed.school === "all" ? "" : schools.find((s) => s.slug === feed.school)?.short_name ?? homeSchool?.short_name ?? "");
  const heading = category
    ? department && department.id !== category.id ? `${department.name} › ${category.name}` : category.name
    : scopeShort ? `New at ${scopeShort}` : "New across Tanu";
  const pillClass = "chip shrink-0";
  const hrefFor = (slug: string) => `${pathname}${feedQueryString({ ...feed, category: slug, size: "" })}`;

  return (
    <section className="mx-auto max-w-6xl px-4 pt-6 pb-12 sm:px-6 sm:pt-9 desktop:pb-16">
      {above}
      {home ? <div className="mb-5 flex items-end justify-between gap-4">
        <h1 className="type-wide text-display font-extrabold ">{heading}</h1>
        <Link href="/search" className="flex min-h-11 shrink-0 items-center text-label font-semibold text-ink underline decoration-ink/30 decoration-2 underline-offset-4 hover:decoration-ink">Filters</Link>
      </div> : <div className="mb-5">
        <p className="text-label font-semibold text-muted">{scopeName}</p>
        <h1 className="type-wide mt-1 text-display font-extrabold ">{heading}</h1>
      </div>}

      {department && (subcategories.length > 0 || shoeShortcut) && <nav aria-label={`${department.name} categories`} className="-mx-1 mb-5 flex gap-2 overflow-x-auto px-1 pb-1 [scrollbar-width:none]">
        <Link href={hrefFor(department.slug)} aria-current={category?.id === department.id ? "page" : undefined} className={pillClass}>All {department.name}</Link>
        {subcategories.map((child) => <Link key={child.id} href={hrefFor(child.slug)} aria-current={category?.id === child.id ? "page" : undefined} className={pillClass}>{child.name}</Link>)}
        {shoeShortcut && <Link href={hrefFor(shoeShortcut.slug)} className={pillClass}>{shoeShortcut.name}</Link>}
      </nav>}

      {/* Keyed on the URL, so the bar's half-typed inputs (prices, waist and length) start
          over whenever the filters change from outside it: links, back/forward, Clear. */}
      {!home && <MarketplaceFilterBar key={searchParams.toString()} feed={feed} update={update} tree={tree} schools={schools} showSchool={!school} homeSchool={homeSchool?.slug ?? ""} />}
      {/* Keyed on the URL too, so a half-written name starts over when the filters change. */}
      {!home && viewerId !== undefined && hasSearchFilters(feed) && current.state !== "invalid" && <div className="-mt-3 mb-6"><SaveSearch key={searchParams.toString()} feed={feed} fixedSchool={school?.slug} categoryLabel={category ? heading : undefined} schoolLabel={school ? school.short_name : feed.school === "all" ? "All schools" : feed.school ? scopeShort : undefined} /></div>}

      {current.state === "loading" && <div aria-busy="true" aria-label="Loading listings" className="grid grid-cols-2 gap-x-3 gap-y-6 sm:grid-cols-3 sm:gap-x-4 lg:grid-cols-4">{Array.from({ length: 8 }).map((_, index) => <div key={index} className="aspect-[4/5] rounded-lg skeleton" />)}</div>}

      {current.state === "signed-out" && <div className="grid min-h-80 place-items-center rounded-xl bg-surface px-6 text-center"><div><h2 className="type-wide text-title font-extrabold">Log in to browse</h2><p className="mt-2 max-w-sm text-label leading-6 text-muted">Listings on Tanu are only visible to verified students.</p><Link href="/account/login" className="btn btn-primary mt-5">Log in</Link></div></div>}

      {current.state === "error" && <div className="grid min-h-80 place-items-center rounded-xl bg-surface px-6 text-center"><div><h2 className="type-wide text-title font-extrabold">Couldn’t load listings</h2><p className="mt-2 max-w-sm text-label leading-6 text-muted">Check your connection and try again.</p><button type="button" onClick={retry} className="btn btn-secondary mt-5">Try again</button></div></div>}

      {current.state === "invalid" && <div className="grid min-h-80 place-items-center rounded-xl bg-surface px-6 text-center"><div><h2 className="type-wide text-title font-extrabold">This link’s filters don’t work</h2><p className="mt-2 max-w-sm text-label leading-6 text-muted">A category, school or price in it isn’t valid anymore.</p><button type="button" onClick={() => router.replace(pathname)} className="btn btn-secondary mt-5">Clear filters</button></div></div>}

      {current.state === "ready" && (current.listings.length ? <>
        <ul aria-label="Listings" className="grid grid-cols-2 gap-x-3 gap-y-6 sm:grid-cols-3 sm:gap-x-4 sm:gap-y-8 lg:grid-cols-4">
          {current.listings.map((listing) => <li key={listing.id}><ListingCard listing={listing} showSchool={!school && feed.school === "all"} showBookmark={viewerId !== undefined && listing.seller.id !== viewerId} /></li>)}
        </ul>
        <div ref={sentinel} className="mt-8 flex min-h-10 justify-center">
          {current.loadingMore && <p role="status" className="text-label text-muted">Loading more…</p>}
          {current.moreFailed && <button type="button" onClick={loadMore} className="btn btn-secondary">Couldn’t load more. Try again</button>}
          {!current.next && current.listings.length > 8 && <p className="text-label text-muted">You’ve seen everything here.</p>}
        </div>
      </> : home ? <div className="grid min-h-80 place-items-center rounded-xl bg-surface px-6 text-center"><div><h2 className="type-wide text-title font-extrabold">Nothing for sale here yet</h2><p className="mt-2 max-w-sm text-label leading-6 text-muted">Be the first: what you post shows up here for students at your school.</p><Link href="/sell" className="btn btn-primary mt-5">Sell an item</Link></div></div> : <div className="grid min-h-80 place-items-center rounded-xl bg-surface px-6 text-center"><div><h2 className="type-wide text-title font-extrabold">Nothing here yet</h2><p className="mt-2 max-w-sm text-label leading-6 text-muted">Try another category, fewer filters, or another school.</p><button type="button" onClick={() => router.replace(pathname)} className="btn btn-secondary mt-5">Clear filters</button></div></div>)}
    </section>
  );
}
