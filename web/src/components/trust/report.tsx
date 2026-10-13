"use client";

import { useEffect, useId, useState } from "react";
import { createPortal } from "react-dom";

import {
  blockUser,
  listBlocks,
  submitReport,
  unblockUser,
  type ProhibitedCategory,
  type ReportReason,
  type ReportTargetType,
} from "@/lib/trust";

const REASON_LABELS: Record<ReportReason, string> = {
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

// The reasons that make sense for each kind of thing.
const REASONS: Record<ReportTargetType, ReportReason[]> = {
  listing: ["prohibited_item", "counterfeit", "misleading_listing", "scam", "spam", "other"],
  user: ["inappropriate", "harassment", "scam", "spam", "other"],
  message: ["harassment", "scam", "spam", "inappropriate", "unsafe_meetup", "other"],
  conversation: ["harassment", "scam", "spam", "inappropriate", "unsafe_meetup", "other"],
  deal: ["no_show", "unsafe_meetup", "scam", "harassment", "other"],
  review: ["inappropriate", "harassment", "spam", "other"],
};

const PROHIBITED: [ProhibitedCategory, string][] = [
  ["weapon", "Weapon"],
  ["drugs", "Drugs or prescriptions"],
  ["alcohol", "Alcohol"],
  ["tobacco", "Tobacco or vapes"],
  ["food", "Food"],
  ["stolen", "Stolen goods"],
  ["other", "Something else"],
];

const SAFETY_REASONS = new Set<ReportReason>(["harassment", "unsafe_meetup"]);

export type EvidenceMessage = { id: number; body: string; from: string };

/**
 * A "Report" button that opens a short form: reason, optional details, (for a conversation)
 * which messages show the problem, and an option to block the student too.
 */
export function ReportButton({
  targetType,
  targetId,
  subject,
  username,
  messages,
  onBlocked,
  className = "text-sm font-semibold text-muted hover:text-ink hover:underline",
  label = "Report",
}: {
  targetType: ReportTargetType;
  targetId: number;
  /** What's being reported, as a phrase: "this listing", "@sam". */
  subject: string;
  /** The student it's about, for "Also block @username". */
  username: string;
  /** For a conversation report: the messages the reporter can choose from. */
  messages?: EvidenceMessage[];
  onBlocked?: () => void;
  className?: string;
  label?: string;
}) {
  const [open, setOpen] = useState(false);
  return (
    <>
      <button type="button" onClick={() => setOpen(true)} className={className}>
        {label}
      </button>
      {/* Portaled to <body>: a parent with a backdrop blur (like the listing's sticky action
          bar) would otherwise trap the fixed overlay inside itself. */}
      {open && createPortal(
        <ReportDialog
          targetType={targetType}
          targetId={targetId}
          subject={subject}
          username={username}
          messages={messages}
          onBlocked={onBlocked}
          onClose={() => setOpen(false)}
        />,
        document.body,
      )}
    </>
  );
}

function ReportDialog({
  targetType,
  targetId,
  subject,
  username,
  messages,
  onBlocked,
  onClose,
}: {
  targetType: ReportTargetType;
  targetId: number;
  subject: string;
  username: string;
  messages?: EvidenceMessage[];
  onBlocked?: () => void;
  onClose: () => void;
}) {
  const titleId = useId();
  const [reason, setReason] = useState<ReportReason | "">("");
  const [category, setCategory] = useState<ProhibitedCategory | "">("");
  const [details, setDetails] = useState("");
  const [chosen, setChosen] = useState<number[]>([]);
  const [alsoBlock, setAlsoBlock] = useState(false);
  const [sending, setSending] = useState(false);
  const [error, setError] = useState("");
  const [sent, setSent] = useState(false);
  const isConversation = targetType === "conversation";

  useEffect(() => {
    function onKey(event: KeyboardEvent) {
      if (event.key === "Escape") onClose();
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  async function submit() {
    if (!reason) {
      setError("Choose a reason.");
      return;
    }
    if (isConversation && chosen.length === 0) {
      setError("Choose the messages that show what happened.");
      return;
    }
    setSending(true);
    setError("");
    try {
      await submitReport({
        target_type: targetType,
        target_id: targetId,
        reason,
        prohibited_category: reason === "prohibited_item" ? category : "",
        details,
        message_ids: chosen,
        block: alsoBlock,
      });
      setSent(true);
      if (alsoBlock) onBlocked?.();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Your report didn't go through. Try again.");
    } finally {
      setSending(false);
    }
  }

  return (
    <div className="fixed inset-0 z-50 grid place-items-end bg-black/40 sm:place-items-center" onClick={onClose}>
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        onClick={(event) => event.stopPropagation()}
        className="max-h-[90dvh] w-full overflow-y-auto rounded-t-2xl bg-background p-5 shadow-xl sm:max-w-md sm:rounded-2xl"
      >
        {sent ? (
          <div className="text-center">
            <h2 id={titleId} className="type-wide text-xl font-black">Report received</h2>
            <p className="mt-2 text-sm leading-6 text-muted">
              Tanu&apos;s moderation team will review it. {alsoBlock && `You've also blocked @${username}.`}
            </p>
            <button type="button" onClick={onClose} autoFocus className="btn btn-primary mt-5 w-full">Done</button>
          </div>
        ) : (
          <>
            <h2 id={titleId} className="type-wide text-xl font-black">Report {subject}</h2>
            <p className="mt-1 text-sm text-muted">Reports are private. @{username} won&apos;t see who sent it.</p>

            <fieldset className="mt-4">
              <legend className="text-sm font-bold">What&apos;s wrong?</legend>
              <div className="mt-2 grid gap-1.5">
                {REASONS[targetType].map((value, index) => (
                  <label key={value} className={`flex cursor-pointer items-center gap-3 rounded-lg border px-3 py-2.5 text-sm ${reason === value ? "border-ink ring-1 ring-ink" : "border-line"}`}>
                    <input type="radio" name="reason" value={value} checked={reason === value} onChange={() => setReason(value)} autoFocus={index === 0} className="accent-[var(--brand)]" />
                    {REASON_LABELS[value]}
                  </label>
                ))}
              </div>
            </fieldset>

            {reason === "prohibited_item" && (
              <label className="mt-3 block text-sm font-bold">
                What kind of item?
                <select value={category} onChange={(event) => setCategory(event.target.value as ProhibitedCategory)} className="field mt-1.5 h-11 w-full px-3 font-normal">
                  <option value="">Choose one</option>
                  {PROHIBITED.map(([value, text]) => <option key={value} value={value}>{text}</option>)}
                </select>
              </label>
            )}

            {reason && SAFETY_REASONS.has(reason) && (
              <p className="mt-3 rounded-lg border border-[var(--danger)] p-3 text-sm font-semibold text-[var(--danger)]">
                If you&apos;re in immediate danger, call 911 or your campus police now. Reports aren&apos;t monitored around the clock.
              </p>
            )}

            {isConversation && messages && (
              <fieldset className="mt-4">
                <legend className="text-sm font-bold">Which messages show what happened?</legend>
                <p className="text-xs text-muted">Moderators only see the messages you choose.</p>
                <div className="mt-2 max-h-56 space-y-1.5 overflow-y-auto pr-1">
                  {messages.length === 0 && <p className="text-sm text-muted">No messages yet.</p>}
                  {messages.map((message) => (
                    <label key={message.id} className="flex cursor-pointer items-start gap-2 rounded-lg border border-line p-2 text-sm">
                      <input
                        type="checkbox"
                        checked={chosen.includes(message.id)}
                        onChange={() => setChosen((current) => current.includes(message.id) ? current.filter((id) => id !== message.id) : [...current, message.id])}
                        className="mt-1 accent-[var(--brand)]"
                      />
                      <span className="min-w-0">
                        <span className="block text-xs font-bold text-muted">{message.from}</span>
                        <span className="line-clamp-3 break-words">{message.body}</span>
                      </span>
                    </label>
                  ))}
                </div>
              </fieldset>
            )}

            <label className="mt-4 block text-sm font-bold">
              Anything else we should know? <span className="font-normal text-muted">(optional)</span>
              <textarea value={details} onChange={(event) => setDetails(event.target.value)} maxLength={1000} rows={3} className="field mt-1.5 w-full resize-none p-3 text-sm font-normal" />
            </label>

            <label className="mt-3 flex items-center gap-2 text-sm">
              <input type="checkbox" checked={alsoBlock} onChange={(event) => setAlsoBlock(event.target.checked)} className="accent-[var(--brand)]" />
              Also block @{username}
            </label>

            {error && <p role="alert" className="mt-3 text-sm text-[var(--danger)]">{error}</p>}
            <div className="mt-5 flex gap-2">
              <button type="button" onClick={onClose} disabled={sending} className="btn btn-secondary flex-1">Cancel</button>
              <button type="button" onClick={submit} disabled={sending} className="btn btn-primary flex-1">{sending ? "Sending…" : "Send report"}</button>
            </div>
          </>
        )}
      </div>
    </div>
  );
}

/** Block or unblock a student. Asks first, because blocking cancels open deals between you. */
export function BlockButton({
  username,
  className = "btn btn-secondary",
  onChange,
}: {
  username: string;
  className?: string;
  onChange?: (blocked: boolean) => void;
}) {
  const [blocked, setBlocked] = useState<boolean>();
  const [confirming, setConfirming] = useState(false);
  const [working, setWorking] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;
    listBlocks()
      .then((rows) => active && setBlocked(rows.some((row) => row.username === username)))
      .catch(() => active && setBlocked(false));
    return () => {
      active = false;
    };
  }, [username]);

  async function toggle() {
    setWorking(true);
    setError("");
    try {
      if (blocked) await unblockUser(username);
      else await blockUser(username);
      setBlocked(!blocked);
      setConfirming(false);
      onChange?.(!blocked);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "That didn't go through.");
    } finally {
      setWorking(false);
    }
  }

  if (blocked === undefined) return null;
  if (confirming) {
    return (
      <div className="rounded-lg border border-line bg-background p-3 text-sm">
        <p className="font-semibold">Block @{username}?</p>
        <p className="mt-1 text-muted">You won&apos;t be able to message, buy from, or sell to each other, and any open requests between you are canceled. They won&apos;t be told.</p>
        {error && <p role="alert" className="mt-2 text-[var(--danger)]">{error}</p>}
        <div className="mt-3 flex gap-2">
          <button type="button" onClick={() => setConfirming(false)} disabled={working} className="btn btn-secondary btn-sm">Cancel</button>
          <button type="button" onClick={toggle} disabled={working} className="btn btn-primary btn-sm">{working ? "Blocking…" : "Block"}</button>
        </div>
      </div>
    );
  }
  return (
    <>
      <button type="button" onClick={() => (blocked ? toggle() : setConfirming(true))} disabled={working} className={className}>
        {blocked ? "Unblock" : "Block"}
      </button>
      {error && <p role="alert" className="text-sm text-[var(--danger)]">{error}</p>}
    </>
  );
}
