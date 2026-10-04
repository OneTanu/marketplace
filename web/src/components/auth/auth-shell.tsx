import Link from "next/link";
import type { ReactNode } from "react";

export function AuthShell({ eyebrow, title, description, children, footer }: { eyebrow: string; title: string; description: string; children: ReactNode; footer?: ReactNode }) {
  return <section className="mx-auto grid min-h-[calc(100vh-4rem)] max-w-6xl items-stretch lg:grid-cols-[.9fr_1.1fr]">
    <aside className="relative hidden overflow-hidden border-r border-line bg-forest p-12 text-white lg:flex lg:flex-col lg:justify-between">
      <div className="absolute -right-28 top-16 size-72 rounded-full border border-white/10" /><div className="absolute -right-12 top-32 size-48 rounded-full border border-white/10" />
      <Link href="/" className="relative text-sm font-bold text-white/75">← Back to Tanu</Link>
      <div className="relative max-w-sm"><p className="text-xs font-bold uppercase tracking-[.2em] text-[#a7d1b5]">Built for campus life</p><blockquote className="mt-5 text-4xl font-bold leading-tight tracking-[-.04em]">Good stuff is already on your campus. Tanu makes it easier to find.</blockquote><div className="mt-9 flex items-center gap-3 border-t border-white/15 pt-6 text-sm text-white/65"><span className="grid size-9 place-items-center rounded-full bg-white/10 font-bold text-white">U</span>Launching first at the University of Maryland</div></div>
    </aside>
    <div className="flex items-center justify-center px-4 py-12 sm:px-10 lg:px-16"><div className="animate-in w-full max-w-md"><p className="text-xs font-bold uppercase tracking-[.18em] text-brand">{eyebrow}</p><h1 className="mt-3 text-4xl font-black tracking-[-.045em] sm:text-5xl">{title}</h1><p className="mt-4 leading-7 text-muted">{description}</p><div className="mt-8">{children}</div>{footer && <div className="mt-7 text-center text-sm text-muted">{footer}</div>}</div></div>
  </section>;
}
