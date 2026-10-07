import Link from "next/link";

export function SiteFooter() {
  return <footer className="border-t border-line"><div className="mx-auto flex max-w-6xl flex-col gap-4 px-4 py-8 text-sm text-muted sm:flex-row sm:items-center sm:justify-between sm:px-6">
    <p><span className="type-wide font-black text-ink">tanu</span> <span className="ml-2">© 2026. Built by students.</span></p>
    <div className="flex gap-5"><Link className="transition hover:text-ink" href="/terms">Terms</Link><Link className="transition hover:text-ink" href="/privacy">Privacy</Link></div>
    <p className="max-w-sm text-xs sm:text-right">Independent and not affiliated with or endorsed by any university.</p>
  </div></footer>;
}
