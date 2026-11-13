"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import type { components } from "@/lib/api/schema";
import { getFollowList, setFollowing, type FollowDirection } from "@/lib/platform";

type PublicUser = components["schemas"]["PublicUser"];
type ListState =
  | { state: "loading" }
  | { state: "signed-out" | "missing" }
  | { state: "ready"; users: PublicUser[]; next: string | null; loadingMore: boolean; moreFailed: boolean };

const TABS: { direction: FollowDirection; label: string }[] = [
  { direction: "followers", label: "Followers" },
  { direction: "following", label: "Following" },
];

/** A student's followers or the students they follow, newest first, with Follow buttons. */
export function FollowList({ username, direction }: { username: string; direction: FollowDirection }) {
  const [list, setList] = useState<ListState>({ state: "loading" });

  useEffect(() => {
    let current = true;
    getFollowList(username, direction)
      .then((page) => {
        if (!current) return;
        setList(page === null ? { state: "signed-out" } : { state: "ready", users: page.results, next: page.next_cursor, loadingMore: false, moreFailed: false });
      })
      .catch(() => current && setList({ state: "missing" }));
    return () => { current = false; };
  }, [username, direction]);

  async function loadMore() {
    if (list.state !== "ready" || !list.next || list.loadingMore) return;
    setList({ ...list, loadingMore: true, moreFailed: false });
    try {
      const page = await getFollowList(username, direction, list.next);
      setList((latest) => {
        if (latest.state !== "ready" || !page) return latest;
        const seen = new Set(latest.users.map((user) => user.id));
        return { ...latest, users: [...latest.users, ...page.results.filter((user) => !seen.has(user.id))], next: page.next_cursor, loadingMore: false };
      });
    } catch {
      setList((latest) => latest.state === "ready" ? { ...latest, loadingMore: false, moreFailed: true } : latest);
    }
  }

  function replaceUser(updated: PublicUser) {
    setList((latest) => latest.state === "ready" ? { ...latest, users: latest.users.map((user) => user.id === updated.id ? updated : user) } : latest);
  }

  return <main className="mx-auto min-h-[70vh] max-w-2xl px-4 py-8 pb-28 sm:px-6 desktop:pb-12">
    <Link href={`/users/${username}`} className="text-sm font-semibold text-muted hover:text-ink hover:underline">← @{username}</Link>
    <nav className="mt-4 flex gap-1 border-b border-line" aria-label="Follow lists">
      {TABS.map((tab) => <Link key={tab.direction} href={`/users/${username}/${tab.direction}`} replace aria-current={tab.direction === direction ? "page" : undefined} className="relative min-w-max px-5 py-3 text-sm font-bold text-muted transition hover:text-foreground aria-[current=page]:text-foreground after:absolute after:inset-x-3 after:bottom-0 after:h-0.5 after:rounded-full after:bg-brand after:opacity-0 aria-[current=page]:after:opacity-100">{tab.label}</Link>)}
    </nav>
    <section className="mt-5">
      {list.state === "loading" && <div aria-busy="true" aria-label="Loading" className="grid gap-3">{Array.from({ length: 4 }).map((_, index) => <div key={index} className="h-[4.5rem] animate-pulse rounded-xl bg-surface" />)}</div>}
      {list.state === "signed-out" && <p className="rounded-xl bg-surface p-5 text-sm"><Link href="/account/login" className="font-bold text-brand underline underline-offset-2">Log in</Link> to see who students follow.</p>}
      {list.state === "missing" && <p className="rounded-xl bg-surface p-5 text-sm text-muted">This list isn’t available. The account may not exist, or Tanu couldn’t load it. Refresh to try again.</p>}
      {list.state === "ready" && (list.users.length
        ? <>
          <ul className="grid gap-3" aria-label={direction === "followers" ? "Followers" : "Following"}>{list.users.map((user) => <li key={user.id}><FollowRow user={user} onChange={replaceUser} /></li>)}</ul>
          {list.next && <div className="mt-5 flex justify-center"><button type="button" onClick={loadMore} disabled={list.loadingMore} className="btn btn-secondary">{list.loadingMore ? "Loading…" : "Show more"}</button></div>}
          {list.moreFailed && <p className="mt-3 text-center text-sm text-[var(--danger)]">Couldn’t load more. Try again.</p>}
        </>
        : <div className="grid min-h-48 place-items-center rounded-3xl border border-dashed border-line p-8 text-center"><p className="text-sm text-muted">{direction === "followers" ? "No followers yet." : "Not following anyone yet."}</p></div>)}
    </section>
  </main>;
}

function FollowRow({ user, onChange }: { user: PublicUser; onChange: (user: PublicUser) => void }) {
  const [pending, setPending] = useState(false);
  const [error, setError] = useState("");
  const initial = (user.first_name[0] || user.username[0]).toUpperCase();

  async function toggleFollow() {
    setPending(true);
    setError("");
    try {
      const updated = await setFollowing(user.username, !user.is_following);
      onChange(updated ?? { ...user, is_following: false, follower_count: Math.max(0, user.follower_count - 1) });
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "We couldn’t update this follow.");
    } finally {
      setPending(false);
    }
  }

  return <div className="flex items-center gap-3.5 rounded-xl border border-line p-3.5">
    <Link href={`/users/${user.username}`} className="flex min-w-0 flex-1 items-center gap-3.5">
      <div className="type-wide grid size-11 shrink-0 place-items-center rounded-full bg-[var(--brand-soft)] text-base font-extrabold text-brand" aria-hidden="true">{initial}</div>
      <div className="min-w-0"><p className="truncate font-bold">{user.first_name ? `${user.first_name}${user.last_initial ? ` ${user.last_initial}.` : ""}` : `@${user.username}`}</p><p className="truncate text-sm text-muted">{[user.first_name && `@${user.username}`, user.school?.short_name].filter(Boolean).join(", ")}</p></div>
    </Link>
    {!user.is_self && <div className="shrink-0 text-right">
      <button type="button" onClick={toggleFollow} disabled={pending} aria-label={`${user.is_following ? "Unfollow" : "Follow"} @${user.username}`} className={`btn ${user.is_following ? "btn-secondary" : "btn-primary"} h-9 px-4 text-sm`}>{pending ? "Saving…" : user.is_following ? "Following" : "Follow"}</button>
      {error && <p className="mt-1 max-w-40 text-xs text-[var(--danger)]">{error}</p>}
    </div>}
  </div>;
}
