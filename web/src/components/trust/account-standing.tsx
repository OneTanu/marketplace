"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { RestrictionNotice } from "@/components/trust/restriction-notice";
import type { components } from "@/lib/api/schema";
import { formatDateTime } from "@/lib/time";
import { answerInfoRequest, fileAppeal, getMyStanding } from "@/lib/trust";

type Standing = components["schemas"]["Standing"];
type Notice = components["schemas"]["MyNotice"];
type InfoRequest = components["schemas"]["MyInfoRequest"];

const APPEAL_STATUS: Record<string, string> = {
  pending: "Your appeal is being reviewed by a different moderator.",
  upheld: "Your appeal was reviewed. The decision stands.",
  overturned: "Your appeal was accepted and the decision was reversed.",
};

/** A student's own account status: what's paused, decisions about them (with appeals), and
 * questions from moderators. */
export function AccountStanding() {
  const [standing, setStanding] = useState<Standing | null>();

  useEffect(() => {
    let active = true;
    getMyStanding()
      .then((data) => active && setStanding(data))
      .catch(() => active && setStanding(null));
    return () => {
      active = false;
    };
  }, []);

  async function reload() {
    setStanding(await getMyStanding());
  }

  if (standing === undefined) return <main className="mx-auto min-h-[70vh] max-w-2xl animate-pulse px-4 py-10"><div className="h-64 rounded-2xl bg-surface" /></main>;
  if (standing === null) return <main className="mx-auto grid min-h-[70vh] max-w-xl place-items-center px-4 text-center"><div><h1 className="type-wide text-3xl font-black">Log in to see your account status</h1><Link href="/account/login" className="btn btn-primary mt-6">Log in</Link></div></main>;

  const openQuestions = standing.info_requests.filter((request) => !request.answered_at);
  const allClear = !standing.restrictions.length && !standing.notices.length && !standing.info_requests.length;

  return (
    <main className="mx-auto min-h-[70vh] max-w-2xl px-4 py-8 pb-28 sm:px-6 desktop:pb-12">
      <Link href="/profile" className="text-sm font-bold text-muted hover:text-ink">← Back to profile</Link>
      <h1 className="type-wide mt-4 text-3xl font-black">Account status</h1>
      <p className="mt-2 text-muted">Decisions Tanu&apos;s moderators have made about your account, and any questions they have for you.</p>

      <div className="mt-6"><RestrictionNotice /></div>
      {allClear && <p className="rounded-xl bg-surface p-6 text-center text-sm text-muted">Your account is in good standing. Nothing to show here.</p>}

      {openQuestions.length > 0 && (
        <section aria-labelledby="questions-heading" className="mt-6">
          <h2 id="questions-heading" className="text-lg font-black">Questions from moderators</h2>
          <ul className="mt-3 space-y-3">
            {openQuestions.map((request) => <QuestionItem key={request.id} request={request} onAnswered={reload} />)}
          </ul>
        </section>
      )}

      {standing.notices.length > 0 && (
        <section aria-labelledby="decisions-heading" className="mt-6">
          <h2 id="decisions-heading" className="text-lg font-black">Decisions</h2>
          <ul className="mt-3 space-y-3">
            {standing.notices.map((notice) => <NoticeItem key={notice.id} notice={notice} onAppealed={reload} />)}
          </ul>
        </section>
      )}
    </main>
  );
}

function NoticeItem({ notice, onAppealed }: { notice: Notice; onAppealed: () => Promise<void> }) {
  const [appealing, setAppealing] = useState(false);
  const [message, setMessage] = useState("");
  const [working, setWorking] = useState(false);
  const [error, setError] = useState("");

  async function submit() {
    setWorking(true);
    setError("");
    try {
      await fileAppeal(notice.id, message);
      await onAppealed();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Your appeal didn't go through.");
      setWorking(false);
    }
  }

  return (
    <li className="rounded-xl border border-line p-4 text-sm">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <p className="font-bold">{notice.kind_label}</p>
        <p className="text-xs text-muted">{formatDateTime(notice.created_at)}</p>
      </div>
      {notice.message && <p className="mt-1 whitespace-pre-line">{notice.message}</p>}
      {notice.appeal ? (
        <p className="mt-3 rounded-lg bg-surface p-3 font-semibold">{APPEAL_STATUS[notice.appeal.status]}</p>
      ) : notice.can_appeal ? (
        appealing ? (
          <div className="mt-3 space-y-2">
            <label className="block font-bold">
              Why should we look at this again?
              <textarea value={message} onChange={(event) => setMessage(event.target.value)} maxLength={2000} rows={4} className="field mt-1 w-full resize-none p-3 font-normal" />
            </label>
            {error && <p role="alert" className="text-[var(--danger)]">{error}</p>}
            <div className="flex gap-2">
              <button type="button" onClick={() => setAppealing(false)} disabled={working} className="btn btn-secondary btn-sm">Cancel</button>
              <button type="button" onClick={submit} disabled={working || !message.trim()} className="btn btn-primary btn-sm">{working ? "Sending…" : "Send appeal"}</button>
            </div>
          </div>
        ) : (
          <button type="button" onClick={() => setAppealing(true)} className="mt-3 text-sm font-semibold underline">
            Appeal this decision <span className="font-normal text-muted">(until {formatDateTime(notice.appeal_deadline)})</span>
          </button>
        )
      ) : null}
    </li>
  );
}

function QuestionItem({ request, onAnswered }: { request: InfoRequest; onAnswered: () => Promise<void> }) {
  const [answer, setAnswer] = useState("");
  const [working, setWorking] = useState(false);
  const [error, setError] = useState("");

  async function submit() {
    setWorking(true);
    setError("");
    try {
      await answerInfoRequest(request.id, answer);
      await onAnswered();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Your answer didn't go through.");
      setWorking(false);
    }
  }

  return (
    <li className="rounded-xl border border-signal p-4 text-sm">
      <p className="text-xs text-muted">{formatDateTime(request.created_at)}</p>
      <p className="mt-1 font-bold">{request.question}</p>
      <label className="mt-2 block">
        <span className="sr-only">Your answer</span>
        <textarea value={answer} onChange={(event) => setAnswer(event.target.value)} maxLength={2000} rows={3} aria-label="Your answer" className="field w-full resize-none p-3" />
      </label>
      {error && <p role="alert" className="mt-1 text-[var(--danger)]">{error}</p>}
      <button type="button" onClick={submit} disabled={working || !answer.trim()} className="btn btn-primary btn-sm mt-2">{working ? "Sending…" : "Send answer"}</button>
    </li>
  );
}
