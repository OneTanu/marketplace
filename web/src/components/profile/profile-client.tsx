"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useEffect, useState } from "react";

import { useLogOut } from "@/components/auth/auth-actions";
import { RestrictionNotice } from "@/components/trust/restriction-notice";
import { getCurrentUser } from "@/lib/platform";
import type { components } from "@/lib/api/schema";

import { StudentIdCard } from "./student-id-card";

type CurrentUser = components["schemas"]["CurrentUser"];

function Chevron() {
  return <svg viewBox="0 0 24 24" className="size-[18px] shrink-0 text-muted" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><path d="M9 6l6 6-6 6" /></svg>;
}

const rowClass = "flex min-h-14 w-full items-center justify-between gap-3 border-b border-line text-left text-base font-semibold text-ink transition hover:text-muted";

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
      return <main className="mx-auto grid min-h-[70vh] max-w-xl place-items-center px-4 py-12 text-center"><div className="rounded-2xl bg-surface p-8"><h1 className="type-wide text-2xl font-black">We couldn’t load your profile</h1><p className="mt-3 leading-7 text-muted">Your session may still be active. Check the connection and try loading your account again.</p><button type="button" onClick={retryProfile} className="btn btn-primary mt-6">Try again</button></div></main>;
    }
    return <main className="mx-auto min-h-[70vh] w-full max-w-[28rem] animate-pulse px-4 py-6 sm:py-10"><div className="h-56 rounded-[14px] bg-surface" /><div className="mt-3 h-11 rounded-lg bg-surface" /><div className="mt-4 h-72 rounded-lg bg-surface" /></main>;
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

  const publicHref = `/users/${encodeURIComponent(user.username)}`;
  const rows: { href: string; label: string }[] = [
    { href: "/listings/mine", label: "My listings" },
    { href: "/profile/saved", label: "Saved" },
    { href: "/profile/searches", label: "Saved searches" },
    { href: "/profile/meetup", label: "Meetup preferences" },
    { href: "/profile/standing", label: "Account status" },
    ...(user.is_moderator ? [{ href: "/moderation", label: "Moderation" }] : []),
  ];

  return (
    <div className="mx-auto w-full max-w-[28rem] px-4 py-6 sm:py-10">
      <RestrictionNotice />
      {/* The whole card opens the public profile for a tap or click. It isn't a link itself, so
          screen readers and keyboards get one clear way there: the View profile button. */}
      <div onClick={() => router.push(publicHref)} className="cursor-pointer rounded-[14px] transition hover:shadow-[0_6px_20px_-8px_rgb(23_22_43/25%)]">
        <StudentIdCard firstName={user.first_name} lastInitial={user.last_name[0]?.toUpperCase() ?? ""} username={user.username} schoolName={user.school?.name} schoolColors={user.school?.colors} dateJoined={user.date_joined} soldCount={user.sold_count} followerCount={user.follower_count} />
      </div>
      <div className="mt-3 grid grid-cols-2 gap-2">
        <Link href={publicHref} className="btn btn-secondary">View profile</Link>
        <Link href="/profile/edit" className="btn btn-secondary">Edit profile</Link>
      </div>
      <nav aria-label="Account" className="mt-3">
        <ul>
          {rows.map((row) => <li key={row.href}><Link href={row.href} className={rowClass}>{row.label}<Chevron /></Link></li>)}
          <li><button type="button" onClick={logOutNow} disabled={logOutState === "pending"} className={`${rowClass} border-b-0 disabled:opacity-55`}>{logOutState === "pending" ? "Logging out…" : "Log out"}</button></li>
        </ul>
        {logOutState === "failed" && <p role="alert" className="text-sm text-[var(--danger)]">Couldn’t log out. Check your connection and try again.</p>}
      </nav>
    </div>
  );
}
