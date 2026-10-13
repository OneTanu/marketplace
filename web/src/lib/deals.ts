import { api, requestFailed } from "@/lib/api/client";
import type { components } from "@/lib/api/schema";

const failed = requestFailed;

export async function createDeal(
  listingId: number,
  body: components["schemas"]["CreateDealRequest"],
) {
  const { data, error, response } = await api.POST("/api/listings/{listing_id}/deals/", {
    params: { path: { listing_id: listingId } },
    body,
  });
  return data ?? failed(error, response);
}

export async function listConversationDeals(conversationId: number) {
  const { data, error, response } = await api.GET("/api/deals/", {
    params: { query: { conversation: conversationId } },
  });
  return data ?? failed(error, response);
}

export async function getDeal(id: number) {
  const { data, error, response } = await api.GET("/api/deals/{id}/", {
    params: { path: { id } },
  });
  return data ?? failed(error, response);
}

export async function listDeals() {
  const { data, error, response } = await api.GET("/api/deals/");
  return data ?? failed(error, response);
}

type DealAction = "accept" | "decline" | "cancel" | "confirm-handoff";

export async function actOnDeal(id: number, action: DealAction, meetupProposalId?: number) {
  const paths = {
    accept: "/api/deals/{id}/accept/",
    decline: "/api/deals/{id}/decline/",
    cancel: "/api/deals/{id}/cancel/",
    "confirm-handoff": "/api/deals/{id}/confirm-handoff/",
  } as const;
  const path = paths[action];
  const { data, error, response } = await api.POST(path, {
    params: { path: { id } },
    ...(action === "accept" && meetupProposalId
      ? { body: { meetup_proposal_id: meetupProposalId } }
      : {}),
  });
  return data ?? failed(error, response);
}

export async function getMeetupOptions(listingId: number) {
  const { data, error, response } = await api.GET("/api/listings/{listing_id}/meetup-options/", {
    params: { path: { listing_id: listingId } },
  });
  return data ?? failed(error, response);
}

export async function getMeetupPreferences() {
  const { data, error, response } = await api.GET("/api/meetup-preferences/");
  return data ?? failed(error, response);
}

export async function saveMeetupPreferences(
  body: components["schemas"]["MeetupPreferenceUpdateRequest"],
) {
  const { data, error, response } = await api.PUT("/api/meetup-preferences/", { body });
  return data ?? failed(error, response);
}

export async function proposeMeetup(
  dealId: number,
  body: components["schemas"]["MeetupProposalCreateRequest"],
) {
  const { data, error, response } = await api.POST("/api/deals/{id}/meetup-proposals/", {
    params: { path: { id: dealId } },
    body,
  });
  return data ?? failed(error, response);
}

export async function acceptMeetup(dealId: number, proposalId: number) {
  const { data, error, response } = await api.POST(
    "/api/deals/{id}/meetup-proposals/accept/",
    {
      params: { path: { id: dealId } },
      body: { proposal_id: proposalId },
    },
  );
  return data ?? failed(error, response);
}

export async function updateMeetupStatus(
  dealId: number,
  body: components["schemas"]["MeetupStatusCreateRequest"],
) {
  const { data, error, response } = await api.POST("/api/deals/{id}/meetup-status/", {
    params: { path: { id: dealId } },
    body,
  });
  return data ?? failed(error, response);
}

export async function counterDeal(id: number, amountCents: number, meetupProposalId?: number) {
  const { data, error, response } = await api.POST("/api/deals/{id}/counter/", {
    params: { path: { id } },
    body: {
      amount_cents: amountCents,
      ...(meetupProposalId ? { meetup_proposal_id: meetupProposalId } : {}),
    },
  });
  return data ?? failed(error, response);
}

type Deal = components["schemas"]["Deal"];

/** Meetup proposals from the viewer's side. Proposals whose time has passed can't be
 * accepted, so they only count toward `allStale`. */
export function meetupState(deal: Deal, now: number) {
  const myId = deal.my_role === "seller" ? deal.seller.id : deal.buyer.id;
  const pending = deal.meetup_proposals
    .filter((proposal) => proposal.status === "pending")
    .sort((a, b) => a.starts_at.localeCompare(b.starts_at));
  const fresh = pending.filter((proposal) => new Date(proposal.starts_at).getTime() > now);
  return {
    accepted: deal.meetup_proposals.find((proposal) => proposal.status === "accepted"),
    fromOther: fresh.filter((proposal) => proposal.proposed_by.id !== myId),
    fromMe: fresh.filter((proposal) => proposal.proposed_by.id === myId),
    allStale: pending.length > 0 && fresh.length === 0,
  };
}

export async function getTradeOptions(dealId: number) {
  const { data, error, response } = await api.GET("/api/deals/{id}/trade-options/", {
    params: { path: { id: dealId } },
  });
  return data ?? failed(error, response);
}

export async function offerTrade(dealId: number, body: components["schemas"]["TradeOfferRequest"]) {
  const { data, error, response } = await api.POST("/api/deals/{id}/trade-offer/", {
    params: { path: { id: dealId } },
    body,
  });
  return data ?? failed(error, response);
}

/** A trade's package on the table: its latest offer, or undefined before the seller picks. */
export function tradePackage(deal: Deal) {
  if (deal.kind !== "trade") return undefined;
  return deal.offers.at(-1);
}
