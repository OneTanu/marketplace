"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { getPublicUser, setFollowing } from "@/lib/platform";
import { startConversation } from "@/lib/messaging";
import type { components } from "@/lib/api/schema";

import { InstagramLink } from "./instagram-link";
import { StudentIdCard } from "./student-id-card";

type PublicUser = components["schemas"]["PublicUser"];

export function PublicProfile({ username }: { username: string }) {
  const router = useRouter();
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

  async function messageUser() {
    if (!user || user.is_self) return;
    setPending(true);
    setError("");
    try {
      const conversation = await startConversation(user.username);
      router.push(`/inbox/${conversation.id}`);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "We couldn’t start this conversation.");
      setPending(false);
    }
  }

  if (user === undefined) {
    return <main className="mx-auto min-h-[70vh] max-w-6xl animate-pulse px-4 py-10 sm:px-6"><div className="h-72 rounded-3xl bg-foreground/5" /></main>;
  }
  if (user === null) {
    return <main className="mx-auto min-h-[70vh] max-w-2xl px-4 py-20 text-center"><h1 className="text-3xl font-black">Profile unavailable</h1><p className="mt-3 text-muted">This account does not exist, is not verified, or requires you to log in.</p><Link href="/account/login" className="mt-6 inline-flex btn btn-primary">Log in</Link></main>;
  }

  return <main className="mx-auto min-h-[70vh] max-w-6xl px-4 py-10 pb-28 sm:px-6 desktop:pb-12">
    <section className="grid items-start gap-6 lg:grid-cols-[minmax(0,26rem)_1fr] lg:gap-8">
      <StudentIdCard firstName={user.first_name} lastInitial={user.last_initial} username={user.username} schoolName={user.school?.name} schoolColors={user.school?.colors} dateJoined={user.date_joined} soldCount={user.sold_count} />
      <div>
        <p className="max-w-2xl leading-7 text-foreground/80">{user.profile_description || "This student has not added a profile description yet."}</p>
        <div className="mt-4 flex flex-wrap items-center gap-x-7 gap-y-3 text-sm">
          <div className="flex gap-6"><div><strong className="text-base">{user.follower_count}</strong> <span className="text-muted">Followers</span></div><div><strong className="text-base">{user.following_count}</strong> <span className="text-muted">Following</span></div></div>
          {user.instagram_handle && <InstagramLink handle={user.instagram_handle} />}
        </div>
        <div className="mt-5 flex gap-2">
          {user.is_self ? <Link href="/profile" className="btn btn-secondary">Edit your profile</Link> : <><button onClick={toggleFollow} disabled={pending} className={`btn ${user.is_following ? "btn-secondary" : "btn-primary"}`}>{pending ? "Saving…" : user.is_following ? "Following" : "Follow"}</button><button onClick={messageUser} disabled={pending} className="btn btn-secondary">Message</button></>}
        </div>
        {error && <p className="mt-3 text-sm text-[var(--danger)]">{error}</p>}
      </div>
    </section>
    <section className="mt-8"><h2 className="text-xl font-black">Items for sale</h2><div className="mt-4 grid min-h-56 place-items-center rounded-3xl border border-dashed border-line bg-white/45 p-8 text-center"><div><p className="font-bold">No active listings yet</p><p className="mt-2 text-sm text-muted">This seller’s available items will appear here after the Listings API is connected.</p></div></div></section>
  </main>;
}
