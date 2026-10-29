"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { ListingCard } from "@/components/discovery/listing-card";
import { BlockButton, ReportButton } from "@/components/trust/report";
import type { ListingCard as Card } from "@/lib/discovery";
import { getPublicUser, getPublicUserListings, setFollowing } from "@/lib/platform";
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
  const [listingTab, setListingTab] = useState<"selling" | "sold">("selling");
  const [listings, setListings] = useState<Card[] | null>();

  useEffect(() => {
    getPublicUser(username).then(setUser).catch(() => setUser(null));
    getPublicUserListings(username).then(setListings).catch(() => setListings(null));
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
        <div className="mt-5 flex flex-wrap items-start gap-2">
          {user.is_self ? <Link href="/profile" className="btn btn-secondary">Edit your profile</Link> : <><button onClick={toggleFollow} disabled={pending} className={`btn ${user.is_following ? "btn-secondary" : "btn-primary"}`}>{pending ? "Saving…" : user.is_following ? "Following" : "Follow"}</button><button onClick={messageUser} disabled={pending} className="btn btn-secondary">Message</button></>}
        </div>
        {!user.is_self && (
          <div className="mt-3 flex flex-wrap items-center gap-x-4 gap-y-2">
            <ReportButton targetType="user" targetId={user.id} subject={`@${user.username}`} username={user.username} label="Report profile" />
            <BlockButton username={user.username} className="text-sm font-semibold text-muted hover:text-ink hover:underline" />
          </div>
        )}
        {error && <p className="mt-3 text-sm text-[var(--danger)]">{error}</p>}
      </div>
    </section>
    <section className="mt-8">
      <div className="mb-5 flex gap-1 overflow-x-auto border-b border-line" role="tablist" aria-label="Seller listings">
        <button type="button" role="tab" aria-selected={listingTab === "selling"} onClick={() => setListingTab("selling")} className="relative min-w-max px-5 py-3 text-sm font-bold text-muted transition hover:text-foreground aria-[selected=true]:text-foreground after:absolute after:inset-x-3 after:bottom-0 after:h-0.5 after:rounded-full after:bg-brand after:opacity-0 aria-[selected=true]:after:opacity-100">Selling</button>
        <button type="button" role="tab" aria-selected={listingTab === "sold"} onClick={() => setListingTab("sold")} className="relative min-w-max px-5 py-3 text-sm font-bold text-muted transition hover:text-foreground aria-[selected=true]:text-foreground after:absolute after:inset-x-3 after:bottom-0 after:h-0.5 after:rounded-full after:bg-brand after:opacity-0 aria-[selected=true]:after:opacity-100">Sold</button>
      </div>
      <PublicListings tab={listingTab} listings={listings} isSelf={user.is_self} />
    </section>
  </main>;
}

function PublicListings({ tab, listings, isSelf }: { tab: "selling" | "sold"; listings: Card[] | null | undefined; isSelf: boolean }) {
  if (listings === undefined) {
    return <div aria-busy="true" aria-label="Loading listings" className="grid grid-cols-2 gap-x-3 gap-y-6 sm:grid-cols-3 sm:gap-x-4 lg:grid-cols-4">{Array.from({ length: 4 }).map((_, index) => <div key={index} className="aspect-[4/5] animate-pulse rounded-md bg-surface" />)}</div>;
  }
  if (listings === null) {
    return <p className="rounded-xl bg-surface px-5 py-8 text-center text-sm text-muted">Couldn’t load this seller’s listings. Refresh to try again.</p>;
  }
  const shown = listings.filter((listing) => tab === "sold" ? listing.status === "sold" : listing.status === "available" || listing.status === "pending");
  if (!shown.length) {
    return <div className="grid min-h-56 place-items-center rounded-3xl border border-dashed border-line bg-white/45 p-8 text-center"><div><p className="font-bold">{tab === "sold" ? "No sold items yet" : "No active listings"}</p><p className="mt-2 text-sm text-muted">{tab === "sold" ? "Completed sales will appear here." : "This student is not currently selling anything."}</p></div></div>;
  }
  return <ul aria-label={tab === "sold" ? "Sold listings" : "Listings for sale"} className="grid grid-cols-2 gap-x-3 gap-y-6 sm:grid-cols-3 sm:gap-x-4 sm:gap-y-8 lg:grid-cols-4">{shown.map((listing) => <li key={listing.id}><ListingCard listing={listing} showBookmark={!isSelf} /></li>)}</ul>;
}
