/** Stand-in page body until the owning workstream builds the real screen. */
export function Placeholder({ title, note }: { title: string; note: string }) {
  return (
    <section className="mx-auto w-full max-w-6xl px-4 py-6">
      <h1 className="text-2xl font-semibold tracking-tight">{title}</h1>
      <p className="mt-2 text-sm text-foreground/60">{note}</p>
    </section>
  );
}
