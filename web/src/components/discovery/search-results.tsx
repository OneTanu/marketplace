"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useEffect, useMemo, useState } from "react";

import { ListingCard } from "@/components/discovery/listing-card";
import { DISCOVERY_PREVIEW_LISTINGS } from "@/lib/discovery";
import { searchUsers, type PublicUser } from "@/lib/platform";

function UserResult({ user }: { user: PublicUser }) {
  const initial = (user.first_name[0] || user.username[0]).toUpperCase();
  return <Link href={`/users/${user.username}`} className="flex items-center gap-4 rounded-2xl border border-line bg-surface p-4 transition hover:-translate-y-0.5 hover:border-forest hover:shadow-sm">
    <div className="grid size-12 shrink-0 place-items-center rounded-2xl bg-[var(--brand-soft)] text-lg font-black text-brand">{initial}</div>
    <div className="min-w-0 flex-1"><p className="font-black">{user.first_name || `@${user.username}`}</p><p className="truncate text-sm text-muted">@{user.username}{user.school ? ` · ${user.school.short_name}` : ""}</p></div>
    <span className="text-lg text-muted" aria-hidden="true">→</span>
  </Link>;
}

export function SearchResults() {
  const params = useSearchParams();
  const query = (params.get("search") ?? "").trim();
  const [result, setResult] = useState<{
    query: string;
    people: PublicUser[];
    state: "ready" | "signed-out" | "error";
  }>({ query: "", people: [], state: "ready" });

  useEffect(() => {
    if (!query) return;
    let active = true;
    searchUsers(query)
      .then((users) => {
        if (active) setResult({ query, people: users, state: "ready" });
      })
      .catch((error: Error & { message: string }) => {
        if (active) {
          setResult({
            query,
            people: [],
            state:
              error.message.includes("403") || error.message.includes("401")
                ? "signed-out"
                : "error",
          });
        }
      });
    return () => { active = false; };
  }, [query]);

  const state = result.query === query ? result.state : "loading";
  const people = result.query === query ? result.people : [];

  const listings = useMemo(() => {
    const normalized = query.toLowerCase();
    return normalized
      ? DISCOVERY_PREVIEW_LISTINGS.filter((listing) => `${listing.title} ${listing.brand ?? ""} ${listing.category.name}`.toLowerCase().includes(normalized))
      : DISCOVERY_PREVIEW_LISTINGS;
  }, [query]);

  return <main className="mx-auto min-h-[70vh] max-w-6xl px-4 py-10 pb-28 sm:px-6 desktop:pb-12">
    <p className="text-sm font-bold text-brand">{query ? "Search results" : "Explore Tanu"}</p><h1 className="mt-2 text-3xl font-black tracking-[-.04em]">{query ? `“${query}”` : "Browse the marketplace"}</h1>
    {!query && <p className="mt-3 text-muted">Discover clothing, shoes, accessories, and campus essentials from UMD students.</p>}
    {query && <section className="mt-9"><div className="flex items-end justify-between"><div><h2 className="text-xl font-black">People</h2><p className="mt-1 text-sm text-muted">Verified students matching this name or username.</p></div></div>
      {state === "loading" && <div className="mt-4 h-20 animate-pulse rounded-2xl bg-foreground/5" />}
      {state === "signed-out" && <div className="mt-4 rounded-2xl border border-line bg-surface p-5 text-sm"><Link href="/account/login" className="font-black text-forest underline">Log in</Link> to search verified student accounts.</div>}
      {state === "error" && <p className="mt-4 text-sm text-[var(--danger)]">We couldn’t search accounts. Please try again.</p>}
      {state === "ready" && (people.length ? <div className="mt-4 grid gap-3 sm:grid-cols-2">{people.map((user) => <UserResult key={user.id} user={user} />)}</div> : <p className="mt-4 rounded-2xl border border-dashed border-line p-6 text-sm text-muted">No verified accounts match this search.</p>)}
    </section>}
    <section className={query ? "mt-12" : "mt-9"}><h2 className="text-xl font-black">{query ? "Marketplace" : "Available now"}</h2><p className="mt-1 text-sm text-muted">{query ? "Listings matching your search." : "Sample listings previewing what students can sell on Tanu."}</p>{listings.length ? <div className="mt-5 grid grid-cols-2 gap-x-3 gap-y-7 sm:grid-cols-3 lg:grid-cols-4">{listings.map((listing) => <ListingCard key={listing.id} listing={listing} />)}</div> : <p className="mt-4 rounded-2xl border border-dashed border-line p-6 text-sm text-muted">No preview listings match this search.</p>}</section>
  </main>;
}
