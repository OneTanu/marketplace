"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useEffect, useMemo, useState } from "react";

import {
  ACCESSORY_DEPARTMENTS,
  brandSlug,
  CONDITION_LABELS,
  DISCOVERY_CATEGORIES,
  DISCOVERY_PREVIEW_LISTINGS,
  FASHION_DEPARTMENTS,
  POPULAR_BRANDS,
  type DiscoveryListing,
  type ListingCondition,
} from "@/lib/discovery";
import { getSchools, searchUsers, type PublicUser, type SchoolMarketplace } from "@/lib/platform";
import { ListingCard } from "./listing-card";

type SortOption = "newest" | "price_low" | "price_high";

function UserResult({ user }: { user: PublicUser }) {
  const initial = (user.first_name[0] || user.username[0]).toUpperCase();
  return <Link href={`/users/${user.username}`} className="flex items-center gap-4 rounded-2xl border border-line bg-surface p-4 transition hover:-translate-y-0.5 hover:border-forest hover:shadow-sm">
    <div className="grid size-12 shrink-0 place-items-center rounded-2xl bg-[var(--brand-soft)] text-lg font-black text-brand">{initial}</div>
    <div className="min-w-0 flex-1"><p className="font-black">{user.first_name || `@${user.username}`}</p><p className="truncate text-sm text-muted">@{user.username}{user.school ? ` · ${user.school.short_name}` : ""}</p></div>
    <span className="text-lg text-muted" aria-hidden="true">→</span>
  </Link>;
}

export function MarketplaceFeed({ school }: { school?: SchoolMarketplace }) {
  const searchParams = useSearchParams();
  const [search, setSearch] = useState(() => searchParams.get("search") ?? "");
  const [schoolFilter, setSchoolFilter] = useState(() => school?.slug ?? searchParams.get("school") ?? "");
  const [category, setCategory] = useState(() => searchParams.get("category") ?? "trending");
  const [subcategory, setSubcategory] = useState(() => searchParams.get("subcategory") ?? "");
  const [brand, setBrand] = useState(() => searchParams.get("brand") ?? "");
  const [condition, setCondition] = useState<ListingCondition | "">(() => (searchParams.get("condition") ?? "") as ListingCondition | "");
  const [maxPrice, setMaxPrice] = useState(() => searchParams.get("max_price") ?? "");
  const [size, setSize] = useState(() => searchParams.get("size") ?? "");
  const [sort, setSort] = useState<SortOption>(() => (searchParams.get("ordering") as SortOption) || "newest");
  const [filtersOpen, setFiltersOpen] = useState(false);
  const [schools, setSchools] = useState<SchoolMarketplace[]>(school ? [school] : []);
  const [peopleResult, setPeopleResult] = useState<{ query: string; people: PublicUser[]; state: "ready" | "signed-out" | "error" }>({ query: "", people: [], state: "ready" });

  useEffect(() => {
    if (school) return;
    getSchools().then((items) => setSchools(items.filter((item) => item.marketplace_status === "open"))).catch(() => setSchools([]));
  }, [school]);

  useEffect(() => {
    if (school || !search.trim()) return;
    let active = true;
    const query = search.trim();
    searchUsers(query).then((people) => active && setPeopleResult({ query, people, state: "ready" })).catch((error: Error) => {
      if (!active) return;
      setPeopleResult({ query, people: [], state: error.message.includes("401") || error.message.includes("403") ? "signed-out" : "error" });
    });
    return () => { active = false; };
  }, [school, search]);

  useEffect(() => {
    const params = new URLSearchParams();
    if (search) params.set("search", search);
    if (!school && schoolFilter) params.set("school", schoolFilter);
    if (category !== "trending") params.set("category", category);
    if (subcategory) params.set("subcategory", subcategory);
    if (brand) params.set("brand", brand);
    if (condition) params.set("condition", condition);
    if (maxPrice) params.set("max_price", maxPrice);
    if (size) params.set("size", size);
    if (sort !== "newest") params.set("ordering", sort);
    const query = params.toString();
    window.history.replaceState(null, "", `${window.location.pathname}${query ? `?${query}` : ""}`);
  }, [brand, category, condition, maxPrice, school, schoolFilter, search, size, sort, subcategory]);

  const listings = useMemo(() => {
    const query = search.trim().toLowerCase();
    const ceiling = maxPrice ? Number(maxPrice) * 100 : null;
    const filtered = DISCOVERY_PREVIEW_LISTINGS.filter((listing) => {
      const matchesSchool = school ? listing.school.slug === school.slug : !schoolFilter || listing.school.slug === schoolFilter;
      const matchesSearch = !query || `${listing.title} ${listing.brand ?? ""} ${listing.category.name}`.toLowerCase().includes(query);
      const campusItem = !["clothing", "shoes", "accessories"].includes(listing.category.slug);
      const fashionItem = !campusItem;
      const matchesCategory = (category === "trending" && fashionItem) ||
        (["women", "men", "unisex"].includes(category) && listing.audience === category) ||
        (category === "brands" && fashionItem && Boolean(listing.brand)) ||
        (category === "campus-items" && campusItem) ||
        listing.category.slug === category;
      const matchesCondition = !condition || listing.condition === condition;
      const matchesPrice = ceiling === null || listing.price_cents <= ceiling;
      const matchesSize = !size || listing.size === size;
      const matchesSubcategory = !subcategory || listing.fashion_category === subcategory;
      const matchesBrand = !brand || Boolean(listing.brand && brandSlug(listing.brand) === brand);
      return matchesSchool && matchesSearch && matchesCategory && matchesCondition && matchesPrice && matchesSize && matchesSubcategory && matchesBrand;
    });
    return filtered.sort((a, b) => {
      if (sort === "price_low") return a.price_cents - b.price_cents;
      if (sort === "price_high") return b.price_cents - a.price_cents;
      return Date.parse(b.created_at) - Date.parse(a.created_at);
    });
  }, [brand, category, condition, maxPrice, school, schoolFilter, search, size, sort, subcategory]);

  const activeFilterCount = Number(Boolean(!school && schoolFilter)) + Number(Boolean(condition)) + Number(Boolean(maxPrice)) + Number(Boolean(size));
  const fashionSelected = !["campus-items"].includes(category);
  const peopleState = peopleResult.query === search.trim() ? peopleResult.state : "loading";
  const people = peopleResult.query === search.trim() ? peopleResult.people : [];

  function clearFilters() {
    setCondition("");
    setMaxPrice("");
    setCategory("trending");
    setSubcategory("");
    setBrand("");
    setSize("");
    if (!school) setSchoolFilter("");
  }

  return (
    <>
      <section className="border-b border-line bg-surface">
        <div className="mx-auto max-w-6xl px-4 py-8 sm:px-6 sm:py-11">
          <div className="flex flex-col gap-6 lg:flex-row lg:items-end lg:justify-between">
            <div>
              <h1 className="mt-3 text-2xl font-black tracking-[-.04em] sm:text-3xl">{school ? `${school.short_name} Marketplace` : "All Marketplaces"}</h1>
              <p className="mt-2 text-sm text-muted">{school ? "Shop student closets across campus." : "Discover clothing and campus items from every school on Tanu."}</p>
            </div>
          </div>

        </div>
      </section>

      <section className="mx-auto max-w-6xl px-4 py-7 pb-28 sm:px-6 desktop:pb-12">
        {!school && search.trim() && <section className="mb-9"><h2 className="text-xl font-black">People</h2><p className="mt-1 text-sm text-muted">Verified students matching this name or username.</p>
          {peopleState === "loading" && <div className="mt-4 h-20 animate-pulse rounded-2xl bg-foreground/5" />}
          {peopleState === "signed-out" && <div className="mt-4 rounded-2xl border border-line bg-surface p-5 text-sm"><Link href="/account/login" className="font-black text-forest underline">Log in</Link> to search verified student accounts.</div>}
          {peopleState === "error" && <p className="mt-4 text-sm text-[var(--danger)]">We couldn’t search accounts. Please try again.</p>}
          {peopleState === "ready" && (people.length ? <div className="mt-4 grid gap-3 sm:grid-cols-2">{people.map((user) => <UserResult key={user.id} user={user} />)}</div> : <p className="mt-4 rounded-2xl border border-dashed border-line p-6 text-sm text-muted">No verified accounts match this search.</p>)}
        </section>}
        <div className="mb-6 flex flex-wrap items-center justify-between gap-3">
          <div>
            <h2 className="text-xl font-black tracking-tight">{search ? `Results for “${search}”` : brand ? POPULAR_BRANDS.find((item) => item.slug === brand)?.name : subcategory ? (category === "accessories" ? ACCESSORY_DEPARTMENTS : FASHION_DEPARTMENTS[category as "women" | "men"] ?? []).find((item) => item.slug === subcategory)?.name : category === "trending" ? school ? `Trending at ${school.short_name}` : "Trending across Tanu" : DISCOVERY_CATEGORIES.find((item) => item.slug === category)?.name}</h2>
            <p className="mt-1 text-xs text-muted">Previewing the discovery experience with sample listings.</p>
          </div>
          <div className="flex items-center gap-2">
            <button onClick={() => setFiltersOpen((value) => !value)} aria-expanded={filtersOpen} className="rounded-full border border-line bg-white px-4 py-2.5 text-sm font-bold transition hover:border-forest">Filters{activeFilterCount ? ` · ${activeFilterCount}` : ""}</button>
            <label className="sr-only" htmlFor="listing-sort">Sort listings</label>
            <select id="listing-sort" value={sort} onChange={(event) => setSort(event.target.value as SortOption)} className="h-10 rounded-full border border-line bg-white px-4 text-sm font-bold outline-none focus:border-forest">
              <option value="newest">Newest</option>
              <option value="price_low">Price: low to high</option>
              <option value="price_high">Price: high to low</option>
            </select>
          </div>
        </div>

        <div className={`grid gap-7 ${filtersOpen ? "lg:grid-cols-[15rem_1fr]" : ""}`}>
          {filtersOpen && <aside className="h-fit rounded-2xl border border-line bg-surface p-5 lg:sticky lg:top-24">
            <div className="flex items-center justify-between"><h3 className="font-black">Filters</h3><button onClick={clearFilters} className="text-xs font-bold text-brand">Clear all</button></div>
            {!school && <label className="mt-5 block text-sm font-bold">School<select value={schoolFilter} onChange={(event) => setSchoolFilter(event.target.value)} className="mt-2 h-11 w-full rounded-xl border border-line bg-white px-3 font-normal outline-none focus:border-forest"><option value="">All schools</option>{schools.map((item) => <option key={item.slug} value={item.slug}>{item.name}</option>)}</select></label>}
            <label className="mt-5 block text-sm font-bold">Condition<select value={condition} onChange={(event) => setCondition(event.target.value as ListingCondition | "")} className="mt-2 h-11 w-full rounded-xl border border-line bg-white px-3 font-normal outline-none focus:border-forest"><option value="">Any condition</option>{Object.entries(CONDITION_LABELS).map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select></label>
            {fashionSelected && <label className="mt-5 block text-sm font-bold">Size<select value={size} onChange={(event) => setSize(event.target.value)} className="mt-2 h-11 w-full rounded-xl border border-line bg-white px-3 font-normal outline-none focus:border-forest"><option value="">Any size</option>{["S", "M", "L", "28", "10", "One size"].map((value) => <option key={value} value={value}>{value}</option>)}</select></label>}
            <label className="mt-5 block text-sm font-bold">Maximum price<div className="mt-2 flex h-11 items-center rounded-xl border border-line bg-white px-3 focus-within:border-forest"><span className="text-muted">$</span><input value={maxPrice} onChange={(event) => setMaxPrice(event.target.value.replace(/[^0-9]/g, ""))} inputMode="numeric" className="h-full min-w-0 flex-1 bg-transparent pl-1 font-normal outline-none" placeholder="No maximum" /></div></label>
            {school && <div className="mt-5 border-t border-line pt-4 text-xs leading-5 text-muted">School is fixed to <strong className="text-foreground">{school.name}</strong>. Use the school switcher to browse another marketplace.</div>}
          </aside>}

          <div>
            {listings.length ? <div className={`grid grid-cols-2 gap-x-3 gap-y-7 sm:grid-cols-3 sm:gap-x-5 ${filtersOpen ? "xl:grid-cols-3" : "lg:grid-cols-4"}`}>{listings.map((listing: DiscoveryListing) => <ListingCard key={listing.id} listing={listing} />)}</div> : <div className="grid min-h-80 place-items-center rounded-3xl border border-dashed border-line bg-white/45 px-6 text-center"><div><div className="mx-auto grid size-12 place-items-center rounded-2xl bg-[var(--brand-soft)] text-xl text-brand">⌕</div><h3 className="mt-4 text-xl font-black">No matching items</h3><p className="mt-2 max-w-sm text-sm leading-6 text-muted">Try a broader search, another category, or remove one of your filters.</p><button onClick={() => { clearFilters(); setSearch(""); }} className="mt-5 rounded-full border border-line bg-white px-5 py-2.5 text-sm font-bold">Clear search and filters</button></div></div>}
          </div>
        </div>
      </section>
    </>
  );
}
