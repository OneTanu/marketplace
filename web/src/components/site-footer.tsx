import Link from "next/link";

export function SiteFooter() {
  return <footer className="border-t border-line/80 bg-[#f0eee7]"><div className="mx-auto flex max-w-6xl flex-col gap-4 px-4 py-8 text-sm text-muted sm:flex-row sm:items-center sm:justify-between sm:px-6">
    <p>© 2026 Tanu. Built for students, by students.</p>
    <div className="flex gap-5"><Link className="transition hover:text-foreground" href="/terms">Terms</Link><Link className="transition hover:text-foreground" href="/privacy">Privacy</Link></div>
    <p className="max-w-sm text-xs sm:text-right">Independent and not affiliated with or endorsed by any university.</p>
  </div></footer>;
}
