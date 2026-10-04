"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { AuthActions } from "./auth/auth-actions";
import { NAV_ITEMS } from "./nav-items";
import { SchoolSwitcher } from "./school-switcher";

function isActive(pathname: string, href: string) {
  return href === "/" ? pathname === "/" : pathname.startsWith(href);
}

function Wordmark() {
  return <span className="flex items-center gap-2.5"><span className="grid size-8 place-items-center rounded-[10px] bg-brand text-[15px] font-black text-white shadow-[0_4px_14px_rgb(237_91_43/25%)]">T</span><span className="text-xl font-bold tracking-[-0.04em]">tanu</span></span>;
}

export function SiteNav() {
  const pathname = usePathname();
  const isAccountPage = pathname.startsWith("/account/");

  return <>
    <header className="sticky top-0 z-20 border-b border-line/80 bg-[#f7f5ef]/90 backdrop-blur-xl">
      <div className="mx-auto flex h-16 max-w-6xl items-center justify-between px-4 sm:px-6">
        <div className="flex items-center gap-4">
          <Link href="/" aria-label="Tanu home"><Wordmark /></Link>
          <SchoolSwitcher />
        </div>
        <nav className="hidden items-center gap-1 desktop:flex" aria-label="Main">
          {NAV_ITEMS.slice(0, 4).map((item) => <Link key={item.href} href={item.href} aria-current={isActive(pathname, item.href) ? "page" : undefined} className="rounded-full px-4 py-2 text-sm font-semibold text-foreground/65 transition hover:bg-white/70 hover:text-foreground aria-[current=page]:bg-white aria-[current=page]:text-foreground aria-[current=page]:shadow-sm">{item.label}</Link>)}
        </nav>
        <AuthActions />
      </div>
    </header>
    {!isAccountPage && <nav aria-label="Main" className="fixed inset-x-0 bottom-0 z-20 border-t border-line bg-[#fffdf8]/95 pb-[env(safe-area-inset-bottom)] backdrop-blur-xl desktop:hidden">
      <ul className="grid grid-cols-5">{NAV_ITEMS.map((item) => <li key={item.href}><Link href={item.href} aria-current={isActive(pathname, item.href) ? "page" : undefined} className="flex min-h-16 flex-col items-center justify-center gap-1 text-[11px] font-semibold text-muted transition aria-[current=page]:text-brand">{item.icon}{item.label}</Link></li>)}</ul>
    </nav>}
  </>;
}
