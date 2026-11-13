"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

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

  return <main className="mx-auto min-h-[70vh] max-w-3xl px-4 py-8 pb-28 sm:px-6 sm:py-10 desktop:pb-12">
    <Link href="/profile" className="text-sm font-bold text-muted hover:text-ink">← Back to profile</Link>
    <div className="mt-5">
      <h1 className="type-wide text-3xl font-black">Blocked accounts</h1>
      <p className="mt-2 max-w-2xl leading-6 text-muted">You and the students you block can’t see each other’s profiles or listings, message, or make deals. They aren’t told they were blocked.</p>
    </div>
    {failed && <div role="alert" className="mt-8 rounded-2xl bg-surface p-6 text-center"><p className="font-bold">Couldn’t load your blocked accounts</p><p className="mt-1 text-sm text-muted">Refresh to try again, or log in if you’re signed out.</p></div>}
    {!failed && blocks === undefined && <div aria-busy="true" aria-label="Loading blocked accounts" className="mt-8 h-32 animate-pulse rounded-2xl bg-surface" />}
    {blocks && (blocks.length === 0
      ? <p className="mt-8 rounded-2xl bg-surface p-6 text-center text-sm text-muted">You haven’t blocked anyone.</p>
      : <ul className="mt-8 grid gap-3">{blocks.map((row) => <li key={row.username} className="flex items-center justify-between gap-3 rounded-xl border border-line p-3.5">
          <div className="min-w-0"><p className="truncate font-bold">{row.first_name || `@${row.username}`}</p><p className="truncate text-sm text-muted">{row.first_name ? `@${row.username}` : `Blocked ${new Date(row.created_at).toLocaleDateString("en-US", { month: "short", day: "numeric", timeZone: "America/New_York" })}`}</p></div>
          <button type="button" onClick={() => unblock(row.username)} disabled={pending === row.username} className="btn btn-secondary h-9 shrink-0 px-4 text-sm">{pending === row.username ? "Unblocking…" : "Unblock"}</button>
        </li>)}</ul>)}
    {error && <p role="alert" className="mt-3 text-sm text-[var(--danger)]">{error}</p>}
  </main>;
}
