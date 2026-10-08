"use client";

import { useEffect, useRef, useState } from "react";

import type { components } from "@/lib/api/schema";
import type { CategoryTree } from "@/lib/categories";
import {
  COLOR_SWATCHES,
  CONDITION_DESCRIPTIONS,
  GENERAL_SIZES,
  LENGTH_SIZES,
  PANTS_SLUG,
  POPULAR_BRANDS,
  SHOE_SIZES,
  SORTS,
  WAIST_SIZES,
  type FeedParams,
} from "@/lib/discovery";
import { COLORS, CONDITIONS, conditionLabel } from "@/lib/listing-options";

type School = components["schemas"]["School"];

type MenuName = "school" | "brand" | "price" | "size" | "color" | "condition" | "sort";

function Chevron({ open }: { open: boolean }) {
  return <svg viewBox="0 0 16 16" className={`size-4 transition ${open ? "rotate-180" : ""}`} fill="none" stroke="currentColor" strokeWidth="1.8" aria-hidden="true"><path d="m3 6 5 5 5-5" /></svg>;
}

function Check({ checked }: { checked: boolean }) {
  return <span className={`grid size-5 shrink-0 place-items-center rounded border ${checked ? "border-ink bg-ink text-background" : "border-line bg-background"}`}>{checked && <svg viewBox="0 0 16 16" className="size-3" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true"><path d="m3 8 3 3 7-7" /></svg>}</span>;
}

/** Filter menus and the chips that clear them. Every change goes through `update`, which
 * writes the URL; the feed reads its filters back from there. */
export function MarketplaceFilterBar({
  feed,
  update,
  tree,
  schools,
  showSchool,
  homeSchool,
}: {
  feed: FeedParams;
  update: (patch: Partial<FeedParams>) => void;
  tree: CategoryTree | null;
  schools: School[];
  showSchool: boolean;
  homeSchool: string;
}) {
  const [open, setOpen] = useState<MenuName | null>(null);
  const [brandQuery, setBrandQuery] = useState("");
  const [minPrice, setMinPrice] = useState(feed.minPrice);
  const [maxPrice, setMaxPrice] = useState(feed.maxPrice);
  const rootRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function close(event: PointerEvent) {
      if (rootRef.current && !rootRef.current.contains(event.target as Node)) setOpen(null);
    }
    function escape(event: KeyboardEvent) {
      if (event.key === "Escape") setOpen(null);
    }
    document.addEventListener("pointerdown", close);
    document.addEventListener("keydown", escape);
    return () => {
      document.removeEventListener("pointerdown", close);
      document.removeEventListener("keydown", escape);
    };
  }, []);

  const category = tree?.bySlug.get(feed.category);
  const department = category && tree?.departmentOf(category);
  const pantSizing = PANTS_SLUG.test(feed.category);
  const sizes = department?.slug === "shoes" ? SHOE_SIZES : GENERAL_SIZES;
  const [chosenWaist, chosenLength] = /^\d+x\d+$/.test(feed.size) ? feed.size.split("x") : ["", ""];
  // A waist or length picked on its own waits here until the other one is picked.
  const [waist, setWaist] = useState(chosenWaist);
  const [length, setLength] = useState(chosenLength);
  const brands = POPULAR_BRANDS.filter((name) => name.toLowerCase().includes(brandQuery.toLowerCase()));
  const typedBrand = brandQuery.trim();

  const buttonClass = "flex h-11 shrink-0 items-center gap-2 rounded-md border border-line bg-background px-4 text-sm font-bold transition hover:border-ink aria-expanded:border-ink";
  const panelClass = "absolute left-0 top-[calc(100%+0.45rem)] z-30 max-h-[26rem] min-w-72 overflow-auto rounded-lg border border-line bg-background shadow-xl";
  const rowClass = "flex w-full items-center justify-between gap-4 border-b border-line px-4 py-3 text-left text-sm last:border-b-0 hover:bg-surface";

  function toggle(menu: MenuName) {
    setOpen((current) => (current === menu ? null : menu));
  }

  function choose(patch: Partial<FeedParams>) {
    update(patch);
    setOpen(null);
  }

  /** Jeans and pants are sized "<waist>x<length>", so the filter applies once both are set. */
  function pickPants(nextWaist: string, nextLength: string) {
    setWaist(nextWaist);
    setLength(nextLength);
    if (nextWaist && nextLength) choose({ size: `${nextWaist}x${nextLength}` });
    else if (feed.size) update({ size: "" });
  }

  const schoolName = (slug: string) => schools.find((s) => s.slug === slug)?.short_name ?? slug;
  const chips: { key: string; label: string; clear: () => void }[] = [];
  if (showSchool && feed.school) chips.push({ key: "school", label: feed.school === "all" ? "All schools" : schoolName(feed.school), clear: () => update({ school: "" }) });
  if (category) chips.push({ key: "category", label: department && department.id !== category.id ? `${department.name} › ${category.name}` : category.name, clear: () => update({ category: "", size: "" }) });
  if (feed.brand) chips.push({ key: "brand", label: feed.brand, clear: () => update({ brand: "" }) });
  if (feed.minPrice || feed.maxPrice) chips.push({ key: "price", label: `$${feed.minPrice || "0"} – ${feed.maxPrice ? `$${feed.maxPrice}` : "any"}`, clear: () => { setMinPrice(""); setMaxPrice(""); update({ minPrice: "", maxPrice: "" }); } });
  if (feed.size) chips.push({ key: "size", label: `Size ${feed.size}`, clear: () => update({ size: "" }) });
  if (feed.color) chips.push({ key: "color", label: COLORS.find((c) => c.value === feed.color)?.label ?? feed.color, clear: () => update({ color: "" }) });
  if (feed.condition) chips.push({ key: "condition", label: conditionLabel(feed.condition), clear: () => update({ condition: "" }) });

  return <div ref={rootRef} className="mb-7 border-y border-line py-4">
    <div className="flex flex-wrap gap-2 pb-1">
      {showSchool && <div className="relative shrink-0">
        <button type="button" onClick={() => toggle("school")} aria-expanded={open === "school"} className={buttonClass}>School <Chevron open={open === "school"} /></button>
        {open === "school" && <div className={panelClass}>
          <button type="button" className={rowClass} onClick={() => choose({ school: "" })}>Your school{homeSchool ? ` (${schoolName(homeSchool)})` : ""}<Check checked={!feed.school} /></button>
          <button type="button" className={rowClass} onClick={() => choose({ school: "all" })}>All schools <Check checked={feed.school === "all"} /></button>
          {schools.filter((s) => s.slug !== homeSchool).map((s) => <button type="button" key={s.slug} className={rowClass} onClick={() => choose({ school: s.slug })}>{s.name}<Check checked={feed.school === s.slug} /></button>)}
        </div>}
      </div>}

      <div className="relative shrink-0">
        <button type="button" onClick={() => toggle("brand")} aria-expanded={open === "brand"} className={buttonClass}>Brand <Chevron open={open === "brand"} /></button>
        {open === "brand" && <div className={panelClass}>
          <form className="sticky top-0 border-b border-line bg-background p-3" onSubmit={(event) => { event.preventDefault(); if (typedBrand) choose({ brand: typedBrand }); }}>
            <input value={brandQuery} onChange={(event) => setBrandQuery(event.target.value)} placeholder="Search or type a brand" aria-label="Brand" className="field h-10 px-3 text-sm" />
          </form>
          {typedBrand && !brands.some((name) => name.toLowerCase() === typedBrand.toLowerCase()) && <button type="button" className={rowClass} onClick={() => choose({ brand: typedBrand })}>Use “{typedBrand}”</button>}
          {brands.map((name) => <button type="button" key={name} className={rowClass} onClick={() => choose({ brand: name })}>{name}<Check checked={feed.brand.toLowerCase() === name.toLowerCase()} /></button>)}
        </div>}
      </div>

      <div className="relative shrink-0">
        <button type="button" onClick={() => toggle("price")} aria-expanded={open === "price"} className={buttonClass}>Price <Chevron open={open === "price"} /></button>
        {open === "price" && <form className={`${panelClass} p-4`} onSubmit={(event) => { event.preventDefault(); choose({ minPrice, maxPrice }); }}>
          <div className="grid grid-cols-[1fr_auto_1fr] items-end gap-3">
            <label className="text-xs font-bold">Min.<span className="field mt-2 flex h-11 items-center px-3 text-sm font-normal"><span className="text-muted">$</span><input value={minPrice} onChange={(event) => setMinPrice(event.target.value.replace(/[^0-9]/g, "").slice(0, 6))} inputMode="numeric" className="min-w-0 flex-1 bg-transparent pl-1 outline-none" /></span></label>
            <span className="pb-3 text-muted">–</span>
            <label className="text-xs font-bold">Max.<span className="field mt-2 flex h-11 items-center px-3 text-sm font-normal"><span className="text-muted">$</span><input value={maxPrice} onChange={(event) => setMaxPrice(event.target.value.replace(/[^0-9]/g, "").slice(0, 6))} inputMode="numeric" className="min-w-0 flex-1 bg-transparent pl-1 outline-none" /></span></label>
          </div>
          {minPrice && maxPrice && Number(minPrice) > Number(maxPrice) && <p className="mt-2 text-xs text-[var(--danger)]">The minimum is above the maximum.</p>}
          <div className="mt-4 grid grid-cols-2 gap-2">
            <button type="button" className="btn btn-secondary" onClick={() => { setMinPrice(""); setMaxPrice(""); choose({ minPrice: "", maxPrice: "" }); }}>Reset</button>
            <button type="submit" disabled={Boolean(minPrice && maxPrice && Number(minPrice) > Number(maxPrice))} className="btn btn-primary">Done</button>
          </div>
        </form>}
      </div>

      <div className="relative shrink-0">
        <button type="button" onClick={() => toggle("size")} aria-expanded={open === "size"} className={buttonClass}>Size <Chevron open={open === "size"} /></button>
        {open === "size" && <div className={`${panelClass} p-4`}>
          {pantSizing ? <>
            <p className="text-sm font-bold">Waist and length</p>
            <p className="mt-1 text-xs leading-5 text-muted">Pick both to match listings with exactly that size.</p>
            <div className="mt-3 grid grid-cols-2 gap-3">
              <label className="text-xs font-bold">Waist<select value={waist} onChange={(event) => pickPants(event.target.value, length)} className="field mt-2 h-11 px-3 text-sm font-normal"><option value="">Any</option>{WAIST_SIZES.map((w) => <option key={w} value={w}>W{w}</option>)}</select></label>
              <label className="text-xs font-bold">Length<select value={length} onChange={(event) => pickPants(waist, event.target.value)} className="field mt-2 h-11 px-3 text-sm font-normal"><option value="">Any</option>{LENGTH_SIZES.map((l) => <option key={l} value={l}>L{l}</option>)}</select></label>
            </div>
          </> : <div className="grid grid-cols-3 gap-2">
            {sizes.map((value) => <button type="button" key={value} aria-pressed={feed.size === value} onClick={() => choose({ size: feed.size === value ? "" : value })} className="chip justify-center">{value}</button>)}
          </div>}
        </div>}
      </div>

      <div className="relative shrink-0">
        <button type="button" onClick={() => toggle("color")} aria-expanded={open === "color"} className={buttonClass}>Color <Chevron open={open === "color"} /></button>
        {open === "color" && <div className={panelClass}>{COLORS.map((c) => <button type="button" key={c.value} className={rowClass} onClick={() => choose({ color: c.value })}><span className="flex items-center gap-3"><span className="size-5 rounded-full border border-line" style={{ background: COLOR_SWATCHES[c.value] }} />{c.label}</span><Check checked={feed.color === c.value} /></button>)}</div>}
      </div>

      <div className="relative shrink-0">
        <button type="button" onClick={() => toggle("condition")} aria-expanded={open === "condition"} className={buttonClass}>Condition <Chevron open={open === "condition"} /></button>
        {open === "condition" && <div className={`${panelClass} min-w-80`}>{CONDITIONS.map((c) => <button type="button" key={c.value} className={rowClass} onClick={() => choose({ condition: c.value })}><span><span className="block font-semibold">{c.label}</span><span className="mt-0.5 block max-w-60 text-xs leading-5 text-muted">{CONDITION_DESCRIPTIONS[c.value]}</span></span><Check checked={feed.condition === c.value} /></button>)}</div>}
      </div>

      <div className="relative ml-auto shrink-0">
        <button type="button" onClick={() => toggle("sort")} aria-expanded={open === "sort"} className={buttonClass}><svg viewBox="0 0 16 16" className="size-4" fill="none" stroke="currentColor" strokeWidth="1.6" aria-hidden="true"><path d="M5 2v12m0 0-3-3m3 3 3-3M11 14V2m0 0L8 5m3-3 3 3" /></svg>Sort</button>
        {open === "sort" && <div className={`${panelClass} left-auto right-0`}>{SORTS.map((s) => <button type="button" key={s.value} className={rowClass} onClick={() => choose({ sort: s.value })}>{s.label}<Check checked={feed.sort === s.value} /></button>)}</div>}
      </div>
    </div>

    {chips.length > 0 && <div className="mt-3 flex flex-wrap items-center gap-2">
      {chips.map((chip) => <button type="button" key={chip.key} onClick={chip.clear} aria-label={`Remove filter: ${chip.label}`} className="flex items-center gap-2 rounded-full bg-surface px-3 py-1.5 text-sm">{chip.label}<span aria-hidden="true">×</span></button>)}
      <button type="button" onClick={() => { setMinPrice(""); setMaxPrice(""); update({ school: "", category: "", brand: "", condition: "", color: "", size: "", minPrice: "", maxPrice: "" }); }} className="ml-1 text-sm font-semibold underline underline-offset-4">Clear all</button>
    </div>}
  </div>;
}
