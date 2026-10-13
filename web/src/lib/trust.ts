import { api, requestFailed } from "@/lib/api/client";
import type { components } from "@/lib/api/schema";

export type ReportTargetType = components["schemas"]["ReportTargetType"];
export type ReportReason = components["schemas"]["ReportReason"];
export type ProhibitedCategory = components["schemas"]["ProhibitedCategory"];

export const REASON_LABELS: Record<ReportReason, string> = {
  prohibited_item: "Prohibited item",
  counterfeit: "Counterfeit item",
  scam: "Scam or payment concern",
  harassment: "Harassment",
  spam: "Spam",
  unsafe_meetup: "Unsafe meetup behavior",
  no_show: "Didn't show up to the meetup",
  misleading_listing: "Misleading listing",
  inappropriate: "Inappropriate profile or message",
  other: "Something else",
};

export async function submitReport(body: components["schemas"]["ReportCreateRequest"]) {
  const { data, error, response } = await api.POST("/api/reports/", { body });
  return data ?? requestFailed(error, response);
}

export async function listBlocks() {
  const { data, error, response } = await api.GET("/api/blocks/");
  return data ?? requestFailed(error, response);
}

export async function blockUser(username: string) {
  const { data, error, response } = await api.POST("/api/blocks/", { body: { username } });
  return data ?? requestFailed(error, response);
}

export async function unblockUser(username: string) {
  const { error, response } = await api.DELETE("/api/blocks/{username}/", {
    params: { path: { username } },
  });
  if (!response.ok) requestFailed(error, response);
}

export async function getMyRestrictions() {
  const { data, error, response } = await api.GET("/api/me/restrictions/");
  return data ?? requestFailed(error, response);
}

export async function getMyStanding() {
  const { data, error, response } = await api.GET("/api/me/standing/");
  return data ?? requestFailed(error, response);
}

export async function fileAppeal(actionId: number, message: string) {
  const { data, error, response } = await api.POST("/api/me/appeals/", {
    body: { action_id: actionId, message },
  });
  return data ?? requestFailed(error, response);
}

export async function answerInfoRequest(id: number, answer: string) {
  const { data, error, response } = await api.POST("/api/me/info-requests/{id}/answer/", {
    params: { path: { id } },
    body: { answer },
  });
  return data ?? requestFailed(error, response);
}
