import { api, errorMessage } from "@/lib/api/client";

function failed(error: unknown, response: Response): never {
  throw new Error(errorMessage(error, "detail") ?? `Request failed with ${response.status}`);
}

export async function listDealReviews(dealId: number) {
  const { data, error, response } = await api.GET("/api/deals/{deal_id}/reviews/", {
    params: { path: { deal_id: dealId } },
  });
  return data ?? failed(error, response);
}

export async function createReview(dealId: number, rating: number, comment: string) {
  const { data, error, response } = await api.POST("/api/deals/{deal_id}/reviews/", {
    params: { path: { deal_id: dealId } },
    body: { rating, comment },
  });
  return data ?? failed(error, response);
}
