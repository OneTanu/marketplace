"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { refusalMessage, toFieldErrors } from "@/components/listings/listing-form";
import { PhotoGallery } from "@/components/listings/photo-gallery";
import { MeetupPicker, type MeetupSelection } from "@/components/deals/meetup-picker";
import { api } from "@/lib/api/client";
import type { components } from "@/lib/api/schema";
import { createDeal } from "@/lib/deals";
import {
  STATUS_BADGE_CLASSES,
  STATUS_LABELS,
  colorLabel,
  conditionLabel,
} from "@/lib/listing-options";
import { startConversation } from "@/lib/messaging";
import { centsToDollars } from "@/lib/money";
import { formatShortDate } from "@/lib/time";

type Listing = components["schemas"]["Listing"];

const OFFLINE = "Couldn't reach Tanu. Check your connection and try again.";

type Loaded =
  | { state: "loading" }
  | { state: "blocked"; title: string; message: string; signIn?: boolean }
  | { state: "ready"; listing: Listing; isSeller: boolean };

/** A listing as buyers see it. Its seller sees the same page with Edit and Remove instead of
 * the buyer actions, plus a banner while it isn't Available. */
export function ListingDetail({ listingId }: { listingId: number }) {
  const [loaded, setLoaded] = useState<Loaded>({ state: "loading" });

  useEffect(() => {
    let cancelled = false;
    Promise.all([
      api.GET("/api/listings/{id}/", { params: { path: { id: listingId } } }),
      api.GET("/api/me/"),
    ])
      .then(([listing, me]) => {
        if (cancelled) return;
        if (listing.data) {
          setLoaded({
            state: "ready",
            listing: listing.data,
            isSeller: me.data?.id === listing.data.seller.id,
          });
        } else if (listing.response.status === 403 || listing.response.status === 401) {
          setLoaded({
            state: "blocked",
            title: "Sign in to see this listing",
            message: "Listings on Tanu are only visible to verified students.",
            signIn: true,
          });
        } else if (listing.response.status === 404) {
          setLoaded({
            state: "blocked",
            title: "Listing not found",
            message: "It may have been removed by its seller.",
          });
        } else {
          setLoaded({
            state: "blocked",
            title: "Couldn't load this listing",
            message: "Refresh to try again.",
          });
        }
      })
      .catch(() => {
        if (!cancelled) {
          setLoaded({ state: "blocked", title: "Couldn't load this listing", message: OFFLINE });
        }
      });
    return () => {
      cancelled = true;
    };
  }, [listingId]);

  if (loaded.state === "loading") {
    return (
      <div className="mx-auto max-w-6xl animate-pulse sm:px-6 sm:pt-6 lg:grid lg:grid-cols-[1.2fr_1fr] lg:gap-10">
        <div className="aspect-[4/5] bg-surface sm:rounded-lg" />
        <div className="space-y-3 px-4 pt-5 sm:px-0">
          <div className="h-7 w-24 rounded bg-surface" />
          <div className="h-5 w-3/4 rounded bg-surface" />
        </div>
      </div>
    );
  }

  if (loaded.state === "blocked") {
    return (
      <section className="mx-auto max-w-xl px-4 py-20 text-center">
        <h1 className="type-wide text-2xl font-black">{loaded.title}</h1>
        <p className="mt-3 text-muted">{loaded.message}</p>
        {loaded.signIn ? (
          <Link href="/account/login" className="btn btn-primary mt-6">
            Log in
          </Link>
        ) : (
          <Link href="/search" className="btn btn-secondary mt-6">
            Keep browsing
          </Link>
        )}
      </section>
    );
  }

  return (
    <ListingView
      listing={loaded.listing}
      isSeller={loaded.isSeller}
      onChange={(listing) => setLoaded({ ...loaded, listing })}
    />
  );
}

function ListingView({
  listing,
  isSeller,
  onChange,
}: {
  listing: Listing;
  isSeller: boolean;
  onChange: (listing: Listing) => void;
}) {
  const details = listing.item_details;
  const chips = [
    details && conditionLabel(details.condition),
    details?.size && `Size ${details.size}`,
    details?.brand,
    details?.color && colorLabel(details.color),
    listing.category.name,
  ].filter((chip): chip is string => Boolean(chip));

  return (
    <article className="mx-auto max-w-6xl pb-6 sm:px-6 sm:pt-6 desktop:pb-12 lg:grid lg:grid-cols-[1.2fr_1fr] lg:items-start lg:gap-10">
      <PhotoGallery photos={listing.photos} title={listing.title} />

      <div className="px-4 pt-5 sm:px-0 lg:sticky lg:top-24 lg:rounded-xl lg:border lg:border-line lg:p-6">
        {isSeller && <SellerBanner listing={listing} />}

        <div className="flex items-start justify-between gap-3">
          <p className="type-wide text-3xl font-black">
            {listing.price_cents === 0 ? "Free" : centsToDollars(listing.price_cents)}
          </p>
          {listing.status !== "available" && (
            <span
              className={`mt-1 rounded-full px-2.5 py-1 text-xs font-semibold ${STATUS_BADGE_CLASSES[listing.status]}`}
            >
              {STATUS_LABELS[listing.status]}
            </span>
          )}
        </div>
        <h1 className="mt-1 text-lg font-semibold leading-snug">{listing.title}</h1>

        <ul aria-label="Details" className="mt-3 flex flex-wrap gap-1.5">
          {chips.map((chip, index) => (
            <li key={index} className="rounded-md bg-surface px-2.5 py-1 text-[13px] font-medium">
              {chip}
            </li>
          ))}
        </ul>

        {listing.description && (
          <p className="mt-4 whitespace-pre-line leading-7 text-ink/85">{listing.description}</p>
        )}

        <div className="mt-5 flex items-center gap-3 border-t border-line pt-4">
          <div className="type-wide grid size-10 shrink-0 place-items-center rounded-full bg-[var(--brand-soft)] font-extrabold text-brand">
            {listing.seller.username[0].toUpperCase()}
          </div>
          <div className="min-w-0 flex-1 text-sm">
            <Link href={`/users/${listing.seller.username}`} className="font-bold hover:underline">
              @{listing.seller.username}
            </Link>
            <p className="text-muted">
              {listing.school.short_name} · Listed {formatShortDate(listing.created_at)}
            </p>
          </div>
          <ShareButton title={listing.title} />
        </div>

        <p className="mt-4 rounded-lg bg-surface p-3 text-sm leading-6 text-muted">
          <span className="font-semibold text-ink">Meet in a public spot.</span> Hand off on
          campus where other people are around, and check the item before you pay.
        </p>

        {isSeller ? (
          <SellerActions listing={listing} onChange={onChange} />
        ) : (
          <BuyerActions listing={listing} />
        )}
      </div>
    </article>
  );
}

/** On phones, sticks above the bottom tab bar while the panel is on screen. Sticky rather than
 * fixed, so it keeps its place in the page and never covers the content above it. Inline in
 * the side panel on desktop. */
const actionBarClass =
  "sticky bottom-[calc(4rem+env(safe-area-inset-bottom))] z-10 -mx-4 mt-5 border-t border-line bg-background/95 px-4 py-3 backdrop-blur sm:mx-0 desktop:static desktop:border-0 desktop:bg-transparent desktop:p-0";
// Three buttons share a phone-width row, so they trade the usual side padding for room.
const actionButton = "btn min-w-0 flex-1 px-2";

function BuyerActions({ listing }: { listing: Listing }) {
  const router = useRouter();
  const [starting, setStarting] = useState(false);
  const [mode, setMode] = useState<"offer" | "buy_now" | "trade" | null>(null);
  const [asap, setAsap] = useState(false);
  // How many of the buyer's own listings a seller could pick from; undefined while loading.
  const [tradable, setTradable] = useState<number | null>();
  const [offer, setOffer] = useState("");
  const [error, setError] = useState("");
  const [meetup, setMeetup] = useState<MeetupSelection>({
    meetingSpotId: null,
    startsAt: [],
    configured: false,
    loading: true,
  });
  const canBuy = listing.status === "available";

  async function message() {
    setStarting(true);
    setError("");
    try {
      const conversation = await startConversation(listing.seller.username);
      router.push(`/inbox/${conversation.id}?listing=${listing.id}`);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : OFFLINE);
      setStarting(false);
    }
  }

  useEffect(() => {
    if (mode !== "trade") return;
    let active = true;
    api
      .GET("/api/listings/mine/")
      .then(({ data }) => active && setTradable(data ? data.filter((item) => item.status === "available").length : null))
      .catch(() => active && setTradable(null));
    return () => {
      active = false;
    };
  }, [mode]);

  async function requestDeal() {
    if (!mode) return;
    const amountCents = Math.round(Number(offer) * 100);
    if (mode === "offer" && (!Number.isFinite(amountCents) || amountCents < 1)) {
      setError("Enter an offer of at least $0.01.");
      return;
    }
    // Sellers who haven't set meetup preferences yet agree on a time in chat instead.
    const needsMeetup = meetup.configured;
    if (needsMeetup && (meetup.meetingSpotId === null || meetup.startsAt.length === 0)) {
      setError("Choose a meetup location and time before sending your request.");
      return;
    }
    const meetupFields =
      needsMeetup && meetup.meetingSpotId !== null
        ? { meeting_spot_id: meetup.meetingSpotId, proposed_starts_at: meetup.startsAt }
        : {};
    setStarting(true);
    setError("");
    try {
      await createDeal(
        listing.id,
        mode === "offer"
          ? { kind: "offer", amount_cents: amountCents, asap, ...meetupFields }
          : { kind: mode, asap, ...meetupFields },
      );
      router.push("/deals");
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : OFFLINE);
      setStarting(false);
    }
  }

  if (mode) {
    return (
      <div className={actionBarClass}>
        <p className="font-semibold">
          {mode === "offer" ? "Make an offer" : mode === "trade" ? "Propose a trade" : `Request to buy for ${centsToDollars(listing.price_cents)}`}
        </p>
        <p className="mt-1 text-sm leading-5 text-muted">
          {mode === "trade"
            ? "The seller looks through your listings and picks what they'd take, maybe with some cash. You can accept, counter, or cancel anytime."
            : "No money moves through Tanu. The seller must accept, then you arrange a public-campus handoff."}
        </p>
        {mode === "trade" && tradable === 0 && (
          <p className="mt-3 rounded-lg border border-line bg-surface p-3 text-sm">
            You don&apos;t have any available listings to trade yet. <Link href="/sell" className="font-semibold underline">List an item</Link> first.
          </p>
        )}
        {mode === "offer" && (
          <label className="field mt-3 flex h-11 items-center px-3">
            <span className="text-muted">$</span>
            <input
              value={offer}
              onChange={(event) => setOffer(event.target.value.replace(/[^0-9.]/g, ""))}
              inputMode="decimal"
              autoFocus
              aria-label="Offer amount"
              className="min-w-0 flex-1 bg-transparent pl-1 outline-none"
            />
          </label>
        )}
        <label className="mt-3 flex items-start gap-3 rounded-lg border border-line p-3 text-sm">
          <input type="checkbox" checked={asap} onChange={(event) => setAsap(event.target.checked)} className="mt-0.5 size-4 accent-[var(--brand)]" />
          <span>
            <span className="block font-semibold">I want this as soon as possible</span>
            <span className="block text-muted">Lets the seller know the earliest meetup works best for you.</span>
          </span>
        </label>
        <MeetupPicker
          listingId={listing.id}
          allowTwo={mode !== "buy_now"}
          onChange={setMeetup}
        />
        {error && <p role="alert" className="mt-2 text-sm text-[var(--danger)]">{error}</p>}
        <div className="mt-3 flex gap-2">
          <button type="button" onClick={() => { setMode(null); setError(""); }} disabled={starting} className="btn btn-secondary flex-1">
            Back
          </button>
          <button type="button" onClick={requestDeal} disabled={starting || meetup.loading || (mode === "trade" && !tradable)} className="btn btn-primary flex-1">
            {starting ? "Sending…" : "Send request"}
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className={actionBarClass}>
      {error && (
        <p role="alert" className="mb-2 text-sm text-[var(--danger)]">
          {error}
        </p>
      )}
      <div className="flex gap-2">
        <button type="button" onClick={message} disabled={starting} className={`${actionButton} btn-secondary`}>
          {starting ? "Opening…" : "Message"}
        </button>
        <button type="button" onClick={() => setMode("offer")} disabled={!canBuy || starting} className={`${actionButton} btn-secondary`}>
          Make offer
        </button>
        <button type="button" onClick={() => setMode("buy_now")} disabled={!canBuy || starting} className={`${actionButton} btn-primary`}>
          Buy now
        </button>
      </div>
      {canBuy && (
        <button type="button" onClick={() => setMode("trade")} disabled={starting} className="mt-2 w-full text-center text-sm font-semibold text-brand hover:underline">
          Or propose a trade with your items
        </button>
      )}
      <p className="mt-2 text-center text-xs text-muted">
        {canBuy
          ? "The seller has 24 hours to respond. Payment happens when you meet."
          : `This item is ${STATUS_LABELS[listing.status].toLowerCase()}.`}
      </p>
    </div>
  );
}

function SellerBanner({ listing }: { listing: Listing }) {
  let text: string | null = null;
  if (listing.status === "pending") text = "Pending. You've accepted a buyer for this item.";
  if (listing.status === "sold") text = "Sold. This listing stays here for your records.";
  if (listing.removed_by === "moderation") {
    text = "Removed by moderation. Buyers can't see this listing.";
  } else if (listing.status === "removed") {
    text = "You removed this listing. Buyers can't see it.";
  }
  if (!text) return null;
  return (
    <p role="status" className="mb-4 rounded-lg bg-surface p-3 text-sm font-medium">
      {text}
    </p>
  );
}

function SellerActions({
  listing,
  onChange,
}: {
  listing: Listing;
  onChange: (listing: Listing) => void;
}) {
  const [confirming, setConfirming] = useState(false);
  const [removing, setRemoving] = useState(false);
  const [error, setError] = useState("");

  if (listing.status !== "available") return null;

  async function remove() {
    setRemoving(true);
    setError("");
    try {
      const { error: body, response } = await api.DELETE("/api/listings/{id}/", {
        params: { path: { id: listing.id } },
      });
      if (response.ok) {
        onChange({ ...listing, status: "removed", removed_by: "seller" });
        return;
      }
      setError(
        refusalMessage(response.status, toFieldErrors(body).detail?.[0], {
          failed: "Couldn't remove this listing. Try again.",
          signIn: "Sign in to remove your listing.",
        }),
      );
    } catch {
      setError(OFFLINE);
    }
    setRemoving(false);
  }

  if (confirming) {
    return (
      <div role="group" aria-label="Remove this listing" className={actionBarClass}>
        <p className="text-sm">
          <span className="font-semibold">Remove this listing?</span> Buyers won&apos;t see it
          anymore. This can&apos;t be undone.
        </p>
        {error && (
          <p role="alert" className="mt-1 text-sm text-[var(--danger)]">
            {error}
          </p>
        )}
        <div className="mt-2 flex gap-2">
          <button type="button" onClick={() => setConfirming(false)} disabled={removing} className="btn btn-secondary flex-1">
            Cancel
          </button>
          <button type="button" onClick={remove} disabled={removing} className="btn flex-1 bg-[var(--danger)] text-white">
            {removing ? "Removing…" : "Remove listing"}
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className={actionBarClass}>
      <div className="flex gap-2">
        <Link href={`/listings/${listing.id}/edit`} className="btn btn-primary flex-1">
          Edit listing
        </Link>
        <button type="button" onClick={() => setConfirming(true)} className="btn btn-secondary flex-1">
          Remove
        </button>
      </div>
    </div>
  );
}

function ShareButton({ title }: { title: string }) {
  const [copied, setCopied] = useState(false);

  async function share() {
    const url = window.location.href;
    if (navigator.share) {
      try {
        await navigator.share({ title, url });
      } catch {
        // The share sheet was dismissed.
      }
      return;
    }
    try {
      await navigator.clipboard.writeText(url);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // Clipboard access denied; nothing else to fall back to.
    }
  }

  return (
    <button type="button" onClick={share} className="btn btn-sm btn-quiet shrink-0">
      <svg viewBox="0 0 24 24" className="size-4" fill="none" stroke="currentColor" strokeWidth={2} aria-hidden="true">
        <path d="M12 3v12M7 8l5-5 5 5M5 13v6a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2v-6" />
      </svg>
      <span aria-live="polite">{copied ? "Link copied" : "Share"}</span>
    </button>
  );
}
