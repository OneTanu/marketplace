export type ListingCondition = "new_with_tags" | "like_new" | "excellent" | "good" | "fair" | "poor";

export type ListingColor = "black" | "white" | "grey" | "blue" | "brown" | "tan" | "red" | "green" | "multicolor";

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
  waist?: number;
  inseam?: number;
  color?: ListingColor;
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
  { slug: "campus-items", name: "Campus items" },
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
    { slug: "pants", name: "Pants" },
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
  return brand.toLowerCase().replace(/[’']/g, "").replace(/[^a-z0-9]+/g, "-").replace(/(^-|-$)/g, "");
}

export const CONDITION_LABELS: Record<ListingCondition, string> = {
  new_with_tags: "Brand new",
  like_new: "Like new",
  excellent: "Used - Excellent",
  good: "Used - Good",
  fair: "Used - Fair",
  poor: "Poor condition",
};

export const CONDITION_DESCRIPTIONS: Record<ListingCondition, string> = {
  new_with_tags: "Never worn, with the original tags still included",
  like_new: "Tried on or worn briefly, with no visible wear",
  excellent: "Light use and only minimal signs of wear",
  good: "Regularly used, with small signs of wear shown in the listing",
  fair: "Noticeable wear or flaws, all clearly shown by the seller",
  poor: "Needs repair, restoration, or a creative second life",
};

export const DISCOVERY_COLORS: { slug: ListingColor; name: string; swatch: string }[] = [
  { slug: "black", name: "Black", swatch: "#171717" },
  { slug: "white", name: "White", swatch: "#ffffff" },
  { slug: "grey", name: "Grey", swatch: "#8b8b8b" },
  { slug: "blue", name: "Blue", swatch: "#3569a8" },
  { slug: "brown", name: "Brown", swatch: "#77513a" },
  { slug: "tan", name: "Tan", swatch: "#c29a68" },
  { slug: "red", name: "Red", swatch: "#b73232" },
  { slug: "green", name: "Green", swatch: "#48724e" },
  { slug: "multicolor", name: "Multicolor", swatch: "linear-gradient(135deg,#e85d5d 0 33%,#f1c75b 33% 66%,#477bc1 66%)" },
];

// Temporary preview records. Replace this export with GET /api/listings/ when
// the Listings workstream publishes its read contract.
export const DISCOVERY_PREVIEW_LISTINGS: DiscoveryListing[] = [
  { id: "photo-5", title: "Tan washed canvas chore jacket", price_cents: 3600, currency: "USD", condition: "good", category: { slug: "clothing", name: "Clothing" }, school: { slug: "umd", short_name: "UMD" }, seller: { username: "mitchellscloset", first_name: "Mitchell" }, image_url: "/demo-listings/real/tan-washed-chore-jacket.jpg", audience: "men", fashion_category: "coats-jackets", size: "M", color: "tan", created_at: "2026-10-07T16:40:00Z", is_bookmarked: false },
  { id: "photo-6", title: "Coach signature crossbody bag", price_cents: 5500, currency: "USD", condition: "good", category: { slug: "accessories", name: "Accessories" }, school: { slug: "umd", short_name: "UMD" }, seller: { username: "mitchellscloset", first_name: "Mitchell" }, image_url: "/demo-listings/real/coach-signature-crossbody.jpg", audience: "unisex", fashion_category: "bags", brand: "Coach", size: "One size", color: "black", created_at: "2026-10-07T16:35:00Z", is_bookmarked: false },
  { id: "photo-7", title: "Black washed wide-leg jeans", price_cents: 2800, currency: "USD", condition: "good", category: { slug: "clothing", name: "Clothing" }, school: { slug: "umd", short_name: "UMD" }, seller: { username: "mitchellscloset", first_name: "Mitchell" }, image_url: "/demo-listings/real/black-washed-wide-jeans.jpg", audience: "men", fashion_category: "jeans", waist: 32, inseam: 32, color: "black", created_at: "2026-10-07T16:30:00Z", is_bookmarked: false },
  { id: "photo-8", title: "Black straight-leg sweatpants", price_cents: 2000, currency: "USD", condition: "good", category: { slug: "clothing", name: "Clothing" }, school: { slug: "umd", short_name: "UMD" }, seller: { username: "mitchellscloset", first_name: "Mitchell" }, image_url: "/demo-listings/real/black-straight-sweatpants.jpg", audience: "men", fashion_category: "pants", size: "M", color: "black", created_at: "2026-10-07T16:25:00Z", is_bookmarked: false },
  { id: "photo-9", title: "Adidas three-stripe track pants", price_cents: 2500, currency: "USD", condition: "good", category: { slug: "clothing", name: "Clothing" }, school: { slug: "umd", short_name: "UMD" }, seller: { username: "mitchellscloset", first_name: "Mitchell" }, image_url: "/demo-listings/real/adidas-three-stripe-track-pants.jpg", audience: "men", fashion_category: "pants", brand: "Adidas", size: "M", color: "black", created_at: "2026-10-07T16:20:00Z", is_bookmarked: false },
  { id: "photo-10", title: "Timberland wheat waterproof boots", price_cents: 6500, currency: "USD", condition: "good", category: { slug: "shoes", name: "Shoes" }, school: { slug: "umd", short_name: "UMD" }, seller: { username: "mitchellscloset", first_name: "Mitchell" }, image_url: "/demo-listings/real/timberland-wheat-boots.jpg", audience: "men", fashion_category: "shoes", brand: "Timberland", size: "10", color: "tan", created_at: "2026-10-07T16:15:00Z", is_bookmarked: false },
  { id: "photo-11", title: "Grey Yeezy-style foam runners", price_cents: 4500, currency: "USD", condition: "good", category: { slug: "shoes", name: "Shoes" }, school: { slug: "umd", short_name: "UMD" }, seller: { username: "mitchellscloset", first_name: "Mitchell" }, image_url: "/demo-listings/real/grey-foam-runners.jpg", audience: "men", fashion_category: "shoes", brand: "Adidas", size: "10", color: "grey", created_at: "2026-10-07T16:10:00Z", is_bookmarked: false },
  { id: "photo-12", title: "Black chunky canvas sneakers", price_cents: 5000, currency: "USD", condition: "good", category: { slug: "shoes", name: "Shoes" }, school: { slug: "umd", short_name: "UMD" }, seller: { username: "mitchellscloset", first_name: "Mitchell" }, image_url: "/demo-listings/real/black-chunky-canvas-sneakers.jpg", audience: "men", fashion_category: "shoes", size: "10", color: "black", created_at: "2026-10-07T16:05:00Z", is_bookmarked: false },
  { id: "photo-13", title: "Black Squier Stratocaster electric guitar", price_cents: 14000, currency: "USD", condition: "good", category: { slug: "music", name: "Musical instruments" }, school: { slug: "umd", short_name: "UMD" }, seller: { username: "mitchellscloset", first_name: "Mitchell" }, image_url: "/demo-listings/real/black-squier-stratocaster.jpg", brand: "Squier", color: "black", created_at: "2026-10-07T16:00:00Z", is_bookmarked: false },
  { id: "photo-1", title: "Faded black canvas zip hoodie", price_cents: 3800, currency: "USD", condition: "good", category: { slug: "clothing", name: "Clothing" }, school: { slug: "umd", short_name: "UMD" }, seller: { username: "mitchellscloset", first_name: "Mitchell" }, image_url: "/demo-listings/real/faded-black-zip-hoodie.jpg", audience: "men", fashion_category: "hoodies-sweats", size: "M", color: "black", created_at: "2026-10-07T15:30:00Z", is_bookmarked: false },
  { id: "photo-2", title: "White Atelier graphic tee", price_cents: 1800, currency: "USD", condition: "like_new", category: { slug: "clothing", name: "Clothing" }, school: { slug: "umd", short_name: "UMD" }, seller: { username: "mitchellscloset", first_name: "Mitchell" }, image_url: "/demo-listings/real/white-graphic-tee.jpg", audience: "men", fashion_category: "t-shirts", brand: "Atelier", size: "M", color: "white", created_at: "2026-10-07T15:20:00Z", is_bookmarked: false },
  { id: "photo-3", title: "Brown faux-leather zip jacket", price_cents: 4200, currency: "USD", condition: "like_new", category: { slug: "clothing", name: "Clothing" }, school: { slug: "umd", short_name: "UMD" }, seller: { username: "mitchellscloset", first_name: "Mitchell" }, image_url: "/demo-listings/real/brown-novamen-jacket.jpg", audience: "men", fashion_category: "coats-jackets", brand: "NovaMEN", size: "M", color: "brown", created_at: "2026-10-07T15:10:00Z", is_bookmarked: false },
  { id: "photo-4", title: "Light-wash Levi's relaxed jeans", price_cents: 2600, currency: "USD", condition: "good", category: { slug: "clothing", name: "Clothing" }, school: { slug: "umd", short_name: "UMD" }, seller: { username: "mitchellscloset", first_name: "Mitchell" }, image_url: "/demo-listings/real/light-wash-jeans.jpg", audience: "men", fashion_category: "jeans", brand: "Levi's", waist: 32, inseam: 30, color: "blue", created_at: "2026-10-07T15:00:00Z", is_bookmarked: false },
];

export function formatPrice(cents: number, currency = "USD") {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency,
    maximumFractionDigits: cents % 100 === 0 ? 0 : 2,
  }).format(cents / 100);
}
