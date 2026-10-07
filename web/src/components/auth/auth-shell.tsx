import Image from "next/image";
import Link from "next/link";
import type { ReactNode } from "react";

export function AuthShell({ eyebrow, title, description, children, footer }: { eyebrow: string; title: string; description: string; children: ReactNode; footer?: ReactNode }) {
  return <section className="mx-auto grid min-h-[calc(100vh-4rem)] max-w-6xl items-stretch lg:grid-cols-[.9fr_1.1fr]">
    <aside className="relative hidden overflow-hidden bg-ink lg:block">
      <Image src="/demo-listings/real/brown-novamen-jacket.jpg" alt="" fill sizes="40vw" className="object-cover opacity-70" />
      <div className="absolute inset-x-0 bottom-0 bg-gradient-to-t from-ink via-ink/80 to-transparent p-10 pt-32 text-white">
        <p className="type-wide max-w-sm text-3xl font-black leading-tight">Good stuff is already on your campus.</p>
        <p className="mt-3 text-sm text-white/70">Launching first at the University of Maryland.</p>
      </div>
      <Link href="/" className="absolute left-8 top-8 rounded bg-background px-3 py-1.5 text-sm font-semibold text-ink">Back to Tanu</Link>
    </aside>
    <div className="flex items-center justify-center px-4 py-12 sm:px-10 lg:px-16"><div className="w-full max-w-md"><p className="text-sm font-semibold text-brand">{eyebrow}</p><h1 className="type-wide mt-2 text-[2rem] font-black leading-tight sm:text-[2.5rem]">{title}</h1><p className="mt-3 leading-7 text-muted">{description}</p><div className="mt-8">{children}</div>{footer && <div className="mt-7 text-center text-sm text-muted">{footer}</div>}</div></div>
  </section>;
}
