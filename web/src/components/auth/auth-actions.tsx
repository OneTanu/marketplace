"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { usePathname, useRouter } from "next/navigation";
import { NotificationBell } from "@/components/notifications/notification-bell";
import { Avatar } from "@/components/messaging/avatar";
import { Menu, MenuButton, MenuDivider, MenuLink } from "@/components/ui/menu";
import type { components } from "@/lib/api/schema";
import { authRequest } from "@/lib/auth";
import { getCurrentUser } from "@/lib/platform";

type CurrentUser = components["schemas"]["CurrentUser"];

/** Ends the session and goes Home. Used by the desktop account menu and the Profile page.
 * Resolves to whether the session ended. */
export function useLogOut() {
  const router = useRouter();
  return async function logOut() {
    // allauth answers a successful logout with 401 (meaning "no longer authenticated").
    const { response } = await authRequest("auth/session", { method: "DELETE" });
    const done = response.ok || response.status === 401;
    if (done) { router.push("/"); router.refresh(); }
    return done;
  };
}

/** The right end of the header. Phone: the bell (Sell and Profile are in the bottom bar).
 * Desktop: the bell, Sell and the account menu. Guests: Log in and Join. */
export function AuthActions() {
  const pathname = usePathname();
  const logOut = useLogOut();
  // undefined while loading, null for a guest.
  const [user, setUser] = useState<CurrentUser | null | undefined>(undefined);

  useEffect(() => {
    let active = true;
    getCurrentUser().then((current) => active && setUser(current))
      // A failed check (server error, dropped connection) keeps what we knew, so a signed-in
      // student doesn't flash to the guest header; on the first load it falls back to guest.
      .catch(() => active && setUser((current) => current ?? null));
    return () => { active = false; };
  }, [pathname]);

  if (user === undefined) return <div className="h-11 w-11 animate-pulse rounded-lg bg-surface desktop:w-40" aria-hidden="true" />;
  if (user) return <div className="flex shrink-0 items-center gap-1">
    <NotificationBell />
    <Link href="/sell" className="btn btn-primary btn-sm ml-2 hidden desktop:inline-flex">Sell</Link>
    <div className="ml-1 hidden desktop:block">
      <Menu label="Account menu" triggerClassName="flex h-11 items-center gap-1.5 rounded-full pl-1 pr-2 transition hover:bg-surface aria-expanded:bg-surface" trigger={<>
        <Avatar user={user} size="sm" />
        <svg aria-hidden="true" viewBox="0 0 12 12" className="size-2.5 text-muted" fill="none" stroke="currentColor" strokeWidth={1.8}><path d="m2 4 4 4 4-4" /></svg>
      </>}>
        <p role="none" className="px-4 pb-2 pt-1.5 text-fine text-muted">Signed in as <span className="font-semibold text-ink">@{user.username}</span></p>
        <MenuDivider />
        <MenuLink href="/profile">Profile</MenuLink>
        <MenuLink href="/listings/mine">My listings</MenuLink>
        <MenuLink href="/profile?tab=bookmarks">Saved</MenuLink>
        <MenuDivider />
        <MenuButton onSelect={async () => { if (await logOut()) setUser(null); }}>Log out</MenuButton>
      </Menu>
    </div>
  </div>;
  return <div className="flex shrink-0 items-center gap-1"><Link href="/account/login" className="btn btn-quiet btn-sm hidden sm:inline-flex">Log in</Link><Link href="/account/signup" className="btn btn-primary btn-sm">Join Tanu</Link></div>;
}
