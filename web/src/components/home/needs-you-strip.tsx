"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { listDeals, needsYou } from "@/lib/deals";
import { ChevronRightIcon } from "@/components/ui/icons";

/** Home's one-line "N deals need you" strip. It links to Deals, where they're answered, and
 * shows nothing while loading, on an error, or when nothing is waiting. */
export function NeedsYouStrip() {
  const [summary, setSummary] = useState<ReturnType<typeof needsYou>>(null);

  useEffect(() => {
    let active = true;
    listDeals("current")
      .then((deals) => active && setSummary(needsYou(deals, Date.now())))
      .catch(() => {});
    return () => { active = false; };
  }, []);

  if (!summary) return null;
  return <Link href="/deals" className="mb-5 flex min-h-14 w-full items-center gap-3 rounded-xl bg-surface py-2 pl-4 pr-3 transition hover:bg-ink-soft desktop:w-auto desktop:max-w-md desktop:inline-flex">
    <span className="size-2.5 shrink-0 rounded-full bg-signal" aria-hidden="true" />
    <span className="min-w-0 flex-1 leading-tight">
      <span className="block truncate font-semibold">{summary.title}</span>
      <span className="mt-0.5 block text-fine text-muted">{summary.detail}</span>
    </span>
    <ChevronRightIcon className="size-5 shrink-0 text-muted" aria-hidden="true" />
  </Link>;
}
