"use client";

import { useEffect, useState } from "react";

import { getSchools, type SchoolMarketplace } from "@/lib/platform";

export function SupportedSchoolsNote() {
  const [schools, setSchools] = useState<SchoolMarketplace[]>([]);

  useEffect(() => {
    let active = true;
    getSchools()
      .then((directory) => {
        if (active) setSchools(directory.filter((school) => school.signup_is_open));
      })
      .catch(() => undefined);
    return () => {
      active = false;
    };
  }, []);

  if (schools.length === 0) {
    return <div className="rounded-xl bg-surface px-4 py-3 text-sm leading-6 text-ink"><strong>School email required.</strong> Use an email from a university currently supported by Tanu.</div>;
  }

  return <div className="rounded-xl bg-surface px-4 py-3 text-sm leading-6 text-ink"><strong>Open for signup:</strong> {schools.map((school) => school.short_name).join(", ")}. Accepted domains: {schools.flatMap((school) => school.domains.map((domain) => `@${domain}`)).join(", ")}.</div>;
}
