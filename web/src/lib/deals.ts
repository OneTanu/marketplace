import { api, errorMessage } from "@/lib/api/client";

function failed(error: unknown, response: Response): never {
  throw new Error(errorMessage(error, "detail") ?? `Request failed with ${response.status}`);
}

export async function createDeal(
  listingId: number,
  body: { kind: "buy_now" } | { kind: "offer"; amount_cents: number },
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

export async function listDeals() {
  const { data, error, response } = await api.GET("/api/deals/");
  return data ?? failed(error, response);
}

type DealAction = "accept" | "decline" | "cancel" | "confirm-handoff";

export async function actOnDeal(id: number, action: DealAction) {
  const paths = {
    accept: "/api/deals/{id}/accept/",
    decline: "/api/deals/{id}/decline/",
    cancel: "/api/deals/{id}/cancel/",
    "confirm-handoff": "/api/deals/{id}/confirm-handoff/",
  } as const;
  const path = paths[action];
  const { data, error, response } = await api.POST(path, { params: { path: { id } } });
  return data ?? failed(error, response);
}

export async function counterDeal(id: number, amountCents: number) {
  const { data, error, response } = await api.POST("/api/deals/{id}/counter/", {
    params: { path: { id } },
    body: { amount_cents: amountCents },
  });
  return data ?? failed(error, response);
}
