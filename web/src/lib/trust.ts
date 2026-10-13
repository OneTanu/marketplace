import { api, requestFailed } from "@/lib/api/client";
import type { components } from "@/lib/api/schema";

export type ReportTargetType = components["schemas"]["ReportTargetType"];
export type ReportReason = components["schemas"]["ReportReason"];
export type ProhibitedCategory = components["schemas"]["ProhibitedCategory"];

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
