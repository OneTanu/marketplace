"use client";

import { useEffect, useMemo, useRef, useState } from "react";

import {
  ACCESSORY_DEPARTMENTS,
  CONDITION_DESCRIPTIONS,
  CONDITION_LABELS,
  DISCOVERY_CATEGORIES,
  DISCOVERY_COLORS,
  FASHION_DEPARTMENTS,
  POPULAR_BRANDS,
  brandSlug,
  type DiscoveryListing,
  type ListingColor,
  type ListingCondition,
} from "@/lib/discovery";
import type { SchoolMarketplace } from "@/lib/platform";

export type SortOption = "relevance" | "newest" | "price_low" | "price_high";

type FilterBarProps = {
  listings: DiscoveryListing[];
  schools: SchoolMarketplace[];
  showSchool: boolean;
  school: string;
  category: string;
  subcategory: string;
  brand: string;
  minPrice: string;
  maxPrice: string;
  size: string;
  waist: string;
  inseam: string;
  color: ListingColor | "";
  condition: ListingCondition | "";
  sort: SortOption;
  setSchool: (value: string) => void;
  setCategory: (value: string) => void;
  setSubcategory: (value: string) => void;
  setBrand: (value: string) => void;
  setMinPrice: (value: string) => void;
  setMaxPrice: (value: string) => void;
  setSize: (value: string) => void;
  setWaist: (value: string) => void;
  setInseam: (value: string) => void;
  setColor: (value: ListingColor | "") => void;
  setCondition: (value: ListingCondition | "") => void;
  setSort: (value: SortOption) => void;
  clearAll: () => void;
};

type MenuName = "school" | "category" | "subcategory" | "brand" | "price" | "size" | "color" | "condition" | "sort";

const generalSizes = ["XS", "S", "M", "L", "XL", "XXL", "One size"];
const shoeSizes = ["5", "6", "7", "8", "9", "10", "11", "12", "13"];
const waistSizes = ["26", "28", "30", "32", "34", "36", "38", "40"];
const inseamSizes = ["28", "30", "32", "34", "36"];
const filterConditions: ListingCondition[] = ["new_with_tags", "like_new", "excellent", "good", "fair"];

function Chevron({ open }: { open: boolean }) {
  return <svg viewBox="0 0 16 16" className={`size-4 transition ${open ? "rotate-180" : ""}`} fill="none" stroke="currentColor" strokeWidth="1.8" aria-hidden="true"><path d="m3 6 5 5 5-5" /></svg>;
}

function Check({ checked }: { checked: boolean }) {
  return <span className={`grid size-5 shrink-0 place-items-center rounded border ${checked ? "border-ink bg-ink text-background" : "border-line bg-background"}`}>{checked && <svg viewBox="0 0 16 16" className="size-3" fill="none" stroke="currentColor" strokeWidth="2"><path d="m3 8 3 3 7-7" /></svg>}</span>;
}

export function MarketplaceFilterBar(props: FilterBarProps) {
  const [open, setOpen] = useState<MenuName | null>(null);
  const [brandQuery, setBrandQuery] = useState("");
  const rootRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function close(event: PointerEvent) {
      if (rootRef.current && !rootRef.current.contains(event.target as Node)) setOpen(null);
    }
    document.addEventListener("pointerdown", close);
    return () => document.removeEventListener("pointerdown", close);
  }, []);

  const departments = props.category === "accessories"
    ? ACCESSORY_DEPARTMENTS
    : props.category === "women" || props.category === "men"
      ? FASHION_DEPARTMENTS[props.category]
      : [];
  const pantSizing = props.subcategory === "jeans" || props.subcategory === "pants";
  const availableSizes = props.category === "shoes" || props.subcategory === "shoes" ? shoeSizes : generalSizes;
  const brands = useMemo(() => {
    const values = new Map<string, string>(POPULAR_BRANDS.map((item) => [item.slug, item.name]));
    props.listings.forEach((listing) => { if (listing.brand) values.set(brandSlug(listing.brand), listing.brand); });
    return [...values].map(([slug, name]) => ({ slug, name })).filter((item) => item.name.toLowerCase().includes(brandQuery.toLowerCase()));
  }, [brandQuery, props.listings]);

  const buttonClass = "flex h-11 shrink-0 items-center gap-2 rounded-md border border-line bg-background px-4 text-sm font-bold transition hover:border-ink";
  const panelClass = "absolute left-0 top-[calc(100%+0.45rem)] z-30 max-h-[26rem] min-w-72 overflow-auto rounded-lg border border-line bg-background shadow-xl";
  const rowClass = "flex w-full items-center justify-between gap-4 border-b border-line px-4 py-3 text-left text-sm last:border-b-0 hover:bg-surface";

  function toggle(menu: MenuName) {
    setOpen((current) => current === menu ? null : menu);
  }

  function chooseCategory(value: string) {
    props.setCategory(value);
    props.setSubcategory("");
    props.setSize("");
    props.setWaist("");
    props.setInseam("");
    setOpen(null);
  }

  const chips: { label: string; clear: () => void }[] = [];
  if (props.showSchool && props.school) chips.push({ label: props.schools.find((item) => item.slug === props.school)?.short_name ?? props.school, clear: () => props.setSchool("") });
  if (props.category !== "trending") chips.push({ label: DISCOVERY_CATEGORIES.find((item) => item.slug === props.category)?.name ?? props.category, clear: () => chooseCategory("trending") });
  if (props.subcategory) chips.push({ label: departments.find((item) => item.slug === props.subcategory)?.name ?? props.subcategory, clear: () => props.setSubcategory("") });
  if (props.brand) chips.push({ label: brands.find((item) => item.slug === props.brand)?.name ?? props.brand, clear: () => props.setBrand("") });
  if (props.minPrice || props.maxPrice) chips.push({ label: `$${props.minPrice || "0"} – ${props.maxPrice ? `$${props.maxPrice}` : "Any"}`, clear: () => { props.setMinPrice(""); props.setMaxPrice(""); } });
  if (props.size) chips.push({ label: `Size ${props.size}`, clear: () => props.setSize("") });
  if (props.waist) chips.push({ label: `W${props.waist}`, clear: () => props.setWaist("") });
  if (props.inseam) chips.push({ label: `L${props.inseam}`, clear: () => props.setInseam("") });
  if (props.color) chips.push({ label: DISCOVERY_COLORS.find((item) => item.slug === props.color)?.name ?? props.color, clear: () => props.setColor("") });
  if (props.condition) chips.push({ label: CONDITION_LABELS[props.condition], clear: () => props.setCondition("") });

  return <div ref={rootRef} className="mb-7 border-y border-line py-4">
    <div className="flex flex-wrap gap-2 overflow-visible pb-1">
      {props.showSchool && <div className="relative shrink-0">
        <button type="button" onClick={() => toggle("school")} aria-expanded={open === "school"} className={buttonClass}>School <Chevron open={open === "school"} /></button>
        {open === "school" && <div className={panelClass}>
          <button className={rowClass} onClick={() => { props.setSchool(""); setOpen(null); }}>All schools <Check checked={!props.school} /></button>
          {props.schools.map((item) => <button key={item.slug} className={rowClass} onClick={() => { props.setSchool(item.slug); setOpen(null); }}>{item.name}<Check checked={props.school === item.slug} /></button>)}
        </div>}
      </div>}

      <div className="relative shrink-0">
        <button type="button" onClick={() => toggle("category")} aria-expanded={open === "category"} className={buttonClass}>Category <Chevron open={open === "category"} /></button>
        {open === "category" && <div className={panelClass}>{DISCOVERY_CATEGORIES.filter((item) => item.slug !== "brands").map((item) => <button key={item.slug} className={rowClass} onClick={() => chooseCategory(item.slug)}>{item.name}<Check checked={props.category === item.slug} /></button>)}</div>}
      </div>

      <div className="relative shrink-0">
        <button type="button" onClick={() => toggle("subcategory")} aria-expanded={open === "subcategory"} className={buttonClass}>Subcategory <Chevron open={open === "subcategory"} /></button>
        {open === "subcategory" && <div className={panelClass}>{departments.length ? departments.map((item) => <button key={item.slug} className={rowClass} onClick={() => { props.setSubcategory(item.slug); setOpen(null); }}>{item.name}<Check checked={props.subcategory === item.slug} /></button>) : <p className="max-w-xs px-4 py-4 text-sm leading-6 text-muted">Choose Women, Men, or Accessories first to browse their subcategories.</p>}</div>}
      </div>

      <div className="relative shrink-0">
        <button type="button" onClick={() => toggle("brand")} aria-expanded={open === "brand"} className={buttonClass}>Brand <Chevron open={open === "brand"} /></button>
        {open === "brand" && <div className={panelClass}>
          <div className="sticky top-0 border-b border-line bg-background p-3"><input value={brandQuery} onChange={(event) => setBrandQuery(event.target.value)} placeholder="Search brands" className="field h-10 px-3 text-sm" /></div>
          {brands.map((item) => <button key={item.slug} className={rowClass} onClick={() => { props.setBrand(item.slug); setOpen(null); }}>{item.name}<Check checked={props.brand === item.slug} /></button>)}
        </div>}
      </div>

      <div className="relative shrink-0">
        <button type="button" onClick={() => toggle("price")} aria-expanded={open === "price"} className={buttonClass}>Price <Chevron open={open === "price"} /></button>
        {open === "price" && <div className={`${panelClass} p-4`}>
          <div className="grid grid-cols-[1fr_auto_1fr] items-end gap-3"><label className="text-xs font-bold">Min.<span className="field mt-2 flex h-11 items-center px-3 text-sm font-normal"><span className="text-muted">$</span><input value={props.minPrice} onChange={(event) => props.setMinPrice(event.target.value.replace(/[^0-9]/g, ""))} inputMode="numeric" className="min-w-0 flex-1 bg-transparent pl-1 outline-none" placeholder="0" /></span></label><span className="pb-3 text-muted">—</span><label className="text-xs font-bold">Max.<span className="field mt-2 flex h-11 items-center px-3 text-sm font-normal"><span className="text-muted">$</span><input value={props.maxPrice} onChange={(event) => props.setMaxPrice(event.target.value.replace(/[^0-9]/g, ""))} inputMode="numeric" className="min-w-0 flex-1 bg-transparent pl-1 outline-none" placeholder="Any" /></span></label></div>
          <div className="mt-4 grid grid-cols-2 gap-2"><button className="btn btn-secondary" onClick={() => { props.setMinPrice(""); props.setMaxPrice(""); }}>Reset</button><button className="btn btn-primary" onClick={() => setOpen(null)}>Done</button></div>
        </div>}
      </div>

      <div className="relative shrink-0">
        <button type="button" onClick={() => toggle("size")} aria-expanded={open === "size"} className={buttonClass}>Size <Chevron open={open === "size"} /></button>
        {open === "size" && <div className={`${panelClass} p-4`}>
          {pantSizing ? <><p className="text-sm font-bold">Pant measurements</p><p className="mt-1 text-xs leading-5 text-muted">Filter the waist and length independently for a more accurate fit.</p><div className="mt-4 grid grid-cols-2 gap-3"><label className="text-xs font-bold">Waist<select value={props.waist} onChange={(event) => props.setWaist(event.target.value)} className="field mt-2 h-11 px-3 font-normal"><option value="">Any</option>{waistSizes.map((value) => <option key={value} value={value}>W{value}</option>)}</select></label><label className="text-xs font-bold">Inseam / length<select value={props.inseam} onChange={(event) => props.setInseam(event.target.value)} className="field mt-2 h-11 px-3 font-normal"><option value="">Any</option>{inseamSizes.map((value) => <option key={value} value={value}>L{value}</option>)}</select></label></div></> : <div className="grid grid-cols-3 gap-2">{availableSizes.map((value) => <button key={value} onClick={() => props.setSize(props.size === value ? "" : value)} className={`rounded-md border px-2 py-2 text-sm font-semibold ${props.size === value ? "border-ink bg-ink text-background" : "border-line hover:border-ink"}`}>{value}</button>)}</div>}
          <button className="btn btn-primary mt-4 w-full" onClick={() => setOpen(null)}>Done</button>
        </div>}
      </div>

      <div className="relative shrink-0">
        <button type="button" onClick={() => toggle("color")} aria-expanded={open === "color"} className={buttonClass}>Color <Chevron open={open === "color"} /></button>
        {open === "color" && <div className={panelClass}>{DISCOVERY_COLORS.map((item) => <button key={item.slug} className={rowClass} onClick={() => { props.setColor(item.slug); setOpen(null); }}><span className="flex items-center gap-3"><span className="size-5 rounded-full border border-line" style={{ background: item.swatch }} />{item.name}</span><Check checked={props.color === item.slug} /></button>)}</div>}
      </div>

      <div className="relative shrink-0">
        <button type="button" onClick={() => toggle("condition")} aria-expanded={open === "condition"} className={buttonClass}>Condition <Chevron open={open === "condition"} /></button>
        {open === "condition" && <div className={`${panelClass} min-w-80`}>{filterConditions.map((value) => <button key={value} className={rowClass} onClick={() => { props.setCondition(value); setOpen(null); }}><span><span className="block font-semibold">{CONDITION_LABELS[value]}</span><span className="mt-0.5 block max-w-60 text-xs leading-5 text-muted">{CONDITION_DESCRIPTIONS[value]}</span></span><Check checked={props.condition === value} /></button>)}</div>}
      </div>

      <div className="relative ml-auto shrink-0">
        <button type="button" onClick={() => toggle("sort")} aria-expanded={open === "sort"} className={buttonClass}><svg viewBox="0 0 16 16" className="size-4" fill="none" stroke="currentColor" strokeWidth="1.6"><path d="M5 2v12m0 0-3-3m3 3 3-3M11 14V2m0 0L8 5m3-3 3 3" /></svg>Sort</button>
        {open === "sort" && <div className={`${panelClass} left-auto right-0`}>{([{ value: "relevance", label: "Relevance" }, { value: "price_low", label: "Price: low to high" }, { value: "price_high", label: "Price: high to low" }, { value: "newest", label: "Newly listed" }] as { value: SortOption; label: string }[]).map((item) => <button key={item.value} className={rowClass} onClick={() => { props.setSort(item.value); setOpen(null); }}>{item.label}<Check checked={props.sort === item.value} /></button>)}</div>}
      </div>
    </div>

    {chips.length > 0 && <div className="mt-3 flex flex-wrap items-center gap-2">{chips.map((chip) => <button key={chip.label} onClick={chip.clear} className="flex items-center gap-2 rounded-full bg-surface px-3 py-1.5 text-sm">{chip.label}<span aria-hidden="true">×</span></button>)}<button onClick={props.clearAll} className="ml-1 text-sm font-semibold underline underline-offset-4">Clear all</button></div>}
  </div>;
}
