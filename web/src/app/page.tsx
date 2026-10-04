import Link from "next/link";

const features = [
  { number: "01", title: "Verified students", text: "Every account starts with a supported school email." },
  { number: "02", title: "Local by default", text: "See items from your campus community, not across the country." },
  { number: "03", title: "Simple handoffs", text: "Message, make an offer, and meet somewhere that works for both of you." },
];

export default function HomePage() {
  return <div className="overflow-hidden">
    <section className="relative mx-auto grid min-h-[650px] max-w-6xl items-center gap-12 px-4 py-16 sm:px-6 lg:grid-cols-[1.08fr_.92fr] lg:py-24">
      <div className="animate-in relative z-10 max-w-2xl">
        <div className="mb-6 inline-flex items-center gap-2 rounded-full border border-forest/15 bg-[var(--forest-soft)] px-3 py-1.5 text-xs font-bold uppercase tracking-[0.16em] text-forest"><span className="size-2 rounded-full bg-[#36a269]" />For verified university students</div>
        <h1 className="text-5xl font-black leading-[.98] tracking-[-0.06em] text-foreground sm:text-6xl lg:text-[76px]">Campus finds,<span className="block text-brand">without the noise.</span></h1>
        <p className="mt-7 max-w-xl text-lg leading-8 text-muted sm:text-xl">Buy and sell with verified students at your school. Less scrolling, easier meetups, better finds.</p>
        <div className="mt-9 flex flex-col gap-3 sm:flex-row">
          <Link href="/account/signup" className="rounded-full bg-foreground px-6 py-3.5 text-center text-sm font-bold text-white shadow-[0_10px_30px_rgb(20_35_29/18%)] transition hover:-translate-y-0.5 hover:bg-forest">Join with your school email</Link>
          <Link href="/account/login" className="rounded-full border border-line bg-white/65 px-6 py-3.5 text-center text-sm font-bold text-foreground transition hover:bg-white">I already have an account</Link>
        </div>
        <p className="mt-5 flex items-center gap-2 text-sm text-muted"><span className="text-forest">●</span> Free to join · Student email required</p>
      </div>
      <div className="relative mx-auto w-full max-w-lg lg:max-w-none">
        <div className="absolute -inset-16 -z-10 rounded-full bg-brand/10 blur-3xl" />
        <div className="rotate-2 rounded-[2rem] border border-white/80 bg-white/85 p-4 shadow-[0_30px_80px_rgb(50_56_49/18%)] backdrop-blur"><div className="rounded-[1.4rem] bg-[#dce9df] p-5">
          <div className="mb-5 flex items-center justify-between"><div><p className="text-xs font-bold uppercase tracking-[.16em] text-forest/65">Just listed</p><p className="mt-1 font-bold text-forest">Your school marketplace</p></div><span className="rounded-full bg-white/75 px-3 py-1.5 text-xs font-semibold text-forest">Verified students</span></div>
          <div className="grid grid-cols-2 gap-3"><article className="rounded-2xl bg-[#f6b980] p-3 pt-28 shadow-sm"><div className="rounded-xl bg-white/90 p-3"><p className="font-bold">Vintage crewneck</p><p className="mt-1 text-sm text-muted">$24 · Like new</p></div></article><article className="rounded-2xl bg-[#92aeb7] p-3 pt-28 shadow-sm"><div className="rounded-xl bg-white/90 p-3"><p className="font-bold">Desk lamp</p><p className="mt-1 text-sm text-muted">$12 · Good</p></div></article></div>
        </div></div>
        <div className="absolute -bottom-6 -left-4 -rotate-3 rounded-2xl border border-line bg-[#fffdf8] p-4 shadow-xl sm:-left-10"><p className="text-xs font-bold uppercase tracking-wider text-muted">School verified</p><p className="mt-1 font-bold text-forest">✓ Student account</p></div>
      </div>
    </section>
    <section className="border-y border-line bg-[#fffdf8]"><div className="mx-auto grid max-w-6xl gap-px bg-line sm:grid-cols-3">{features.map((feature) => <article key={feature.number} className="bg-[#fffdf8] px-6 py-10 sm:px-8"><span className="font-mono text-xs font-bold text-brand">{feature.number}</span><h2 className="mt-6 text-xl font-bold tracking-tight">{feature.title}</h2><p className="mt-2 leading-6 text-muted">{feature.text}</p></article>)}</div></section>
  </div>;
}
