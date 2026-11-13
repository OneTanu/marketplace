"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Suspense } from "react";
import { AuthActions } from "./auth/auth-actions";
import { MarketplaceDepartmentNav } from "./discovery/marketplace-department-nav";
import { UnreadBadge } from "./messaging/unread-badge";
import { BOTTOM_BAR, DESKTOP_LINKS, isActive, isFocusedPath, SELL } from "./nav-items";

function Wordmark() {
  return <span className="type-wide text-[1.375rem] font-black leading-none text-ink desktop:text-[1.625rem]">tanu</span>;
}

/** The site header and, on phones, the bottom bar.
 * Phone header: logo, search, bell. Desktop header: logo, search, Deals, Inbox, bell, Sell,
 * account menu. Focused screens (see isFocusedPath) drop both on phones and draw their own
 * back button and title. */
export function SiteNav() {
  const pathname = usePathname();
  const isAccountPage = pathname.startsWith("/account/");
  const focused = isFocusedPath(pathname);
  const schoolSlug = pathname.match(/^\/schools\/([^/]+)/)?.[1];
  const showDepartments = Boolean(schoolSlug) || pathname === "/search";

  return <>
    <header className={`sticky top-0 z-20 border-b border-line bg-background/95 backdrop-blur-xl ${focused ? "hidden desktop:block" : ""}`}>
      <div className="mx-auto flex h-16 max-w-6xl items-center gap-3 px-4 sm:px-6 desktop:gap-6">
        <Link href="/" aria-label="Tanu home" className="shrink-0"><Wordmark /></Link>
        {isAccountPage ? <div className="flex-1" /> : <form action="/search" role="search" className="min-w-0 flex-1 desktop:max-w-xl">
          {schoolSlug && <input type="hidden" name="school" value={schoolSlug} />}
          <div className="flex h-11 w-full items-center rounded-[0.625rem] border border-transparent bg-surface px-3 transition focus-within:border-brand focus-within:bg-background focus-within:shadow-[0_0_0_3px_var(--brand-soft)]">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} className="size-[18px] shrink-0 text-muted" aria-hidden="true"><path d="m21 21-4.3-4.3M10.5 18a7.5 7.5 0 1 1 0-15 7.5 7.5 0 0 1 0 15Z" /></svg>
            <input name="search" type="search" enterKeyHint="search" className="h-full min-w-0 flex-1 bg-transparent px-2 outline-none placeholder:text-muted" placeholder="Search listings" aria-label="Search listings" />
          </div>
        </form>}
        <nav className="ml-auto hidden items-center gap-6 desktop:flex" aria-label="Main">
          {DESKTOP_LINKS.map((item) => <Link key={item.href} href={item.href} aria-current={isActive(pathname, item.href) ? "page" : undefined} className="relative flex h-16 items-center text-sm font-semibold text-muted transition hover:text-ink aria-[current=page]:text-ink aria-[current=page]:after:absolute aria-[current=page]:after:inset-x-0 aria-[current=page]:after:-bottom-px aria-[current=page]:after:h-0.5 aria-[current=page]:after:bg-ink">{item.label}{item.href === "/inbox" && <UnreadBadge />}</Link>)}
        </nav>
        <AuthActions />
      </div>
      {showDepartments && <div className="border-t border-line"><Suspense fallback={<div className="h-12" />}><MarketplaceDepartmentNav schoolSlug={schoolSlug} /></Suspense></div>}
    </header>
    {!isAccountPage && !focused && <nav aria-label="Main" className="fixed inset-x-0 bottom-0 z-20 border-t border-line bg-background/95 pb-[env(safe-area-inset-bottom)] backdrop-blur-xl desktop:hidden">
      <ul className="grid grid-cols-5">{BOTTOM_BAR.map((item) => <li key={item.href}>
        <Link href={item.href} aria-current={isActive(pathname, item.href) ? "page" : undefined} className="flex min-h-16 flex-col items-center justify-center gap-0.5 text-fine font-semibold text-muted transition aria-[current=page]:text-ink">
          {/* Every icon gets the same 40px box, so the labels line up under Sell's filled circle. */}
          <span className={`grid size-10 place-items-center ${item === SELL ? "rounded-full bg-ink text-white" : ""}`}>{item.icon}</span>
          <span>{item.label}{item.href === "/inbox" && <UnreadBadge />}</span>
        </Link>
      </li>)}</ul>
    </nav>}
  </>;
}
