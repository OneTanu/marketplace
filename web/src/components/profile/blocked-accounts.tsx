"use client";

import { useEffect, useState } from "react";

import { Skeleton } from "@/components/ui/card";
import { FocusedHeader } from "@/components/ui/focused-header";
import type { components } from "@/lib/api/schema";
import { listBlocks, unblockUser } from "@/lib/trust";

type BlockedUser = components["schemas"]["BlockedUser"];

/** The students you've blocked, with Unblock. Blocked students' profiles can't be opened, so
 * this is the place to undo a block. */
export function BlockedAccounts() {
  const [blocks, setBlocks] = useState<BlockedUser[] | null>();
  const [failed, setFailed] = useState(false);
  const [pending, setPending] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;
    listBlocks().then((rows) => active && setBlocks(rows)).catch(() => active && setFailed(true));
    return () => { active = false; };
  }, []);

  async function unblock(username: string) {
    setPending(username);
    setError("");
    try {
      await unblockUser(username);
      setBlocks((rows) => rows?.filter((row) => row.username !== username));
    } catch {
      setError(`We couldn’t unblock @${username}. Try again.`);
    } finally {
      setPending("");
    }
  }

  return <>
    <FocusedHeader title="Blocked accounts" backHref="/profile" backLabel="Back to profile" />
    <main className="mx-auto min-h-[70vh] max-w-2xl px-4 pb-12 pt-4 sm:px-6">
      <p className="max-w-2xl leading-6 text-muted">You and the students you block can’t see each other’s profiles or listings, message, or make deals. They aren’t told they were blocked.</p>
      {failed && <div role="alert" className="mt-6 rounded-xl bg-surface p-6 text-center"><p className="font-semibold">Couldn’t load your blocked accounts</p><p className="mt-1 text-label text-muted">Refresh to try again, or log in if you’re signed out.</p></div>}
      {!failed && blocks === undefined && <Skeleton className="mt-6 h-32" />}
      {blocks && (blocks.length === 0
        ? <p className="mt-6 rounded-xl bg-surface p-6 text-center text-label text-muted">You haven’t blocked anyone.</p>
        : <ul className="mt-6 grid gap-3">{blocks.map((row) => <li key={row.username} className="flex items-center justify-between gap-3 rounded-xl border border-line p-3.5">
            <div className="min-w-0"><p className="truncate font-semibold">{row.first_name || `@${row.username}`}</p><p className="truncate text-label text-muted">{row.first_name ? `@${row.username}` : `Blocked ${new Date(row.created_at).toLocaleDateString("en-US", { month: "short", day: "numeric", timeZone: "America/New_York" })}`}</p></div>
            <button type="button" onClick={() => unblock(row.username)} disabled={pending === row.username} className="btn btn-secondary shrink-0">{pending === row.username ? "Unblocking…" : "Unblock"}</button>
          </li>)}</ul>)}
      {error && <p role="alert" className="mt-3 text-label text-danger">{error}</p>}
    </main>
  </>;
}
