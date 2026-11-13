"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import { SUPPORT_EMAIL } from "@/lib/site";

import { isFocusedPath } from "./nav-items";

/** Terms, Privacy and the non-affiliation note. Focused screens leave it out. On phones its
 * bottom padding keeps it, the last thing on the page, clear of the bottom bar. */
export function SiteFooter() {
  const pathname = usePathname();
  if (isFocusedPath(pathname)) return null;
  const hasBottomBar = !pathname.startsWith("/account/");
  return <footer className={`border-t border-line ${hasBottomBar ? "pb-[calc(4rem+env(safe-area-inset-bottom))] desktop:pb-0" : ""}`}><div className="mx-auto flex max-w-6xl flex-col gap-4 px-4 py-8 text-sm text-muted sm:flex-row sm:items-center sm:justify-between sm:px-6">
    <p><span className="type-wide font-black text-ink">tanu</span> <span className="ml-2">© 2026. Built by students.</span></p>
    <div className="flex gap-5"><Link className="transition hover:text-ink" href="/terms">Terms</Link><Link className="transition hover:text-ink" href="/privacy">Privacy</Link><a className="transition hover:text-ink" href={`mailto:${SUPPORT_EMAIL}`}>Contact support</a></div>
    <p className="max-w-sm text-xs sm:text-right">Independent and not affiliated with or endorsed by any university.</p>
  </div></footer>;
}
