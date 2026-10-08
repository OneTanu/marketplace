import { api } from "@/lib/api/client";
import type { components } from "@/lib/api/schema";

export type Category = components["schemas"]["Category"];

/** Top-level categories (departments) in display order, and each one's subcategories. The API
 * sends the tree flat, siblings already in display order. */
export function categoryTree(categories: Category[]) {
  const children = new Map<number, Category[]>();
  for (const category of categories) {
    if (category.parent === null) continue;
    children.set(category.parent, [...(children.get(category.parent) ?? []), category]);
  }
  // A category whose parent isn't in the list (retired) is offered at the top level.
  const ids = new Set(categories.map((c) => c.id));
  const departments = categories.filter((c) => c.parent === null || !ids.has(c.parent));
  const bySlug = new Map(categories.map((c) => [c.slug, c]));
  /** The department a category is in (itself, for a department). */
  const departmentOf = (category: Category) =>
    departments.find((d) => d.id === category.id || d.id === category.parent);
  return { departments, children, bySlug, departmentOf };
}

export type CategoryTree = ReturnType<typeof categoryTree>;

// Shoes is its own department, but Women and Men link across to their shoes with a pill.
// These are UI shortcuts, not categories.
export const SHOE_SHORTCUTS: Record<string, { slug: string; name: string }> = {
  women: { slug: "shoes-women", name: "Shoes" },
  men: { slug: "shoes-men", name: "Shoes" },
};

let itemCategories: Promise<Category[] | null> | null = null;

/** The active item categories, shared by the header nav and the feed. Null when signed out
 * (the API is for verified students only) or the request failed; only a successful answer is
 * kept, so signing in later in the same tab loads them. */
export function loadItemCategories(): Promise<Category[] | null> {
  itemCategories ??= api
    .GET("/api/categories/", { params: { query: { kind: "item" } } })
    .then(({ data }) => data ?? null)
    .catch(() => null)
    .then((categories) => {
      if (!categories) itemCategories = null;
      return categories;
    });
  return itemCategories;
}
