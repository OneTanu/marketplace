"use client";

import Link from "next/link";
import { FormEvent, useEffect, useState } from "react";

import { categoryTree, loadItemCategories, type CategoryTree } from "@/lib/categories";
import { priceLabel } from "@/lib/discovery";
import { COLORS, CONDITIONS } from "@/lib/listing-options";
import {
  deleteSavedSearch,
  listSavedSearches,
  MAX_NAME_LENGTH,
  savedSearchHref,
  updateSavedSearch,
  type SavedSearch,
} from "@/lib/saved-searches";

/** The filters of a saved search in words, e.g. ["“denim”", "Men › Jeans", "Under $40"]. */
function describe(filters: SavedSearch["filters"], tree: CategoryTree | null) {
  const category = filters.category ? tree?.bySlug.get(filters.category) : undefined;
  const department = category && tree?.departmentOf(category);
  const low = filters.min_price, high = filters.max_price;
  return [
    filters.q && `“${filters.q}”`,
    filters.category && (category ? (department && department.id !== category.id ? `${department.name} › ${category.name}` : category.name) : filters.category),
    filters.brand,
    filters.size && `Size ${filters.size}`,
    COLORS.find((c) => c.value === filters.color)?.label,
    CONDITIONS.find((c) => c.value === filters.condition)?.label,
    low != null && high != null ? `${priceLabel(low)}–${priceLabel(high)}` : high != null ? `Under ${priceLabel(high)}` : low != null ? `${priceLabel(low)} and up` : "",
    filters.school === "all" ? "All schools" : filters.school ? filters.school.toUpperCase() : "Your school",
  ].filter((part): part is string => Boolean(part));
}

function SavedSearchRow({ search, tree, onChange, onDelete }: {
  search: SavedSearch;
  tree: CategoryTree | null;
  onChange: (search: SavedSearch) => void;
  onDelete: () => void;
}) {
  const [renaming, setRenaming] = useState(false);
  const [confirming, setConfirming] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function run(action: () => Promise<void>) {
    setBusy(true);
    setError("");
    try {
      await action();
    } catch (failure) {
      setError(failure instanceof Error ? failure.message : "Something went wrong. Try again.");
    } finally {
      setBusy(false);
    }
  }

  function rename(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const name = String(new FormData(event.currentTarget).get("name") ?? "");
    run(async () => { onChange(await updateSavedSearch(search.id, { name })); setRenaming(false); });
  }

  const titleId = `saved-search-${search.id}`;
  return <li aria-labelledby={titleId} className="rounded-2xl border border-line bg-background p-5">
    {renaming
      ? <form onSubmit={rename} className="flex flex-wrap items-end gap-2">
          <label className="min-w-0 flex-1 text-sm font-bold">Search name
            <input name="name" defaultValue={search.name} maxLength={MAX_NAME_LENGTH} required autoFocus className="field mt-2 text-[15px] font-normal" />
          </label>
          <button disabled={busy} className="btn btn-primary btn-sm h-11">{busy ? "Saving…" : "Save name"}</button>
          <button type="button" onClick={() => setRenaming(false)} className="btn btn-quiet btn-sm h-11">Cancel</button>
        </form>
      : <h2 id={titleId} className="text-lg font-bold">{search.name}</h2>}
    <p className="mt-1 text-sm text-muted">{describe(search.filters, tree).join(" · ")}</p>

    <div className="mt-4 flex flex-wrap items-center gap-2">
      <Link href={savedSearchHref(search.filters)} className="btn btn-primary btn-sm">Run search</Link>
      {!renaming && <button type="button" onClick={() => setRenaming(true)} className="btn btn-secondary btn-sm">Rename</button>}
      <label className="ml-auto flex cursor-pointer items-center gap-2 text-sm font-semibold">
        <input type="checkbox" role="switch" checked={search.alerts_enabled} disabled={busy} onChange={(event) => { const on = event.target.checked; run(async () => onChange(await updateSavedSearch(search.id, { alerts_enabled: on }))); }} className="size-4 accent-[var(--brand)]" />
        New-listing alerts
      </label>
    </div>

    <div className="mt-3 border-t border-line pt-3">
      {confirming
        ? <div role="group" aria-label={`Delete ${search.name}`} className="flex flex-wrap items-center gap-2 text-sm">
            <span>Delete this saved search?</span>
            <button type="button" disabled={busy} onClick={() => run(async () => { await deleteSavedSearch(search.id); onDelete(); })} className="btn btn-sm bg-[var(--danger)] text-white">{busy ? "Deleting…" : "Delete"}</button>
            <button type="button" onClick={() => setConfirming(false)} className="btn btn-quiet btn-sm">Keep it</button>
          </div>
        : <button type="button" onClick={() => setConfirming(true)} className="text-sm font-semibold text-[var(--danger)] hover:underline">Delete</button>}
    </div>
    {error && <p role="alert" className="mt-2 text-sm text-[var(--danger)]">{error}</p>}
  </li>;
}

/** /profile/searches: the student's saved searches, to run, rename, switch alerts for, or delete. */
export function SavedSearches() {
  // undefined while loading, null when signed out.
  const [searches, setSearches] = useState<SavedSearch[] | null>();
  const [failed, setFailed] = useState(false);
  const [tree, setTree] = useState<CategoryTree | null>(null);
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    let active = true;
    listSavedSearches()
      .then((list) => { if (active) { setSearches(list); setFailed(false); } })
      .catch(() => active && setFailed(true));
    loadItemCategories().then((categories) => active && setTree(categories ? categoryTree(categories) : null));
    return () => { active = false; };
  }, [attempt]);

  const header = <>
    <Link href="/profile" className="text-sm font-bold text-muted hover:text-ink">← Back to profile</Link>
    <div className="mt-5">
      <h1 className="type-wide text-3xl font-black">Saved searches</h1>
      <p className="mt-2 max-w-2xl leading-6 text-muted">Run a search again in one tap, and get a notification when a new listing matches one with alerts on.</p>
    </div>
  </>;
  const shell = "mx-auto min-h-[70vh] max-w-3xl px-4 py-8 pb-28 sm:px-6 sm:py-10 desktop:pb-12";

  if (failed) {
    return <main className={shell}>{header}<div role="alert" className="mt-8 rounded-2xl bg-surface p-6 text-center"><p className="font-bold">Couldn’t load your saved searches</p><button type="button" onClick={() => { setFailed(false); setAttempt((n) => n + 1); }} className="btn btn-secondary mt-4">Try again</button></div></main>;
  }
  if (searches === undefined) {
    return <main className={shell}>{header}<div aria-busy="true" aria-label="Loading saved searches" className="mt-8 h-40 animate-pulse rounded-2xl bg-surface" /></main>;
  }
  if (searches === null) {
    return <main className={shell}>{header}<div className="mt-8 rounded-2xl bg-surface p-6 text-center"><p className="font-bold">Log in to see your saved searches</p><Link href="/account/login" className="btn btn-primary mt-4">Log in</Link></div></main>;
  }
  return <main className={shell}>
    {header}
    {searches.length
      ? <ul aria-label="Saved searches" className="mt-8 space-y-3">
          {searches.map((search) => <SavedSearchRow key={search.id} search={search} tree={tree}
            onChange={(updated) => setSearches((list) => list?.map((s) => (s.id === updated.id ? updated : s)))}
            onDelete={() => setSearches((list) => list?.filter((s) => s.id !== search.id))} />)}
        </ul>
      : <div className="mt-8 grid min-h-56 place-items-center rounded-3xl border border-dashed border-line bg-white/45 px-6 text-center"><div className="max-w-sm py-8"><h2 className="text-lg font-bold">No saved searches yet</h2><p className="mt-2 text-sm leading-6 text-muted">Search or filter the marketplace, then choose “Save this search”.</p><Link href="/search" className="btn btn-secondary mt-5">Browse listings</Link></div></div>}
  </main>;
}
