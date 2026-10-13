"use client";

import { useEffect, useState } from "react";

import type { components } from "@/lib/api/schema";
import { formatDateTime } from "@/lib/time";
import { getMyRestrictions } from "@/lib/trust";

type Restriction = components["schemas"]["MyRestriction"];

const PAUSED: Record<string, string> = {
  selling: "Posting and selling items",
  messaging: "Sending messages",
  deals: "Making and answering requests",
};

/** Tells a student what a moderator has paused on their account, and until when. Renders
 * nothing for everyone else. */
export function RestrictionNotice({ only }: { only?: Restriction["kind"][] }) {
  const [restrictions, setRestrictions] = useState<Restriction[]>([]);

  useEffect(() => {
    let active = true;
    getMyRestrictions()
      .then((rows) => active && setRestrictions(rows))
      .catch(() => {});
    return () => {
      active = false;
    };
  }, []);

  const shown = restrictions.filter((row) => !only || only.includes(row.kind));
  if (!shown.length) return null;
  return (
    <div role="status" className="mb-4 rounded-xl border border-[var(--danger)] bg-background p-4 text-sm">
      <p className="font-bold">Some features are paused on your account</p>
      <ul className="mt-2 space-y-1 text-muted">
        {shown.map((row, index) => (
          <li key={index}>
            {PAUSED[row.kind] ?? row.kind_label} is paused{" "}
            {row.expires_at ? `until ${formatDateTime(row.expires_at)}` : "until a moderator lifts it"} after a moderation review.
          </li>
        ))}
      </ul>
      <p className="mt-2 text-muted">Anything already in progress, like a Pending handoff, can still be finished.</p>
    </div>
  );
}
