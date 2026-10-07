export type ListingCondition = "new_with_tags" | "like_new" | "good" | "fair" | "poor";

export type DiscoveryListing = {
  id: string;
  title: string;
  price_cents: number;
  currency: "USD";
  condition: ListingCondition;
  category: { slug: string; name: string };
  school: { slug: string; short_name: string };
  seller: { username: string; first_name: string };
  image_url: string;
  audience?: "women" | "men" | "unisex";
  fashion_category?: string;
  brand?: string;
  size?: string;
  created_at: string;
  is_bookmarked: boolean;
};

export const DISCOVERY_CATEGORIES = [
  { slug: "trending", name: "Trending" },
  { slug: "women", name: "Women" },
  { slug: "men", name: "Men" },
  { slug: "unisex", name: "Unisex" },
  { slug: "brands", name: "Brands" },
  { slug: "shoes", name: "Shoes" },
  { slug: "accessories", name: "Accessories" },
  { slug: "campus-items", name: "Campus Items" },
] as const;

export const FASHION_DEPARTMENTS = {
  women: [
    { slug: "tops", name: "Tops" },
    { slug: "jeans", name: "Jeans" },
    { slug: "sweaters", name: "Sweaters" },
    { slug: "skirts", name: "Skirts" },
    { slug: "dresses", name: "Dresses" },
    { slug: "coats-jackets", name: "Coats & Jackets" },
    { slug: "shoes", name: "Shoes" },
    { slug: "bags", name: "Bags" },
    { slug: "accessories", name: "Accessories" },
  ],
  men: [
    { slug: "t-shirts", name: "T-shirts" },
    { slug: "shirts", name: "Shirts" },
    { slug: "jeans", name: "Jeans" },
    { slug: "hoodies-sweats", name: "Hoodies & Sweats" },
    { slug: "coats-jackets", name: "Coats & Jackets" },
    { slug: "shoes", name: "Shoes" },
    { slug: "bags", name: "Bags" },
    { slug: "accessories", name: "Accessories" },
  ],
} as const;

export const ACCESSORY_DEPARTMENTS = [
  { slug: "bags", name: "Bags" },
  { slug: "jewelry", name: "Jewelry" },
  { slug: "hats", name: "Hats" },
  { slug: "sunglasses", name: "Sunglasses" },
  { slug: "belts", name: "Belts" },
  { slug: "watches", name: "Watches" },
  { slug: "wallets", name: "Wallets" },
  { slug: "scarves", name: "Scarves" },
  { slug: "hair-accessories", name: "Hair Accessories" },
] as const;

export const POPULAR_BRANDS = [
  { slug: "nike", name: "Nike" },
  { slug: "adidas", name: "Adidas" },
  { slug: "aritzia", name: "Aritzia" },
  { slug: "levis", name: "Levi's" },
  { slug: "lululemon", name: "Lululemon" },
  { slug: "abercrombie", name: "Abercrombie" },
  { slug: "carhartt", name: "Carhartt" },
  { slug: "the-north-face", name: "The North Face" },
  { slug: "new-balance", name: "New Balance" },
  { slug: "coach", name: "Coach" },
  { slug: "zara", name: "Zara" },
  { slug: "urban-outfitters", name: "Urban Outfitters" },
] as const;

export function brandSlug(brand: string) {
  return brand.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/(^-|-$)/g, "");
}

export const CONDITION_LABELS: Record<ListingCondition, string> = {
  new_with_tags: "New with tags",
  like_new: "Like new",
  good: "Good",
  fair: "Fair",
  poor: "For parts",
};

// Temporary preview records. Replace this export with GET /api/listings/ when
// the Listings workstream publishes its read contract.
export const DISCOVERY_PREVIEW_LISTINGS: DiscoveryListing[] = [
  { id: "preview-1", title: "Vintage Maryland crewneck", price_cents: 2800, currency: "USD", condition: "good", category: { slug: "clothing", name: "Clothing" }, school: { slug: "umd", short_name: "UMD" }, seller: { username: "campuscloset", first_name: "Maya" }, image_url: "/demo-listings/crewneck.svg", audience: "unisex", fashion_category: "sweaters", brand: "Vintage", size: "M", created_at: "2026-10-03T22:00:00Z", is_bookmarked: false },
  { id: "preview-2", title: "Oversized denim jacket", price_cents: 4200, currency: "USD", condition: "like_new", category: { slug: "clothing", name: "Clothing" }, school: { slug: "umd", short_name: "UMD" }, seller: { username: "closetbyrae", first_name: "Rae" }, image_url: "/demo-listings/jacket.svg", audience: "women", fashion_category: "coats-jackets", brand: "Levi's", size: "L", created_at: "2026-10-03T20:30:00Z", is_bookmarked: true },
  { id: "preview-3", title: "Relaxed straight-leg jeans", price_cents: 2400, currency: "USD", condition: "good", category: { slug: "clothing", name: "Clothing" }, school: { slug: "umd", short_name: "UMD" }, seller: { username: "threadedterp", first_name: "Avery" }, image_url: "/demo-listings/jeans.svg", audience: "women", fashion_category: "jeans", brand: "Abercrombie", size: "28", created_at: "2026-10-02T18:00:00Z", is_bookmarked: false },
  { id: "preview-4", title: "Nike running shoes", price_cents: 3500, currency: "USD", condition: "good", category: { slug: "shoes", name: "Shoes" }, school: { slug: "umd", short_name: "UMD" }, seller: { username: "milesahead", first_name: "Chris" }, image_url: "/demo-listings/shoes.svg", audience: "men", fashion_category: "shoes", brand: "Nike", size: "10", created_at: "2026-10-02T15:15:00Z", is_bookmarked: false },
  { id: "preview-5", title: "Everyday canvas tote", price_cents: 1400, currency: "USD", condition: "like_new", category: { slug: "accessories", name: "Accessories" }, school: { slug: "umd", short_name: "UMD" }, seller: { username: "stylebysam", first_name: "Sam" }, image_url: "/demo-listings/tote.svg", audience: "unisex", fashion_category: "bags", brand: "Baggu", size: "One size", created_at: "2026-10-01T17:40:00Z", is_bookmarked: false },
  { id: "preview-6", title: "Ribbed everyday tee", price_cents: 1200, currency: "USD", condition: "like_new", category: { slug: "clothing", name: "Clothing" }, school: { slug: "umd", short_name: "UMD" }, seller: { username: "livscloset", first_name: "Olivia" }, image_url: "/demo-listings/tee.svg", audience: "women", fashion_category: "tops", brand: "Aritzia", size: "S", created_at: "2026-09-30T14:20:00Z", is_bookmarked: false },
  { id: "preview-7", title: "TI-84 Plus calculator", price_cents: 4500, currency: "USD", condition: "good", category: { slug: "electronics", name: "Electronics" }, school: { slug: "umd", short_name: "UMD" }, seller: { username: "alexk", first_name: "Alex" }, image_url: "/demo-listings/calculator.svg", created_at: "2026-09-29T19:10:00Z", is_bookmarked: false },
  { id: "preview-8", title: "Compact dorm mini fridge", price_cents: 6000, currency: "USD", condition: "like_new", category: { slug: "dorm", name: "Dorm" }, school: { slug: "umd", short_name: "UMD" }, seller: { username: "terpmoves", first_name: "Jordan" }, image_url: "/demo-listings/fridge.svg", created_at: "2026-09-28T13:00:00Z", is_bookmarked: false },
];

export function formatPrice(cents: number, currency = "USD") {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency,
    maximumFractionDigits: cents % 100 === 0 ? 0 : 2,
  }).format(cents / 100);
}
