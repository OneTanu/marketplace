"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { TradeSummary } from "@/components/deals/trade";
import { actOnDeal, counterDeal, DEAL_STATUS_LABELS, dealNextStep, listConversationDeals, meetupState, tradePackage } from "@/lib/deals";
import { api } from "@/lib/api/client";
import type { components } from "@/lib/api/schema";
import { centsToDollars } from "@/lib/money";
import { createReview, listDealReviews } from "@/lib/reviews";
import { formatDateTime } from "@/lib/time";

type Deal = components["schemas"]["Deal"];
type MeetingSpot = components["schemas"]["MeetingSpot"];
type Review = components["schemas"]["Review"];

const statusText = DEAL_STATUS_LABELS;

function deadlineText(value: string | null | undefined) {
  return value ? formatDateTime(value) : "";
}

export function DealPanel({ conversationId, listingId }: { conversationId: number; listingId?: number }) {
  const [deal, setDeal] = useState<Deal | null>(null);
  const [loading, setLoading] = useState(true);
  const [working, setWorking] = useState(false);
  const [error, setError] = useState("");
  const [countering, setCountering] = useState(false);
  const [counter, setCounter] = useState("");
  const [confirmingHandoff, setConfirmingHandoff] = useState(false);
  const [meetingSpots, setMeetingSpots] = useState<MeetingSpot[]>([]);
  const [reviews, setReviews] = useState<Review[]>([]);
  const [rating, setRating] = useState(5);
  const [reviewComment, setReviewComment] = useState("");
  const [chosenProposalId, setMeetupProposalId] = useState<number | undefined>();
  const [now] = useState(() => Date.now());

  useEffect(() => {
    let active = true;
    async function refresh() {
      try {
        const deals = await listConversationDeals(conversationId);
        if (active) {
          setDeal((listingId ? deals.find((item) => item.listing.id === listingId) : deals[0]) ?? null);
        }
      } catch {
        // Messaging remains usable if deal status cannot refresh.
      } finally {
        if (active) setLoading(false);
      }
    }
    void refresh();
    const timer = window.setInterval(refresh, 4_000);
    return () => {
      active = false;
      window.clearInterval(timer);
    };
  }, [conversationId, listingId]);

  const schoolSlug = deal?.listing.school_slug;
  const dealStatus = deal?.status;
  useEffect(() => {
    let active = true;
    if (!schoolSlug || dealStatus !== "pending") {
      return;
    }
    api.GET("/api/schools/{slug}/meeting-spots/", {
      params: { path: { slug: schoolSlug } },
    }).then(({ data }) => {
      if (active && data) setMeetingSpots(data);
    });
    return () => {
      active = false;
    };
  }, [schoolSlug, dealStatus]);

  const dealId = deal?.id;
  useEffect(() => {
    let active = true;
    if (!dealId || dealStatus !== "completed") return;
    listDealReviews(dealId).then((items) => {
      if (active) setReviews(items);
    }).catch(() => {
      // The completed deal remains usable even if reviews do not load.
    });
    return () => {
      active = false;
    };
  }, [dealId, dealStatus]);

  if (loading || !deal) return null;

  const meetups = meetupState(deal, now);
  // Fall back to the first time on offer if the chosen one was replaced.
  const meetupProposalId = meetups.fromOther.some((proposal) => proposal.id === chosenProposalId)
    ? chosenProposalId
    : meetups.fromOther[0]?.id;

  const mineConfirmed = deal.my_role === "buyer" ? deal.buyer_confirmed : deal.seller_confirmed;
  const open = deal.section === "current";
  const can = deal.actions;

  async function run(action: "accept" | "decline" | "cancel" | "confirm-handoff") {
    setWorking(true);
    setError("");
    try {
      setDeal(
        await actOnDeal(
          deal!.id,
          action,
          action === "accept" ? meetupProposalId : undefined,
        ),
      );
      setConfirmingHandoff(false);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "That action did not go through.");
    } finally {
      setWorking(false);
    }
  }

  async function submitCounter() {
    const amount = Math.round(Number(counter) * 100);
    if (!Number.isFinite(amount) || amount < 1) {
      setError("Enter an amount of at least $0.01.");
      return;
    }
    setWorking(true);
    setError("");
    try {
      setDeal(await counterDeal(deal!.id, amount, meetupProposalId));
      setCountering(false);
      setCounter("");
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "The counteroffer did not go through.");
    } finally {
      setWorking(false);
    }
  }

  async function submitReview() {
    setWorking(true);
    setError("");
    try {
      const review = await createReview(deal!.id, rating, reviewComment);
      setReviews((current) => [review, ...current]);
      setReviewComment("");
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "The review did not go through.");
    } finally {
      setWorking(false);
    }
  }

  const myUsername = deal.my_role === "buyer" ? deal.buyer.username : deal.seller.username;
  const myReview = reviews.find((review) => review.author.username === myUsername);
  const acceptedMeetup = meetups.accepted;
  const isTrade = deal.kind === "trade";
  const tradeOffer = tradePackage(deal);
  const latestMeetupUpdate = deal.meetup_updates[0];

  return (
    <section className="border-b border-line bg-surface/60 px-4 py-3 sm:px-6" aria-label="Purchase status">
      <div className="flex items-center gap-3">
        {deal.listing.cover_url && (
          // eslint-disable-next-line @next/next/no-img-element -- media is uploaded at runtime.
          <img src={deal.listing.cover_url} alt="" className="size-12 rounded-md object-cover" />
        )}
        <div className="min-w-0 flex-1">
          <Link href={`/listings/${deal.listing.id}`} className="block truncate text-sm font-bold hover:underline">
            {deal.listing.title}
          </Link>
          <p className="text-sm">
            <span className="font-semibold">{isTrade ? "Trade" : centsToDollars(deal.agreed_amount_cents ?? deal.current_amount_cents)}</span>
            <span className="text-muted"> · {statusText[deal.status]}</span>
            {deal.asap && <span className="ml-2 rounded-full bg-[var(--brand-soft)] px-2 py-0.5 text-xs font-bold text-brand">ASAP</span>}
          </p>
        </div>
      </div>

      {isTrade && (
        <div className="mt-2 rounded-lg border border-line bg-background p-3">
          <TradeSummary deal={deal} compact />
          {deal.awaiting_me && (
            <Link href="/deals" className="mt-2 inline-block text-sm font-semibold text-brand underline">
              {tradeOffer ? "Counter with different items in Deals" : "Pick items in Deals"}
            </Link>
          )}
        </div>
      )}
      {deal.asap && deal.my_role === "seller" && open && deal.status !== "pending" && (
        <p className="mt-2 text-xs font-semibold text-brand">@{deal.buyer.username} wants to meet as soon as possible.</p>
      )}
      {(deal.status === "backup" || deal.status === "disputed") && (
        <p className="mt-2 text-xs leading-5 text-muted">{dealNextStep(deal)}</p>
      )}
      {deal.status === "pending" && (
        <div className="mt-2 text-xs leading-5 text-muted">
          <p>Meet in a public campus location. Inspect the item and exchange payment in person. Tanu doesn’t handle or verify payment.</p>
          {acceptedMeetup && (
            <p className="mt-1 font-semibold text-ink">
              {acceptedMeetup.meeting_spot.name} · {deadlineText(acceptedMeetup.starts_at)}
            </p>
          )}
          <p className="mt-1">
            Buyer {deal.buyer_confirmed ? "confirmed" : "not confirmed"} · Seller {deal.seller_confirmed ? "confirmed" : "not confirmed"}
            {deal.handoff_deadline ? ` · Complete by ${deadlineText(deal.handoff_deadline)}` : ""}
          </p>
        </div>
      )}
      {latestMeetupUpdate && deal.status === "pending" && (
        <p className="mt-2 text-sm font-semibold text-ink">
          @{latestMeetupUpdate.actor.username} {latestMeetupUpdate.kind === "arrived" ? "is here." : `is running about ${latestMeetupUpdate.minutes_late} minutes late.`}
        </p>
      )}
      {deal.awaiting_me && meetups.allStale && (
        <p className="mt-2 text-xs leading-5 text-ink">
          The proposed meetup times have passed. <Link href="/deals" className="font-semibold underline">Suggest a new time</Link> before accepting.
        </p>
      )}
      {deal.awaiting_me && meetups.fromOther.length > 0 && (
        <fieldset className="mt-2">
          <legend className="text-xs font-bold text-muted">
            {meetups.fromOther.length > 1 ? "Choose a meetup time" : "Proposed meetup"} · <Link href="/deals" className="underline">suggest another</Link>
          </legend>
          <div className="mt-2 flex flex-wrap gap-2">
            {meetups.fromOther.map((proposal) => (
              <button key={proposal.id} type="button" onClick={() => setMeetupProposalId(proposal.id)} aria-pressed={meetupProposalId === proposal.id} className={`rounded-lg border px-3 py-2 text-left text-xs ${meetupProposalId === proposal.id ? "border-ink bg-background ring-1 ring-ink" : "border-line"}`}>
                <span className="block font-bold text-ink">{deadlineText(proposal.starts_at)}</span>
                <span className="block text-muted">{proposal.meeting_spot.name}</span>
              </button>
            ))}
          </div>
        </fieldset>
      )}
      {deal.status === "pending" && meetingSpots.length > 0 && (
        <details className="mt-2 rounded-lg border border-line bg-background px-3 py-2 text-sm">
          <summary className="cursor-pointer font-semibold">Suggested {deal.listing.school_name} meetup spots</summary>
          <ul className="mt-2 space-y-2">
            {meetingSpots.map((spot) => (
              <li key={spot.id}>
                <p className="font-semibold">{spot.name}{spot.is_indoor ? " · Indoors" : ""}</p>
                <p className="text-xs leading-5 text-muted">{spot.directions}</p>
                {spot.safety_note && <p className="text-xs leading-5 text-muted">{spot.safety_note}</p>}
              </li>
            ))}
          </ul>
          <p className="mt-2 text-xs text-muted">Agree on the exact place and time in chat before traveling.</p>
        </details>
      )}
      {deal.response_deadline && open && (
        <p className="mt-1 text-xs text-muted">Response due {deadlineText(deal.response_deadline)}</p>
      )}

      {error && <p role="alert" className="mt-2 text-sm text-[var(--danger)]">{error}</p>}

      {countering && (
        <div className="mt-3 flex gap-2">
          <label className="field flex h-10 flex-1 items-center px-3">
            <span className="text-muted">$</span>
            <input value={counter} onChange={(event) => setCounter(event.target.value.replace(/[^0-9.]/g, ""))} inputMode="decimal" autoFocus aria-label="Counteroffer amount" className="min-w-0 flex-1 bg-transparent pl-1 outline-none" />
          </label>
          <button type="button" onClick={submitCounter} disabled={working} className="btn btn-primary">Send</button>
          <button type="button" onClick={() => setCountering(false)} disabled={working} className="btn btn-secondary">Back</button>
        </div>
      )}

      {confirmingHandoff && (
        <div className="mt-3 rounded-lg border border-line bg-background p-3 text-sm">
          <p className="font-semibold">
            {deal.my_role === "buyer"
              ? "Confirm that you received the item."
              : "Confirm that you handed over the item and received the agreed payment."}
          </p>
          <p className="mt-1 text-muted">The listing becomes Sold only after both people confirm.</p>
          <div className="mt-2 flex gap-2">
            <button type="button" onClick={() => setConfirmingHandoff(false)} disabled={working} className="btn btn-secondary flex-1">Back</button>
            <button type="button" onClick={() => run("confirm-handoff")} disabled={working} className="btn btn-primary flex-1">Confirm handoff</button>
          </div>
        </div>
      )}

      {!countering && !confirmingHandoff && (
        <div className="mt-3 flex flex-wrap gap-2">
          {can.accept && (!isTrade || tradeOffer) && (
            <button type="button" onClick={() => run("accept")} disabled={working} className="btn btn-primary h-9 px-3 text-sm">Accept</button>
          )}
          {can.counter && !isTrade && <button type="button" onClick={() => setCountering(true)} disabled={working} className="btn btn-secondary h-9 px-3 text-sm">Counter</button>}
          {can.decline && <button type="button" onClick={() => run("decline")} disabled={working} className="btn btn-secondary h-9 px-3 text-sm">{deal.status === "backup" ? "Remove from line" : "Decline"}</button>}
          {can.confirm_handoff && (
            <button type="button" onClick={() => setConfirmingHandoff(true)} disabled={working} className="btn btn-primary h-9 px-3 text-sm">Confirm handoff</button>
          )}
          {deal.status === "pending" && mineConfirmed && <p className="self-center text-sm font-semibold text-muted">Waiting for the other person to confirm</p>}
          {can.cancel && <button type="button" onClick={() => run("cancel")} disabled={working} className="btn btn-secondary h-9 px-3 text-sm">{deal.status === "backup" ? "Leave the line" : `Cancel ${deal.status === "pending" ? "purchase" : "request"}`}</button>}
          {can.report_problem && <Link href="/deals" className="btn btn-quiet h-9 px-3 text-sm">Report a problem</Link>}
        </div>
      )}

      {deal.status === "completed" && (
        <div className="mt-3 border-t border-line pt-3">
          {myReview ? (
            <div className="text-sm">
              <p className="font-semibold">Your review: {myReview.rating}/5</p>
              {myReview.comment && <p className="mt-1 text-muted">{myReview.comment}</p>}
            </div>
          ) : (
            <div>
              <p className="text-sm font-semibold">How did the handoff go?</p>
              <div className="mt-2 flex gap-1" role="group" aria-label="Rating">
                {[1, 2, 3, 4, 5].map((value) => (
                  <button key={value} type="button" onClick={() => setRating(value)} aria-pressed={rating === value} className={`grid size-9 place-items-center rounded-full text-sm font-bold ${rating === value ? "bg-brand text-white" : "bg-surface text-ink"}`}>
                    {value}
                  </button>
                ))}
              </div>
              <textarea value={reviewComment} onChange={(event) => setReviewComment(event.target.value)} maxLength={500} rows={2} placeholder="Optional review" className="field mt-2 resize-none text-sm" />
              <button type="button" onClick={submitReview} disabled={working} className="btn btn-primary mt-2 h-9 px-3 text-sm">Submit review</button>
            </div>
          )}
        </div>
      )}
    </section>
  );
}
