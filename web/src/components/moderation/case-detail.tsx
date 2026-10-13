"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { ModeratorsOnly } from "@/components/moderation/queue";
import type { components } from "@/lib/api/schema";
import {
  actOnCase,
  caseTarget,
  getCase,
  liftRestriction,
  PRIORITY_STYLES,
  type CaseAction,
  type CaseDetail,
} from "@/lib/moderation";
import { centsToDollars } from "@/lib/money";
import { formatDateTime } from "@/lib/time";
import { REASON_LABELS, type ReportReason } from "@/lib/trust";

type Report = components["schemas"]["CaseReport"];
type Evidence = components["schemas"]["Evidence"];
type Action = components["schemas"]["Action"];
type Restriction = components["schemas"]["StaffRestriction"];
type Appeal = components["schemas"]["StaffAppeal"];
type InfoRequest = components["schemas"]["StaffInfoRequest"];
type ActionName = CaseAction["action"];

const DAY = 24 * 60 * 60 * 1000;
const DURATIONS: [string, number][] = [
  ["1 day", 1],
  ["3 days", 3],
  ["7 days", 7],
  ["30 days", 30],
];

// Consequences the student is told about; the moderator can write what they see.
const NOTICE_ACTIONS = new Set<ActionName>(["warn", "restrict", "suspend", "ban", "remove_listing"]);

const ACTIONS: { value: ActionName; label: string; senior?: boolean; needsUser?: boolean; listing?: "remove" | "restore"; tone?: "danger" }[] = [
  { value: "note", label: "Add note" },
  { value: "request_info", label: "Ask for more information", needsUser: true },
  { value: "dismiss", label: "Dismiss: no violation" },
  { value: "warn", label: "Send warning", needsUser: true },
  { value: "restrict", label: "Restrict a feature", needsUser: true },
  { value: "remove_listing", label: "Remove listing", listing: "remove", tone: "danger" },
  { value: "restore_listing", label: "Restore listing", listing: "restore" },
  { value: "suspend", label: "Suspend account", senior: true, needsUser: true, tone: "danger" },
  { value: "ban", label: "Ban permanently", senior: true, needsUser: true, tone: "danger" },
  { value: "escalate", label: "Escalate to a senior" },
  { value: "resolve", label: "Resolve case" },
];

function daysFromNow(days: number) {
  return new Date(Date.now() + days * DAY).toISOString();
}

function text(value: unknown) {
  return typeof value === "string" ? value : value == null ? "" : String(value);
}

export function CaseDetailView({ caseId }: { caseId: number }) {
  const [detail, setDetail] = useState<CaseDetail | null>();
  const [denied, setDenied] = useState("");

  useEffect(() => {
    let active = true;
    getCase(caseId)
      .then((data) => active && setDetail(data))
      .catch((caught) => {
        if (!active) return;
        setDetail(null);
        setDenied(caught instanceof Error ? caught.message : "This case isn't available to you.");
      });
    return () => {
      active = false;
    };
  }, [caseId]);

  async function reload() {
    setDetail(await getCase(caseId));
  }

  if (detail === undefined) return <main className="mx-auto min-h-[70vh] max-w-6xl animate-pulse px-4 py-10 sm:px-6"><div className="h-8 w-64 rounded bg-surface" /><div className="mt-6 h-96 rounded-xl bg-surface" /></main>;
  if (detail === null) return <ModeratorsOnly message={denied} />;

  const row = detail.case;
  return (
    <main className="mx-auto min-h-[70vh] max-w-6xl px-4 py-8 pb-28 sm:px-6 desktop:pb-12">
      <Link href="/moderation" className="text-sm font-bold text-muted hover:text-ink">← Moderation queue</Link>
      <div className="mt-3 flex flex-wrap items-center gap-2 text-xs">
        <span className={`rounded-full px-2.5 py-1 font-bold ${PRIORITY_STYLES[row.priority]}`}>{row.priority_label}</span>
        <span className="rounded-full bg-surface px-2.5 py-1 font-semibold capitalize">{row.status}</span>
        {row.escalated && <span className="rounded-full border border-ink px-2.5 py-1 font-bold">Escalated</span>}
        {detail.legal_hold && <span className="rounded-full border border-ink px-2.5 py-1 font-bold">Legal hold</span>}
        <span className="text-muted">Case #{row.id}{row.school_name ? ` · ${row.school_name}` : ""} · opened {formatDateTime(row.created_at)}</span>
      </div>
      <h1 className="type-wide mt-2 text-2xl font-black">{row.reasons.map((reason) => REASON_LABELS[reason as ReportReason] ?? reason).join(" · ")}</h1>
      <p className="mt-1">
        {caseTarget(row)}
        {row.listing && <> · <span className="text-muted">now {row.listing.status}{row.listing.removed_by ? ` (by ${row.listing.removed_by})` : ""}</span></>}
      </p>
      <p className="mt-1 text-sm text-muted">{row.assigned_to ? `Assigned to @${row.assigned_to.username}` : "Unassigned"}</p>

      <div className="mt-6 grid items-start gap-6 lg:grid-cols-[minmax(0,1fr)_21rem]">
        <div className="min-w-0 space-y-6">
          <section aria-labelledby="reports-heading">
            <h2 id="reports-heading" className="text-lg font-black">Reports ({detail.reports.length})</h2>
            <ul className="mt-3 space-y-3">
              {detail.reports.map((report) => <ReportCard key={report.id} report={report} />)}
            </ul>
            {detail.reporter_records.some((record) => record.reviewed > 0) && (
              <div className="mt-3 rounded-xl bg-surface p-3 text-sm">
                <p className="font-bold">Reporters&apos; track record</p>
                <ul className="mt-1 space-y-1">
                  {detail.reporter_records.filter((record) => record.reviewed > 0).map((record) => (
                    <li key={record.user.id}>
                      @{record.user.username}: {record.upheld} of {record.reviewed} reviewed reports led to action
                      {record.possible_false_reporter && <span className="ml-2 rounded-full border border-signal px-2 py-0.5 text-xs font-bold">Mostly dismissed</span>}
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </section>
          {detail.appeals.length > 0 && <Appeals appeals={detail.appeals} caseId={row.id} onChange={setDetail} />}
          {detail.info_requests.length > 0 && <InfoRequests requests={detail.info_requests} />}
          <SubjectHistory detail={detail} onChanged={reload} />
          <ActivityLog actions={detail.actions} />
        </div>
        <ActionPanel detail={detail} onChange={setDetail} />
      </div>
    </main>
  );
}

function ReportCard({ report }: { report: Report }) {
  return (
    <li className="rounded-xl border border-line p-4">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <p className="font-bold">
          {report.reason_label}
          {report.prohibited_category && <span className="font-semibold text-[var(--danger)]"> · {report.prohibited_category}</span>}
        </p>
        <p className="text-xs text-muted">@{report.reporter.username} · {formatDateTime(report.created_at)} · {report.target_type}</p>
      </div>
      {report.details && <p className="mt-2 whitespace-pre-line text-sm">“{report.details}”</p>}
      {report.evidence.length > 0 && (
        <div className="mt-3 space-y-2 rounded-lg bg-surface p-3">
          <p className="text-xs font-bold uppercase tracking-wide text-muted">Evidence saved at report time</p>
          {report.evidence.map((snapshot) => <EvidenceView key={snapshot.id} snapshot={snapshot} />)}
        </div>
      )}
    </li>
  );
}

function EvidenceView({ snapshot }: { snapshot: Evidence }) {
  const data = snapshot.data as Record<string, unknown>;
  if (snapshot.kind === "listing") {
    return (
      <div className="text-sm">
        <p className="font-bold">{text(data.title)} · {centsToDollars(Number(data.price_cents ?? 0))}</p>
        <p className="text-xs text-muted">{[data.category, data.condition, data.brand, `status: ${text(data.status)}`].filter(Boolean).map(text).join(" · ")}</p>
        {text(data.description) && <p className="mt-1 whitespace-pre-line">{text(data.description)}</p>}
        {snapshot.files.length > 0 && (
          <div className="mt-2 flex flex-wrap gap-2">
            {snapshot.files.map((url) => (
              <a key={url} href={url} target="_blank" rel="noreferrer" className="block size-24 overflow-hidden rounded-md bg-background">
                {/* eslint-disable-next-line @next/next/no-img-element -- evidence copies are runtime media. */}
                <img src={url} alt="Reported listing photo" className="size-full object-cover" />
              </a>
            ))}
          </div>
        )}
      </div>
    );
  }
  if (snapshot.kind === "message") {
    return (
      <div className="rounded-lg bg-background p-2 text-sm">
        <p className="text-xs font-bold text-muted">@{text(data.sender)} · {data.sent_at ? formatDateTime(text(data.sent_at)) : ""}</p>
        <p className="whitespace-pre-line break-words">{text(data.body)}</p>
      </div>
    );
  }
  if (snapshot.kind === "profile") {
    return (
      <div className="text-sm">
        <p className="font-bold">@{text(data.username)} {text(data.first_name)}</p>
        {text(data.profile_description) && <p className="mt-1">{text(data.profile_description)}</p>}
        {text(data.instagram_handle) && <p className="text-xs text-muted">Instagram: @{text(data.instagram_handle)}</p>}
      </div>
    );
  }
  if (snapshot.kind === "deal") {
    const events = (data.events as { type: string; at: string }[] | undefined) ?? [];
    const meetups = (data.meetups as { spot: string; starts_at: string; status: string }[] | undefined) ?? [];
    return (
      <div className="text-sm">
        <p className="font-bold">{text(data.listing)} · {text(data.kind)} · {text(data.status)}</p>
        {meetups.length > 0 && (
          <ul className="mt-1 text-xs">
            {meetups.map((meetup, index) => <li key={index}>Meetup: {meetup.spot}, {formatDateTime(meetup.starts_at)} ({meetup.status})</li>)}
          </ul>
        )}
        <ol className="mt-1 space-y-0.5 text-xs text-muted">
          {events.map((event, index) => <li key={index}>{formatDateTime(event.at)} · {event.type.replaceAll("_", " ")}</li>)}
        </ol>
      </div>
    );
  }
  if (snapshot.kind === "review") {
    return (
      <div className="text-sm">
        <p className="font-bold">{text(data.rating)}/5 by @{text(data.author)}</p>
        {text(data.comment) && <p className="mt-1">{text(data.comment)}</p>}
      </div>
    );
  }
  return <pre className="overflow-x-auto text-xs">{JSON.stringify(data, null, 2)}</pre>;
}

function SubjectHistory({ detail, onChanged }: { detail: CaseDetail; onChanged: () => Promise<void> }) {
  const subject = detail.subject;
  return (
    <section aria-labelledby="subject-heading" className="rounded-xl border border-line p-4">
      <h2 id="subject-heading" className="text-lg font-black">
        <Link href={`/users/${subject.user.username}`} className="hover:underline">@{subject.user.username}</Link>
        <span className="ml-2 text-sm font-semibold text-muted">{subject.user.first_name}</span>
      </h2>
      <p className="mt-1 text-sm text-muted">
        {subject.email} · {subject.school_name || "No school"} · joined {formatDateTime(subject.date_joined)}
        {!subject.is_active && <span className="font-bold text-[var(--danger)]"> · account off</span>}
      </p>
      {subject.repeat_offender && (
        <p className="mt-2 inline-block rounded-full border border-[var(--danger)] px-2.5 py-1 text-xs font-bold text-[var(--danger)]">
          Repeat offender · {subject.recent_consequences} consequences in 90 days
        </p>
      )}
      <p className="mt-1 text-sm">
        Reported {subject.reports_received} {subject.reports_received === 1 ? "time" : "times"} · has filed {subject.reports_made} {subject.reports_made === 1 ? "report" : "reports"}
      </p>

      <h3 className="mt-4 text-sm font-bold">Active restrictions</h3>
      {subject.active_restrictions.length === 0 ? (
        <p className="text-sm text-muted">None.</p>
      ) : (
        <ul className="mt-1 space-y-2">
          {subject.active_restrictions.map((restriction) => (
            <RestrictionRow key={restriction.id} restriction={restriction} caseId={detail.case.id} senior={detail.viewer.is_senior} onLifted={onChanged} />
          ))}
        </ul>
      )}

      <h3 className="mt-4 text-sm font-bold">Earlier warnings and actions</h3>
      {subject.past_actions.length === 0 ? (
        <p className="text-sm text-muted">None.</p>
      ) : (
        <ul className="mt-1 space-y-1 text-sm">
          {subject.past_actions.map((action) => (
            <li key={action.id}>
              <span className="font-semibold">{action.kind_label}</span> · {formatDateTime(action.created_at)}
              {action.case_id && <> · <Link href={`/moderation/cases/${action.case_id}`} className="underline">case #{action.case_id}</Link></>}
              <span className="block text-muted">{action.reason}</span>
            </li>
          ))}
        </ul>
      )}

      <h3 className="mt-4 text-sm font-bold">Other cases about them</h3>
      {subject.other_cases.length === 0 ? (
        <p className="text-sm text-muted">None.</p>
      ) : (
        <ul className="mt-1 space-y-1 text-sm">
          {subject.other_cases.map((other) => (
            <li key={other.id}>
              <Link href={`/moderation/cases/${other.id}`} className="underline">Case #{other.id}</Link> · {other.reasons.map((reason) => REASON_LABELS[reason as ReportReason] ?? reason).join(", ")} · {other.status}
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

function RestrictionRow({ restriction, caseId, senior, onLifted }: { restriction: Restriction; caseId: number; senior: boolean; onLifted: () => Promise<void> }) {
  const [lifting, setLifting] = useState(false);
  const [reason, setReason] = useState("");
  const [error, setError] = useState("");
  const needsSenior = restriction.kind === "suspension" || restriction.kind === "ban";

  async function lift() {
    setError("");
    try {
      await liftRestriction(restriction.id, reason, caseId);
      await onLifted();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Couldn't lift it.");
    }
  }

  return (
    <li className="rounded-lg bg-surface p-3 text-sm">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <span>
          <span className="font-bold">{restriction.kind_label}</span> · {restriction.expires_at ? `until ${formatDateTime(restriction.expires_at)}` : "until lifted"}
        </span>
        {!lifting && (!needsSenior || senior) && <button type="button" onClick={() => setLifting(true)} className="text-sm font-semibold underline">Lift</button>}
      </div>
      <p className="mt-1 text-muted">{restriction.reason}</p>
      {lifting && (
        <div className="mt-2 flex flex-wrap gap-2">
          <input value={reason} onChange={(event) => setReason(event.target.value)} placeholder="Why lift it?" aria-label="Reason for lifting" className="field h-9 min-w-0 flex-1 px-3" />
          <button type="button" onClick={lift} className="btn btn-primary btn-sm">Lift</button>
          <button type="button" onClick={() => setLifting(false)} className="btn btn-secondary btn-sm">Cancel</button>
        </div>
      )}
      {error && <p role="alert" className="mt-1 text-[var(--danger)]">{error}</p>}
    </li>
  );
}

function ActivityLog({ actions }: { actions: Action[] }) {
  return (
    <section aria-labelledby="activity-heading">
      <h2 id="activity-heading" className="text-lg font-black">Activity</h2>
      {actions.length === 0 ? (
        <p className="mt-2 text-sm text-muted">No actions yet.</p>
      ) : (
        <ol className="mt-3 space-y-3 border-l border-line pl-4">
          {actions.map((action) => (
            <li key={action.id} className="text-sm">
              <p>
                <span className="font-bold">{action.kind_label}</span>
                {action.target_user && <> · @{action.target_user.username}</>}
                <span className="text-muted"> · {action.actor ? `@${action.actor.username}` : "System"} · {formatDateTime(action.created_at)}</span>
              </p>
              <p className="whitespace-pre-line text-muted">{action.reason}</p>
            </li>
          ))}
        </ol>
      )}
    </section>
  );
}

function ActionPanel({ detail, onChange }: { detail: CaseDetail; onChange: (detail: CaseDetail) => void }) {
  const viewer = detail.viewer;
  const listing = detail.case.listing;
  const [chosen, setChosen] = useState<ActionName | "">("");
  const [userId, setUserId] = useState(detail.case.subject_user.id);
  const [kind, setKind] = useState<"selling" | "messaging" | "deals">("selling");
  const [days, setDays] = useState(7);
  const [reason, setReason] = useState("");
  const [userMessage, setUserMessage] = useState("");
  const [override, setOverride] = useState("");
  const [assignee, setAssignee] = useState("");
  const [confirmBan, setConfirmBan] = useState(false);
  const [working, setWorking] = useState(false);
  const [error, setError] = useState("");
  const [saved, setSaved] = useState("");

  const blocked = !viewer.can_act && !(viewer.conflict_overridable && viewer.is_senior && override.trim());
  const available = ACTIONS.filter((action) => {
    if (action.listing === "remove") return listing && listing.status !== "removed";
    if (action.listing === "restore") return listing && listing.status === "removed" && listing.removed_by === "moderation";
    return true;
  });
  const current = ACTIONS.find((action) => action.value === chosen);

  async function send(body: Omit<CaseAction, "override_reason" | "user_message"> & { user_message?: string }, label: string) {
    setWorking(true);
    setError("");
    setSaved("");
    try {
      onChange(await actOnCase(detail.case.id, { user_message: "", ...body, override_reason: override }));
      setSaved(label);
      setReason("");
      setUserMessage("");
      setChosen("");
      setConfirmBan(false);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "That action didn't go through.");
    } finally {
      setWorking(false);
    }
  }

  function submit() {
    if (!current) return;
    const until = current.value === "suspend" || (current.value === "restrict" && days > 0)
      ? daysFromNow(days)
      : null;
    void send(
      {
        action: current.value,
        reason,
        ...(NOTICE_ACTIONS.has(current.value) ? { user_message: userMessage } : {}),
        ...(current.needsUser ? { user_id: userId } : {}),
        ...(current.value === "restrict" ? { restriction_kind: kind } : {}),
        ...(until ? { until } : {}),
      },
      `${current.label} saved.`,
    );
  }

  return (
    <aside className="space-y-4 lg:sticky lg:top-24" aria-label="Actions">
      {!viewer.can_act && (
        <div className="rounded-xl border border-[var(--danger)] p-4 text-sm">
          <p className="font-bold">You can&apos;t act on this case because {viewer.conflict}.</p>
          {viewer.conflict_overridable && viewer.is_senior ? (
            <label className="mt-2 block">
              <span className="text-muted">As a senior moderator you can override it. Your reason is logged.</span>
              <textarea value={override} onChange={(event) => setOverride(event.target.value)} rows={2} aria-label="Override reason" className="field mt-2 w-full resize-none p-2" />
            </label>
          ) : (
            <p className="mt-1 text-muted">Pass it to another moderator.</p>
          )}
        </div>
      )}

      <div className="rounded-xl border border-line p-4">
        <h2 className="font-black">Assign</h2>
        <div className="mt-2 flex gap-2">
          <select value={assignee} onChange={(event) => setAssignee(event.target.value)} aria-label="Moderator" className="field h-10 min-w-0 flex-1 px-2 text-sm">
            <option value="">Choose a moderator</option>
            {detail.eligible_assignees.map((user) => <option key={user.id} value={user.id}>@{user.username}</option>)}
          </select>
          <button type="button" disabled={working || blocked || !assignee} onClick={() => send({ action: "assign", reason: "Assigned", assignee_id: Number(assignee) }, "Case assigned.")} className="btn btn-secondary btn-sm">Assign</button>
        </div>
      </div>

      <div className="rounded-xl border border-line p-4">
        <h2 className="font-black">Take action</h2>
        <div className="mt-2 grid gap-1.5" role="group" aria-label="Action">
          {available.map((action) => {
            const locked = action.senior && !viewer.is_senior;
            return (
              <button
                key={action.value}
                type="button"
                disabled={locked || blocked}
                onClick={() => {
                  setChosen(action.value);
                  // Start each action on the reported student, so a choice made for an
                  // earlier action (e.g. asking a reporter) can't carry over by accident.
                  setUserId(detail.case.subject_user.id);
                  setError("");
                  setSaved("");
                }}
                aria-pressed={chosen === action.value}
                className={`rounded-lg border px-3 py-2 text-left text-sm font-semibold disabled:opacity-50 ${chosen === action.value ? "border-ink ring-1 ring-ink" : "border-line"} ${action.tone === "danger" ? "text-[var(--danger)]" : ""}`}
              >
                {action.label}{locked ? " (senior only)" : ""}
              </button>
            );
          })}
        </div>

        {current && (
          <div className="mt-4 space-y-3 border-t border-line pt-3 text-sm">
            {current.needsUser && (
              <label className="block font-bold">
                Student
                <select value={userId} onChange={(event) => setUserId(Number(event.target.value))} className="field mt-1 h-10 w-full px-2 font-normal">
                  {detail.involved_users.map((user, index) => <option key={user.id} value={user.id}>@{user.username}{index === 0 ? " (reported)" : " (reporter)"}</option>)}
                </select>
              </label>
            )}
            {current.value === "restrict" && (
              <label className="block font-bold">
                Restrict
                <select value={kind} onChange={(event) => setKind(event.target.value as typeof kind)} className="field mt-1 h-10 w-full px-2 font-normal">
                  <option value="selling">Selling</option>
                  <option value="messaging">Messaging</option>
                  <option value="deals">Buying and deals</option>
                </select>
              </label>
            )}
            {(current.value === "restrict" || current.value === "suspend") && (
              <label className="block font-bold">
                For
                <select value={days} onChange={(event) => setDays(Number(event.target.value))} className="field mt-1 h-10 w-full px-2 font-normal">
                  {DURATIONS.map(([label, value]) => <option key={value} value={value}>{label}</option>)}
                  {current.value === "restrict" && <option value={0}>Until lifted</option>}
                </select>
              </label>
            )}
            {current.value === "suspend" && <p className="text-muted">Signs them out and cancels all their open deals, including Pending ones.</p>}
            {current.value === "ban" && (
              <label className="flex items-start gap-2 font-semibold text-[var(--danger)]">
                <input type="checkbox" checked={confirmBan} onChange={(event) => setConfirmBan(event.target.checked)} className="mt-0.5" />
                I understand this is permanent: their deals are canceled, listings removed, and their email can&apos;t sign up again.
              </label>
            )}
            {NOTICE_ACTIONS.has(current.value) && (
              <label className="block font-bold">
                Message to the student <span className="font-normal text-muted">(optional)</span>
                <textarea value={userMessage} onChange={(event) => setUserMessage(event.target.value)} rows={3} placeholder="Leave blank to send Tanu's standard message for this action." className="field mt-1 w-full resize-none p-2 font-normal" />
              </label>
            )}
            <label className="block font-bold">
              {current.value === "note" ? "Note" : current.value === "request_info" ? "Question" : "Internal reason"}{" "}
              <span className="font-normal text-muted">{current.value === "request_info" ? "(the student sees this)" : "(required, staff only, logged permanently)"}</span>
              <textarea value={reason} onChange={(event) => setReason(event.target.value)} rows={3} className="field mt-1 w-full resize-none p-2 font-normal" />
            </label>
            <button type="button" onClick={submit} disabled={working || blocked || !reason.trim() || (current.value === "ban" && !confirmBan)} className={`btn w-full ${current.tone === "danger" ? "bg-[var(--danger)] text-white" : "btn-primary"}`}>
              {working ? "Saving…" : current.label}
            </button>
          </div>
        )}
        {error && <p role="alert" className="mt-3 text-sm text-[var(--danger)]">{error}</p>}
        {saved && <p role="status" className="mt-3 text-sm font-semibold text-brand">{saved}</p>}
      </div>
    </aside>
  );
}

function Appeals({ appeals, caseId, onChange }: { appeals: Appeal[]; caseId: number; onChange: (detail: CaseDetail) => void }) {
  return (
    <section aria-labelledby="appeals-heading" className="rounded-xl border border-signal p-4">
      <h2 id="appeals-heading" className="text-lg font-black">Appeals</h2>
      <ul className="mt-3 space-y-3">
        {appeals.map((appeal) => <AppealItem key={appeal.id} appeal={appeal} caseId={caseId} onChange={onChange} />)}
      </ul>
    </section>
  );
}

function AppealItem({ appeal, caseId, onChange }: { appeal: Appeal; caseId: number; onChange: (detail: CaseDetail) => void }) {
  const [reason, setReason] = useState("");
  const [working, setWorking] = useState(false);
  const [error, setError] = useState("");

  async function decide(decision: "uphold" | "overturn") {
    setWorking(true);
    setError("");
    try {
      onChange(await actOnCase(caseId, { action: "decide_appeal", appeal_id: appeal.id, decision, reason, user_message: "", override_reason: "" }));
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "That didn't go through.");
    } finally {
      setWorking(false);
    }
  }

  return (
    <li className="rounded-lg bg-surface p-3 text-sm">
      <p className="font-bold">
        @{appeal.user.username} appealed: {appeal.action.kind_label}
        <span className="font-normal text-muted"> by {appeal.action.actor ? `@${appeal.action.actor.username}` : "System"} · {formatDateTime(appeal.created_at)}</span>
      </p>
      <p className="mt-1 whitespace-pre-line">“{appeal.message}”</p>
      {appeal.status === "pending" ? (
        <div className="mt-3 space-y-2">
          <textarea value={reason} onChange={(event) => setReason(event.target.value)} rows={2} placeholder="Why? (staff only)" aria-label="Appeal decision reason" className="field w-full resize-none p-2" />
          <div className="flex gap-2">
            <button type="button" disabled={working || !reason.trim()} onClick={() => decide("uphold")} className="btn btn-secondary btn-sm">Uphold decision</button>
            <button type="button" disabled={working || !reason.trim()} onClick={() => decide("overturn")} className="btn btn-primary btn-sm">Overturn and undo</button>
          </div>
          <p className="text-xs text-muted">A different moderator from the one who made the decision has to review it.</p>
          {error && <p role="alert" className="text-[var(--danger)]">{error}</p>}
        </div>
      ) : (
        <p className="mt-2 font-semibold">
          {appeal.status === "overturned" ? "Overturned" : "Upheld"} by @{appeal.decided_by?.username}: <span className="font-normal text-muted">{appeal.decision_reason}</span>
        </p>
      )}
    </li>
  );
}

function InfoRequests({ requests }: { requests: InfoRequest[] }) {
  return (
    <section aria-labelledby="questions-heading" className="rounded-xl border border-line p-4">
      <h2 id="questions-heading" className="text-lg font-black">Questions to students</h2>
      <ul className="mt-3 space-y-3 text-sm">
        {requests.map((request) => (
          <li key={request.id}>
            <p><span className="font-bold">To @{request.recipient.username}</span> <span className="text-muted">from @{request.asked_by.username} · {formatDateTime(request.created_at)}</span></p>
            <p className="mt-1">Q: {request.question}</p>
            <p className="mt-1 text-muted">{request.answer ? `A: ${request.answer}` : "Waiting for an answer."}</p>
          </li>
        ))}
      </ul>
    </section>
  );
}
