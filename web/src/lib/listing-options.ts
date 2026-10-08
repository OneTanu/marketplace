import type { components } from "@/lib/api/schema";

type Condition = components["schemas"]["ConditionEnum"];
type Color = components["schemas"]["ColorEnum"];

// Labels for the choices the API accepts. Typed against the generated schema, so the type
// check fails if the backend adds or renames a choice.
export const CONDITIONS: { value: Condition; label: string }[] = [
  { value: "new_with_tags", label: "New with tags" },
  { value: "like_new", label: "Like new" },
  { value: "good", label: "Good" },
  { value: "fair", label: "Fair" },
  { value: "poor", label: "Poor" },
];

export const COLORS: { value: Color; label: string }[] = [
  { value: "black", label: "Black" },
  { value: "white", label: "White" },
  { value: "gray", label: "Gray" },
  { value: "brown", label: "Brown" },
  { value: "beige", label: "Beige" },
  { value: "red", label: "Red" },
  { value: "pink", label: "Pink" },
  { value: "orange", label: "Orange" },
  { value: "yellow", label: "Yellow" },
  { value: "green", label: "Green" },
  { value: "blue", label: "Blue" },
  { value: "purple", label: "Purple" },
  { value: "gold", label: "Gold" },
  { value: "silver", label: "Silver" },
  { value: "multi", label: "Multicolor" },
];

// Matches the backend's FREE_CATEGORY_SLUG: items in Free are always $0.
export const FREE_CATEGORY_SLUG = "free";

// Mirrors the backend's photo rules so sellers hear about a bad photo before uploading.
export const MAX_PHOTOS = 10;
export const MAX_PHOTO_BYTES = 10 * 1024 * 1024;
export const PHOTO_TYPES = ["image/jpeg", "image/png", "image/webp"];
