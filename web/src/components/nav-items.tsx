import type { ReactNode } from "react";

export type NavItem = { href: string; label: string; icon: ReactNode };

export function NavIcon({ d, className = "size-6" }: { d: string; className?: string }) {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={1.8}
      strokeLinecap="round"
      strokeLinejoin="round"
      className={className}
      aria-hidden="true"
    >
      <path d={d} />
    </svg>
  );
}

export const HOME: NavItem = { href: "/", label: "Home", icon: <NavIcon d="M3 10.5 12 3l9 7.5V21h-6v-6H9v6H3z" /> };
export const DEALS: NavItem = { href: "/deals", label: "Deals", icon: <NavIcon d="M7 7h10v10H7zM4 10h3m10 0h3M4 14h3m10 0h3" /> };
export const SELL: NavItem = { href: "/sell", label: "Sell", icon: <NavIcon d="M12 5v14M5 12h14" className="size-6" /> };
export const INBOX: NavItem = { href: "/inbox", label: "Inbox", icon: <NavIcon d="M4 5h16v11H8l-4 4z" /> };
export const PROFILE: NavItem = { href: "/profile", label: "Profile", icon: <NavIcon d="M12 12a4 4 0 1 0 0-8 4 4 0 0 0 0 8zM4 21a8 8 0 0 1 16 0" /> };

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
