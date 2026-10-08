import Image from "next/image";
import Link from "next/link";

import { priceLabel, type ListingCard as Card } from "@/lib/discovery";
import { conditionLabel } from "@/lib/listing-options";

export function ListingCard({ listing, showSchool = false }: { listing: Card; showSchool?: boolean }) {
  const detail = [listing.brand, listing.size ? `Size ${listing.size}` : conditionLabel(listing.condition)]
    .filter(Boolean)
    .join(", ");

  return (
    <article className="group min-w-0">
      <Link href={`/listings/${listing.id}`} className="block">
        <div className="relative aspect-[4/5] overflow-hidden rounded-md bg-surface">
          {listing.cover_url && (
            // unoptimized: Django serves /media directly, so Next's image optimizer isn't in the path.
            <Image src={listing.cover_url} alt="" fill unoptimized sizes="(max-width: 640px) 50vw, (max-width: 1024px) 33vw, 25vw" className="object-cover transition duration-500 desktop:group-hover:scale-[1.03]" />
          )}
          {listing.status === "pending" && <span className="absolute left-2 top-2 rounded bg-amber-400 px-1.5 py-0.5 text-[11px] font-bold text-ink">Pending</span>}
          {showSchool && <span className="absolute bottom-2 left-2 rounded bg-background/90 px-1.5 py-0.5 text-[11px] font-bold text-ink">{listing.school.short_name}</span>}
        </div>
        <div className="pt-2.5">
          <p className="type-wide text-[15px] font-extrabold text-ink">{priceLabel(listing.price_cents)}</p>
          <h3 className="mt-0.5 truncate text-sm text-ink">{listing.title}</h3>
          <p className="mt-0.5 truncate text-[13px] text-muted">{detail}</p>
        </div>
      </Link>
    </article>
  );
}
