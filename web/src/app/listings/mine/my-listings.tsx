"use client";

import Image from "next/image";
import Link from "next/link";
import { useEffect, useRef, useState } from "react";

import { refusalMessage, toFieldErrors } from "@/components/listings/listing-form";
import { api } from "@/lib/api/client";
import type { components } from "@/lib/api/schema";
import { STATUS_BADGE_CLASSES, STATUS_LABELS } from "@/lib/listing-options";
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

/** One listing, with a View link. Available listings also get Edit and Remove; Remove asks
 * for confirmation inside the row, then calls onRemoved once the API has removed it. */
function ListingRow({ listing, onRemoved }: { listing: Listing; onRemoved: (listing: Listing) => void }) {
  const cover = coverPhoto(listing.photos);
  const [confirming, setConfirming] = useState(false);
  const [removing, setRemoving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const removeButton = useRef<HTMLButtonElement>(null);
  const cancelButton = useRef<HTMLButtonElement>(null);

  // Focus follows the confirm step: onto Cancel when it opens, back to Remove when it closes.
  const opened = useRef(false);
  useEffect(() => {
    if (confirming) cancelButton.current?.focus();
    else if (opened.current) removeButton.current?.focus();
    opened.current = confirming;
  }, [confirming]);

  function cancel() {
    setConfirming(false);
    setError(null);
  }

  async function remove() {
    if (removing) return;
    setRemoving(true);
    setError(null);
    try {
      const { error: body, response } = await api.DELETE("/api/listings/{id}/", {
        params: { path: { id: listing.id } },
      });
      if (response.ok) {
        onRemoved(listing);
        return;
      }
      setError(
        refusalMessage(response.status, toFieldErrors(body).detail?.[0], {
          failed: "Couldn't remove this listing. Try again.",
          signIn: "Sign in to remove your listing.",
        }),
      );
    } catch {
      setError("Couldn't reach Tanu. Check your connection and try again.");
    }
    setRemoving(false);
  }

  return (
    <li
      className={`rounded-xl border p-2 ${
        confirming
          ? "border-[var(--danger)] bg-[var(--danger-soft)]"
          : "border-black/10 dark:border-white/10"
      }`}
    >
      <div className="flex gap-3">
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
            className={`mt-1.5 inline-block rounded-full px-2 py-0.5 text-xs font-medium ${STATUS_BADGE_CLASSES[listing.status]}`}
          >
            {STATUS_LABELS[listing.status]}
          </span>
        </div>
      </div>
      {listing.removed_by === "moderation" && (
        <p className="mt-2 text-sm text-foreground/60">
          Removed by moderation. Buyers can&apos;t see this listing.
        </p>
      )}
      {!confirming && (
        <div className="mt-2 flex justify-end gap-1.5">
          <Link href={`/listings/${listing.id}`} className="btn btn-sm btn-quiet">
            View
          </Link>
          {listing.status === "available" && (
            <>
              <Link href={`/listings/${listing.id}/edit`} className="btn btn-sm btn-quiet">
                Edit
              </Link>
              <button
                ref={removeButton}
                type="button"
                onClick={() => setConfirming(true)}
                className="btn btn-sm text-[var(--danger)] hover:bg-[var(--danger-soft)]"
              >
                Remove
              </button>
            </>
          )}
        </div>
      )}
      {confirming && (
        <div
          role="group"
          aria-label={`Remove ${listing.title}`}
          onKeyDown={(event) => {
            if (event.key === "Escape" && !removing) cancel();
          }}
          className="mt-2 border-t border-[var(--danger)]/20 pt-2"
        >
          <p className="text-sm">
            <span className="block font-semibold">Remove this listing?</span>
            Buyers won&apos;t see it anymore. This can&apos;t be undone.
          </p>
          {error && (
            <p role="alert" className="mt-1.5 text-sm text-[var(--danger)]">
              {error}
            </p>
          )}
          {/* aria-disabled rather than disabled: disabling the focused button would drop focus
              out of the row. */}
          <div className="mt-2 flex justify-end gap-1.5">
            <button
              ref={cancelButton}
              type="button"
              onClick={() => {
                if (!removing) cancel();
              }}
              aria-disabled={removing}
              className="btn btn-sm btn-quiet aria-disabled:cursor-not-allowed aria-disabled:opacity-55"
            >
              Cancel
            </button>
            <button
              type="button"
              onClick={remove}
              aria-disabled={removing}
              className="btn btn-sm bg-[var(--danger)] text-white aria-disabled:cursor-not-allowed aria-disabled:opacity-55"
            >
              {removing ? "Removing…" : "Remove listing"}
            </button>
          </div>
        </div>
      )}
    </li>
  );
}

export function MyListings() {
  const [filter, setFilter] = useState<Filter>("all");
  const [result, setResult] = useState<Result | null>(null);
  const [announcement, setAnnouncement] = useState("");
  // Listings removed on this page. A list request already in flight when one was removed
  // would otherwise bring it back.
  const removedIds = useRef(new Set<number>());
  const results = useRef<HTMLDivElement>(null);

  useEffect(() => {
    let cancelled = false;
    api
      .GET("/api/listings/mine/", {
        params: { query: filter === "all" ? {} : { status: filter } },
      })
      .then(({ data, response }) => {
        if (cancelled) return;
        if (data)
          setResult({ filter, listings: data.filter((l) => !removedIds.current.has(l.id)) });
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

  function dropListing(removed: Listing) {
    removedIds.current.add(removed.id);
    setResult((current) =>
      current && "listings" in current
        ? { ...current, listings: current.listings.filter((listing) => listing.id !== removed.id) }
        : current,
    );
    // The focused button goes with the row. Keep focus at the list (Tab continues from there)
    // and tell screen readers what happened.
    results.current?.focus();
    setAnnouncement(`Removed ${removed.title}.`);
  }

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
      <ul className="grid grid-cols-1 items-start gap-3 sm:grid-cols-2 lg:grid-cols-3">
        {result.listings.map((listing) => (
          <ListingRow key={listing.id} listing={listing} onRemoved={dropListing} />
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
      <div
        ref={results}
        tabIndex={-1}
        aria-busy={loading}
        className={`mt-4 outline-none ${result && loading ? "opacity-60" : ""}`}
      >
        {body}
      </div>
      <p role="status" className="sr-only">
        {announcement}
      </p>
    </>
  );
}
