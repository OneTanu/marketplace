"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useEffect, useMemo, useState } from "react";

import {
  ACCESSORY_DEPARTMENTS,
  brandSlug,
  DISCOVERY_CATEGORIES,
  DISCOVERY_PREVIEW_LISTINGS,
  FASHION_DEPARTMENTS,
  POPULAR_BRANDS,
  type DiscoveryListing,
  type ListingColor,
  type ListingCondition,
} from "@/lib/discovery";
import type { components } from "@/lib/api/schema";
import { getCurrentUser, getSchools, searchUsers } from "@/lib/platform";
import { ListingCard } from "./listing-card";
import { MarketplaceFilterBar, type SortOption } from "./marketplace-filter-bar";

type PublicUser = components["schemas"]["PublicUser"];
type School = components["schemas"]["School"];

function UserResult({ user }: { user: PublicUser }) {
  const initial = (user.first_name[0] || user.username[0]).toUpperCase();
  return <Link href={`/users/${user.username}`} className="flex items-center gap-3.5 rounded-xl border border-line p-3.5 transition hover:border-ink">
    <div className="type-wide grid size-11 shrink-0 place-items-center rounded-full bg-[var(--brand-soft)] text-base font-extrabold text-brand">{initial}</div>
    <div className="min-w-0 flex-1"><p className="font-bold">{user.first_name || `@${user.username}`}</p><p className="truncate text-sm text-muted">@{user.username}{user.school ? `, ${user.school.short_name}` : ""}</p></div>
  </Link>;
}

export function MarketplaceFeed({ school }: { school?: School }) {
  const searchParams = useSearchParams();
  const requestedSchool = searchParams.get("school");
  const [search, setSearch] = useState(() => searchParams.get("search") ?? "");
  const [schoolFilter, setSchoolFilter] = useState(() => school?.slug ?? (requestedSchool === "all" ? "" : requestedSchool) ?? "");
  const [homeSchoolSlug, setHomeSchoolSlug] = useState("");
  const [allSchoolsExplicit, setAllSchoolsExplicit] = useState(requestedSchool === "all");
  const [schoolScopeReady, setSchoolScopeReady] = useState(Boolean(school || requestedSchool));
  const [category, setCategory] = useState(() => searchParams.get("category") ?? "trending");
  const [subcategory, setSubcategory] = useState(() => searchParams.get("subcategory") ?? "");
  const [brand, setBrand] = useState(() => searchParams.get("brand") ?? "");
  const [condition, setCondition] = useState<ListingCondition | "">(() => (searchParams.get("condition") ?? "") as ListingCondition | "");
  const [minPrice, setMinPrice] = useState(() => searchParams.get("min_price") ?? "");
  const [maxPrice, setMaxPrice] = useState(() => searchParams.get("max_price") ?? "");
  const [size, setSize] = useState(() => searchParams.get("size") ?? "");
  const [waist, setWaist] = useState(() => searchParams.get("waist") ?? "");
  const [inseam, setInseam] = useState(() => searchParams.get("inseam") ?? "");
  const [color, setColor] = useState<ListingColor | "">(() => (searchParams.get("color") ?? "") as ListingColor | "");
  const [sort, setSort] = useState<SortOption>(() => (searchParams.get("ordering") as SortOption) || "relevance");
  const [schools, setSchools] = useState<School[]>(school ? [school] : []);
  const [peopleResult, setPeopleResult] = useState<{ query: string; people: PublicUser[]; state: "ready" | "signed-out" | "error" }>({ query: "", people: [], state: "ready" });

  useEffect(() => {
    if (school) return;
    getSchools().then((items) => setSchools(items.filter((item) => item.marketplace_status === "open"))).catch(() => setSchools([]));
  }, [school]);

  useEffect(() => {
    if (school) return;
    let active = true;
    getCurrentUser().then((user) => {
      if (!active) return;
      const homeSchool = user?.school?.slug ?? "";
      setHomeSchoolSlug(homeSchool);
      if (!requestedSchool) setSchoolFilter(homeSchool);
      setSchoolScopeReady(true);
    }).catch(() => active && setSchoolScopeReady(true));
    return () => { active = false; };
  }, [requestedSchool, school]);

  useEffect(() => {
    if (school || !schoolScopeReady || !search.trim()) return;
    let active = true;
    const query = search.trim();
    const schoolScope = schoolFilter || (allSchoolsExplicit ? "all" : undefined);
    searchUsers(query, schoolScope).then((people) => active && setPeopleResult({ query, people, state: "ready" })).catch((error: Error) => {
      if (!active) return;
      setPeopleResult({ query, people: [], state: error.message.includes("401") || error.message.includes("403") ? "signed-out" : "error" });
    });
    return () => { active = false; };
  }, [allSchoolsExplicit, school, schoolFilter, schoolScopeReady, search]);

  useEffect(() => {
    if (!school && !schoolScopeReady) return;
    const params = new URLSearchParams();
    if (search) params.set("search", search);
    if (!school && schoolFilter && schoolFilter !== homeSchoolSlug) params.set("school", schoolFilter);
    if (!school && !schoolFilter && allSchoolsExplicit) params.set("school", "all");
    if (category !== "trending") params.set("category", category);
    if (subcategory) params.set("subcategory", subcategory);
    if (brand) params.set("brand", brand);
    if (condition) params.set("condition", condition);
    if (minPrice) params.set("min_price", minPrice);
    if (maxPrice) params.set("max_price", maxPrice);
    if (size) params.set("size", size);
    if (waist) params.set("waist", waist);
    if (inseam) params.set("inseam", inseam);
    if (color) params.set("color", color);
    if (sort !== "relevance") params.set("ordering", sort);
    const query = params.toString();
    window.history.replaceState(null, "", `${window.location.pathname}${query ? `?${query}` : ""}`);
  }, [allSchoolsExplicit, brand, category, color, condition, homeSchoolSlug, inseam, maxPrice, minPrice, school, schoolFilter, schoolScopeReady, search, size, sort, subcategory, waist]);

  const listings = useMemo(() => {
    const query = search.trim().toLowerCase();
    const floor = minPrice ? Number(minPrice) * 100 : null;
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
      const matchesPrice = (floor === null || listing.price_cents >= floor) && (ceiling === null || listing.price_cents <= ceiling);
      const matchesSize = !size || listing.size === size;
      const matchesWaist = !waist || listing.waist === Number(waist);
      const matchesInseam = !inseam || listing.inseam === Number(inseam);
      const matchesColor = !color || listing.color === color;
      const matchesSubcategory = !subcategory || listing.fashion_category === subcategory;
      const matchesBrand = !brand || Boolean(listing.brand && brandSlug(listing.brand) === brand);
      return matchesSchool && matchesSearch && matchesCategory && matchesCondition && matchesPrice && matchesSize && matchesWaist && matchesInseam && matchesColor && matchesSubcategory && matchesBrand;
    });
    return filtered.sort((a, b) => {
      if (sort === "price_low") return a.price_cents - b.price_cents;
      if (sort === "price_high") return b.price_cents - a.price_cents;
      if (sort === "newest") return Date.parse(b.created_at) - Date.parse(a.created_at);
      return 0;
    });
  }, [brand, category, color, condition, inseam, maxPrice, minPrice, school, schoolFilter, search, size, sort, subcategory, waist]);

  const peopleState = peopleResult.query === search.trim() ? peopleResult.state : "loading";
  const people = peopleResult.query === search.trim() ? peopleResult.people : [];
  const selectedSchool = schools.find((item) => item.slug === schoolFilter);
  const activeSchool = school ?? selectedSchool;

  function clearFilters() {
    setCondition("");
    setMinPrice("");
    setMaxPrice("");
    setCategory("trending");
    setSubcategory("");
    setBrand("");
    setSize("");
    setWaist("");
    setInseam("");
    setColor("");
    setSort("relevance");
    if (!school) {
      setSchoolFilter(homeSchoolSlug);
      setAllSchoolsExplicit(false);
    }
  }

  function selectSchool(value: string) {
    setSchoolFilter(value);
    setAllSchoolsExplicit(!value);
  }

  return (
    <section className="mx-auto max-w-6xl px-4 pt-6 pb-28 sm:px-6 sm:pt-9 desktop:pb-16">
      {!school && search.trim() && <section className="mb-10"><h2 className="type-wide text-lg font-extrabold">People</h2>
        {peopleState === "loading" && <div className="mt-4 h-20 animate-pulse rounded-xl bg-surface" />}
        {peopleState === "signed-out" && <p className="mt-3 rounded-xl bg-surface p-4 text-sm"><Link href="/account/login" className="font-bold text-brand underline underline-offset-2">Log in</Link> to search for students by name or username.</p>}
        {peopleState === "error" && <p className="mt-3 text-sm text-[var(--danger)]">Account search isn’t available right now. Try again in a moment.</p>}
        {peopleState === "ready" && (people.length ? <div className="mt-4 grid gap-3 sm:grid-cols-2">{people.map((user) => <UserResult key={user.id} user={user} />)}</div> : <p className="mt-3 text-sm text-muted">No students match “{search.trim()}”.</p>)}
      </section>}

      <div className="mb-6 flex flex-wrap items-end justify-between gap-x-6 gap-y-4">
        <div>
          <p className="text-sm font-semibold text-muted">{school?.name ?? selectedSchool?.name ?? "All schools"}</p>
          <h1 className="type-wide mt-1 text-2xl font-black sm:text-[2rem]">{search ? `Results for “${search}”` : brand ? POPULAR_BRANDS.find((item) => item.slug === brand)?.name : subcategory ? (category === "accessories" ? ACCESSORY_DEPARTMENTS : FASHION_DEPARTMENTS[category as "women" | "men"] ?? []).find((item) => item.slug === subcategory)?.name : category === "trending" ? activeSchool ? `Trending at ${activeSchool.short_name}` : "Trending across Tanu" : DISCOVERY_CATEGORIES.find((item) => item.slug === category)?.name}</h1>
          <p className="mt-1.5 text-sm text-muted">{listings.length} {listings.length === 1 ? "item" : "items"}. Sample listings shown while selling is being built.</p>
        </div>
      </div>

      <MarketplaceFilterBar listings={DISCOVERY_PREVIEW_LISTINGS} schools={schools} showSchool={!school} school={schoolFilter} category={category} subcategory={subcategory} brand={brand} minPrice={minPrice} maxPrice={maxPrice} size={size} waist={waist} inseam={inseam} color={color} condition={condition} sort={sort} setSchool={selectSchool} setCategory={setCategory} setSubcategory={setSubcategory} setBrand={setBrand} setMinPrice={setMinPrice} setMaxPrice={setMaxPrice} setSize={setSize} setWaist={setWaist} setInseam={setInseam} setColor={setColor} setCondition={setCondition} setSort={setSort} clearAll={clearFilters} />

      <div>
        {listings.length ? <div className="grid grid-cols-2 gap-x-3 gap-y-6 sm:grid-cols-3 sm:gap-x-4 sm:gap-y-8 lg:grid-cols-4">{listings.map((listing: DiscoveryListing) => <ListingCard key={listing.id} listing={listing} showSchool={!school} />)}</div> : <div className="grid min-h-80 place-items-center rounded-xl bg-surface px-6 text-center"><div><h2 className="type-wide text-xl font-extrabold">Nothing matches yet</h2><p className="mt-2 max-w-sm text-sm leading-6 text-muted">Try a broader search, another category, or fewer filters.</p><button onClick={() => { clearFilters(); setSearch(""); }} className="btn btn-secondary mt-5">Clear search and filters</button></div></div>}
      </div>
    </section>
  );
}
