"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { BOOKMARK_FAILURES, setBookmarked, useIsBookmarked } from "@/lib/bookmarks";

/** Save or unsave a listing. The heart fills at once and empties again if the request fails;
 * signed-out students are sent to log in. `variant` sizes it for a card photo or a listing page. */
export function BookmarkButton({ listingId, isBookmarked, variant = "card" }: {
  listingId: number;
  isBookmarked: boolean;
  variant?: "card" | "page";
}) {
  const router = useRouter();
  const saved = useIsBookmarked(listingId, isBookmarked);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function toggle() {
    if (busy) return;
    setBusy(true);
    setError("");
    const failure = await setBookmarked(listingId, !saved, saved);
    setBusy(false);
    if (failure === "signed-out") router.push("/account/login");
    else if (failure) setError(BOOKMARK_FAILURES[failure]);
  }

  const heart = <svg viewBox="0 0 24 24" className={variant === "card" ? "size-[18px]" : "size-4"} fill={saved ? "currentColor" : "none"} stroke="currentColor" strokeWidth={2} aria-hidden="true"><path d="M12 20.5s-7.5-4.6-9.3-9.2C1.5 8.1 3.6 4.5 7.2 4.5c2 0 3.6 1.1 4.8 2.9 1.2-1.8 2.8-2.9 4.8-2.9 3.6 0 5.7 3.6 4.5 6.8-1.8 4.6-9.3 9.2-9.3 9.2Z" /></svg>;
  const label = saved ? "Remove saved listing" : "Save listing";
  const status = error && <span role="alert" className={variant === "card" ? "absolute right-0 top-11 z-10 w-44 rounded-md bg-ink px-2.5 py-1.5 text-xs font-medium text-white shadow" : "text-xs text-[var(--danger)]"}>{error}</span>;

  if (variant === "page") {
    return <span className="flex flex-col items-end gap-1">
      <button type="button" onClick={toggle} disabled={busy} aria-pressed={saved} aria-label={label} className={`btn btn-sm btn-quiet shrink-0 ${saved ? "text-brand" : ""}`}>{heart}<span aria-hidden="true">{saved ? "Saved" : "Save"}</span></button>
      {status}
    </span>;
  }
  return <span className="absolute right-2 top-2">
    <button type="button" onClick={toggle} disabled={busy} aria-pressed={saved} aria-label={label} className={`grid size-9 place-items-center rounded-full bg-white/90 shadow-sm backdrop-blur transition hover:scale-105 disabled:opacity-70 ${saved ? "text-[#d42b33]" : "text-ink"}`}>{heart}</button>
    {status}
  </span>;
}
