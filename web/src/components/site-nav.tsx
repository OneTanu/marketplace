"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Suspense } from "react";
import { AuthActions } from "./auth/auth-actions";
import { MarketplaceDepartmentNav } from "./discovery/marketplace-department-nav";
import { UnreadBadge } from "./messaging/unread-badge";
import { BOTTOM_BAR, DESKTOP_LINKS, isActive, isFocusedPath, SELL } from "./nav-items";
import { SearchIcon } from "./ui/icons";

function Wordmark() {
  return <span className="wordmark text-ink">tanu</span>;
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
          <div className="flex h-11 w-full items-center rounded-lg border border-transparent bg-surface px-3 transition focus-within:border-brand focus-within:bg-background focus-within:ring-3 focus-within:ring-ink/12">
            <SearchIcon className="size-5 shrink-0 text-muted" aria-hidden="true" />
            <input name="search" type="search" enterKeyHint="search" className="h-full min-w-0 flex-1 bg-transparent px-2 outline-none placeholder:text-muted" placeholder="Search listings" aria-label="Search listings" />
          </div>
        </form>}
        <nav className="ml-auto hidden items-center gap-6 desktop:flex" aria-label="Main">
          {DESKTOP_LINKS.map((item) => <Link key={item.href} href={item.href} aria-current={isActive(pathname, item.href) ? "page" : undefined} className="relative flex h-16 items-center text-label font-semibold text-muted transition hover:text-ink aria-[current=page]:text-ink aria-[current=page]:after:absolute aria-[current=page]:after:inset-x-0 aria-[current=page]:after:-bottom-px aria-[current=page]:after:h-0.5 aria-[current=page]:after:bg-ink">{item.label}{item.href === "/inbox" && <UnreadBadge />}</Link>)}
        </nav>
        <AuthActions />
      </div>
      {showDepartments && <div className="border-t border-line"><Suspense fallback={<div className="h-12" />}><MarketplaceDepartmentNav schoolSlug={schoolSlug} /></Suspense></div>}
    </header>
    {!isAccountPage && !focused && <nav aria-label="Main" className="fixed inset-x-0 bottom-0 z-20 border-t border-line bg-background pb-[env(safe-area-inset-bottom)] desktop:hidden">
      <ul className="grid grid-cols-5">{BOTTOM_BAR.map((item) => { const current = isActive(pathname, item.href); return <li key={item.href}>
        <Link href={item.href} aria-current={current ? "page" : undefined} className="flex min-h-16 flex-col items-center justify-center gap-0.5 text-fine font-semibold text-muted transition aria-[current=page]:text-ink">
          {/* Every icon gets the same 40px box, so the labels line up under Sell's filled circle. */}
          {/* Lucide has no filled icons, so the current tab is ink with a heavier line. */}
          <span className={`grid size-10 place-items-center ${item === SELL ? "rounded-full bg-ink text-white" : ""}`}><item.icon className="size-6" strokeWidth={current && item !== SELL ? 2.4 : 2} aria-hidden="true" /></span>
          <span>{item.label}{item.href === "/inbox" && <UnreadBadge />}</span>
        </Link>
      </li>; })}</ul>
    </nav>}
  </>;
}
