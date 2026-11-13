"use client";

import { type ReactNode, Suspense, useEffect, useState } from "react";

import { MarketplaceDepartmentNav } from "@/components/discovery/marketplace-department-nav";
import { MarketplaceFeed } from "@/components/discovery/marketplace-feed";
import { BottomBarSpacer } from "@/components/site-footer";
import { getCurrentUser } from "@/lib/platform";

import { NeedsYouStrip } from "./needs-you-strip";

function FeedSkeleton() {
  return <div aria-busy="true" aria-label="Loading listings" className="mx-auto max-w-6xl animate-pulse px-4 pt-6 sm:px-6 sm:pt-9">
    <div className="h-8 w-48 rounded bg-surface" />
    <div className="mt-6 grid grid-cols-2 gap-x-3 gap-y-6 sm:grid-cols-3 sm:gap-x-4 lg:grid-cols-4">{Array.from({ length: 8 }).map((_, index) => <div key={index} className="aspect-[4/5] rounded-md bg-surface" />)}</div>
  </div>;
}

/** Home for a signed-in student: the category tabs, the "Needs you" strip, and their school's
 * feed. If the session turns out to have expired, it shows `guest` (the guest Home) instead. */
export function SignedInHome({ guest }: { guest: ReactNode }) {
  // The feed starts loading at once (the API scopes it to the viewer's school); this check only
  // decides whether the session expired. A failed check keeps the feed, which reports its own
  // errors.
  const [signedOut, setSignedOut] = useState(false);

  useEffect(() => {
    let active = true;
    getCurrentUser().then((current) => active && setSignedOut(current === null), () => {});
    return () => { active = false; };
  }, []);

  if (signedOut) return guest;
  // data-home-feed hides the site footer on this page (globals.css), so it's gone from the first
  // paint; if the session turns out to be expired, the guest page comes back with it.
  return <div data-home-feed>
    {/* Under the sticky site header (64px), like the department tabs on Search. They open Search. */}
    <div className="sticky top-16 z-10 border-b border-line bg-background/95 backdrop-blur-xl">
      <Suspense fallback={<div className="h-12" />}><MarketplaceDepartmentNav /></Suspense>
    </div>
    <Suspense fallback={<FeedSkeleton />}><MarketplaceFeed variant="home" above={<NeedsYouStrip />} /></Suspense>
    <BottomBarSpacer />
  </div>;
}
