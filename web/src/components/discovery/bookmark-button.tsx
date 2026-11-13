"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { BOOKMARK_FAILURES, setBookmarked, useIsBookmarked } from "@/lib/bookmarks";
import { HeartIcon } from "@/components/ui/icons";

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

  // Lucide has no filled heart: a saved one is the outline filled in.
  const heart = <HeartIcon className={variant === "card" ? "size-5" : "size-4"} fill={saved ? "currentColor" : "none"} aria-hidden="true" />;
  const label = saved ? "Remove saved listing" : "Save listing";
  const status = error && <span role="alert" className={variant === "card" ? "absolute right-0 top-11 z-10 w-44 rounded-lg bg-ink px-2.5 py-1.5 text-fine font-semibold text-white shadow-float" : "text-fine text-danger"}>{error}</span>;

  if (variant === "page") {
    return <span className="flex flex-col items-end gap-1">
      <button type="button" onClick={toggle} disabled={busy} aria-pressed={saved} aria-label={label} className={`btn btn-sm btn-quiet shrink-0 ${saved ? "text-brand" : ""}`}>{heart}<span aria-hidden="true">{saved ? "Saved" : "Save"}</span></button>
      {status}
    </span>;
  }
  return <span className="absolute right-0.5 top-0.5">
    {/* A 44px target around the 36px circle, so a near miss doesn't open the listing. */}
    <button type="button" onClick={toggle} disabled={busy} aria-pressed={saved} aria-label={label} className={`group/save grid size-11 place-items-center rounded-full -outline-offset-4 disabled:opacity-70 ${saved ? "text-danger" : "text-ink"}`}>
      <span className="grid size-9 place-items-center rounded-full bg-white/90 shadow-float backdrop-blur transition-transform duration-150 motion-safe:group-hover/save:scale-105 motion-safe:group-active/save:scale-90">{heart}</span>
    </button>
    {status}
  </span>;
}
