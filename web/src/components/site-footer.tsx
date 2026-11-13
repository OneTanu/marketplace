"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import { SUPPORT_EMAIL } from "@/lib/site";

import { isFocusedPath } from "./nav-items";

/** Pages that show the footer: Home for guests, Terms, Privacy, the Profile page, and log in,
 * sign up and the other account pages. These are where the non-affiliation note stays reachable.
 * On Home the footer is in the page for everyone, and a signed-in student's feed hides it with
 * CSS (see `data-home-feed` in globals.css): the layout can't tell who is signed in, and this
 * keeps the footer in the server-rendered page and outside <main>. */
export function hasFooter(pathname: string) {
  return pathname === "/" || pathname === "/terms" || pathname === "/privacy" || pathname === "/profile" || pathname.startsWith("/account/");
}

/** Room at the bottom of the page for the phone bottom bar, so it never covers the content. */
export function BottomBarSpacer() {
  return <div aria-hidden="true" className="h-[calc(4rem+env(safe-area-inset-bottom))] shrink-0 desktop:hidden" />;
}

/** Terms, Privacy and the non-affiliation note. `bottomBar` adds room under it for the phone
 * bottom bar, when the page has one. */
export function Footer({ bottomBar = false }: { bottomBar?: boolean }) {
  return <footer data-site-footer className={`border-t border-line ${bottomBar ? "pb-[calc(4rem+env(safe-area-inset-bottom))] desktop:pb-0" : ""}`}><div className="mx-auto flex max-w-6xl flex-col gap-4 px-4 py-8 text-label text-muted sm:flex-row sm:items-center sm:justify-between sm:px-6">
    <p><span className="type-wide font-extrabold text-ink">tanu</span> <span className="ml-2">© 2026. Built by students.</span></p>
    <div className="flex gap-5"><Link className="transition hover:text-ink" href="/terms">Terms</Link><Link className="transition hover:text-ink" href="/privacy">Privacy</Link><a className="transition hover:text-ink" href={`mailto:${SUPPORT_EMAIL}`}>Contact support</a></div>
    <p className="max-w-sm text-fine sm:text-right">Independent and not affiliated with or endorsed by any university.</p>
  </div></footer>;
}

/** The end of every page: the footer where it belongs (see hasFooter), otherwise just room for
 * the phone bottom bar. Focused screens have neither. */
export function SiteFooter() {
  const pathname = usePathname();
  if (isFocusedPath(pathname)) return null;
  const bottomBar = !pathname.startsWith("/account/");
  if (hasFooter(pathname)) return <Footer bottomBar={bottomBar} />;
  return bottomBar ? <BottomBarSpacer /> : null;
}
