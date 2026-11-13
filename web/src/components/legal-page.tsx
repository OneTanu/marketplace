import type { ReactNode } from "react";

/** A long-form policy page (Terms, Privacy): readable line length, numbered sections, and the
 * date it last changed. */
export function LegalPage({ title, updated, intro, children }: { title: string; updated: string; intro: ReactNode; children: ReactNode }) {
  return <article className="mx-auto max-w-3xl px-4 py-12 sm:px-6 sm:py-16">
    <h1 className="type-wide text-display font-extrabold leading-tight ">{title}</h1>
    <p className="mt-3 text-label text-muted">Last updated {updated}</p>
    <div className="mt-8 space-y-4 leading-7 text-ink">{intro}</div>
    <div className="mt-10 space-y-10">{children}</div>
  </article>;
}

export function LegalSection({ title, children }: { title: string; children: ReactNode }) {
  return <section className="space-y-4 leading-7">
    <h2 className="type-wide text-title font-extrabold">{title}</h2>
    {children}
  </section>;
}

export function LegalList({ items }: { items: ReactNode[] }) {
  return <ul className="list-disc space-y-2 pl-6 marker:text-muted">{items.map((item, index) => <li key={index}>{item}</li>)}</ul>;
}
