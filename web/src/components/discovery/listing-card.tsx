import Image from "next/image";
import Link from "next/link";

import { priceLabel, type ListingCard as Card } from "@/lib/discovery";
import { schoolPalette } from "@/lib/school-colors";

import { PriceTag } from "@/components/ui/price-tag";

import { BookmarkButton } from "./bookmark-button";
import styles from "./listing-card.module.css";

/** A listing in a grid: the price is a kraft tag hanging off the photo's bottom edge, so it never
 * covers the item, and Pending and Sold are stamps. `previousPriceCents` marks a price drop (no API data for it yet; the design lab uses it).
 * `showBookmark` adds a heart to save it (callers leave it off on the viewer's own listings). */
export function ListingCard({ listing, showSchool = false, previousPriceCents, showBookmark = false }: {
  listing: Card;
  showSchool?: boolean;
  previousPriceCents?: number;
  showBookmark?: boolean;
}) {
  const sold = listing.status === "sold";
  const dropped = !sold && previousPriceCents !== undefined && previousPriceCents > listing.price_cents;
  const price = priceLabel(listing.price_cents);
  // Brand and size only: condition is on the listing page, not the grid.
  const detail = [listing.brand, listing.size === "One size" ? listing.size : listing.size ? `Size ${listing.size}` : ""]
    .filter(Boolean)
    .join(", ");
  const school = schoolPalette(listing.school.colors);

  return (
    <article className="group relative min-w-0">
      <Link href={`/listings/${listing.id}`} className="block rounded-xl transition-transform duration-150 motion-safe:active:scale-[0.98]">
        <div className="relative">
        <div className="relative aspect-[4/5] overflow-hidden rounded-xl bg-surface">
          {listing.cover_url && (
            // unoptimized: Django serves /media directly, so Next's image optimizer isn't in the path.
            <Image src={listing.cover_url} alt="" fill unoptimized sizes="(max-width: 640px) 50vw, (max-width: 1024px) 33vw, 25vw" className={`object-cover transition-transform duration-300 motion-safe:group-hover:scale-[1.03] ${sold ? "opacity-60 grayscale" : ""}`} />
          )}
          {showSchool && <span className={styles.badge} style={{ background: school.lead, color: school.text, ["--accent" as string]: school.accent }}>{listing.school.short_name}</span>}
          {listing.status === "pending" && <span className={`${styles.stamp} ${styles.onPhoto} text-ink`}>PENDING</span>}
          {sold && <span className={`${styles.stamp} ${styles.onPhoto} text-danger`}>SOLD</span>}
        </div>
        {/* Outside the photo's clipping box, so it can hang over the edge. */}
        {!sold && <PriceTag label={price} was={dropped ? priceLabel(previousPriceCents) : undefined} />}
        </div>
        <div className={sold ? "pt-2.5" : "pt-5.5"}>
          <h2 className="truncate text-label font-semibold text-ink">{listing.title}</h2>
          {(sold || detail) && <p className="mt-0.5 truncate text-fine text-muted">{sold ? `Sold for ${price}` : detail}</p>}
        </div>
      </Link>
      {/* Outside the link: a button can't sit inside one. */}
      {/* A Sold listing can't be newly saved, but one saved earlier can be unsaved. */}
      {showBookmark && (listing.is_bookmarked || !sold) && <BookmarkButton listingId={listing.id} isBookmarked={listing.is_bookmarked} />}
    </article>
  );
}
