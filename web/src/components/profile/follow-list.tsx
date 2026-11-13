"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import type { components } from "@/lib/api/schema";
import { getFollowList, setFollowing, type FollowDirection } from "@/lib/platform";

import { Avatar } from "@/components/ui/avatar";
import { Skeleton } from "@/components/ui/card";
import { BackLink } from "@/components/ui/focused-header";

type PublicUser = components["schemas"]["PublicUser"];
type ListState =
  | { state: "loading" }
  | { state: "signed-out" | "missing" }
  | { state: "ready"; users: PublicUser[]; next: string | null; loadingMore: boolean; moreFailed: boolean };

const TABS: { direction: FollowDirection; label: string }[] = [
  { direction: "followers", label: "Followers" },
  { direction: "following", label: "Following" },
];

/** A student's followers or the students they follow, newest first, with Follow buttons. Follow is
 * a secondary button: a list of people has no single next step (spec principle 1). */
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

  return <div className="mx-auto min-h-[70vh] max-w-2xl px-4 pb-12 pt-4 sm:px-6">
    <div className="flex items-center gap-1">
      <BackLink href={`/users/${encodeURIComponent(username)}`} label={`Back to @${username}`} />
      <h1 className="type-wide min-w-0 truncate text-title font-extrabold">@{username}</h1>
    </div>
    <nav className="mt-2 flex gap-1 border-b border-line" aria-label="Follow lists">
      {TABS.map((tab) => <Link key={tab.direction} href={`/users/${username}/${tab.direction}`} replace aria-current={tab.direction === direction ? "page" : undefined} className="relative flex min-h-11 min-w-max items-center px-4 text-label font-semibold text-muted transition-colors hover:text-ink aria-[current=page]:text-ink after:absolute after:inset-x-3 after:bottom-0 after:h-0.5 after:bg-ink after:opacity-0 aria-[current=page]:after:opacity-100">{tab.label}</Link>)}
    </nav>
    <section className="mt-2">
      {list.state === "loading" && <div role="status" className="divide-y divide-line"><span className="sr-only">Loading…</span>{Array.from({ length: 4 }).map((_, index) => <div key={index} className="flex items-center gap-3 py-3"><Skeleton className="size-11 rounded-full" /><Skeleton className="h-4 w-40 rounded-full" /></div>)}</div>}
      {list.state === "signed-out" && <p className="mt-4 text-label text-muted"><Link href="/account/login" className="font-semibold text-ink underline decoration-ink/30 underline-offset-4">Log in</Link> to see who students follow.</p>}
      {list.state === "missing" && <p className="mt-4 text-label text-muted">This list isn’t available. The account may not exist, or Tanu couldn’t load it. Refresh to try again.</p>}
      {list.state === "ready" && (list.users.length
        ? <>
          <ul className="divide-y divide-line" aria-label={direction === "followers" ? "Followers" : "Following"}>{list.users.map((user) => <li key={user.id}><FollowRow user={user} onChange={replaceUser} /></li>)}</ul>
          {list.next && <div className="mt-5 flex justify-center"><button type="button" onClick={loadMore} disabled={list.loadingMore} className="btn btn-secondary">{list.loadingMore ? "Loading…" : "Show more"}</button></div>}
          {list.moreFailed && <p role="alert" className="mt-3 text-center text-label text-danger">Couldn’t load more. Try again.</p>}
        </>
        : <p className="mt-10 text-center text-label text-muted">{direction === "followers" ? "No followers yet." : "Not following anyone yet."}</p>)}
    </section>
  </div>;
}

function FollowRow({ user, onChange }: { user: PublicUser; onChange: (user: PublicUser) => void }) {
  const [pending, setPending] = useState(false);
  const [error, setError] = useState("");

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

  const name = user.first_name ? `${user.first_name}${user.last_initial ? ` ${user.last_initial}.` : ""}` : `@${user.username}`;
  return <div className="flex min-h-16 items-center gap-3 py-2">
    <Link href={`/users/${user.username}`} className="flex min-w-0 flex-1 items-center gap-3">
      <Avatar user={user} />
      <span className="min-w-0">
        <span className="block truncate text-label font-semibold text-ink">{name}</span>
        <span className="block truncate text-fine text-muted">{[user.first_name && `@${user.username}`, user.school?.short_name].filter(Boolean).join(" · ")}</span>
      </span>
    </Link>
    {!user.is_self && <div className="shrink-0 text-right">
      <button type="button" onClick={toggleFollow} disabled={pending} aria-pressed={user.is_following} aria-label={`Follow @${user.username}`} className="btn btn-secondary btn-sm">{pending ? "Saving…" : user.is_following ? "Following" : "Follow"}</button>
      {error && <p role="alert" className="mt-1 max-w-40 text-fine text-danger">{error}</p>}
    </div>}
  </div>;
}
