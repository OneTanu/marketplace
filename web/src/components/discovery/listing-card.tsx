"use client";

import Image from "next/image";
import { useState } from "react";

import { CONDITION_LABELS, formatPrice, type DiscoveryListing } from "@/lib/discovery";

export function ListingCard({ listing, showSchool = false }: { listing: DiscoveryListing; showSchool?: boolean }) {
  const [bookmarked, setBookmarked] = useState(listing.is_bookmarked);
  const measurement = listing.waist
    ? `W${listing.waist}${listing.inseam ? ` × L${listing.inseam}` : ""}`
    : listing.size
      ? `Size ${listing.size}`
      : CONDITION_LABELS[listing.condition];
  const detail = [listing.brand, measurement].filter(Boolean).join(", ");

  return (
    <article className="group min-w-0">
      <div className="relative aspect-[4/5] overflow-hidden rounded-md bg-surface">
        <Image src={listing.image_url} alt="" fill sizes="(max-width: 640px) 50vw, (max-width: 1024px) 33vw, 25vw" className="object-cover transition duration-500 desktop:group-hover:scale-[1.03]" />
        {showSchool && <span className="absolute bottom-2 left-2 rounded bg-background/90 px-1.5 py-0.5 text-[11px] font-bold text-ink">{listing.school.short_name}</span>}
        <button type="button" onClick={() => setBookmarked((value) => !value)} aria-label={bookmarked ? `Remove ${listing.title} from bookmarks` : `Bookmark ${listing.title}`} aria-pressed={bookmarked} className="absolute right-2 top-2 grid size-9 place-items-center rounded-full bg-background/90 text-ink transition active:scale-90">
          <svg viewBox="0 0 24 24" className={`size-[18px] ${bookmarked ? "fill-signal stroke-signal" : "fill-none stroke-current"}`} strokeWidth="2" aria-hidden="true"><path d="M20.8 4.6a5.5 5.5 0 0 0-7.8 0L12 5.7l-1.1-1.1a5.5 5.5 0 0 0-7.8 7.8l1.1 1.1L12 21l7.8-7.5 1.1-1.1a5.5 5.5 0 0 0-.1-7.8Z" /></svg>
        </button>
      </div>
      <div className="pt-2.5">
        <p className="type-wide text-[15px] font-extrabold text-ink">{formatPrice(listing.price_cents, listing.currency)}</p>
        <h3 className="mt-0.5 truncate text-sm text-ink">{listing.title}</h3>
        <p className="mt-0.5 truncate text-[13px] text-muted">{detail || `@${listing.seller.username}`}</p>
      </div>
    </article>
  );
}
