"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import { NAV_ITEMS } from "./nav-items";

function isActive(pathname: string, href: string) {
  return href === "/" ? pathname === "/" : pathname.startsWith(href);
}

/** Top nav on devices with a mouse/trackpad, bottom tab bar on touch devices. */
export function SiteNav() {
  const pathname = usePathname();

  return (
    <>
      <header className="sticky top-0 z-10 border-b border-black/10 bg-background/90 backdrop-blur dark:border-white/10">
        <div className="mx-auto flex h-14 max-w-6xl items-center justify-between px-4">
          <Link href="/" className="text-xl font-bold tracking-tight">
            Tanu
          </Link>
          <nav className="hidden gap-1 desktop:flex" aria-label="Main">
            {NAV_ITEMS.map((item) => (
              <Link
                key={item.href}
                href={item.href}
                aria-current={isActive(pathname, item.href) ? "page" : undefined}
                className="rounded-full px-4 py-2 text-sm font-medium text-foreground/70 hover:bg-foreground/5 aria-[current=page]:bg-foreground aria-[current=page]:text-background"
              >
                {item.label}
              </Link>
            ))}
          </nav>
        </div>
      </header>

      <nav
        aria-label="Main"
        className="fixed inset-x-0 bottom-0 z-10 border-t border-black/10 bg-background pb-[env(safe-area-inset-bottom)] desktop:hidden dark:border-white/10"
      >
        <ul className="grid grid-cols-5">
          {NAV_ITEMS.map((item) => (
            <li key={item.href}>
              <Link
                href={item.href}
                aria-current={isActive(pathname, item.href) ? "page" : undefined}
                className="flex flex-col items-center gap-0.5 py-2 text-[11px] text-foreground/60 aria-[current=page]:text-foreground"
              >
                {item.icon}
                {item.label}
              </Link>
            </li>
          ))}
        </ul>
      </nav>
    </>
  );
}
