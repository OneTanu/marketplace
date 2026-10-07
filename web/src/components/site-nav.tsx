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
  return <span className="flex items-center gap-2.5"><span className="grid size-8 place-items-center rounded-[10px] bg-brand text-[15px] font-black text-white shadow-[0_4px_14px_rgb(237_91_43/25%)]">T</span><span className="hidden text-xl font-bold tracking-[-0.04em] sm:inline">tanu</span></span>;
}

export function SiteNav() {
  const pathname = usePathname();
  const isAccountPage = pathname.startsWith("/account/");
  const schoolMatch = pathname.match(/^\/schools\/([^/]+)/);
  const schoolSlug = schoolMatch?.[1];
  const showMarketplaceSearch = Boolean(schoolSlug) || pathname === "/search";

  return <>
    <header className="sticky top-0 z-20 border-b border-line/80 bg-[#f7f5ef]/90 backdrop-blur-xl">
      <div className="mx-auto flex min-h-16 max-w-6xl flex-wrap items-center justify-between gap-x-4 px-4 sm:px-6">
        <div className="flex items-center gap-2.5 sm:gap-4">
          <Link href="/" aria-label="Tanu home"><Wordmark /></Link>
          <SchoolSwitcher />
        </div>
        {showMarketplaceSearch && <form action="/search" className="order-3 flex w-full items-center pb-3 desktop:order-none desktop:max-w-xl desktop:flex-1 desktop:pb-0">
          {schoolSlug && <input type="hidden" name="school" value={schoolSlug} />}
          <div className="flex h-11 w-full items-center rounded-full border border-line bg-white px-4 shadow-sm transition focus-within:border-forest focus-within:ring-4 focus-within:ring-forest/10">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.8} className="size-5 shrink-0 text-muted" aria-hidden="true"><path d="m21 21-4.3-4.3M10.5 18a7.5 7.5 0 1 1 0-15 7.5 7.5 0 0 1 0 15Z" /></svg>
            <input name="search" className="h-full min-w-0 flex-1 bg-transparent px-3 text-sm outline-none" placeholder="Search for clothing, brands, and campus items" aria-label="Search marketplace" />
            <button className="text-xs font-black text-forest">Search</button>
          </div>
        </form>}
        {!schoolSlug && <nav className="hidden items-center gap-1 desktop:flex" aria-label="Main">
          {NAV_ITEMS.slice(0, 4).map((item) => <Link key={item.href} href={item.href} aria-current={isActive(pathname, item.href) ? "page" : undefined} className="rounded-full px-4 py-2 text-sm font-semibold text-foreground/65 transition hover:bg-white/70 hover:text-foreground aria-[current=page]:bg-white aria-[current=page]:text-foreground aria-[current=page]:shadow-sm">{item.label}{item.href === "/inbox" && <UnreadBadge />}</Link>)}
        </nav>}
        <AuthActions />
      </div>
      {schoolSlug && <div className="border-t border-line/70 bg-surface/80"><Suspense fallback={<div className="h-14" />}><MarketplaceDepartmentNav schoolSlug={schoolSlug} /></Suspense></div>}
    </header>
    {!isAccountPage && <nav aria-label="Main" className="fixed inset-x-0 bottom-0 z-20 border-t border-line bg-[#fffdf8]/95 pb-[env(safe-area-inset-bottom)] backdrop-blur-xl desktop:hidden">
      <ul className="grid grid-cols-5">{NAV_ITEMS.map((item) => <li key={item.href}><Link href={item.href} aria-current={isActive(pathname, item.href) ? "page" : undefined} className="flex min-h-16 flex-col items-center justify-center gap-1 text-[11px] font-semibold text-muted transition aria-[current=page]:text-brand">{item.icon}<span>{item.label}{item.href === "/inbox" && <UnreadBadge />}</span></Link></li>)}</ul>
    </nav>}
  </>;
}
