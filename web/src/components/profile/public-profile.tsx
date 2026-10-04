"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { getPublicUser, setFollowing, type PublicUser } from "@/lib/platform";

export function PublicProfile({ username }: { username: string }) {
  const [user, setUser] = useState<PublicUser | null>();
  const [pending, setPending] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    getPublicUser(username).then(setUser).catch(() => setUser(null));
  }, [username]);

  async function toggleFollow() {
    if (!user || user.is_self) return;
    setPending(true);
    setError("");
    try {
      const updated = await setFollowing(user.username, !user.is_following);
      setUser(
        updated ?? {
          ...user,
          is_following: false,
          follower_count: Math.max(0, user.follower_count - 1),
        },
      );
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "We couldn’t update this follow.");
    } finally {
      setPending(false);
    }
  }

  if (user === undefined) {
    return <main className="mx-auto min-h-[70vh] max-w-6xl animate-pulse px-4 py-10 sm:px-6"><div className="h-72 rounded-3xl bg-foreground/5" /></main>;
  }
  if (user === null) {
    return <main className="mx-auto min-h-[70vh] max-w-2xl px-4 py-20 text-center"><h1 className="text-3xl font-black">Profile unavailable</h1><p className="mt-3 text-muted">This account does not exist, is not verified, or requires you to log in.</p><Link href="/account/login" className="mt-6 inline-flex rounded-full bg-foreground px-6 py-3 text-sm font-bold text-white">Log in</Link></main>;
  }

  const initial = (user.first_name[0] || user.username[0]).toUpperCase();
  return <main className="mx-auto min-h-[70vh] max-w-6xl px-4 py-10 pb-28 sm:px-6 desktop:pb-12">
    <section className="overflow-hidden rounded-[2rem] border border-line bg-surface shadow-[0_18px_60px_rgb(20_35_29/8%)]">
      <div className="h-28 bg-[linear-gradient(120deg,#174b37,#2d7154_58%,#ed5b2b)] sm:h-36" />
      <div className="px-5 pb-8 sm:px-8">
        <div className="-mt-12 flex flex-col gap-5 sm:-mt-14 sm:flex-row sm:items-end sm:justify-between">
          <div className="flex flex-col items-start gap-4 sm:flex-row sm:items-end">
            <div className="grid size-24 place-items-center rounded-[1.75rem] border-4 border-surface bg-[var(--brand-soft)] text-4xl font-black text-brand sm:size-28">{initial}</div>
            <div className="pb-1"><div className="flex items-center gap-2"><h1 className="text-3xl font-black tracking-[-.04em]">{user.first_name || `@${user.username}`}</h1><span className="rounded-full bg-[var(--forest-soft)] px-2.5 py-1 text-xs font-bold text-forest">Verified</span></div><p className="mt-1 text-muted">@{user.username}</p></div>
          </div>
          <div className="flex gap-2">
            {user.is_self ? <Link href="/profile" className="rounded-full border border-line bg-white px-5 py-2.5 text-sm font-bold">Edit your profile</Link> : <><button onClick={toggleFollow} disabled={pending} className={`rounded-full px-5 py-2.5 text-sm font-bold transition disabled:opacity-60 ${user.is_following ? "border border-line bg-white" : "bg-foreground text-white hover:bg-forest"}`}>{pending ? "Saving…" : user.is_following ? "Following" : "Follow"}</button><button disabled title="Messaging is the next feature" className="rounded-full border border-line bg-white px-5 py-2.5 text-sm font-bold opacity-60">Message</button></>}
          </div>
        </div>
        <div className="mt-6 grid gap-5 lg:grid-cols-[1fr_auto] lg:items-end">
          <div><p className="max-w-2xl leading-7 text-foreground/80">{user.profile_description || "This student has not added a profile description yet."}</p><div className="mt-4 flex flex-wrap gap-4 text-sm">{user.school && <span className="font-semibold">{user.school.name}</span>}{user.instagram_handle && <a href={`https://www.instagram.com/${user.instagram_handle}/`} target="_blank" rel="noreferrer" className="font-semibold text-forest underline underline-offset-4">@{user.instagram_handle} ↗</a>}</div>{error && <p className="mt-3 text-sm text-[var(--danger)]">{error}</p>}</div>
          <div className="flex gap-7 text-sm"><div><strong className="block text-xl">{user.follower_count}</strong><span className="text-muted">Followers</span></div><div><strong className="block text-xl">{user.following_count}</strong><span className="text-muted">Following</span></div></div>
        </div>
      </div>
    </section>
    <section className="mt-8"><h2 className="text-xl font-black">Items for sale</h2><div className="mt-4 grid min-h-56 place-items-center rounded-3xl border border-dashed border-line bg-white/45 p-8 text-center"><div><p className="font-bold">No active listings yet</p><p className="mt-2 text-sm text-muted">This seller’s available items will appear here after the Listings API is connected.</p></div></div></section>
  </main>;
}
