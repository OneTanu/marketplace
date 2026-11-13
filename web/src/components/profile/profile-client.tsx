"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useEffect, useState } from "react";

import { useLogOut } from "@/components/auth/auth-actions";
import { RestrictionNotice } from "@/components/trust/restriction-notice";
import { Skeleton } from "@/components/ui/card";
import { HeartIcon, LogOutIcon, MapPinIcon, ModerationIcon, SearchIcon, ShieldCheckIcon, StoreIcon } from "@/components/ui/icons";
import { ListButton, ListGroup, ListRow } from "@/components/ui/list-row";
import { getCurrentUser } from "@/lib/platform";
import type { components } from "@/lib/api/schema";

import { StudentIdCard } from "./student-id-card";

type CurrentUser = components["schemas"]["CurrentUser"];

/** The account hub: the ID card (tap it, or View profile, for the public profile), Edit profile,
 * then one row per account page, and Log out. The same single column on phones and desktop. */
export function ProfileClient() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const logOut = useLogOut();
  // undefined until clicked; then pending, or the error to show.
  const [logOutState, setLogOutState] = useState<"pending" | "failed">();
  const [user, setUser] = useState<CurrentUser | null>();
  const [loadError, setLoadError] = useState(false);

  // Saved used to be a tab here (/profile?tab=bookmarks); old links land on its own page.
  const oldTab = searchParams.get("tab");
  useEffect(() => {
    if (oldTab === "bookmarks") router.replace("/profile/saved");
  }, [oldTab, router]);

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

  async function logOutNow() {
    setLogOutState("pending");
    const done = await logOut().catch(() => false);
    if (!done) setLogOutState("failed");
  }

  if (user === undefined) {
    if (loadError) {
      return <main className="mx-auto grid min-h-[70vh] max-w-xl place-items-center px-4 py-12 text-center"><div className="rounded-xl bg-surface p-8"><h1 className="type-wide text-display font-extrabold">We couldn’t load your profile</h1><p className="mt-3 leading-7 text-muted">Your session may still be active. Check the connection and try loading your account again.</p><button type="button" onClick={retryProfile} className="btn btn-primary mt-6">Try again</button></div></main>;
    }
    return <div data-page-tint role="status" className="mx-auto min-h-[70vh] w-full max-w-md px-4 py-6 sm:py-10"><span className="sr-only">Loading your profile…</span><Skeleton className="aspect-[85.6/54] bg-background" /><Skeleton className="mt-3 h-11 bg-background" /><Skeleton className="mt-4 h-72 bg-background" /></div>;
  }

  if (user === null) {
    return (
      <main className="mx-auto grid min-h-[70vh] max-w-xl place-items-center px-4 py-12 text-center">
        <div className="rounded-xl border border-line bg-surface p-8 shadow-float">
          <div className="mx-auto grid size-16 place-items-center rounded-xl bg-ink-soft text-display font-extrabold text-ink">T</div>
          <h1 className="type-wide mt-5 text-display font-extrabold">Sign in to view your profile</h1>
          <p className="mt-3 leading-7 text-muted">Your profile, school identity, and marketplace activity are connected to your verified student account.</p>
          <Link href="/account/login" className="mt-6 inline-flex btn btn-primary">Log in</Link>
        </div>
      </main>
    );
  }

  const publicHref = `/users/${encodeURIComponent(user.username)}`;
  const rows = [
    { href: "/listings/mine", label: "My listings", icon: StoreIcon },
    { href: "/profile/saved", label: "Saved", icon: HeartIcon },
    { href: "/profile/searches", label: "Saved searches", icon: SearchIcon },
    { href: "/profile/meetup", label: "Meetup preferences", icon: MapPinIcon },
    { href: "/profile/standing", label: "Account status", icon: ShieldCheckIcon },
    ...(user.is_moderator ? [{ href: "/moderation", label: "Moderation", icon: ModerationIcon }] : []),
  ];

  return (
    // An account page: the grey page with white cards (spec 1c, C3).
    <div data-page-tint className="mx-auto w-full max-w-md px-4 py-6 sm:py-10">
      <RestrictionNotice />
      {/* The whole card opens the public profile for a tap or click. It isn't a link itself, so
          screen readers and keyboards get one clear way there: the View profile button. */}
      <div onClick={() => router.push(publicHref)} className="cursor-pointer rounded-xl transition-transform motion-safe:hover:-translate-y-0.5 motion-safe:active:scale-[0.99]">
        <StudentIdCard firstName={user.first_name} lastInitial={user.last_name[0]?.toUpperCase() ?? ""} username={user.username} schoolName={user.school?.name} schoolColors={user.school?.colors} dateJoined={user.date_joined} soldCount={user.sold_count} followerCount={user.follower_count} />
      </div>
      <div className="mt-3 grid grid-cols-2 gap-2">
        <Link href={publicHref} className="btn btn-secondary">View profile</Link>
        <Link href="/profile/edit" className="btn btn-secondary">Edit profile</Link>
      </div>
      <nav aria-label="Account" className="mt-4">
        <ListGroup>
          {rows.map((row) => <ListRow key={row.href} href={row.href} icon={row.icon}>{row.label}</ListRow>)}
        </ListGroup>
        {/* Log out stands apart from the pages above it. */}
        <ListGroup className="mt-4">
          <ListButton onClick={logOutNow} disabled={logOutState === "pending"} icon={LogOutIcon} tone="muted">{logOutState === "pending" ? "Logging out…" : "Log out"}</ListButton>
        </ListGroup>
        {logOutState === "failed" && <p role="alert" className="mt-2 text-label text-danger">Couldn’t log out. Check your connection and try again.</p>}
      </nav>
    </div>
  );
}
