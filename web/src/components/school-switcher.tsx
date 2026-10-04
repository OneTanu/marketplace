"use client";

import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { getCurrentUser, getSchools, type SchoolMarketplace } from "@/lib/platform";

export function SchoolSwitcher() {
  const pathname = usePathname();
  const router = useRouter();
  const [schools, setSchools] = useState<SchoolMarketplace[]>([]);
  const [homeSlug, setHomeSlug] = useState("");
  const [ready, setReady] = useState(false);
  const routeSlug = pathname.match(/^\/schools\/([^/]+)/)?.[1];

  useEffect(() => {
    let active = true;
    Promise.all([getCurrentUser(), getSchools()])
      .then(([user, directory]) => {
        if (!active) return;
        setHomeSlug(user?.school?.slug ?? "");
        setSchools(directory.filter((school) => school.marketplace_status === "open"));
        setReady(true);
      })
      .catch(() => active && setReady(false));
    return () => {
      active = false;
    };
  }, []);

  if (!ready || schools.length === 0) return null;

  const selected = routeSlug && schools.some((school) => school.slug === routeSlug)
    ? routeSlug
    : homeSlug || schools[0]?.slug;

  return (
    <label className="relative block">
      <span className="sr-only">School marketplace</span>
      <select
        aria-label="School marketplace"
        value={selected}
        onChange={(event) => router.push(`/schools/${event.target.value}`)}
        className="h-10 max-w-40 appearance-none truncate rounded-full border border-line bg-white/70 py-2 pl-3 pr-8 text-[13px] font-semibold text-foreground outline-none transition hover:bg-white focus:border-forest focus:ring-4 focus:ring-forest/10 sm:max-w-48 sm:pl-4 sm:pr-9 sm:text-sm"
      >
        {schools.map((school) => (
          <option key={school.slug} value={school.slug}>
            {school.short_name} Marketplace
          </option>
        ))}
      </select>
      <span aria-hidden="true" className="pointer-events-none absolute right-3 top-2.5 text-xs text-muted">⌄</span>
    </label>
  );
}
