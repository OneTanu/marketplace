"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";

import { MeetupPicker, type MeetupSelection } from "@/components/deals/meetup-picker";
import { TradeBuilder, TradeSummary } from "@/components/deals/trade";
import { ReportButton } from "@/components/trust/report";
import type { components } from "@/lib/api/schema";
import {
  acceptMeetup,
  actOnDeal,
  counterDeal,
  DEAL_STATUS_LABELS,
  dealNextStep,
  getDeal,
  listDeals,
  meetupState,
  PROBLEM_KINDS,
  proposeMeetup,
  reportDealProblem,
  setDealArchived,
  tradePackage,
  updateMeetupStatus,
  type DealProblemKind,
} from "@/lib/deals";
import { centsToDollars } from "@/lib/money";
import { formatDateTime } from "@/lib/time";

type Deal = components["schemas"]["Deal"];
type Role = "buyer" | "seller";


function deadline(value: string | null | undefined) {
  return value ? formatDateTime(value) : "";
}

function statusLabel(deal: Deal) {
  if (deal.status === "canceled" && deal.events.some((event) => event.event_type === "canceled_by_moderation")) {
    return "Canceled by Tanu";
  }
  if (deal.kind === "trade" && deal.awaiting_me) {
    return tradePackage(deal) ? "Trade offer — your response" : "Trade request — pick items";
  }
  if (deal.awaiting_me) {
    if (deal.status === "awaiting_buyer") return "Seller countered — your response";
    return "Needs your response";
  }
  if (deal.status === "backup" && deal.backup_position) return `Backup buyer · #${deal.backup_position} in line`;
  if (deal.status === "canceled" && deal.close_reason === "no_show_reported") return "Canceled · no-show reported";
  return DEAL_STATUS_LABELS[deal.status];
}

/** Report a no-show or another problem with an accepted deal. */
function ProblemReporter({ deal, onDone, onCancel }: { deal: Deal; onDone: (deal: Deal) => void; onCancel: () => void }) {
  const [kind, setKind] = useState<DealProblemKind>("no_show");
  const [details, setDetails] = useState("");
  const [working, setWorking] = useState(false);
  const [error, setError] = useState("");
  const confirmed = deal.buyer_confirmed || deal.seller_confirmed;

  async function submit() {
    setWorking(true);
    setError("");
    try {
      onDone(await reportDealProblem(deal.id, kind, details));
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Your report didn’t go through.");
    } finally {
      setWorking(false);
    }
  }

  return (
    <div className="mt-3 border-t border-line pt-3" role="group" aria-label="Report a problem">
      <p className="font-bold">Report a problem</p>
      <p className="mt-1 text-sm text-muted">
        {deal.status === "pending" && confirmed
          ? "Someone already confirmed this handoff, so a moderator will review it before anything changes."
          : deal.status === "pending" && kind === "no_show"
            ? "Reporting a no-show ends this deal and makes the item available again."
            : "Tanu’s moderators will review it. Nobody is penalized automatically."}
      </p>
      <label className="mt-3 block text-sm font-bold">What happened?
        <select value={kind} onChange={(event) => setKind(event.target.value as DealProblemKind)} className="field mt-2 h-11 px-3 text-sm font-normal">
          {PROBLEM_KINDS.map((option) => <option key={option.value} value={option.value} disabled={deal.my_problems.includes(option.value)}>{option.label}</option>)}
        </select>
      </label>
      <label className="mt-3 block text-sm font-bold">Details <span className="font-normal text-muted">Optional</span>
        <textarea value={details} onChange={(event) => setDetails(event.target.value)} maxLength={1000} rows={3} className="mt-2 w-full resize-none rounded-xl border border-line bg-white px-3 py-2 text-sm font-normal outline-none focus:border-brand" />
      </label>
      {error && <p role="alert" className="mt-2 text-sm text-[var(--danger)]">{error}</p>}
      <div className="mt-3 flex gap-2">
        <button type="button" onClick={onCancel} disabled={working} className="btn btn-secondary btn-sm">Back</button>
        <button type="button" onClick={submit} disabled={working || deal.my_problems.includes(kind)} className="btn btn-primary btn-sm">{working ? "Sending…" : "Send report"}</button>
      </div>
    </div>
  );
}

function DealCard({ deal, onChange }: { deal: Deal; onChange: (deal: Deal) => void }) {
  const [working, setWorking] = useState(false);
  const [countering, setCountering] = useState(false);
  const [counter, setCounter] = useState("");
  const [error, setError] = useState("");
  const [rescheduling, setRescheduling] = useState(false);
  const [trading, setTrading] = useState(false);
  const [reporting, setReporting] = useState(false);
  const isTrade = deal.kind === "trade";
  const tradeOffer = tradePackage(deal);
  const [meetupSelection, setMeetupSelection] = useState<MeetupSelection>({ meetingSpotId: null, startsAt: [], configured: false, loading: true });
  const [now] = useState(() => Date.now());
  const meetups = meetupState(deal, now);
  const acceptedMeetup = meetups.accepted;
  const pendingFromOther = meetups.fromOther[0];
  const pendingFromMe = meetups.fromMe[0];
  const [chosenProposalId, setMeetupProposalId] = useState<number | undefined>();
  // Fall back to the first time on offer if the chosen one was replaced.
  const meetupProposalId = meetups.fromOther.some((proposal) => proposal.id === chosenProposalId)
    ? chosenProposalId
    : pendingFromOther?.id;
  const negotiating = deal.status === "awaiting_seller" || deal.status === "awaiting_buyer";
  const latestMeetupUpdate = deal.meetup_updates[0];
  const counterpart = deal.my_role === "seller" ? deal.buyer : deal.seller;
  const open = deal.section === "current";
  const can = deal.actions;
  const due = deal.status === "pending" ? deal.handoff_deadline : deal.response_deadline;

  async function archive(archived: boolean) {
    setWorking(true);
    setError("");
    try {
      onChange(await setDealArchived(deal.id, archived));
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "That didn’t go through.");
    } finally {
      setWorking(false);
    }
  }

  async function run(action: "accept" | "decline" | "cancel" | "confirm-handoff") {
    setWorking(true);
    setError("");
    try {
      onChange(
        await actOnDeal(
          deal.id,
          action,
          action === "accept" ? meetupProposalId : undefined,
        ),
      );
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "That action did not go through.");
    } finally {
      setWorking(false);
    }
  }

  async function setMeetupStatus(kind: "running_late" | "arrived", minutesLate?: number) {
    setWorking(true);
    setError("");
    try {
      const update = await updateMeetupStatus(deal.id, {
        kind,
        ...(minutesLate ? { minutes_late: minutesLate } : {}),
      });
      onChange({ ...deal, meetup_updates: [update, ...deal.meetup_updates] });
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "That meetup update did not go through.");
    } finally {
      setWorking(false);
    }
  }

  async function submitReschedule() {
    if (meetupSelection.meetingSpotId === null || meetupSelection.startsAt.length === 0) {
      setError("Choose a meetup location and time.");
      return;
    }
    setWorking(true);
    setError("");
    try {
      await proposeMeetup(deal.id, {
        meeting_spot_id: meetupSelection.meetingSpotId,
        starts_at: meetupSelection.startsAt[0],
      });
      // Suggesting a time while it's your turn hands the turn over, so reload the deal.
      onChange(await getDeal(deal.id));
      setRescheduling(false);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "The reschedule request did not go through.");
    } finally {
      setWorking(false);
    }
  }

  async function approveReschedule() {
    if (!pendingFromOther) return;
    setWorking(true);
    setError("");
    try {
      const accepted = await acceptMeetup(deal.id, pendingFromOther.id);
      onChange({
        ...deal,
        meetup_proposals: deal.meetup_proposals.map((proposal) =>
          proposal.id === accepted.id
            ? accepted
            : proposal.status === "accepted"
              ? { ...proposal, status: "superseded" }
              : proposal,
        ),
      });
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "The new meetup time could not be accepted.");
    } finally {
      setWorking(false);
    }
  }

  async function submitCounter() {
    const amountCents = Math.round(Number(counter) * 100);
    if (!Number.isFinite(amountCents) || amountCents < 1) {
      setError("Enter an amount of at least $0.01.");
      return;
    }
    setWorking(true);
    setError("");
    try {
      onChange(await counterDeal(deal.id, amountCents, meetupProposalId));
      setCountering(false);
      setCounter("");
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "The counteroffer did not go through.");
    } finally {
      setWorking(false);
    }
  }

  return (
    <article className={`rounded-xl border p-4 ${deal.awaiting_me ? "border-signal bg-[var(--brand-soft)]/35" : "border-line bg-background"}`}>
      <div className="flex gap-3">
        <Link href={`/listings/${deal.listing.id}`} className="size-20 shrink-0 overflow-hidden rounded-lg bg-surface">
          {deal.listing.cover_url ? (
            // eslint-disable-next-line @next/next/no-img-element -- uploaded media is runtime data.
            <img src={deal.listing.cover_url} alt="" className="size-full object-cover" />
          ) : (
            <span className="grid size-full place-items-center text-xs font-semibold text-muted">No photo</span>
          )}
        </Link>
        <div className="min-w-0 flex-1">
          <div className="flex items-start justify-between gap-3">
            <div className="min-w-0">
              <Link href={`/listings/${deal.listing.id}`} className="block truncate font-bold hover:underline">{deal.listing.title}</Link>
              <p className="mt-0.5 text-sm text-muted">
                {deal.my_role === "seller" ? "Buyer" : "Seller"}: <Link href={`/users/${counterpart.username}`} className="font-semibold text-ink hover:underline">@{counterpart.username}</Link>
              </p>
            </div>
            <p className="type-wide shrink-0 text-lg font-black">{isTrade ? "Trade" : centsToDollars(deal.agreed_amount_cents ?? deal.current_amount_cents)}</p>
          </div>
          <div className="mt-2 flex flex-wrap items-center gap-2 text-xs">
            <span className={`rounded-full px-2.5 py-1 font-bold ${deal.awaiting_me ? "bg-signal text-white" : "bg-surface text-ink"}`}>{statusLabel(deal)}</span>
            <span className="text-muted">{deal.kind === "buy_now" ? "Buy now" : deal.kind === "trade" ? "Trade" : "Offer"}</span>
            {deal.asap && <span className="rounded-full bg-[var(--brand-soft)] px-2.5 py-1 font-bold text-brand">ASAP</span>}
            {due && open && <span className="text-muted">Due {deadline(due)}</span>}
          </div>
        </div>
      </div>

      {isTrade && (
        <div className="mt-3 rounded-lg bg-surface p-3">
          <TradeSummary deal={deal} />
        </div>
      )}
      {deal.asap && deal.my_role === "seller" && open && deal.status !== "pending" && (
        <p className="mt-3 text-sm font-semibold text-brand">@{deal.buyer.username} wants to meet as soon as possible. The earliest time works best.</p>
      )}
      {deal.status === "pending" && (
        <div className="mt-3 rounded-lg bg-surface p-3 text-sm">
          {acceptedMeetup ? (
            <>
              <p className="font-bold text-ink">{acceptedMeetup.meeting_spot.name}</p>
              <p className="mt-0.5 text-muted">{deadline(acceptedMeetup.starts_at)} · {acceptedMeetup.meeting_spot.directions}</p>
            </>
          ) : (
            <p className="font-semibold text-muted">Meetup time still needs to be confirmed.</p>
          )}
          <p className="mt-2 text-muted">Buyer {deal.buyer_confirmed ? "confirmed" : "not confirmed"} · Seller {deal.seller_confirmed ? "confirmed" : "not confirmed"}</p>
          <p className="mt-1 text-xs text-muted">Payment happens in person between you. Tanu doesn’t handle or verify it.{deal.handoff_extensions > 0 ? " The deadline was extended once for a reschedule." : ""}</p>
        </div>
      )}
      {deal.status === "disputed" && (
        <div role="status" className="mt-3 rounded-lg border border-line bg-surface p-3 text-sm">
          <p className="font-bold">Under review by Tanu</p>
          <p className="mt-1 text-muted">The handoff couldn’t be settled automatically, so a moderator will decide whether it happened. The listing stays on hold until then.</p>
        </div>
      )}
      {deal.dispute?.outcome && (
        <p className="mt-3 rounded-lg bg-surface p-3 text-sm text-muted">A moderator reviewed this handoff and decided {deal.dispute.outcome === "completed" ? "it happened" : "it didn’t happen"}.</p>
      )}
      {open && <p className="mt-3 text-sm text-ink">{dealNextStep(deal)}</p>}
      {deal.status === "pending" && pendingFromOther && (
        <div className="mt-3 rounded-lg border border-signal bg-[var(--brand-soft)]/35 p-3 text-sm">
          <p className="font-bold">New meetup proposed</p>
          <p className="mt-1 text-muted">{pendingFromOther.meeting_spot.name} · {deadline(pendingFromOther.starts_at)}</p>
          <button type="button" onClick={approveReschedule} disabled={working} className="btn btn-primary btn-sm mt-3">Accept new meetup</button>
        </div>
      )}
      {(deal.status === "pending" || (negotiating && !deal.awaiting_me)) && pendingFromMe && (
        <p className="mt-3 rounded-lg bg-surface p-3 text-sm text-muted">Waiting for @{counterpart.username} to respond to your proposed meetup: {meetups.fromMe.map((proposal) => deadline(proposal.starts_at)).join(" or ")}.</p>
      )}
      {deal.status === "pending" && latestMeetupUpdate && (
        <p className="mt-3 text-sm font-semibold text-ink">
          @{latestMeetupUpdate.actor.username} {latestMeetupUpdate.kind === "arrived" ? "is here." : `is running about ${latestMeetupUpdate.minutes_late} minutes late.`}
        </p>
      )}

      {deal.awaiting_me && meetups.fromOther.length > 0 && (
        <fieldset className="mt-3">
          <legend className="text-sm font-bold">
            {meetups.fromOther.length > 1 ? "Choose a meetup time" : "Proposed meetup"}
          </legend>
          <p className="mt-1 text-xs text-muted">Accepting or countering keeps this time.</p>
          <div className="mt-2 flex flex-wrap gap-2">
            {meetups.fromOther.map((proposal) => (
              <button key={proposal.id} type="button" onClick={() => setMeetupProposalId(proposal.id)} aria-pressed={meetupProposalId === proposal.id} className={`rounded-lg border px-3 py-2 text-left text-sm ${meetupProposalId === proposal.id ? "border-ink bg-surface ring-1 ring-ink" : "border-line"}`}>
                <span className="block font-bold">{deadline(proposal.starts_at)}</span>
                <span className="block text-xs text-muted">{proposal.meeting_spot.name}</span>
              </button>
            ))}
          </div>
        </fieldset>
      )}
      {deal.awaiting_me && meetups.allStale && (
        <p className="mt-3 rounded-lg border border-signal p-3 text-sm">The proposed meetup times have passed. Suggest a new time before accepting.</p>
      )}
      {error && <p role="alert" className="mt-3 text-sm text-[var(--danger)]">{error}</p>}

      {reporting ? (
        <ProblemReporter deal={deal} onDone={(updated) => { onChange(updated); setReporting(false); }} onCancel={() => setReporting(false)} />
      ) : trading ? (
        <TradeBuilder
          deal={deal}
          meetupProposalId={meetupProposalId}
          onDone={(updated) => { onChange(updated); setTrading(false); }}
          onCancel={() => setTrading(false)}
        />
      ) : countering ? (
        <div className="mt-3 flex flex-wrap gap-2">
          <label className="field flex h-10 min-w-40 flex-1 items-center px-3">
            <span className="text-muted">$</span>
            <input value={counter} onChange={(event) => setCounter(event.target.value.replace(/[^0-9.]/g, ""))} inputMode="decimal" autoFocus aria-label="Counteroffer amount" className="min-w-0 flex-1 bg-transparent pl-1 outline-none" />
          </label>
          <button type="button" onClick={submitCounter} disabled={working} className="btn btn-primary btn-sm">Send counter</button>
          <button type="button" onClick={() => setCountering(false)} disabled={working} className="btn btn-secondary btn-sm">Back</button>
        </div>
      ) : rescheduling ? (
        <div className="mt-3 border-t border-line pt-3">
          <p className="font-bold">{acceptedMeetup ? "Propose a new meetup" : "Suggest a meetup time"}</p>
          <p className="mt-1 text-sm text-muted">
            {acceptedMeetup
              ? "The current meetup stays confirmed until the other person accepts this change."
              : negotiating && deal.awaiting_me
                ? `This replaces the proposed times, and @${counterpart.username} will need to respond.`
                : `@${counterpart.username} will need to accept this time.`}
          </p>
          <MeetupPicker listingId={deal.listing.id} allowTwo={false} onChange={setMeetupSelection} />
          <div className="mt-3 flex gap-2">
            <button type="button" onClick={() => setRescheduling(false)} disabled={working} className="btn btn-secondary flex-1">Back</button>
            <button type="button" onClick={submitReschedule} disabled={working || meetupSelection.loading || !meetupSelection.configured} className="btn btn-primary flex-1">Send change</button>
          </div>
        </div>
      ) : (
        <div className="mt-3 flex flex-wrap gap-2 border-t border-line pt-3">
          {can.counter && isTrade && !tradeOffer && (
            <button type="button" onClick={() => setTrading(true)} disabled={working} className="btn btn-primary btn-sm">Pick items</button>
          )}
          {can.accept && (!isTrade || tradeOffer) && <button type="button" onClick={() => run("accept")} disabled={working} className="btn btn-primary btn-sm">Accept</button>}
          {can.counter && (!isTrade || tradeOffer) && <button type="button" onClick={() => (isTrade ? setTrading(true) : setCountering(true))} disabled={working} className="btn btn-secondary btn-sm">Counter</button>}
          {can.decline && <button type="button" onClick={() => run("decline")} disabled={working} className="btn btn-secondary btn-sm">{deal.status === "backup" ? "Remove from line" : "Decline"}</button>}
          {can.confirm_handoff && <button type="button" onClick={() => run("confirm-handoff")} disabled={working} className="btn btn-primary btn-sm">Confirm handoff</button>}
          {deal.status === "pending" && acceptedMeetup && (
            <>
              {[5, 10, 15].map((minutes) => <button key={minutes} type="button" onClick={() => setMeetupStatus("running_late", minutes)} disabled={working} className="btn btn-quiet btn-sm">{minutes} min late</button>)}
              <button type="button" onClick={() => setMeetupStatus("arrived")} disabled={working} className="btn btn-quiet btn-sm">I&apos;m here</button>
            </>
          )}
          {((deal.status === "pending" && !pendingFromOther && !pendingFromMe) || negotiating) && (
            <button type="button" onClick={() => setRescheduling(true)} disabled={working} className="btn btn-quiet btn-sm">
              {acceptedMeetup ? "Reschedule" : negotiating && !deal.awaiting_me ? "Change my time" : "Suggest another time"}
            </button>
          )}
          {can.cancel && <button type="button" onClick={() => run("cancel")} disabled={working} className="btn btn-secondary btn-sm">{deal.status === "backup" ? "Leave the line" : `Cancel ${deal.status === "pending" ? "purchase" : "request"}`}</button>}
          {can.report_problem && <button type="button" onClick={() => setReporting(true)} disabled={working} className="btn btn-quiet btn-sm">Report a problem</button>}
          {can.archive && <button type="button" onClick={() => archive(true)} disabled={working} className="btn btn-quiet btn-sm">Archive</button>}
          {can.unarchive && <button type="button" onClick={() => archive(false)} disabled={working} className="btn btn-quiet btn-sm">Move back to Cancelled</button>}
          <Link href={`/inbox/${deal.conversation}?listing=${deal.listing.id}`} className="btn btn-quiet btn-sm">Message</Link>
          {!can.report_problem && <ReportButton targetType="deal" targetId={deal.id} subject="this deal" username={counterpart.username} className="btn btn-quiet btn-sm" />}
        </div>
      )}
    </article>
  );
}

function DealSection({ title, description, deals, onChange, empty }: { title: string; description?: string; deals: Deal[]; onChange: (deal: Deal) => void; empty: string }) {
  return (
    <section className="mt-8">
      <div className="flex items-end justify-between gap-4 border-b border-line pb-3">
        <div>
          <h2 className="type-wide text-xl font-black">{title}</h2>
          {description && <p className="mt-1 text-sm text-muted">{description}</p>}
        </div>
        <span className="text-sm font-semibold text-muted">{deals.length}</span>
      </div>
      {deals.length ? <div className="mt-4 grid gap-3 lg:grid-cols-2">{deals.map((deal) => <DealCard key={deal.id} deal={deal} onChange={onChange} />)}</div> : <p className="rounded-xl bg-surface px-5 py-8 text-center text-sm text-muted">{empty}</p>}
    </section>
  );
}

function CollapsedSection({ title, description, deals, onChange, empty }: { title: string; description: string; deals: Deal[]; onChange: (deal: Deal) => void; empty: string }) {
  return (
    <details className="group mt-8 border-y border-line py-1">
      <summary className="flex cursor-pointer list-none items-center justify-between gap-4 py-4 [&::-webkit-details-marker]:hidden">
        <div>
          <h2 className="type-wide text-lg font-black">{title}</h2>
          <p className="mt-1 text-sm text-muted">{description}</p>
        </div>
        <span className="flex shrink-0 items-center gap-2 text-sm font-semibold text-muted">
          {deals.length}
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} className="size-4 transition group-open:rotate-180" aria-hidden="true"><path d="m6 9 6 6 6-6" /></svg>
        </span>
      </summary>
      {deals.length ? (
        <div className="grid gap-3 pb-5 lg:grid-cols-2">{deals.map((deal) => <DealCard key={deal.id} deal={deal} onChange={onChange} />)}</div>
      ) : (
        <p className="pb-5 text-sm text-muted">{empty}</p>
      )}
    </details>
  );
}

export function DealsClient() {
  const [deals, setDeals] = useState<Deal[] | null>();
  const [role, setRole] = useState<Role | null>(null);

  useEffect(() => {
    let active = true;
    async function refresh() {
      try {
        const items = await listDeals();
        if (!active) return;
        setDeals(items);
        setRole((current) => current ?? (items.some((deal) => deal.my_role === "seller" && deal.awaiting_me) ? "seller" : "buyer"));
      } catch {
        if (active) setDeals(null);
      }
    }
    void refresh();
    const timer = window.setInterval(refresh, 8_000);
    return () => { active = false; window.clearInterval(timer); };
  }, []);

  const visible = useMemo(() => deals?.filter((deal) => deal.my_role === role) ?? [], [deals, role]);
  // Current first puts what needs the viewer's answer at the top.
  const current = visible.filter((deal) => deal.section === "current").sort((a, b) => Number(b.awaiting_me) - Number(a.awaiting_me));
  const history = visible.filter((deal) => deal.section === "history");
  const cancelled = visible.filter((deal) => deal.section === "cancelled");
  const archived = visible.filter((deal) => deal.section === "archived");
  const buyingCount = deals?.filter((deal) => deal.my_role === "buyer" && deal.section === "current").length ?? 0;
  const sellingCount = deals?.filter((deal) => deal.my_role === "seller" && deal.section === "current").length ?? 0;

  function update(updated: Deal) {
    setDeals((current) => current?.map((deal) => deal.id === updated.id ? updated : deal) ?? [updated]);
    // One deal's change can move others on the same listing (accepting one buyer makes the
    // rest backups), so reload them all rather than wait for the next poll.
    listDeals().then(setDeals, () => {});
  }

  if (deals === undefined) return <main className="mx-auto min-h-[70vh] max-w-5xl animate-pulse px-4 py-10 sm:px-6"><div className="h-9 w-36 rounded bg-surface" /><div className="mt-8 grid gap-3 lg:grid-cols-2"><div className="h-40 rounded-xl bg-surface" /><div className="h-40 rounded-xl bg-surface" /></div></main>;
  if (deals === null) return <main className="mx-auto grid min-h-[70vh] max-w-xl place-items-center px-4 text-center"><div><h1 className="type-wide text-3xl font-black">Log in to see your deals</h1><p className="mt-3 text-muted">Offers, purchase requests, and transaction history are tied to your verified account.</p><Link href="/account/login" className="btn btn-primary mt-6">Log in</Link></div></main>;

  return (
    <main className="mx-auto min-h-[70vh] max-w-5xl px-4 py-8 pb-28 sm:px-6 sm:py-10 desktop:pb-12">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="text-sm font-bold uppercase tracking-[0.14em] text-signal">Offers and purchases</p>
          <h1 className="type-wide mt-1 text-3xl font-black">Deals</h1>
          <p className="mt-2 max-w-xl text-sm leading-6 text-muted">Manage every offer and purchase here. Use messages to coordinate details after you choose who to deal with.</p>
        </div>
        <Link href="/sell" className="btn btn-primary">Sell an item</Link>
      </div>

      <div className="mt-7 grid grid-cols-2 rounded-xl bg-surface p-1" role="tablist" aria-label="Deal role">
        <button type="button" role="tab" aria-selected={role === "buyer"} onClick={() => setRole("buyer")} className={`rounded-lg px-4 py-2.5 text-sm font-bold transition ${role === "buyer" ? "bg-background shadow-sm" : "text-muted hover:text-ink"}`}>Buying{buyingCount ? ` · ${buyingCount}` : ""}</button>
        <button type="button" role="tab" aria-selected={role === "seller"} onClick={() => setRole("seller")} className={`rounded-lg px-4 py-2.5 text-sm font-bold transition ${role === "seller" ? "bg-background shadow-sm" : "text-muted hover:text-ink"}`}>Selling{sellingCount ? ` · ${sellingCount}` : ""}</button>
      </div>

      <DealSection title="Current deals" description={role === "seller" ? "Offers that need your answer, backup buyers, handoffs, and anything under review." : "Requests, offers, handoffs, and anything under review."} deals={current} onChange={update} empty={role === "seller" ? "No active offers on your listings." : "You have no active purchases or offers."} />
      <DealSection title="Transaction history" description={role === "seller" ? "Completed sales and trades only." : "Completed purchases and trades only."} deals={history} onChange={update} empty="No completed transactions yet." />
      <CollapsedSection title="Cancelled" description="Declined, canceled, and expired deals, kept for reference." deals={cancelled} onChange={update} empty="Nothing cancelled." />
      <CollapsedSection title="Archived" description="Closed deals you’ve archived. Nothing is deleted." deals={archived} onChange={update} empty="Nothing archived." />
    </main>
  );
}
