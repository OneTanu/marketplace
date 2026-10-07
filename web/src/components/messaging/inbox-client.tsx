"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { listConversations, type Conversation } from "@/lib/messaging";

function time(value: string | null) {
  if (!value) return "";
  return new Intl.DateTimeFormat(undefined, { month: "short", day: "numeric" }).format(new Date(value));
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

  if (conversations === undefined) return <main className="mx-auto min-h-[70vh] max-w-4xl animate-pulse px-4 py-10 sm:px-6"><div className="h-72 rounded-3xl bg-foreground/5" /></main>;
  if (conversations === null) return <main className="mx-auto grid min-h-[70vh] max-w-xl place-items-center px-4 text-center"><div><h1 className="text-3xl font-black">Sign in to view messages</h1><p className="mt-3 text-muted">Your private conversations are connected to your verified student account.</p><Link href="/account/login" className="mt-6 inline-flex rounded-full bg-foreground px-6 py-3 text-sm font-bold text-white">Log in</Link></div></main>;

  return <main className="mx-auto min-h-[70vh] max-w-4xl px-4 py-10 pb-28 sm:px-6 desktop:pb-12">
    <p className="text-sm font-bold text-brand">Messages</p><h1 className="mt-2 text-3xl font-black tracking-[-.04em]">Inbox</h1><p className="mt-2 text-muted">Private conversations with verified Tanu students.</p>
    {conversations.length ? <div className="mt-8 overflow-hidden rounded-3xl border border-line bg-surface shadow-sm">{conversations.map((conversation) => {
      const user = conversation.other_user;
      const initial = (user.first_name[0] || user.username[0]).toUpperCase();
      return <Link key={conversation.id} href={`/inbox/${conversation.id}`} className="flex items-center gap-4 border-b border-line p-4 transition last:border-0 hover:bg-white/70 sm:p-5">
        <div className="grid size-12 shrink-0 place-items-center rounded-2xl bg-[var(--brand-soft)] text-lg font-black text-brand">{initial}</div>
        <div className="min-w-0 flex-1"><div className="flex items-center gap-2"><p className="truncate font-black">{user.first_name || `@${user.username}`}</p>{conversation.unread_count > 0 && <span className="rounded-full bg-brand px-2 py-0.5 text-[10px] font-black text-white">{conversation.unread_count}</span>}</div><p className="truncate text-sm text-muted">{conversation.latest_message ? `${conversation.latest_message.is_mine ? "You: " : ""}${conversation.latest_message.body}` : `Start a conversation with @${user.username}`}</p></div>
        <div className="shrink-0 text-right"><p className="text-xs text-muted">{time(conversation.last_message_at)}</p><p className="mt-1 text-xs font-semibold text-muted">{user.school?.short_name}</p></div>
      </Link>;
    })}</div> : <div className="mt-8 grid min-h-72 place-items-center rounded-3xl border border-dashed border-line bg-white/45 p-8 text-center"><div><div className="mx-auto grid size-12 place-items-center rounded-2xl bg-[var(--forest-soft)] text-xl text-forest">◇</div><h2 className="mt-4 text-xl font-black">No conversations yet</h2><p className="mt-2 max-w-sm text-sm leading-6 text-muted">Find another verified student through Search, open their profile, and select Message.</p><Link href="/search" className="mt-5 inline-flex rounded-full border border-line bg-white px-5 py-2.5 text-sm font-bold">Find students</Link></div></div>}
  </main>;
}
