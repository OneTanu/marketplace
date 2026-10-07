"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { MarketplaceFeed } from "@/components/discovery/marketplace-feed";
import { getSchool, type SchoolMarketplace } from "@/lib/platform";

export function SchoolMarketplaceView({ slug }: { slug: string }) {
  const [school, setSchool] = useState<SchoolMarketplace | null>(null);
  const [state, setState] = useState<"loading" | "ready" | "missing">("loading");

  useEffect(() => {
    let active = true;
    getSchool(slug)
      .then((result) => {
        if (!active) return;
        setSchool(result);
        setState("ready");
      })
      .catch(() => active && setState("missing"));
    return () => {
      active = false;
    };
  }, [slug]);

  if (state === "loading") {
    return <div className="mx-auto min-h-[65vh] max-w-6xl animate-pulse px-4 py-9 sm:px-6"><div className="h-4 w-40 rounded bg-surface" /><div className="mt-3 h-9 w-72 rounded bg-surface" /><div className="mt-8 grid grid-cols-2 gap-4 sm:grid-cols-4">{Array.from({ length: 8 }).map((_, index) => <div key={index} className="aspect-[4/5] rounded-md bg-surface" />)}</div></div>;
  }

  if (state === "missing" || !school) {
    return <section className="mx-auto min-h-[65vh] max-w-3xl px-4 py-20 text-center"><p className="text-sm font-semibold text-brand">Marketplace not found</p><h1 className="mt-4 text-4xl type-wide font-black">That school is not on Tanu yet.</h1><p className="mx-auto mt-4 max-w-lg leading-7 text-muted">Choose another supported school marketplace to keep browsing.</p><Link href="/" className="mt-8 inline-flex btn btn-primary">Return home</Link></section>;
  }

  if (school.marketplace_status !== "open") {
    return <section className="mx-auto min-h-[65vh] max-w-3xl px-4 py-20 text-center"><p className="text-sm font-semibold text-brand">{school.marketplace_status}</p><h1 className="mt-4 text-4xl type-wide font-black">{school.name} is coming to Tanu.</h1><p className="mx-auto mt-4 max-w-lg leading-7 text-muted">This school marketplace is not open for browsing yet.</p><Link href="/" className="mt-8 inline-flex btn btn-secondary">Explore Tanu</Link></section>;
  }

  return <MarketplaceFeed school={school} />;
}
