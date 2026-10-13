"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { api } from "@/lib/api/client";
import type { components } from "@/lib/api/schema";
import {
  caseTarget,
  getQueue,
  getQueueSummary,
  PRIORITY_STYLES,
  type CaseRow,
  type QueueFilters,
} from "@/lib/moderation";
import { formatDateTime } from "@/lib/time";
import { REASON_LABELS, type ReportReason } from "@/lib/trust";

type Summary = components["schemas"]["QueueSummary"];
type School = components["schemas"]["School"];

const STATUSES: [NonNullable<QueueFilters["status"]>, string][] = [
  ["active", "Open (all)"],
  ["open", "New"],
  ["investigating", "Investigating"],
  ["appealed", "Appealed"],
  ["resolved", "Resolved"],
];
const TARGETS: [NonNullable<QueueFilters["target_type"]>, string][] = [
  ["listing", "Listings"],
  ["user", "Profiles"],
  ["conversation", "Conversations"],
  ["message", "Messages"],
  ["deal", "Deals and meetups"],
  ["review", "Reviews"],
];

function ago(value: string) {
  const minutes = Math.max(1, Math.round((Date.now() - new Date(value).getTime()) / 60_000));
  if (minutes < 60) return `${minutes} min ago`;
  const hours = Math.round(minutes / 60);
  return hours < 48 ? `${hours} h ago` : formatDateTime(value);
}

/** Shown when a signed-in student (or a signed-out visitor) opens /moderation. */
export function ModeratorsOnly({ message }: { message: string }) {
  return (
    <main className="mx-auto grid min-h-[70vh] max-w-xl place-items-center px-4 text-center">
      <div>
        <p className="text-sm font-bold uppercase tracking-[0.14em] text-muted">403</p>
        <h1 className="type-wide mt-1 text-3xl font-black">Moderators only</h1>
        <p className="mt-3 text-muted">{message}</p>
        <Link href="/" className="btn btn-primary mt-6">Back to Tanu</Link>
      </div>
    </main>
  );
}

export function ModerationQueue() {
  const [summary, setSummary] = useState<Summary | null>();
  const [denied, setDenied] = useState("");
  const [filters, setFilters] = useState<QueueFilters>({ status: "active" });
  const [rows, setRows] = useState<CaseRow[] | null>();
  const [schools, setSchools] = useState<School[]>([]);

  useEffect(() => {
    let active = true;
    getQueueSummary()
      .then((data) => active && setSummary(data))
      .catch((caught) => {
        if (!active) return;
        setSummary(null);
        setDenied(caught instanceof Error ? caught.message : "Only moderators can open the moderation portal.");
      });
    api.GET("/api/schools/").then(({ data }) => active && data && setSchools(data));
    return () => {
      active = false;
    };
  }, []);

  useEffect(() => {
    if (!summary) return;
    let active = true;
    getQueue(filters)
      .then((data) => active && setRows(data))
      .catch(() => active && setRows(null));
    return () => {
      active = false;
    };
  }, [filters, summary]);

  function setFilter<K extends keyof QueueFilters>(key: K, value: QueueFilters[K] | "") {
    setRows(undefined);
    setFilters((current) => {
      const next = { ...current };
      if (value === "" || value === undefined || value === false) delete next[key];
      else next[key] = value as QueueFilters[K];
      return next;
    });
  }

  if (summary === undefined) return <main className="mx-auto min-h-[70vh] max-w-5xl animate-pulse px-4 py-10 sm:px-6"><div className="h-9 w-48 rounded bg-surface" /><div className="mt-6 grid grid-cols-2 gap-3 sm:grid-cols-4">{[0, 1, 2, 3].map((i) => <div key={i} className="h-20 rounded-xl bg-surface" />)}</div></main>;
  if (summary === null) return <ModeratorsOnly message={denied} />;

  const tiles: [string, number, () => void][] = [
    ["Open", summary.open, () => setFilters({ status: "active" })],
    ["Urgent", summary.urgent, () => setFilters({ status: "active", priority: 1 })],
    ["Assigned to me", summary.assigned_to_me, () => setFilters({ status: "active", assigned: "me" })],
    ["Escalated", summary.escalated, () => setFilters({ status: "active" })],
  ];
  // `field` is full width by default; filters sit side by side in one row.
  const select = "field h-10 w-auto px-3 text-sm";

  return (
    <main className="mx-auto min-h-[70vh] max-w-5xl px-4 py-8 pb-28 sm:px-6 desktop:pb-12">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <p className="text-sm font-bold uppercase tracking-[0.14em] text-signal">Staff</p>
          <h1 className="type-wide mt-1 text-3xl font-black">Moderation</h1>
        </div>
        <Link href="/moderation/stats" className="btn btn-secondary btn-sm">Stats</Link>
      </div>

      <div className="mt-6 grid grid-cols-2 gap-3 sm:grid-cols-4">
        {tiles.map(([label, count, onClick]) => (
          <button key={label} type="button" onClick={() => { setRows(undefined); onClick(); }} className={`rounded-xl border p-4 text-left transition hover:border-ink ${label === "Urgent" && count ? "border-[var(--danger)]" : "border-line"}`}>
            <span className="block text-2xl font-black">{count}</span>
            <span className="text-sm text-muted">{label}</span>
          </button>
        ))}
      </div>

      <div className="mt-6 flex flex-wrap items-center gap-2" aria-label="Filters">
        <select aria-label="Status" value={filters.status ?? "active"} onChange={(e) => setFilter("status", e.target.value as QueueFilters["status"])} className={select}>
          {STATUSES.map(([value, label]) => <option key={value} value={value}>{label}</option>)}
        </select>
        <select aria-label="Urgency" value={filters.priority ?? ""} onChange={(e) => setFilter("priority", e.target.value ? (Number(e.target.value) as QueueFilters["priority"]) : "")} className={select}>
          <option value="">Any urgency</option>
          <option value="1">Urgent</option>
          <option value="2">High</option>
          <option value="3">Normal</option>
        </select>
        <select aria-label="Report type" value={filters.reason ?? ""} onChange={(e) => setFilter("reason", e.target.value as QueueFilters["reason"])} className={select}>
          <option value="">Any reason</option>
          {(Object.keys(REASON_LABELS) as ReportReason[]).map((value) => <option key={value} value={value}>{REASON_LABELS[value]}</option>)}
        </select>
        <select aria-label="Reported" value={filters.target_type ?? ""} onChange={(e) => setFilter("target_type", e.target.value as QueueFilters["target_type"])} className={select}>
          <option value="">Anything reported</option>
          {TARGETS.map(([value, label]) => <option key={value} value={value}>{label}</option>)}
        </select>
        <select aria-label="School" value={filters.school ?? ""} onChange={(e) => setFilter("school", e.target.value)} className={select}>
          <option value="">Every school</option>
          {schools.map((school) => <option key={school.slug} value={school.slug}>{school.short_name}</option>)}
        </select>
        <select aria-label="Assigned" value={filters.assigned ?? ""} onChange={(e) => setFilter("assigned", e.target.value as QueueFilters["assigned"])} className={select}>
          <option value="">Anyone</option>
          <option value="me">Assigned to me</option>
          <option value="none">Unassigned</option>
        </select>
        <label className="flex items-center gap-2 text-sm">
          <input type="checkbox" checked={Boolean(filters.repeat)} onChange={(e) => setFilter("repeat", e.target.checked)} className="accent-[var(--brand)]" />
          Repeat reports
        </label>
      </div>

      <section className="mt-5" aria-label="Cases">
        {rows === undefined && <div className="space-y-2">{[0, 1, 2].map((i) => <div key={i} className="h-24 animate-pulse rounded-xl bg-surface" />)}</div>}
        {rows === null && <p className="rounded-xl bg-surface p-6 text-center text-sm text-muted">Couldn&apos;t load the queue. Refresh to try again.</p>}
        {rows && rows.length === 0 && <p className="rounded-xl bg-surface p-8 text-center text-sm text-muted">No cases match these filters.</p>}
        {rows && rows.length > 0 && (
          <ul className="space-y-2">
            {rows.map((row) => (
              <li key={row.id}>
                <Link href={`/moderation/cases/${row.id}`} className="block rounded-xl border border-line p-4 transition hover:border-ink">
                  <div className="flex flex-wrap items-center gap-2 text-xs">
                    <span className={`rounded-full px-2.5 py-1 font-bold ${PRIORITY_STYLES[row.priority]}`}>{row.priority_label}</span>
                    {row.escalated && <span className="rounded-full border border-ink px-2.5 py-1 font-bold">Escalated</span>}
                    {row.recent_consequences >= 2 && <span className="rounded-full border border-[var(--danger)] px-2.5 py-1 font-bold text-[var(--danger)]">Repeat offender · {row.recent_consequences} in 90 days</span>}
                    {row.prior_case_count > 0 && <span className="rounded-full bg-surface px-2.5 py-1 font-semibold">{row.prior_case_count} earlier {row.prior_case_count === 1 ? "case" : "cases"}</span>}
                    <span className="text-muted">{row.status === "open" ? "New" : row.status}</span>
                  </div>
                  <p className="mt-2 font-bold">{row.reasons.map((reason) => REASON_LABELS[reason as ReportReason] ?? reason).join(" · ")}</p>
                  <p className="mt-0.5 text-sm">{caseTarget(row)}</p>
                  <p className="mt-1 text-xs text-muted">
                    Reported by {row.reporter_count} {row.reporter_count === 1 ? "student" : "students"}
                    {row.school_name ? ` · ${row.school_name}` : ""}
                    {row.latest_report_at ? ` · ${ago(row.latest_report_at)}` : ""}
                    {row.assigned_to ? ` · Assigned to @${row.assigned_to.username}` : " · Unassigned"}
                  </p>
                </Link>
              </li>
            ))}
          </ul>
        )}
      </section>
    </main>
  );
}
