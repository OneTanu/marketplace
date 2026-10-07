"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { listConversations, type Conversation } from "@/lib/messaging";
import { Avatar } from "./avatar";

function time(value: string | null) {
  if (!value) return "";
  const date = new Date(value);
  const today = new Date();
  if (date.toDateString() === today.toDateString()) {
    return new Intl.DateTimeFormat(undefined, { hour: "numeric", minute: "2-digit" }).format(date);
  }
  return new Intl.DateTimeFormat(undefined, { month: "short", day: "numeric" }).format(date);
}

export function InboxClient() {
  const [conversations, setConversations] = useState<Conversation[] | null>();

  useEffect(() => {
    let active = true;
    const refresh = () => listConversations().then((items) => active && setConversations(items)).catch(() => active && setConversations(null));
    refresh();
    const timer = window.setInterval(refresh, 8_000);
    return () => { active = false; window.clearInterval(timer); };
  }, []);

  if (conversations === undefined) return <main className="mx-auto min-h-[70vh] max-w-2xl animate-pulse px-4 py-10 sm:px-6"><div className="h-9 w-32 rounded bg-surface" /><div className="mt-8 space-y-5">{Array.from({ length: 4 }).map((_, index) => <div key={index} className="flex items-center gap-4"><div className="size-12 rounded-full bg-surface" /><div className="h-10 flex-1 rounded bg-surface" /></div>)}</div></main>;
  if (conversations === null) return <main className="mx-auto grid min-h-[70vh] max-w-xl place-items-center px-4 text-center"><div><h1 className="type-wide text-3xl font-black">Log in to see your messages</h1><p className="mt-3 text-muted">Messages are tied to your verified student account.</p><Link href="/account/login" className="btn btn-primary mt-6">Log in</Link></div></main>;

  return <main className="mx-auto min-h-[70vh] max-w-2xl px-4 py-8 pb-28 sm:px-6 sm:py-10 desktop:pb-12">
    <h1 className="type-wide text-3xl font-black">Inbox</h1>
    {conversations.length ? <ul className="mt-6 divide-y divide-line border-y border-line">{conversations.map((conversation) => {
      const user = conversation.other_user;
      const unread = conversation.unread_count > 0;
      const preview = conversation.latest_message ? `${conversation.latest_message.is_mine ? "You: " : ""}${conversation.latest_message.body}` : "No messages yet";
      return <li key={conversation.id}><Link href={`/inbox/${conversation.id}`} className="-mx-3 flex items-center gap-3.5 rounded-lg px-3 py-4 transition hover:bg-surface">
        <Avatar user={user} />
        <div className="min-w-0 flex-1">
          <div className="flex items-baseline justify-between gap-3">
            <p className="truncate"><span className="font-bold">{user.first_name || `@${user.username}`}</span> <span className="text-sm text-muted">@{user.username}</span></p>
            <p className={`shrink-0 text-xs ${unread ? "font-bold text-signal" : "text-muted"}`}>{time(conversation.last_message_at)}</p>
          </div>
          <div className="mt-0.5 flex items-center justify-between gap-3">
            <p className={`truncate text-sm ${unread ? "font-semibold text-ink" : "text-muted"}`}>{preview}</p>
            {unread && <span className="grid min-w-5 shrink-0 place-items-center rounded-full bg-signal px-1.5 py-0.5 text-[11px] font-bold text-white" aria-label={`${conversation.unread_count} unread`}>{conversation.unread_count}</span>}
          </div>
        </div>
      </Link></li>;
    })}</ul> : <div className="mt-6 rounded-xl bg-surface px-6 py-14 text-center"><h2 className="type-wide text-xl font-extrabold">No messages yet</h2><p className="mx-auto mt-2 max-w-sm text-sm leading-6 text-muted">Open a seller’s profile and choose Message to ask about an item.</p><Link href="/search" className="btn btn-secondary mt-5">Browse listings</Link></div>}
  </main>;
}
