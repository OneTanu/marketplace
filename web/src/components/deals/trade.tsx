"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import type { components } from "@/lib/api/schema";
import { getTradeOptions, offerTrade, tradePackage } from "@/lib/deals";
import { centsToDollars } from "@/lib/money";

type Deal = components["schemas"]["Deal"];
type DealListing = components["schemas"]["DealListing"];
type CashPayer = "buyer" | "seller";

const MAX_ITEMS = 5;

function ItemThumb({ item }: { item: DealListing }) {
  return (
    <span className="block size-12 shrink-0 overflow-hidden rounded-md bg-surface">
      {item.cover_url ? (
        // eslint-disable-next-line @next/next/no-img-element -- uploaded media is runtime data.
        <img src={item.cover_url} alt="" className="size-full object-cover" />
      ) : (
        <span className="grid size-full place-items-center text-[10px] font-semibold text-muted">No photo</span>
      )}
    </span>
  );
}

/** Who pays the cash, from the viewer's side: "you add $15" or "@sam adds $15". */
function cashLine(deal: Deal, amountCents: number, payer: string) {
  if (!amountCents) return null;
  const payerName = payer === "buyer" ? deal.buyer.username : deal.seller.username;
  const mine = payer === deal.my_role;
  return mine ? `You add ${centsToDollars(amountCents)}` : `@${payerName} adds ${centsToDollars(amountCents)}`;
}

/** The trade package on the table, or what's still missing. */
export function TradeSummary({ deal, compact = false }: { deal: Deal; compact?: boolean }) {
  const offer = tradePackage(deal);
  if (!offer) {
    return (
      <p className="text-sm text-muted">
        {deal.my_role === "seller"
          ? `@${deal.buyer.username} wants to trade for this. Look through their listings and pick what you'd take, adding cash if needed.`
          : `Waiting for @${deal.seller.username} to pick items from your listings.`}
      </p>
    );
  }
  const cash = cashLine(deal, offer.amount_cents, offer.cash_payer ?? "");
  const proposer = offer.offered_by.id === (deal.my_role === "seller" ? deal.seller.id : deal.buyer.id) ? "You" : `@${offer.offered_by.username}`;
  return (
    <div className="text-sm">
      <p className="font-bold">
        {deal.status === "pending" || deal.status === "completed" ? "Agreed trade" : `${proposer} offered`}: {deal.listing.title} for
      </p>
      <ul className={`mt-2 grid gap-2 ${compact ? "" : "sm:grid-cols-2"}`}>
        {offer.trade_items.map((item) => (
          <li key={item.id} className="flex items-center gap-2">
            <ItemThumb item={item} />
            <span className="min-w-0">
              <Link href={`/listings/${item.id}`} className="block truncate font-semibold hover:underline">{item.title}</Link>
              <span className="text-xs text-muted">Listed at {centsToDollars(item.price_cents)}</span>
            </span>
          </li>
        ))}
      </ul>
      {cash && <p className="mt-2 font-semibold">+ {cash}</p>}
    </div>
  );
}

/** Pick the buyer's items (and optional cash) for a trade package. */
export function TradeBuilder({
  deal,
  meetupProposalId,
  onDone,
  onCancel,
}: {
  deal: Deal;
  meetupProposalId?: number;
  onDone: (deal: Deal) => void;
  onCancel: () => void;
}) {
  const current = tradePackage(deal);
  const [items, setItems] = useState<DealListing[] | null>();
  const [selected, setSelected] = useState<number[]>(() => current?.trade_items.map((item) => item.id) ?? []);
  const [cash, setCash] = useState(() => (current?.amount_cents ? String(current.amount_cents / 100) : ""));
  const [payer, setPayer] = useState<CashPayer>(() => (current?.cash_payer === "seller" ? "seller" : "buyer"));
  const [working, setWorking] = useState(false);
  const [error, setError] = useState("");
  const other = deal.my_role === "seller" ? deal.buyer : deal.seller;

  useEffect(() => {
    let active = true;
    getTradeOptions(deal.id)
      .then((data) => active && setItems(data))
      .catch(() => active && setItems(null));
    return () => {
      active = false;
    };
  }, [deal.id]);

  function toggle(id: number) {
    setSelected((current) =>
      current.includes(id) ? current.filter((item) => item !== id) : current.length < MAX_ITEMS ? [...current, id] : current,
    );
  }

  async function submit() {
    const cashCents = cash ? Math.round(Number(cash) * 100) : 0;
    if (!Number.isFinite(cashCents) || cashCents < 0) {
      setError("Enter a cash amount, or leave it empty.");
      return;
    }
    if (selected.length === 0) {
      setError("Choose at least one item.");
      return;
    }
    setWorking(true);
    setError("");
    try {
      onDone(
        await offerTrade(deal.id, {
          trade_item_ids: selected,
          cash_cents: cashCents,
          cash_payer: cashCents ? payer : "",
          ...(meetupProposalId ? { meetup_proposal_id: meetupProposalId } : {}),
        }),
      );
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "The trade offer did not go through.");
    } finally {
      setWorking(false);
    }
  }

  const iAm = deal.my_role as CashPayer;
  const theyAre: CashPayer = iAm === "seller" ? "buyer" : "seller";

  return (
    <div className="mt-3 border-t border-line pt-3">
      <p className="font-bold">
        {current
          ? "Counter with a different trade"
          : deal.my_role === "seller"
            ? `Pick from @${deal.buyer.username}'s listings`
            : "Choose which of your items to offer"}
      </p>
      <p className="mt-1 text-sm text-muted">
        Choose up to {MAX_ITEMS} items{deal.my_role === "seller" ? " you'd take" : " you'll give"} for {deal.listing.title}.{" "}
        {deal.my_role === "seller" && <Link href={`/users/${deal.buyer.username}`} className="font-semibold underline">See their profile</Link>}
      </p>

      {items === undefined && <div className="mt-3 h-24 animate-pulse rounded-lg bg-surface" aria-label="Loading listings" />}
      {items === null && <p className="mt-3 text-sm text-muted">Couldn&apos;t load their listings. Try again.</p>}
      {items && items.length === 0 && (
        <p className="mt-3 rounded-lg bg-surface p-3 text-sm text-muted">@{deal.buyer.username} has no available listings to trade right now.</p>
      )}
      {items && items.length > 0 && (
        <div className="mt-3 grid items-start gap-4 lg:grid-cols-[minmax(0,1fr)_17rem]">
          <fieldset>
            <legend className="sr-only">Items for the trade</legend>
            <div className="grid gap-2">
              {items.map((item) => (
                <label key={item.id} className={`flex min-w-0 cursor-pointer items-center gap-3 rounded-lg border p-2 has-[:focus-visible]:outline has-[:focus-visible]:outline-2 has-[:focus-visible]:outline-offset-2 has-[:focus-visible]:outline-[var(--brand)] ${selected.includes(item.id) ? "border-ink ring-1 ring-ink" : "border-line"}`}>
                  <input type="checkbox" checked={selected.includes(item.id)} onChange={() => toggle(item.id)} className="sr-only" />
                  <span className="relative block size-12 shrink-0">
                    <ItemThumb item={item} />
                    <span className={`absolute -left-1 -top-1 grid size-5 place-items-center rounded-full border text-xs font-bold ${selected.includes(item.id) ? "border-ink bg-ink text-background" : "border-line bg-background"}`} aria-hidden="true">
                      {selected.includes(item.id) ? "✓" : ""}
                    </span>
                  </span>
                  <span className="min-w-0 flex-1 text-sm">
                    <span className="block truncate font-semibold" title={item.title}>{item.title}</span>
                    <span className="mt-0.5 block text-xs text-muted">Listed at {centsToDollars(item.price_cents)}</span>
                  </span>
                </label>
              ))}
            </div>
          </fieldset>

          <aside className="rounded-lg bg-surface p-3" aria-label="Trade summary">
            <p className="text-xs font-bold uppercase tracking-wide text-muted">Trade summary</p>
            <p className="mt-2 text-sm font-bold">{deal.listing.title}</p>
            <p className="my-2 text-center text-xs font-bold text-muted">FOR</p>
            {selected.length ? (
              <ul className="space-y-1 text-sm">
                {items.filter((item) => selected.includes(item.id)).map((item) => <li key={item.id} className="truncate font-semibold">{item.title}</li>)}
              </ul>
            ) : <p className="text-sm text-muted">Choose at least one item.</p>}
            {cash && Number(cash) > 0 && <p className="mt-2 text-sm font-semibold">+ {payer === iAm ? "You" : `@${other.username}`} add{payer === iAm ? "" : "s"} ${cash}</p>}
          </aside>
        </div>
      )}

      <fieldset className="mt-3">
        <legend className="text-sm font-bold">Add cash (optional)</legend>
        <div className="mt-2 flex flex-wrap items-center gap-2">
          <label className="field flex h-10 w-32 items-center px-3">
            <span className="text-muted">$</span>
            <input value={cash} onChange={(event) => setCash(event.target.value.replace(/[^0-9.]/g, ""))} inputMode="decimal" aria-label="Cash amount" className="min-w-0 flex-1 bg-transparent pl-1 outline-none" />
          </label>
          <div className="flex rounded-lg bg-surface p-1 text-sm" role="group" aria-label="Who adds the cash">
            {([theyAre, iAm] as CashPayer[]).map((value) => (
              <button key={value} type="button" onClick={() => setPayer(value)} aria-pressed={payer === value} className={`rounded-md px-3 py-1.5 font-semibold ${payer === value ? "bg-background shadow-sm" : "text-muted"}`}>
                {value === iAm ? "I add it" : `@${other.username} adds it`}
              </button>
            ))}
          </div>
        </div>
      </fieldset>

      {error && <p role="alert" className="mt-3 text-sm text-[var(--danger)]">{error}</p>}
      <div className="mt-3 flex gap-2">
        <button type="button" onClick={onCancel} disabled={working} className="btn btn-secondary flex-1">Back</button>
        <button type="button" onClick={submit} disabled={working || !items?.length} className="btn btn-primary flex-1">
          {working ? "Sending…" : "Send trade offer"}
        </button>
      </div>
    </div>
  );
}
