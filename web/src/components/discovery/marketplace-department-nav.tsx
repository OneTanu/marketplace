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
    const query = next.toString();
    return `${basePath}${query ? `?${query}` : ""}`;
  }

  function menuTitle(menu: MenuName) {
    if (menu === "brands") return "Popular Brands";
    if (menu === "accessories") return "Shop Accessories";
    return `Shop ${menu === "women" ? "Women" : "Men"}`;
  }

  return (
    <nav className="relative mx-auto max-w-6xl px-4 sm:px-6" aria-label="Marketplace departments" onMouseLeave={() => setActiveMenu(null)}>
      <div className="flex gap-1 overflow-x-auto py-2 [scrollbar-width:none] sm:gap-3">
        {DISCOVERY_CATEGORIES.map((item) => {
          const hasMenu = ["women", "men", "accessories", "brands"].includes(item.slug);
          const active = category === item.slug;
          const className = `min-w-max rounded-lg px-4 py-2 text-sm font-black transition hover:bg-background ${active ? "bg-foreground text-white" : item.slug === "campus-items" ? "ml-2 border-l border-line pl-6 text-brand" : "text-foreground/75"}`;
          if (hasMenu) {
            const menu = item.slug as MenuName;
            return <button key={item.slug} type="button" className={className} aria-expanded={activeMenu === menu} onMouseEnter={() => setActiveMenu(menu)} onClick={() => setActiveMenu(menu)}>{item.name}<span className="ml-1.5 text-[10px]" aria-hidden="true">⌄</span></button>;
          }
          return <a key={item.slug} href={categoryHref(item.slug)} className={className}>{item.name}</a>;
        })}
      </div>

      {activeMenu && <div className="absolute inset-x-4 top-full z-30 mt-1 rounded-2xl border border-line bg-white p-5 shadow-[0_20px_55px_rgb(20_35_29/16%)] sm:inset-x-6 sm:p-7">
        <div className="flex items-center justify-between"><h2 className="text-lg font-black">{menuTitle(activeMenu)}</h2><button onClick={() => setActiveMenu(null)} className="grid size-8 place-items-center rounded-full bg-background text-lg" aria-label="Close category menu">×</button></div>
        <div className="mt-4 grid grid-cols-2 gap-x-8 sm:grid-cols-3 lg:grid-cols-4">
          {(activeMenu === "women" || activeMenu === "men") && FASHION_DEPARTMENTS[activeMenu].map((item) => <a key={item.slug} href={categoryHref(activeMenu, { subcategory: item.slug })} className="border-b border-line py-3 text-sm font-semibold transition hover:text-brand">{item.name}</a>)}
          {activeMenu === "accessories" && ACCESSORY_DEPARTMENTS.map((item) => <a key={item.slug} href={categoryHref("accessories", { subcategory: item.slug })} className="border-b border-line py-3 text-sm font-semibold transition hover:text-brand">{item.name}</a>)}
          {activeMenu === "brands" && POPULAR_BRANDS.map((item) => <a key={item.slug} href={categoryHref("brands", { brand: item.slug })} className="border-b border-line py-3 text-sm font-semibold transition hover:text-brand">{item.name}</a>)}
        </div>
        <a href={categoryHref(activeMenu)} className="mt-5 inline-block text-sm font-black underline decoration-brand/30 underline-offset-4">Shop all {activeMenu === "brands" ? "brands" : activeMenu}</a>
      </div>}
    </nav>
  );
}
