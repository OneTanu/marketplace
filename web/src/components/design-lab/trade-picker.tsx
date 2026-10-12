"use client";

import { useState } from "react";

const ITEMS = [
  { id: 1, title: "Faded zip hoodie", price: "$38", image: "/demo-listings/real/faded-black-zip-hoodie.jpg" },
  { id: 2, title: "Light-wash Levi's", price: "$26", image: "/demo-listings/real/light-wash-jeans.jpg" },
  { id: 3, title: "Timberland boots", price: "$65", image: "/demo-listings/real/timberland-wheat-boots.jpg" },
];

type Pattern = "inline" | "side-by-side" | "wishlist";

function Item({ item, selected, onSelect }: { item: (typeof ITEMS)[number]; selected: boolean; onSelect: () => void }) {
  return (
    <button type="button" onClick={onSelect} aria-pressed={selected} className={`flex w-full items-center gap-3 rounded-lg border p-2 text-left ${selected ? "border-ink ring-1 ring-ink" : "border-line"}`}>
      {/* eslint-disable-next-line @next/next/no-img-element -- local design-lab image. */}
      <img src={item.image} alt="" className="size-14 rounded-md object-cover" />
      <span className="min-w-0 flex-1">
        <span className="block truncate text-sm font-bold">{item.title}</span>
        <span className="text-xs text-muted">{item.price}</span>
      </span>
      <span className={`grid size-5 place-items-center rounded-full border text-xs ${selected ? "border-ink bg-ink text-background" : "border-line"}`}>{selected ? "✓" : ""}</span>
    </button>
  );
}

export function TradePickerMock() {
  const [pattern, setPattern] = useState<Pattern>("inline");
  const [selected, setSelected] = useState<number[]>([1]);
  const [cash, setCash] = useState("10");
  const toggle = (id: number) => setSelected((current) => current.includes(id) ? current.filter((value) => value !== id) : [...current, id]);

  return (
    <div>
      <div className="flex flex-wrap gap-2" role="tablist" aria-label="Trade picker examples">
        {([
          ["inline", "1. Inline picker"],
          ["side-by-side", "2. Side-by-side builder"],
          ["wishlist", "3. Interested-items shortlist"],
        ] as [Pattern, string][]).map(([value, label]) => (
          <button key={value} type="button" role="tab" aria-selected={pattern === value} onClick={() => setPattern(value)} className={`chip ${pattern === value ? "border-ink bg-ink text-background" : ""}`}>{label}</button>
        ))}
      </div>

      {pattern === "inline" && (
        <div className="mt-5 grid gap-5 rounded-xl border border-line p-4 lg:grid-cols-[minmax(0,1fr)_18rem]">
          <div>
            <p className="type-wide text-lg font-black">Pick what you want from @mayasells</p>
            <p className="mt-1 text-sm text-muted">Choose up to five available listings, then adjust cash if the values differ.</p>
            <div className="mt-4 grid gap-2 sm:grid-cols-2">{ITEMS.map((item) => <Item key={item.id} item={item} selected={selected.includes(item.id)} onSelect={() => toggle(item.id)} />)}</div>
          </div>
          <aside className="rounded-lg bg-surface p-4">
            <p className="text-xs font-bold uppercase tracking-wide text-muted">Trade summary</p>
            <p className="mt-2 font-bold">Your leather jacket</p>
            <p className="my-2 text-center text-sm text-muted">for</p>
            <p className="text-sm font-semibold">{selected.length ? `${selected.length} selected item${selected.length === 1 ? "" : "s"}` : "Choose an item"}</p>
            <label className="mt-4 block text-xs font-bold">Cash adjustment<div className="field mt-1 flex h-10 items-center px-3"><span className="text-muted">$</span><input value={cash} onChange={(event) => setCash(event.target.value.replace(/\D/g, ""))} className="min-w-0 flex-1 bg-transparent pl-1 outline-none" /></div></label>
            <button type="button" disabled={!selected.length} className="btn btn-primary mt-4 w-full">Send counter-trade</button>
          </aside>
        </div>
      )}

      {pattern === "side-by-side" && (
        <div className="mt-5 rounded-xl border border-line p-4">
          <div className="grid items-stretch gap-3 md:grid-cols-[1fr_auto_1fr]">
            <div className="rounded-lg bg-surface p-4"><p className="text-xs font-bold uppercase tracking-wide text-muted">They receive</p><p className="mt-2 font-bold">Brown leather jacket</p><p className="text-sm text-muted">Listed at $42</p></div>
            <span className="self-center text-center text-sm font-black text-muted">TRADE FOR</span>
            <div className="rounded-lg bg-surface p-4"><p className="text-xs font-bold uppercase tracking-wide text-muted">You receive</p><p className="mt-2 font-bold">Faded zip hoodie + $10</p><button type="button" className="mt-3 text-sm font-bold underline">Change items</button></div>
          </div>
          <p className="mt-4 text-sm text-muted">Best when both people need to compare the complete package before accepting or countering.</p>
        </div>
      )}

      {pattern === "wishlist" && (
        <div className="mt-5 grid gap-5 rounded-xl border border-line p-4 md:grid-cols-2">
          <div><p className="type-wide text-lg font-black">Items Jordan would trade for</p><p className="mt-1 text-sm text-muted">Jordan marks acceptable items first. Maya can then build a trade from this shorter list.</p><div className="mt-4 space-y-2">{ITEMS.slice(0, 2).map((item) => <Item key={item.id} item={item} selected onSelect={() => undefined} />)}</div></div>
          <div className="rounded-lg bg-surface p-4"><p className="font-bold">Less negotiation, more setup</p><p className="mt-2 text-sm leading-6 text-muted">This is faster during a deal, but asks users to maintain an “open to trade” shortlist on every listing or profile.</p><button type="button" className="btn btn-secondary mt-4">Build from shortlist</button></div>
        </div>
      )}

      <p className="mt-4 text-sm"><strong>Recommended:</strong> the inline picker. It adds the missing choice directly to the existing Deals flow without creating another inbox or requiring users to maintain a wishlist.</p>
    </div>
  );
}
