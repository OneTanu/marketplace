"use client";

import Link from "next/link";
import { FormEvent, useEffect, useRef, useState } from "react";

import { getConversation, listMessages, markConversationRead, sendMessage, type ChatMessage, type Conversation } from "@/lib/messaging";

function clock(value: string) {
  return new Intl.DateTimeFormat(undefined, { hour: "numeric", minute: "2-digit" }).format(new Date(value));
}

export function ChatClient({ conversationId }: { conversationId: number }) {
  const [conversation, setConversation] = useState<Conversation | null>();
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [body, setBody] = useState("");
  const [pending, setPending] = useState(false);
  const [error, setError] = useState("");
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    let active = true;
    async function refresh() {
      try {
        const [thread, items] = await Promise.all([getConversation(conversationId), listMessages(conversationId)]);
        if (!active) return;
        setConversation(thread); setMessages(items);
        const latest = items.at(-1);
        if (latest) await markConversationRead(conversationId, latest.id);
      } catch { if (active) setConversation(null); }
    }
    refresh();
    const timer = window.setInterval(refresh, 4_000);
    return () => { active = false; window.clearInterval(timer); };
  }, [conversationId]);

  useEffect(() => { bottomRef.current?.scrollIntoView({ behavior: "smooth" }); }, [messages.length]);

  async function submit(event: FormEvent) {
    event.preventDefault();
    const text = body.trim();
    if (!text || pending) return;
    setPending(true); setError("");
    try {
      const message = await sendMessage(conversationId, text);
      setMessages((current) => [...current, message]); setBody("");
    } catch (caught) { setError(caught instanceof Error ? caught.message : "Message could not be sent."); }
    finally { setPending(false); }
  }

  if (conversation === undefined) return <main className="mx-auto min-h-[70vh] max-w-4xl animate-pulse px-4 py-8 sm:px-6"><div className="h-[32rem] rounded-3xl bg-foreground/5" /></main>;
  if (conversation === null) return <main className="mx-auto grid min-h-[70vh] max-w-xl place-items-center px-4 text-center"><div><h1 className="text-3xl font-black">Conversation unavailable</h1><p className="mt-3 text-muted">This conversation does not exist or you do not have access to it.</p><Link href="/inbox" className="mt-6 inline-flex rounded-full bg-foreground px-6 py-3 text-sm font-bold text-white">Back to inbox</Link></div></main>;

  const user = conversation.other_user;
  return <main className="mx-auto flex min-h-[calc(100vh-4rem)] max-w-4xl flex-col px-4 py-6 pb-24 sm:px-6 desktop:pb-8">
    <header className="flex items-center gap-4 rounded-t-3xl border border-line bg-surface p-4 sm:p-5"><Link href="/inbox" className="text-sm font-bold text-muted">← Inbox</Link><div className="h-8 w-px bg-line" /><div className="min-w-0 flex-1"><Link href={`/users/${user.username}`} className="font-black hover:underline">{user.first_name || `@${user.username}`}</Link><p className="truncate text-xs text-muted">@{user.username}{user.school ? ` · ${user.school.short_name}` : ""}</p></div></header>
    <section className="flex min-h-[26rem] flex-1 flex-col gap-3 overflow-y-auto border-x border-line bg-white/40 p-4 sm:p-6" aria-live="polite">{messages.length ? messages.map((message) => <div key={message.id} className={`flex ${message.is_mine ? "justify-end" : "justify-start"}`}><div className={`max-w-[82%] rounded-2xl px-4 py-3 ${message.is_mine ? "rounded-br-md bg-foreground text-white" : "rounded-bl-md border border-line bg-surface"}`}><p className="whitespace-pre-wrap break-words text-sm leading-6">{message.body}</p><p className={`mt-1 text-[10px] ${message.is_mine ? "text-white/60" : "text-muted"}`}>{clock(message.created_at)}</p></div></div>) : <div className="m-auto text-center"><p className="font-bold">Start the conversation</p><p className="mt-1 text-sm text-muted">Send a respectful message to @{user.username}.</p></div>}<div ref={bottomRef} /></section>
    <form onSubmit={submit} className="rounded-b-3xl border border-line bg-surface p-3 sm:p-4"><div className="flex items-end gap-2"><textarea value={body} onChange={(event) => setBody(event.target.value)} maxLength={2000} rows={2} placeholder="Write a message…" aria-label="Message" className="min-h-12 flex-1 resize-none rounded-2xl border border-line bg-white px-4 py-3 text-sm outline-none focus:border-forest focus:ring-4 focus:ring-forest/10" /><button disabled={pending || !body.trim()} className="rounded-full bg-foreground px-5 py-3 text-sm font-black text-white transition hover:bg-forest disabled:opacity-40">{pending ? "Sending…" : "Send"}</button></div>{error && <p role="alert" className="mt-2 text-sm text-[var(--danger)]">{error}</p>}<p className="mt-2 text-right text-[10px] text-muted">{body.length}/2000</p></form>
  </main>;
}
