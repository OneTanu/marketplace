"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { actOnDeal, counterDeal, listConversationDeals } from "@/lib/deals";
import { api } from "@/lib/api/client";
import type { components } from "@/lib/api/schema";
import { centsToDollars } from "@/lib/money";
import { createReview, listDealReviews } from "@/lib/reviews";

type Deal = components["schemas"]["Deal"];
type MeetingSpot = components["schemas"]["MeetingSpot"];
type Review = components["schemas"]["Review"];

const statusText: Record<Deal["status"], string> = {
  awaiting_seller: "Waiting for seller",
  awaiting_buyer: "Waiting for buyer",
  backup: "Backup buyer",
  pending: "Handoff pending",
  completed: "Completed",
  canceled: "Canceled",
  declined: "Declined",
  expired: "Expired",
};

function deadlineText(value: string | null | undefined) {
  if (!value) return "";
  return new Intl.DateTimeFormat(undefined, {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  }).format(new Date(value));
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

  const mineConfirmed = deal.my_role === "buyer" ? deal.buyer_confirmed : deal.seller_confirmed;
  const open = ["awaiting_seller", "awaiting_buyer", "backup", "pending"].includes(deal.status);
  const canCancel = open && !(deal.status === "pending" && (deal.buyer_confirmed || deal.seller_confirmed));

  async function run(action: "accept" | "decline" | "cancel" | "confirm-handoff") {
    setWorking(true);
    setError("");
    try {
      setDeal(await actOnDeal(deal!.id, action));
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
      setDeal(await counterDeal(deal!.id, amount));
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
            <span className="font-semibold">{centsToDollars(deal.agreed_amount_cents ?? deal.current_amount_cents)}</span>
            <span className="text-muted"> · {statusText[deal.status]}</span>
          </p>
        </div>
      </div>

      {deal.status === "backup" && (
        <p className="mt-2 text-xs leading-5 text-muted">
          Another buyer is pending. The seller can choose this request if that handoff falls through.
        </p>
      )}
      {deal.status === "pending" && (
        <div className="mt-2 text-xs leading-5 text-muted">
          <p>Meet in a public campus location. Inspect the item and exchange payment in person.</p>
          <p className="mt-1">
            Buyer {deal.buyer_confirmed ? "confirmed" : "not confirmed"} · Seller {deal.seller_confirmed ? "confirmed" : "not confirmed"}
            {deal.handoff_deadline ? ` · Complete by ${deadlineText(deal.handoff_deadline)}` : ""}
          </p>
        </div>
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
          {deal.awaiting_me && (
            <>
              <button type="button" onClick={() => run("accept")} disabled={working} className="btn btn-primary h-9 px-3 text-sm">
                {deal.status === "backup" ? "Choose this buyer" : "Accept"}
              </button>
              {deal.status !== "backup" && <button type="button" onClick={() => setCountering(true)} disabled={working} className="btn btn-secondary h-9 px-3 text-sm">Counter</button>}
              <button type="button" onClick={() => run("decline")} disabled={working} className="btn btn-secondary h-9 px-3 text-sm">Decline</button>
            </>
          )}
          {deal.status === "pending" && !mineConfirmed && (
            <button type="button" onClick={() => setConfirmingHandoff(true)} disabled={working} className="btn btn-primary h-9 px-3 text-sm">Confirm handoff</button>
          )}
          {deal.status === "pending" && mineConfirmed && <p className="self-center text-sm font-semibold text-muted">Waiting for the other person to confirm</p>}
          {canCancel && <button type="button" onClick={() => run("cancel")} disabled={working} className="btn btn-secondary h-9 px-3 text-sm">Cancel {deal.status === "pending" ? "purchase" : "request"}</button>}
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
