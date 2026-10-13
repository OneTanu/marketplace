import { api, requestFailed } from "@/lib/api/client";
import type { components, operations } from "@/lib/api/schema";

export type CaseRow = components["schemas"]["CaseRow"];
export type CaseDetail = components["schemas"]["CaseDetail"];
export type CaseAction = components["schemas"]["CaseActionRequest"];
export type QueueFilters = NonNullable<operations["moderation_cases_list"]["parameters"]["query"]>;

export async function getQueue(filters: QueueFilters) {
  const { data, error, response } = await api.GET("/api/moderation/cases/", {
    params: { query: filters },
  });
  return data ?? requestFailed(error, response);
}

export async function getQueueSummary() {
  const { data, error, response } = await api.GET("/api/moderation/summary/");
  return data ?? requestFailed(error, response);
}

export async function getCase(id: number) {
  const { data, error, response } = await api.GET("/api/moderation/cases/{id}/", {
    params: { path: { id } },
  });
  return data ?? requestFailed(error, response);
}

export async function actOnCase(id: number, body: CaseAction) {
  const { data, error, response } = await api.POST("/api/moderation/cases/{id}/actions/", {
    params: { path: { id } },
    body,
  });
  return data ?? requestFailed(error, response);
}

export async function liftRestriction(id: number, reason: string, caseId?: number) {
  const { data, error, response } = await api.POST("/api/moderation/restrictions/{id}/lift/", {
    params: { path: { id } },
    body: { reason, ...(caseId ? { case_id: caseId } : {}) },
  });
  return data ?? requestFailed(error, response);
}

/** A queue line's headline: what it's about. */
export function caseTarget(row: CaseRow) {
  const who = `@${row.subject_user.username}`;
  if (row.listing) return `Listing: “${row.listing.title}”`;
  if (row.target_types.includes("conversation") || row.target_types.includes("message")) return `Messages from ${who}`;
  if (row.target_types.includes("deal")) return `Deal or meetup with ${who}`;
  if (row.target_types.includes("review")) return `Review by ${who}`;
  return `Profile: ${who}`;
}

export const PRIORITY_STYLES: Record<number, string> = {
  1: "bg-[var(--danger)] text-white",
  2: "bg-signal text-white",
  3: "bg-surface text-ink",
};

export type ModerationStats = components["schemas"]["ModerationStats"];
export type StatsQuery = NonNullable<operations["moderation_stats_retrieve"]["parameters"]["query"]>;

export async function getModerationStats(query: StatsQuery) {
  const { data, error, response } = await api.GET("/api/moderation/stats/", {
    params: { query },
  });
  return data ?? requestFailed(error, response);
}
