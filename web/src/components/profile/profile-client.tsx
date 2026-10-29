"use client";

import Link from "next/link";
import { FormEvent, useEffect, useState } from "react";

import { ListingCard } from "@/components/discovery/listing-card";
import { RestrictionNotice } from "@/components/trust/restriction-notice";
import { api } from "@/lib/api/client";
import type { ListingCard as Card } from "@/lib/discovery";
import {
  getCurrentUser,
  updateCurrentUser,
  type ProfileUpdateErrors,
} from "@/lib/platform";
import type { components } from "@/lib/api/schema";

import { BookmarksTab } from "./bookmarks-tab";
import { InstagramLink } from "./instagram-link";
import { StudentIdCard } from "./student-id-card";

type CurrentUser = components["schemas"]["CurrentUser"];
type Listing = components["schemas"]["Listing"];

type ProfileTab = "selling" | "sold" | "bookmarks";
type ListingTab = Exclude<ProfileTab, "bookmarks">;

// Which of the seller's own listings each tab shows. Removed ones stay on My listings only.
const TAB_STATUSES: Record<ListingTab, Listing["status"][]> = {
  selling: ["available", "pending"],
  sold: ["sold"],
};

/** The feed card's shape, from a full listing: the cover is the photo with the lowest position. */
function toCard(listing: Listing, details: NonNullable<Listing["item_details"]>): Card {
  const cover = listing.photos.reduce<Listing["photos"][number] | undefined>(
    (best, photo) => (!best || photo.position < best.position ? photo : best),
    undefined,
  );
  return {
    id: listing.id,
    status: listing.status,
    title: listing.title,
    price_cents: listing.price_cents,
    currency: listing.currency,
    cover_url: cover ? (cover.thumbnail_url ?? cover.image_url) : null,
    condition: details.condition,
    size: details.size,
    brand: details.brand,
    school: listing.school,
    seller: listing.seller,
    is_bookmarked: listing.is_bookmarked,
    created_at: listing.created_at,
  };
}

function EmptyCollection({ tab }: { tab: ListingTab }) {
  const content = {
    selling: {
      title: "Nothing for sale yet",
      note: "When you publish a listing, it will appear here for other students to find.",
      action: <Link href="/sell" className="btn btn-primary">Create a listing</Link>,
    },
    sold: {
      title: "No sold items yet",
      note: "Items you've sold will appear here.",
      action: null,
    },
  }[tab];

  return (
    <div className="grid min-h-64 place-items-center rounded-3xl border border-dashed border-line bg-white/45 px-6 text-center">
      <div className="max-w-sm py-10">
        <div className="mx-auto mb-4 grid size-12 place-items-center rounded-2xl bg-[var(--ink-soft)] text-xl text-ink" aria-hidden="true">◇</div>
        <h2 className="text-lg font-bold">{content.title}</h2>
        <p className="mt-2 text-sm leading-6 text-muted">{content.note}</p>
        {content.action && <div className="mt-5">{content.action}</div>}
      </div>
    </div>
  );
}

function TabContent({ tab, listings }: { tab: ListingTab; listings: Card[] | null | undefined }) {
  const statuses = TAB_STATUSES[tab];
  if (listings === undefined) {
    return <div aria-busy="true" aria-label="Loading listings" className="grid grid-cols-2 gap-x-3 gap-y-6 sm:grid-cols-3 sm:gap-x-4 lg:grid-cols-4">{Array.from({ length: 4 }).map((_, index) => <div key={index} className="aspect-[4/5] animate-pulse rounded-md bg-surface" />)}</div>;
  }
  if (listings === null) {
    return <p className="text-sm text-muted">Couldn’t load your listings. Refresh to try again.</p>;
  }
  const shown = listings.filter((listing) => statuses.includes(listing.status));
  if (!shown.length) return <EmptyCollection tab={tab} />;
  return (
    <ul aria-label="Listings" className="grid grid-cols-2 gap-x-3 gap-y-6 sm:grid-cols-3 sm:gap-x-4 sm:gap-y-8 lg:grid-cols-4">
      {shown.map((listing) => <li key={listing.id}><ListingCard listing={listing} /></li>)}
    </ul>
  );
}

export function ProfileClient() {
  const [user, setUser] = useState<CurrentUser | null>();
  const [loadError, setLoadError] = useState(false);
  const [editing, setEditing] = useState(false);
  const [pending, setPending] = useState(false);
  const [saved, setSaved] = useState(false);
  const [errors, setErrors] = useState<ProfileUpdateErrors>({});
  const [tab, setTab] = useState<ProfileTab>("selling");
  // undefined while loading, null if the request failed.
  const [listings, setListings] = useState<Card[] | null>();

  const signedIn = Boolean(user);
  useEffect(() => {
    if (!signedIn) return;
    let active = true;
    api
      .GET("/api/listings/mine/")
      .then(({ data }) => {
        if (!active) return;
        // Every V1 listing is an item, so item_details is always set.
        setListings(data ? data.flatMap((l) => (l.item_details ? [toCard(l, l.item_details)] : [])) : null);
      })
      .catch(() => active && setListings(null));
    return () => { active = false; };
  }, [signedIn]);

  useEffect(() => {
    let active = true;
    getCurrentUser()
      .then((currentUser) => active && setUser(currentUser))
      .catch(() => active && setLoadError(true));
    return () => { active = false; };
  }, []);

  async function retryProfile() {
    setLoadError(false);
    setUser(undefined);
    try {
      setUser(await getCurrentUser());
    } catch {
      setLoadError(true);
    }
  }

  async function saveProfile(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setPending(true);
    setSaved(false);
    setErrors({});
    const data = new FormData(event.currentTarget);
    const result = await updateCurrentUser({
      profile_description: String(data.get("profile_description") ?? ""),
      instagram_handle: String(data.get("instagram_handle") ?? ""),
    });
    if (result.user) {
      setUser(result.user);
      setEditing(false);
      setSaved(true);
    } else {
      setErrors(result.errors);
    }
    setPending(false);
  }

  if (user === undefined) {
    if (loadError) {
      return <main className="mx-auto grid min-h-[70vh] max-w-xl place-items-center px-4 py-12 text-center"><div className="rounded-2xl bg-surface p-8"><h1 className="type-wide text-2xl font-black">We couldn’t load your profile</h1><p className="mt-3 leading-7 text-muted">Your session may still be active. Check the connection and try loading your account again.</p><button type="button" onClick={retryProfile} className="btn btn-primary mt-6">Try again</button></div></main>;
    }
    return <main className="mx-auto min-h-[70vh] max-w-6xl animate-pulse px-4 py-10 sm:px-6"><div className="h-72 rounded-3xl border border-line bg-white/60" /></main>;
  }

  if (user === null) {
    return (
      <main className="mx-auto grid min-h-[70vh] max-w-xl place-items-center px-4 py-12 text-center">
        <div className="rounded-3xl border border-line bg-surface p-8 shadow-sm">
          <div className="mx-auto grid size-16 place-items-center rounded-2xl bg-[var(--ink-soft)] text-2xl font-black text-ink">T</div>
          <h1 className="mt-5 text-2xl font-bold tracking-tight">Sign in to view your profile</h1>
          <p className="mt-3 leading-7 text-muted">Your profile, school identity, and marketplace activity are connected to your verified student account.</p>
          <Link href="/account/login" className="mt-6 inline-flex btn btn-primary">Log in</Link>
        </div>
      </main>
    );
  }

  return (
    <main className="mx-auto w-full max-w-6xl px-4 py-8 pb-28 sm:px-6 sm:py-12 desktop:pb-12">
      <RestrictionNotice />
      <section className="animate-in grid items-start gap-6 lg:grid-cols-[minmax(0,26rem)_1fr] lg:gap-8">
        <StudentIdCard firstName={user.first_name} lastInitial={user.last_name[0]?.toUpperCase() ?? ""} username={user.username} schoolName={user.school?.name} schoolColors={user.school?.colors} dateJoined={user.date_joined} soldCount={user.sold_count} />
        <div>
          {editing ? (
            <form onSubmit={saveProfile} className="max-w-2xl space-y-5 rounded-2xl border border-line bg-white/65 p-5">
              <label className="block">
                <span className="flex justify-between text-sm font-bold">Description <span className="font-normal text-muted">Optional · 300 characters</span></span>
                <textarea name="profile_description" defaultValue={user.profile_description} maxLength={300} rows={4} className="mt-2 w-full resize-none rounded-xl border border-line bg-white px-4 py-3 text-[15px] outline-none transition focus:border-brand focus:ring-4 focus:ring-[var(--brand-soft)]" placeholder="Tell other students a little about you and what you sell." />
                {errors.profile_description && <span className="mt-1.5 block text-sm text-[var(--danger)]">{errors.profile_description}</span>}
              </label>
              <label className="block">
                <span className="flex justify-between text-sm font-bold">Instagram <span className="font-normal text-muted">Optional and public</span></span>
                <div className="mt-2 flex h-12 items-center rounded-xl border border-line bg-white px-4 focus-within:border-brand focus-within:ring-4 focus-within:ring-[var(--brand-soft)]">
                  <span className="text-muted">@</span>
                  <input name="instagram_handle" defaultValue={user.instagram_handle} maxLength={100} className="h-full min-w-0 flex-1 bg-transparent pl-1 outline-none" placeholder="yourhandle" />
                </div>
                <p className="mt-1.5 text-xs leading-5 text-muted">Each Instagram handle can be connected to only one Tanu account. Instagram ownership is not yet verified by Tanu.</p>
                {errors.instagram_handle && <span className="mt-1.5 block text-sm text-[var(--danger)]">{errors.instagram_handle}</span>}
              </label>
              {errors.detail && <p role="alert" className="text-sm text-[var(--danger)]">{errors.detail}</p>}
              <div className="flex justify-end"><button disabled={pending} className="btn btn-primary">{pending ? "Saving…" : "Save profile"}</button></div>
            </form>
          ) : (
            <div>
              <p className="max-w-2xl leading-7 text-foreground/80">{user.profile_description || "Add a short description so other students know a little about you and what you usually sell."}</p>
              <div className="mt-4 flex flex-wrap items-center gap-x-7 gap-y-3 text-sm">
                <div className="flex gap-6"><div><strong className="text-base">{user.follower_count}</strong> <span className="text-muted">Followers</span></div><div><strong className="text-base">{user.following_count}</strong> <span className="text-muted">Following</span></div></div>
                {user.instagram_handle && <InstagramLink handle={user.instagram_handle} />}
              </div>
              {saved && <p className="mt-3 text-sm font-semibold text-ink">Profile saved.</p>}
            </div>
          )}
          <div className="mt-5 flex flex-wrap gap-2">
            <Link href="/listings/mine" className="btn btn-secondary">My listings</Link>
            <Link href="/profile/searches" className="btn btn-secondary">Saved searches</Link>
            <Link href="/profile/meetup" className="btn btn-secondary">Meetup preferences</Link>
            <Link href="/profile/standing" className="btn btn-secondary">Account status</Link>
            {user.is_moderator && <Link href="/moderation" className="btn btn-secondary">Moderation</Link>}
            <button onClick={() => { setEditing((value) => !value); setSaved(false); setErrors({}); }} className="btn btn-secondary">{editing ? "Cancel" : "Edit profile"}</button>
          </div>
        </div>
      </section>

      <section className="mt-8 animate-in [animation-delay:100ms]">
        <div className="mb-5 flex gap-1 overflow-x-auto border-b border-line" role="tablist" aria-label="Profile activity">
          {([["selling", "Selling"], ["sold", "Sold"], ["bookmarks", "Bookmarks"]] as const).map(([value, label]) => (
            <button key={value} role="tab" aria-selected={tab === value} onClick={() => setTab(value)} className="relative min-w-max px-5 py-3 text-sm font-bold text-muted transition hover:text-foreground aria-[selected=true]:text-foreground after:absolute after:inset-x-3 after:bottom-0 after:h-0.5 after:rounded-full after:bg-brand after:opacity-0 aria-[selected=true]:after:opacity-100">{label}</button>
          ))}
        </div>
        {tab === "bookmarks" ? <BookmarksTab /> : <TabContent tab={tab} listings={listings} />}
      </section>
    </main>
  );
}
