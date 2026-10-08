"use client";

import Image from "next/image";
import Link from "next/link";
import { useEffect, useState } from "react";

import { api } from "@/lib/api/client";
import type { components } from "@/lib/api/schema";
import { STATUS_LABELS } from "@/lib/listing-options";
import { centsToDollars } from "@/lib/money";

type Listing = components["schemas"]["Listing"];
type Photo = components["schemas"]["ListingPhoto"];
type Status = components["schemas"]["StatusEnum"];
type Filter = "all" | Exclude<Status, "removed">;

const FILTERS: { value: Filter; label: string }[] = [
  { value: "all", label: "All" },
  { value: "available", label: STATUS_LABELS.available },
  { value: "pending", label: STATUS_LABELS.pending },
  { value: "sold", label: STATUS_LABELS.sold },
];

const STATUS_BADGE: Record<Status, string> = {
  available: "bg-green-600/10 text-green-700 dark:text-green-400",
  pending: "bg-amber-500/15 text-amber-700 dark:text-amber-400",
  sold: "bg-foreground/10 text-foreground/70",
  removed: "bg-red-600/10 text-red-700 dark:text-red-400",
};

// The last response and the filter it was for. While a newer filter loads, the previous
// result stays on screen (dimmed) instead of flashing an empty list.
type Result = { filter: Filter } & ({ listings: Listing[] } | { error: string });

/** The cover is the photo with the lowest position. */
function coverPhoto(photos: Photo[]): Photo | undefined {
  return photos.reduce<Photo | undefined>(
    (cover, photo) => (!cover || photo.position < cover.position ? photo : cover),
    undefined,
  );
}

function ListingRow({ listing }: { listing: Listing }) {
  const cover = coverPhoto(listing.photos);
  return (
    <li className="flex gap-3 rounded-xl border border-black/10 p-2 dark:border-white/10">
      <div className="relative size-20 shrink-0 overflow-hidden rounded-lg bg-foreground/5 sm:size-24">
        {cover && (
          // The full image until the thumbnail job has run. unoptimized: Django serves /media
          // directly, so Next's image optimizer isn't in the path.
          <Image src={cover.thumbnail_url ?? cover.image_url} alt="" fill unoptimized className="object-cover" />
        )}
      </div>
      <div className="min-w-0 flex-1 py-0.5">
        <p className="truncate font-medium">{listing.title}</p>
        <p className="mt-0.5 text-sm text-foreground/80">
          {listing.price_cents === 0 ? "Free" : centsToDollars(listing.price_cents)}
        </p>
        <span
          className={`mt-1.5 inline-block rounded-full px-2 py-0.5 text-xs font-medium ${STATUS_BADGE[listing.status]}`}
        >
          {STATUS_LABELS[listing.status]}
        </span>
      </div>
    </li>
  );
}

export function MyListings() {
  const [filter, setFilter] = useState<Filter>("all");
  const [result, setResult] = useState<Result | null>(null);

  useEffect(() => {
    let cancelled = false;
    api
      .GET("/api/listings/mine/", {
        params: { query: filter === "all" ? {} : { status: filter } },
      })
      .then(({ data, response }) => {
        if (cancelled) return;
        if (data) setResult({ filter, listings: data });
        else if (response.status === 403)
          setResult({ filter, error: "Sign in with your school email to see your listings." });
        else setResult({ filter, error: "Couldn't load your listings. Refresh to try again." });
      })
      .catch(() => {
        if (!cancelled)
          setResult({ filter, error: "Couldn't reach Tanu. Check your connection and refresh." });
      });
    return () => {
      cancelled = true;
    };
  }, [filter]);

  const loading = result?.filter !== filter;

  let body;
  if (!result) {
    body = <p className="text-sm text-foreground/60">Loading…</p>;
  } else if ("error" in result) {
    body = <p className="text-sm text-foreground/70">{result.error}</p>;
  } else if (result.listings.length === 0 && result.filter !== "all") {
    body = (
      <p className="text-sm text-foreground/60">
        No {STATUS_LABELS[result.filter].toLowerCase()} listings.
      </p>
    );
  } else if (result.listings.length === 0) {
    body = (
      <div className="rounded-xl border border-dashed border-black/20 px-4 py-10 text-center dark:border-white/25">
        <p className="font-medium">You haven&apos;t posted anything yet.</p>
        <p className="mt-1 text-sm text-foreground/60">Got something to sell? It takes a minute.</p>
        <Link
          href="/sell"
          className="mt-4 inline-block rounded-full bg-foreground px-5 py-2.5 text-sm font-semibold text-background"
        >
          Sell an item
        </Link>
      </div>
    );
  } else {
    body = (
      <ul className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
        {result.listings.map((listing) => (
          <ListingRow key={listing.id} listing={listing} />
        ))}
      </ul>
    );
  }

  return (
    <>
      <div role="group" aria-label="Filter by status" className="mt-4 flex gap-1 overflow-x-auto">
        {FILTERS.map((option) => (
          <button
            key={option.value}
            type="button"
            onClick={() => setFilter(option.value)}
            aria-pressed={filter === option.value}
            className="shrink-0 rounded-full px-4 py-2 text-sm font-medium text-foreground/70 hover:bg-foreground/5 aria-pressed:bg-foreground aria-pressed:text-background"
          >
            {option.label}
          </button>
        ))}
      </div>
      <div aria-busy={loading} className={`mt-4 ${result && loading ? "opacity-60" : ""}`}>
        {body}
      </div>
    </>
  );
}
