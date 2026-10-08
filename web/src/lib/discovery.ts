// The feed's filters, as URL query parameters and as the API query. The URL is the source of
// truth: a filtered feed can be reloaded or shared, and the same parameters can later be saved
// as a watched search.

import type { components, operations } from "@/lib/api/schema";
import { COLORS, CONDITIONS } from "@/lib/listing-options";
import { centsToDollars } from "@/lib/money";

export type ListingCard = components["schemas"]["ListingCard"];
type Color = components["schemas"]["ColorEnum"];
type Condition = components["schemas"]["ConditionEnum"];
type FeedApiQuery = NonNullable<operations["listings_list"]["parameters"]["query"]>;
export type FeedSort = NonNullable<FeedApiQuery["sort"]>;

export const SORTS: { value: FeedSort; label: string }[] = [
  { value: "newest", label: "Newly listed" },
  { value: "price_asc", label: "Price: low to high" },
  { value: "price_desc", label: "Price: high to low" },
];

export const COLOR_SWATCHES: Record<Color, string> = {
  black: "#171717",
  white: "#ffffff",
  gray: "#8b8b8b",
  brown: "#77513a",
  beige: "#d8c3a0",
  red: "#b73232",
  pink: "#e891b4",
  orange: "#e07a2e",
  yellow: "#efc94c",
  green: "#48724e",
  blue: "#3569a8",
  purple: "#7a4fa3",
  gold: "linear-gradient(135deg,#f3d27a,#b8892b)",
  silver: "linear-gradient(135deg,#f0f0f0,#9a9a9a)",
  multi: "linear-gradient(135deg,#e85d5d 0 33%,#f1c75b 33% 66%,#477bc1 66%)",
};

export const CONDITION_DESCRIPTIONS: Record<Condition, string> = {
  new_with_tags: "Never worn or used, with the original tags or packaging",
  like_new: "Used briefly, with no visible wear",
  good: "Regularly used, with small signs of wear shown in the photos",
  fair: "Noticeable wear or flaws, all clearly shown by the seller",
  poor: "Needs repair, restoration, or a creative second life",
};

// Brand filter shortcuts. Brands are free text on listings; the filter matches any case.
export const POPULAR_BRANDS = [
  "Nike",
  "Adidas",
  "Aritzia",
  "Levi's",
  "Lululemon",
  "Abercrombie",
  "Carhartt",
  "The North Face",
  "New Balance",
  "Coach",
  "Zara",
  "Urban Outfitters",
];

export const GENERAL_SIZES = ["XS", "S", "M", "L", "XL", "XXL", "One size"];
export const SHOE_SIZES = ["5", "6", "7", "8", "9", "10", "11", "12", "13"];
// Jeans and pants are sized "<waist>x<length>" (see the Sell form's SizeField).
export const WAIST_SIZES = ["26", "28", "30", "32", "34", "36", "38", "40"];
export const LENGTH_SIZES = ["28", "30", "32", "34", "36"];
export const PANTS_SLUG = /-(jeans|pants)$/;

/** The feed filters a URL holds. Prices are whole dollars in the URL and cents in the API. */
export type FeedParams = {
  school: string; // a school slug, "all", or "" for the viewer's school
  category: string;
  brand: string;
  condition: Condition | "";
  color: Color | "";
  size: string;
  minPrice: string;
  maxPrice: string;
  sort: FeedSort;
  search: string;
};

const URL_KEYS: Record<keyof FeedParams, string> = {
  school: "school",
  category: "category",
  brand: "brand",
  condition: "condition",
  color: "color",
  size: "size",
  minPrice: "min_price",
  maxPrice: "max_price",
  sort: "sort",
  search: "search",
};

const DEFAULT_SORT: FeedSort = "newest";

export function readFeedParams(params: URLSearchParams): FeedParams {
  const get = (key: keyof FeedParams) => params.get(URL_KEYS[key])?.trim() ?? "";
  const sort = get("sort") as FeedSort;
  const dollars = (key: "minPrice" | "maxPrice") => (/^\d{1,6}$/.test(get(key)) ? get(key) : "");
  return {
    school: get("school"),
    category: get("category"),
    brand: get("brand"),
    // Values the API would refuse (an old link, a typo) are dropped rather than sent.
    condition: CONDITIONS.find((c) => c.value === get("condition"))?.value ?? "",
    color: COLORS.find((c) => c.value === get("color"))?.value ?? "",
    size: get("size"),
    minPrice: dollars("minPrice"),
    maxPrice: dollars("maxPrice"),
    sort: SORTS.some((s) => s.value === sort) ? sort : DEFAULT_SORT,
    search: get("search"),
  };
}

/** The query string for these filters, leaving out empty ones and the default sort. */
export function feedQueryString(feed: FeedParams): string {
  const params = new URLSearchParams();
  for (const key of Object.keys(URL_KEYS) as (keyof FeedParams)[]) {
    const value = feed[key];
    if (!value || (key === "sort" && value === DEFAULT_SORT)) continue;
    params.set(URL_KEYS[key], value);
  }
  const query = params.toString();
  return query ? `?${query}` : "";
}

/** The API query for these filters. A school page passes its school, which wins over the URL.
 * Keyword search isn't part of the feed API yet, so `search` isn't sent. */
export function feedApiQuery(feed: FeedParams, fixedSchool?: string): FeedApiQuery {
  const query: FeedApiQuery = { sort: feed.sort };
  const school = fixedSchool ?? feed.school;
  if (school) query.school = school;
  if (feed.category) query.category = feed.category;
  if (feed.brand) query.brand = feed.brand;
  if (feed.condition) query.condition = [feed.condition];
  if (feed.color) query.color = [feed.color];
  if (feed.size) query.size = feed.size;
  if (feed.minPrice) query.min_price = Number(feed.minPrice) * 100;
  if (feed.maxPrice) query.max_price = Number(feed.maxPrice) * 100;
  return query;
}

export function priceLabel(cents: number) {
  return cents === 0 ? "Free" : centsToDollars(cents);
}
