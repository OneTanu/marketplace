"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Suspense } from "react";
import { AuthActions } from "./auth/auth-actions";
import { MarketplaceDepartmentNav } from "./discovery/marketplace-department-nav";
import { UnreadBadge } from "./messaging/unread-badge";
import { NAV_ITEMS } from "./nav-items";
import { SchoolSwitcher } from "./school-switcher";

function isActive(pathname: string, href: string) {
  return href === "/" ? pathname === "/" : pathname.startsWith(href);
}

function Wordmark() {
  return <span className="type-wide text-[1.625rem] font-black leading-none text-ink">tanu</span>;
}

export function SiteNav() {
  const pathname = usePathname();
  const isAccountPage = pathname.startsWith("/account/");
  const schoolMatch = pathname.match(/^\/schools\/([^/]+)/);
  const schoolSlug = schoolMatch?.[1];
  const showMarketplaceSearch = Boolean(schoolSlug) || pathname === "/search";
  const showDepartments = Boolean(schoolSlug) || pathname === "/search";

  return <>
    <header className="sticky top-0 z-20 border-b border-line bg-background/95 backdrop-blur-xl">
      <div className="mx-auto flex min-h-16 max-w-6xl flex-wrap items-center justify-between gap-x-4 px-4 sm:px-6">
        <div className="flex items-center gap-3 sm:gap-5">
          <Link href="/" aria-label="Tanu home"><Wordmark /></Link>
          <Suspense fallback={null}><SchoolSwitcher /></Suspense>
        </div>
        {showMarketplaceSearch && <form action="/search" role="search" className="order-3 flex w-full items-center pb-3 desktop:order-none desktop:max-w-xl desktop:flex-1 desktop:pb-0">
          {schoolSlug && <input type="hidden" name="school" value={schoolSlug} />}
          <div className="flex h-11 w-full items-center rounded-[0.625rem] border border-transparent bg-surface px-3.5 transition focus-within:border-brand focus-within:bg-background focus-within:shadow-[0_0_0_3px_var(--brand-soft)]">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} className="size-[18px] shrink-0 text-muted" aria-hidden="true"><path d="m21 21-4.3-4.3M10.5 18a7.5 7.5 0 1 1 0-15 7.5 7.5 0 0 1 0 15Z" /></svg>
            <input name="search" type="search" enterKeyHint="search" className="h-full min-w-0 flex-1 bg-transparent px-2.5 text-[15px] outline-none placeholder:text-muted" placeholder="Search clothes, brands, and dorm stuff" aria-label="Search marketplace" />
          </div>
        </form>}
        {!schoolSlug && <nav className="hidden items-center gap-6 desktop:flex" aria-label="Main">
          {NAV_ITEMS.slice(0, 4).map((item) => <Link key={item.href} href={item.href} aria-current={isActive(pathname, item.href) ? "page" : undefined} className="relative py-5 text-sm font-semibold text-muted transition hover:text-ink aria-[current=page]:text-ink aria-[current=page]:after:absolute aria-[current=page]:after:inset-x-0 aria-[current=page]:after:-bottom-px aria-[current=page]:after:h-0.5 aria-[current=page]:after:bg-ink">{item.label}{item.href === "/inbox" && <UnreadBadge />}</Link>)}
        </nav>}
        <AuthActions />
      </div>
      {showDepartments && <div className="border-t border-line"><Suspense fallback={<div className="h-12" />}><MarketplaceDepartmentNav schoolSlug={schoolSlug} /></Suspense></div>}
    </header>
    {!isAccountPage && <nav aria-label="Main" className="fixed inset-x-0 bottom-0 z-20 border-t border-line bg-background/95 pb-[env(safe-area-inset-bottom)] backdrop-blur-xl desktop:hidden">
      <ul className="grid grid-cols-5">{NAV_ITEMS.map((item) => {
        if (item.href === "/sell") {
          return <li key={item.href} className="grid place-items-center"><Link href={item.href} aria-label="Sell an item" aria-current={isActive(pathname, item.href) ? "page" : undefined} className="grid size-12 place-items-center rounded-xl bg-brand text-white transition active:bg-brand-strong">{item.icon}</Link></li>;
        }
        return <li key={item.href}><Link href={item.href} aria-current={isActive(pathname, item.href) ? "page" : undefined} className="flex min-h-16 flex-col items-center justify-center gap-1 text-[11px] font-semibold text-muted transition aria-[current=page]:text-ink">{item.icon}<span>{item.label}{item.href === "/inbox" && <UnreadBadge />}</span></Link></li>;
      })}</ul>
    </nav>}
  </>;
}
