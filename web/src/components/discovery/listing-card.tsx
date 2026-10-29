import Image from "next/image";
import Link from "next/link";

import { priceLabel, type ListingCard as Card } from "@/lib/discovery";
import { schoolPalette } from "@/lib/school-colors";

import { BookmarkButton } from "./bookmark-button";
import styles from "./listing-card.module.css";

// Slight, stable variation so a grid of tags doesn't look stamped out by a machine.
function tilt(id: number) {
  const sum = [...String(id)].reduce((total, char) => total + char.charCodeAt(0), 0);
  return `${-2 - (sum % 4)}deg`;
}

/** A listing in a grid: the price hangs on the photo as a kraft tag, and Pending and Sold are
 * stamps. `previousPriceCents` marks a price drop (no API data for it yet; the design lab uses it).
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
      <Link href={`/listings/${listing.id}`} className="block">
        <div className="relative aspect-[4/5] overflow-hidden rounded-md bg-surface">
          {listing.cover_url && (
            // unoptimized: Django serves /media directly, so Next's image optimizer isn't in the path.
            <Image src={listing.cover_url} alt="" fill unoptimized sizes="(max-width: 640px) 50vw, (max-width: 1024px) 33vw, 25vw" className={`object-cover transition duration-500 desktop:group-hover:scale-[1.03] ${sold ? "opacity-60 grayscale" : ""}`} />
          )}
          {showSchool && <span className={styles.badge} style={{ background: school.lead, color: school.text, ["--accent" as string]: school.accent }}>{listing.school.short_name}</span>}
          {listing.status === "pending" && <span className={`${styles.stamp} ${styles.onPhoto} text-ink`}>PENDING</span>}
          {sold && <span className={`${styles.stamp} ${styles.onPhoto} text-[#d42b33]`}>SOLD</span>}
          {dropped && <span className={`${styles.tag} ${styles.was}`}><span className="sr-only">Was </span>{priceLabel(previousPriceCents)}</span>}
          {!sold && <span className={`${styles.tag} ${dropped ? styles.drop : ""}`} style={{ ["--tilt" as string]: tilt(listing.id) }}>
            {dropped && <span className="sr-only">Now </span>}
            <span className="type-wide text-[17px] font-black">{price}</span>
          </span>}
        </div>
        <div className="pt-2.5">
          <h3 className="truncate text-sm font-semibold text-ink">{listing.title}</h3>
          {(sold || detail) && <p className="mt-0.5 truncate text-[13px] text-muted">{sold ? `Sold for ${price}` : detail}</p>}
        </div>
      </Link>
      {/* Outside the link: a button can't sit inside one. */}
      {/* A Sold listing can't be newly saved, but one saved earlier can be unsaved. */}
      {showBookmark && (listing.is_bookmarked || !sold) && <BookmarkButton listingId={listing.id} isBookmarked={listing.is_bookmarked} />}
    </article>
  );
}
