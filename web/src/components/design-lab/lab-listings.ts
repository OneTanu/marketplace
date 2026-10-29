// Sample listings for the design lab, shaped like the feed API's cards so the real ListingCard
// renders them. Lab-only: the app itself shows real listings from GET /api/listings/.

import type { ListingCard } from "@/lib/discovery";

import { labSchool } from "./lab-schools";

/** A feed card plus the school slug the lab's palettes are keyed by (the API card has none). */
export type LabListing = ListingCard & { school: ListingCard["school"] & { slug: string } };

const SELLER = { id: 1, username: "mayasells" };
const POSTED = "2026-10-07T16:00:00Z";

function card(
  id: number,
  title: string,
  priceCents: number,
  photo: string,
  details: { condition?: ListingCard["condition"]; size?: string; brand?: string } = {},
): LabListing {
  return {
    id,
    status: "available",
    title,
    price_cents: priceCents,
    currency: "USD",
    cover_url: `/demo-listings/real/${photo}.jpg`,
    condition: details.condition ?? "good",
    size: details.size ?? "",
    brand: details.brand ?? "",
    school: { id: 1, short_name: "UMD", slug: "umd", colors: labSchool("umd").colors },
    seller: SELLER,
    is_bookmarked: false,
    created_at: POSTED,
  };
}

export const LAB_LISTINGS = {
  hoodie: card(1, "Faded black canvas zip hoodie", 3800, "faded-black-zip-hoodie", { size: "M" }),
  tee: card(2, "White Atelier graphic tee", 1800, "white-graphic-tee", { condition: "like_new", brand: "Atelier", size: "M" }),
  leatherJacket: card(3, "Brown faux-leather zip jacket", 4200, "brown-novamen-jacket", { condition: "like_new", brand: "NovaMEN", size: "M" }),
  jeans: card(4, "Light-wash Levi's relaxed jeans", 2600, "light-wash-jeans", { brand: "Levi's", size: "32x30" }),
  choreJacket: card(5, "Tan washed canvas chore jacket", 3600, "tan-washed-chore-jacket", { size: "M" }),
  bag: card(6, "Coach signature crossbody bag", 5500, "coach-signature-crossbody", { brand: "Coach", size: "One size" }),
  boots: card(10, "Timberland wheat waterproof boots", 6500, "timberland-wheat-boots", { brand: "Timberland", size: "10" }),
  sneakers: card(12, "Black chunky canvas sneakers", 5000, "black-chunky-canvas-sneakers", { size: "10" }),
  guitar: card(13, "Black Squier Stratocaster electric guitar", 14000, "black-squier-stratocaster", { brand: "Squier" }),
} satisfies Record<string, LabListing>;

/** The listing as if posted at another lab school. */
export function atSchool(listing: LabListing, slug: string): LabListing {
  const school = labSchool(slug);
  return { ...listing, school: { id: listing.school.id, short_name: school.shortName, slug: school.slug, colors: school.colors } };
}
