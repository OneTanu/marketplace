"use client";

import Link from "next/link";
import { FormEvent, useEffect, useState } from "react";

import type { FeedParams } from "@/lib/discovery";
import {
  createSavedSearch,
  defaultSearchName,
  filtersKey,
  listSavedSearches,
  MAX_NAME_LENGTH,
  toSavedFilters,
  type SavedSearch,
} from "@/lib/saved-searches";
import { BookmarkIcon, CheckIcon } from "@/components/ui/icons";

/** "Save this search" for the feed's current filters, or a note that they're already saved.
 * Only for signed-in students, and only when keywords or a filter are set. */
export function SaveSearch({ feed, fixedSchool, categoryLabel, schoolLabel }: {
  feed: FeedParams;
  fixedSchool?: string;
  categoryLabel?: string;
  schoolLabel?: string;
}) {
  // undefined while loading, null if the list couldn't be loaded.
  const [saved, setSaved] = useState<SavedSearch[] | null>();
  const [open, setOpen] = useState(false);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;
    listSavedSearches().then((searches) => active && setSaved(searches)).catch(() => active && setSaved(null));
    return () => { active = false; };
  }, []);

  const filters = toSavedFilters(feed, fixedSchool);
  const key = filtersKey(filters);
  const match = saved?.find((search) => filtersKey(search.filters) === key);
  const suggestedName = defaultSearchName(feed, { category: categoryLabel, school: schoolLabel });

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const data = new FormData(event.currentTarget);
    setPending(true);
    setError("");
    try {
      const search = await createSavedSearch({
        name: String(data.get("name") ?? "").trim(),
        filters,
        alerts_enabled: data.get("alerts") === "on",
      });
      setSaved((list) => [search, ...(list ?? [])]);
      setOpen(false);
    } catch (failure) {
      setError(failure instanceof Error ? failure.message : "Couldn’t save this search. Try again.");
    } finally {
      setPending(false);
    }
  }

  if (saved === undefined) return null;
  if (match) {
    return <p role="status" className="flex flex-wrap items-center gap-x-3 gap-y-1 text-label">
      <span className="inline-flex items-center gap-1.5 font-semibold text-ink"><CheckIcon className="size-4 text-brand" aria-hidden="true" />Saved as “{match.name}”{match.alerts_enabled ? ", with new-listing alerts" : ""}</span>
      <Link href="/profile/searches" className="font-semibold text-muted underline underline-offset-4 hover:text-foreground">Manage saved searches</Link>
    </p>;
  }
  if (!open) {
    return <div>
      <button type="button" onClick={() => { setOpen(true); setError(""); }} className="btn btn-secondary btn-sm">
        <BookmarkIcon className="size-4" aria-hidden="true" />
        Save this search
      </button>
    </div>;
  }
  return <form onSubmit={submit} aria-label="Save this search" className="max-w-xl space-y-3 rounded-xl border border-line bg-white/70 p-4">
    <label className="block text-label font-semibold">Name
      <input name="name" defaultValue={suggestedName} maxLength={MAX_NAME_LENGTH} required autoFocus className="field mt-2 font-normal" />
    </label>
    <label className="flex items-start gap-2.5 text-label">
      <input type="checkbox" name="alerts" defaultChecked className="mt-0.5 size-4 accent-brand" />
      <span><span className="font-semibold">Notify me about new listings</span><span className="block text-muted">Get a notification when something new matches this search.</span></span>
    </label>
    {error && <p role="alert" className="text-label text-danger">{error}</p>}
    {saved === null && <p className="text-label text-muted">Couldn’t check your saved searches; saving may tell you it’s a duplicate.</p>}
    <div className="flex gap-2">
      <button disabled={pending} className="btn btn-primary btn-sm">{pending ? "Saving…" : "Save search"}</button>
      <button type="button" onClick={() => setOpen(false)} className="btn btn-quiet btn-sm">Cancel</button>
    </div>
  </form>;
}
