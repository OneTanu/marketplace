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

  const selected = pathname === "/search"
    ? "all"
    : routeSlug && schools.some((school) => school.slug === routeSlug)
      ? routeSlug
      : homeSlug || schools[0]?.slug;

  return (
    <label className="relative block">
      <span className="sr-only">School marketplace</span>
      <select
        aria-label="School marketplace"
        value={selected}
        onChange={(event) => router.push(event.target.value === "all" ? "/search" : `/schools/${event.target.value}`)}
        className="chip h-9 max-w-36 appearance-none truncate pr-8 text-ink outline-none sm:max-w-48"
      >
        <option value="all">All schools</option>
        {schools.map((school) => (
          <option key={school.slug} value={school.slug}>
            {school.short_name}
          </option>
        ))}
      </select>
      <svg aria-hidden="true" viewBox="0 0 12 12" className="pointer-events-none absolute right-3 top-1/2 size-2.5 -translate-y-1/2 text-muted" fill="none" stroke="currentColor" strokeWidth={1.8}><path d="m2 4 4 4 4-4" /></svg>
    </label>
  );
}
