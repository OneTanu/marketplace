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

export type DealProblemKind = components["schemas"]["DealProblemKind"];

export const DEAL_STATUS_LABELS: Record<Deal["status"], string> = {
  awaiting_seller: "Waiting for seller",
  awaiting_buyer: "Waiting for buyer",
  backup: "Backup buyer",
  pending: "Handoff pending",
  disputed: "Under review",
  completed: "Completed",
  canceled: "Canceled",
  declined: "Declined",
  expired: "Expired",
};

export const PROBLEM_KINDS: { value: DealProblemKind; label: string }[] = [
  { value: "no_show", label: "The other person didn’t show up" },
  { value: "not_as_described", label: "The item wasn’t as described" },
  { value: "payment", label: "There was a payment problem" },
  { value: "safety", label: "I felt unsafe" },
  { value: "other", label: "Something else" },
];

/** What the viewer should do next, in one line. Payment happens in person; Tanu never handles
 * or verifies it. */
export function dealNextStep(deal: Deal): string {
  const mine = deal.my_role === "buyer" ? deal.buyer_confirmed : deal.seller_confirmed;
  const other = deal.my_role === "buyer" ? deal.seller_confirmed : deal.buyer_confirmed;
  switch (deal.status) {
    case "awaiting_seller":
    case "awaiting_buyer":
      return deal.awaiting_me ? "Accept, counter, or decline before the response window closes." : "Waiting for a reply. It expires if there’s no answer in 24 hours.";
    case "backup":
      return deal.my_role === "buyer"
        ? `You’re #${deal.backup_position ?? "?"} in line. If the current handoff falls through, the next buyer in line gets a turn.`
        : "This buyer is waiting in line. They get a turn, in order, if the current handoff falls through.";
    case "pending":
      if (mine) return other ? "Both confirmed." : "You confirmed. Waiting for the other person to confirm before the deadline.";
      if (other) return "The other person confirmed the handoff. Confirm once you have the item or payment, or report a problem.";
      return "Meet up, check the item, and exchange payment in person. Then both confirm the handoff.";
    case "disputed":
      return "A moderator is reviewing this handoff. The listing stays on hold until they decide; nobody is penalized automatically.";
    case "completed":
      return "Completed. Both of you confirmed the handoff.";
    default:
      return "This deal is closed.";
  }
}

export async function reportDealProblem(id: number, kind: DealProblemKind, details: string) {
  const { data, error, response } = await api.POST("/api/deals/{id}/report-problem/", {
    params: { path: { id } },
    body: { kind, details },
  });
  return data ?? failed(error, response);
}

export async function setDealArchived(id: number, archived: boolean) {
  const path = { params: { path: { id } } };
  const { data, error, response } = archived
    ? await api.POST("/api/deals/{id}/archive/", path)
    : await api.DELETE("/api/deals/{id}/archive/", path);
  return data ?? failed(error, response);
}
