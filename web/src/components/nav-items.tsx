import type { LucideIcon } from "lucide-react";

import { DealsIcon, HomeIcon, InboxIcon, PlusIcon, ProfileIcon } from "./ui/icons";

export type NavItem = { href: string; label: string; icon: LucideIcon };

export const HOME: NavItem = { href: "/", label: "Home", icon: HomeIcon };
export const DEALS: NavItem = { href: "/deals", label: "Deals", icon: DealsIcon };
export const SELL: NavItem = { href: "/sell", label: "Sell", icon: PlusIcon };
export const INBOX: NavItem = { href: "/inbox", label: "Inbox", icon: InboxIcon };
export const PROFILE: NavItem = { href: "/profile", label: "Profile", icon: ProfileIcon };

/** The phone bottom bar, in order. Sell sits in the middle. */
export const BOTTOM_BAR: NavItem[] = [HOME, DEALS, SELL, INBOX, PROFILE];
/** Text links in the desktop header (Sell and the account menu sit beside them). */
export const DESKTOP_LINKS: NavItem[] = [DEALS, INBOX];

export function isActive(pathname: string, href: string) {
  return href === "/" ? pathname === "/" : pathname === href || pathname.startsWith(`${href}/`);
}

/** Focused screens: one task, so the page shows its own back button and title instead of the
 * search header, the bottom bar and the footer. */
export function isFocusedPath(pathname: string) {
  return (
    /^\/inbox\/[^/]+\/?$/.test(pathname) ||
    /^\/sell\/?$/.test(pathname) ||
    /^\/listings\/[^/]+\/edit\/?$/.test(pathname) ||
    /^\/profile\/(meetup|edit)\/?$/.test(pathname)
  );
}
