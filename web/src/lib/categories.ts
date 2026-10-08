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
