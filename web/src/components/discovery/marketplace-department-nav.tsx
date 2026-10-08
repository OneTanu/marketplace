"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useEffect, useRef, useState } from "react";

import { categoryTree, loadItemCategories, SHOE_SHORTCUTS, type Category, type CategoryTree } from "@/lib/categories";
import { feedQueryString, POPULAR_BRANDS, readFeedParams, type FeedParams } from "@/lib/discovery";

const BRANDS = "brands";

/** Department tabs under the header on the feed pages: All, every department (with a menu of
 * its subcategories), and popular brands. A subcategory's department shows as current, so
 * Shoes › Men's lights up the Shoes tab. */
export function MarketplaceDepartmentNav({ schoolSlug }: { schoolSlug?: string }) {
  const searchParams = useSearchParams();
  const feed = readFeedParams(searchParams);
  const [tree, setTree] = useState<CategoryTree | null>(null);
  const [activeMenu, setActiveMenu] = useState<string | null>(null);
  // When hover opened a menu, so the click that usually follows doesn't close it again.
  const hoverOpenedAt = useRef(0);
  const basePath = schoolSlug ? `/schools/${schoolSlug}` : "/search";

  useEffect(() => {
    loadItemCategories().then((categories) => setTree(categories ? categoryTree(categories) : null));
  }, []);

  useEffect(() => {
    function escape(event: KeyboardEvent) {
      if (event.key === "Escape") setActiveMenu(null);
    }
    document.addEventListener("keydown", escape);
    return () => document.removeEventListener("keydown", escape);
  }, []);

  // Times are the events' own timestamps (milliseconds since the page loaded).
  function hoverMenu(menu: string, at: number) {
    if (activeMenu !== menu) hoverOpenedAt.current = at;
    setActiveMenu(menu);
  }

  function clickMenu(menu: string, at: number) {
    const justHovered = at - hoverOpenedAt.current < 400;
    setActiveMenu(activeMenu === menu && !justHovered ? null : menu);
  }

  const current = tree?.bySlug.get(feed.category);
  const currentDepartment = current && tree?.departmentOf(current);

  function href(patch: Partial<FeedParams>) {
    return `${basePath}${feedQueryString({ ...feed, size: "", ...patch })}`;
  }

  const tabClass = (active: boolean) => `relative flex min-h-12 min-w-max items-center gap-1 px-3 text-sm font-semibold transition hover:text-ink ${active ? "text-ink after:absolute after:inset-x-3 after:bottom-0 after:h-0.5 after:bg-ink" : "text-muted"}`;
  const menuLink = "flex items-center justify-between border-b border-line py-3 text-sm font-semibold transition hover:text-brand";
  const menuDepartment = tree?.departments.find((d) => d.slug === activeMenu);
  const menuItems: { key: string; label: string; href: string }[] = menuDepartment
    ? [
        ...(tree?.children.get(menuDepartment.id) ?? []).map((child: Category) => ({ key: child.slug, label: child.name, href: href({ category: child.slug, brand: "" }) })),
        ...(SHOE_SHORTCUTS[menuDepartment.slug] ? [{ key: "shoes", label: SHOE_SHORTCUTS[menuDepartment.slug].name, href: href({ category: SHOE_SHORTCUTS[menuDepartment.slug].slug, brand: "" }) }] : []),
      ]
    : activeMenu === BRANDS
      ? POPULAR_BRANDS.map((name) => ({ key: name, label: name, href: href({ brand: name }) }))
      : [];

  return (
    <nav className="relative mx-auto max-w-6xl px-4 sm:px-6" aria-label="Marketplace departments" onMouseLeave={() => setActiveMenu(null)}>
      <div className="-mx-1 flex overflow-x-auto [scrollbar-width:none]">
        <Link href={href({ category: "" })} aria-current={!feed.category ? "page" : undefined} className={tabClass(!feed.category)}>All</Link>
        {tree?.departments.map((department) => {
          const active = currentDepartment?.id === department.id;
          const hasMenu = Boolean(tree.children.get(department.id)?.length);
          if (!hasMenu) return <Link key={department.id} href={href({ category: department.slug })} aria-current={active ? "page" : undefined} className={tabClass(active)}>{department.name}</Link>;
          return <button key={department.id} type="button" className={tabClass(active)} aria-expanded={activeMenu === department.slug} onMouseEnter={(e) => hoverMenu(department.slug, e.timeStamp)} onClick={(e) => clickMenu(department.slug, e.timeStamp)}>{department.name}<svg aria-hidden="true" viewBox="0 0 12 12" className={`size-2.5 transition ${activeMenu === department.slug ? "rotate-180" : ""}`} fill="none" stroke="currentColor" strokeWidth={1.8}><path d="m2 4 4 4 4-4" /></svg></button>;
        })}
        {tree && <button type="button" className={`${tabClass(Boolean(feed.brand))} ml-2 border-l border-line pl-5`} aria-expanded={activeMenu === BRANDS} onMouseEnter={(e) => hoverMenu(BRANDS, e.timeStamp)} onClick={(e) => clickMenu(BRANDS, e.timeStamp)}>Brands</button>}
      </div>

      {activeMenu && <div className="absolute inset-x-4 top-full z-30 rounded-b-xl border border-line bg-background p-5 shadow-[0_24px_48px_-12px_rgb(23_22_43/18%)] sm:inset-x-6 sm:p-7">
        <div className="flex items-center justify-between"><h2 className="type-wide text-lg font-extrabold">{menuDepartment?.name ?? "Popular brands"}</h2><button type="button" onClick={() => setActiveMenu(null)} className="grid size-9 place-items-center rounded-lg text-xl text-muted transition hover:bg-surface hover:text-ink" aria-label="Close category menu">×</button></div>
        <div className="mt-3 grid grid-cols-2 gap-x-8 sm:grid-cols-3 lg:grid-cols-4">
          {menuItems.map((item) => <Link key={item.key} href={item.href} onClick={() => setActiveMenu(null)} className={menuLink}>{item.label}</Link>)}
        </div>
        {menuDepartment && <Link href={href({ category: menuDepartment.slug, brand: "" })} onClick={() => setActiveMenu(null)} className="btn btn-secondary btn-sm mt-5">Shop all {menuDepartment.name}</Link>}
      </div>}
    </nav>
  );
}
