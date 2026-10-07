"use client";

import { useSearchParams } from "next/navigation";
import { useState } from "react";

import {
  ACCESSORY_DEPARTMENTS,
  DISCOVERY_CATEGORIES,
  FASHION_DEPARTMENTS,
  POPULAR_BRANDS,
} from "@/lib/discovery";

type MenuName = "women" | "men" | "accessories" | "brands";

export function MarketplaceDepartmentNav({ schoolSlug }: { schoolSlug?: string }) {
  const searchParams = useSearchParams();
  const category = searchParams.get("category") ?? "trending";
  const [activeMenu, setActiveMenu] = useState<MenuName | null>(null);
  const basePath = schoolSlug ? `/schools/${schoolSlug}` : "/search";

  function categoryHref(nextCategory: string, options: { subcategory?: string; brand?: string } = {}) {
    const next = new URLSearchParams(searchParams.toString());
    if (nextCategory === "trending") next.delete("category");
    else next.set("category", nextCategory);
    if (options.subcategory) next.set("subcategory", options.subcategory);
    else next.delete("subcategory");
    if (options.brand) next.set("brand", options.brand);
    else next.delete("brand");
    next.delete("size");
    next.delete("waist");
    next.delete("inseam");
    const query = next.toString();
    return `${basePath}${query ? `?${query}` : ""}`;
  }

  function menuTitle(menu: MenuName) {
    if (menu === "brands") return "Popular brands";
    if (menu === "accessories") return "Accessories";
    return menu === "women" ? "Women" : "Men";
  }

  const menuLink = "flex items-center justify-between border-b border-line py-3 text-sm font-semibold transition hover:text-brand";

  return (
    <nav className="relative mx-auto max-w-6xl px-4 sm:px-6" aria-label="Marketplace departments" onMouseLeave={() => setActiveMenu(null)}>
      <div className="-mx-1 flex overflow-x-auto [scrollbar-width:none]">
        {DISCOVERY_CATEGORIES.map((item) => {
          const hasMenu = ["women", "men", "accessories", "brands"].includes(item.slug);
          const active = category === item.slug;
          const campus = item.slug === "campus-items";
          const className = `relative flex min-h-12 min-w-max items-center gap-1 px-3 text-sm font-semibold transition hover:text-ink ${active ? "text-ink after:absolute after:inset-x-3 after:bottom-0 after:h-0.5 after:bg-ink" : "text-muted"} ${campus ? "ml-2 border-l border-line pl-5" : ""}`;
          if (hasMenu) {
            const menu = item.slug as MenuName;
            return <button key={item.slug} type="button" className={className} aria-expanded={activeMenu === menu} onMouseEnter={() => setActiveMenu(menu)} onClick={() => setActiveMenu(activeMenu === menu ? null : menu)}>{item.name}<svg aria-hidden="true" viewBox="0 0 12 12" className={`size-2.5 transition ${activeMenu === menu ? "rotate-180" : ""}`} fill="none" stroke="currentColor" strokeWidth={1.8}><path d="m2 4 4 4 4-4" /></svg></button>;
          }
          return <a key={item.slug} href={categoryHref(item.slug)} aria-current={active ? "page" : undefined} className={className}>{item.name}</a>;
        })}
      </div>

      {activeMenu && <div className="absolute inset-x-4 top-full z-30 rounded-b-xl border border-line bg-background p-5 shadow-[0_24px_48px_-12px_rgb(23_22_43/18%)] sm:inset-x-6 sm:p-7">
        <div className="flex items-center justify-between"><h2 className="type-wide text-lg font-extrabold">{menuTitle(activeMenu)}</h2><button onClick={() => setActiveMenu(null)} className="grid size-9 place-items-center rounded-lg text-xl text-muted transition hover:bg-surface hover:text-ink" aria-label="Close category menu">×</button></div>
        <div className="mt-3 grid grid-cols-2 gap-x-8 sm:grid-cols-3 lg:grid-cols-4">
          {(activeMenu === "women" || activeMenu === "men") && FASHION_DEPARTMENTS[activeMenu].map((item) => <a key={item.slug} href={categoryHref(activeMenu, { subcategory: item.slug })} className={menuLink}>{item.name}</a>)}
          {activeMenu === "accessories" && ACCESSORY_DEPARTMENTS.map((item) => <a key={item.slug} href={categoryHref("accessories", { subcategory: item.slug })} className={menuLink}>{item.name}</a>)}
          {activeMenu === "brands" && POPULAR_BRANDS.map((item) => <a key={item.slug} href={categoryHref("brands", { brand: item.slug })} className={menuLink}>{item.name}</a>)}
        </div>
        <a href={categoryHref(activeMenu)} className="btn btn-secondary btn-sm mt-5">Shop all {activeMenu === "brands" ? "brands" : activeMenu}</a>
      </div>}
    </nav>
  );
}
