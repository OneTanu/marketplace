"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

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
    return <div className="mx-auto min-h-[65vh] max-w-6xl animate-pulse px-4 py-12 sm:px-6"><div className="h-8 w-40 rounded-full bg-foreground/5" /><div className="mt-6 h-16 max-w-2xl rounded-2xl bg-foreground/5" /></div>;
  }

  if (state === "missing" || !school) {
    return <section className="mx-auto min-h-[65vh] max-w-3xl px-4 py-20 text-center"><p className="text-xs font-bold uppercase tracking-[.18em] text-brand">Marketplace not found</p><h1 className="mt-4 text-4xl font-black tracking-[-.04em]">That school is not on Tanu yet.</h1><p className="mx-auto mt-4 max-w-lg leading-7 text-muted">Choose another supported school marketplace to keep browsing.</p><Link href="/" className="mt-8 inline-flex rounded-full bg-foreground px-6 py-3 text-sm font-bold text-white">Return home</Link></section>;
  }

  if (school.marketplace_status !== "open") {
    return <section className="mx-auto min-h-[65vh] max-w-3xl px-4 py-20 text-center"><p className="text-xs font-bold uppercase tracking-[.18em] text-brand">{school.marketplace_status}</p><h1 className="mt-4 text-4xl font-black tracking-[-.04em]">{school.name} is coming to Tanu.</h1><p className="mx-auto mt-4 max-w-lg leading-7 text-muted">This school marketplace is not open for browsing yet.</p><Link href="/" className="mt-8 inline-flex rounded-full border border-line bg-white px-6 py-3 text-sm font-bold">Explore Tanu</Link></section>;
  }

  const location = [school.city, school.state].filter(Boolean).join(", ");

  return <>
    <section className="border-b border-line bg-[#fffdf8]"><div className="mx-auto max-w-6xl px-4 py-12 sm:px-6 sm:py-16"><div className="flex flex-col gap-7 sm:flex-row sm:items-end sm:justify-between"><div><div className="inline-flex items-center gap-2 rounded-full bg-[var(--forest-soft)] px-3 py-1.5 text-xs font-bold uppercase tracking-[.14em] text-forest"><span className="size-2 rounded-full bg-[#36a269]" />Open marketplace</div><h1 className="mt-5 text-4xl font-black tracking-[-.05em] sm:text-6xl">{school.short_name} Marketplace</h1><p className="mt-4 text-lg text-muted">{location || school.name} · Buy and sell with verified students.</p></div><Link href="/sell" className="inline-flex justify-center rounded-full bg-foreground px-6 py-3.5 text-sm font-bold text-white transition hover:bg-forest">Sell from your school</Link></div></div></section>
    <section className="mx-auto min-h-[48vh] max-w-6xl px-4 py-12 sm:px-6"><div className="rounded-[2rem] border border-dashed border-line bg-white/45 px-6 py-16 text-center"><div className="mx-auto grid size-14 place-items-center rounded-2xl bg-[var(--brand-soft)] text-2xl text-brand">+</div><h2 className="mt-5 text-2xl font-bold tracking-tight">No listings here yet</h2><p className="mx-auto mt-2 max-w-md leading-7 text-muted">When students at {school.short_name} publish items, the newest listings will appear here.</p></div></section>
  </>;
}
