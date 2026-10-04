"use client";

import Image from "next/image";
import { useState } from "react";

import { CONDITION_LABELS, formatPrice, type DiscoveryListing } from "@/lib/discovery";

export function ListingCard({ listing }: { listing: DiscoveryListing }) {
  const [bookmarked, setBookmarked] = useState(listing.is_bookmarked);

  return (
    <article className="group min-w-0">
      <div className="relative aspect-square overflow-hidden rounded-2xl bg-[#ecebe5]">
        <Image src={listing.image_url} alt="" fill sizes="(max-width: 640px) 50vw, (max-width: 1024px) 33vw, 25vw" className="object-cover transition duration-300 group-hover:scale-[1.025]" />
        <span className="absolute left-2.5 top-2.5 rounded-full bg-white/90 px-2.5 py-1 text-[10px] font-black uppercase tracking-[.08em] text-forest shadow-sm backdrop-blur">Preview</span>
        <button type="button" onClick={() => setBookmarked((value) => !value)} aria-label={bookmarked ? `Remove ${listing.title} from bookmarks` : `Bookmark ${listing.title}`} aria-pressed={bookmarked} className="absolute right-2.5 top-2.5 grid size-9 place-items-center rounded-full bg-white/90 text-foreground shadow-sm backdrop-blur transition hover:scale-105">
          <svg viewBox="0 0 24 24" className="size-5" fill={bookmarked ? "#ed5b2b" : "none"} stroke={bookmarked ? "#ed5b2b" : "currentColor"} strokeWidth="1.8" aria-hidden="true"><path d="M20.8 4.6a5.5 5.5 0 0 0-7.8 0L12 5.7l-1.1-1.1a5.5 5.5 0 0 0-7.8 7.8l1.1 1.1L12 21l7.8-7.5 1.1-1.1a5.5 5.5 0 0 0-.1-7.8Z" /></svg>
        </button>
      </div>
      <div className="px-0.5 pt-3">
        <p className="mb-1 text-xs font-medium text-muted">{listing.size ?? CONDITION_LABELS[listing.condition]}</p>
        <div className="flex items-start justify-between gap-2">
          <p className="text-base font-black tracking-tight">{formatPrice(listing.price_cents, listing.currency)}</p>
          <span className="mt-0.5 text-[11px] font-semibold text-muted">{listing.school.short_name}</span>
        </div>
        <h3 className="mt-1 truncate text-sm font-semibold text-foreground/85">{listing.title}</h3>
        <p className="mt-1 truncate text-xs font-medium text-muted">{listing.brand ?? `@${listing.seller.username}`}</p>
        {listing.brand && <p className="mt-1 truncate text-[11px] text-muted/80">{CONDITION_LABELS[listing.condition]} · @{listing.seller.username}</p>}
      </div>
    </article>
  );
}
