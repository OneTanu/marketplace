"use client";

import { useSearchParams } from "next/navigation";
import { useState } from "react";

import { DISCOVERY_CATEGORIES, FASHION_DEPARTMENTS } from "@/lib/discovery";

export function MarketplaceDepartmentNav({ schoolSlug }: { schoolSlug: string }) {
  const searchParams = useSearchParams();
  const category = searchParams.get("category") ?? "trending";
  const [activeMenu, setActiveMenu] = useState<"women" | "men" | null>(null);

  return (
    <nav className="relative mx-auto max-w-6xl px-4 sm:px-6" aria-label="Marketplace departments" onMouseLeave={() => setActiveMenu(null)}>
      <div className="flex gap-1 overflow-x-auto py-2 [scrollbar-width:none] sm:gap-3">
        {DISCOVERY_CATEGORIES.map((item) => {
          const hasMenu = item.slug === "women" || item.slug === "men";
          const active = category === item.slug;
          const className = `min-w-max rounded-lg px-4 py-2 text-sm font-black transition hover:bg-background ${active ? "bg-foreground text-white" : item.slug === "campus-items" ? "ml-2 border-l border-line pl-6 text-brand" : "text-foreground/75"}`;
          if (hasMenu) {
            return <button key={item.slug} type="button" className={className} aria-expanded={activeMenu === item.slug} onMouseEnter={() => setActiveMenu(item.slug as "women" | "men")} onClick={() => setActiveMenu(item.slug as "women" | "men")}>{item.name}<span className="ml-1.5 text-[10px]" aria-hidden="true">⌄</span></button>;
          }
          return <a key={item.slug} href={`/schools/${schoolSlug}${item.slug === "trending" ? "" : `?category=${item.slug}`}`} className={className}>{item.name}</a>;
        })}
      </div>

      {activeMenu && <div className="absolute inset-x-4 top-full z-30 mt-1 rounded-2xl border border-line bg-white p-5 shadow-[0_20px_55px_rgb(20_35_29/16%)] sm:inset-x-6 sm:p-7">
        <div className="flex items-center justify-between"><h2 className="text-lg font-black">Shop {activeMenu === "women" ? "Women" : "Men"}</h2><button onClick={() => setActiveMenu(null)} className="grid size-8 place-items-center rounded-full bg-background text-lg" aria-label="Close category menu">×</button></div>
        <div className="mt-4 grid grid-cols-2 gap-x-8 sm:grid-cols-3 lg:grid-cols-4">
          {FASHION_DEPARTMENTS[activeMenu].map((item) => <a key={item.slug} href={`/schools/${schoolSlug}?category=${activeMenu}&subcategory=${item.slug}`} className="border-b border-line py-3 text-sm font-semibold transition hover:text-brand">{item.name}</a>)}
        </div>
        <a href={`/schools/${schoolSlug}?category=${activeMenu}`} className="mt-5 inline-block text-sm font-black underline decoration-brand/30 underline-offset-4">Shop all {activeMenu === "women" ? "women's" : "men's"}</a>
      </div>}
    </nav>
  );
}
