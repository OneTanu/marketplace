"use client";

import Link from "next/link";
import { FormEvent, KeyboardEvent, useEffect, useRef, useState } from "react";

import type { components } from "@/lib/api/schema";
import { getConversation, listMessages, markConversationRead, sendMessage } from "@/lib/messaging";
import { Avatar } from "./avatar";

type ChatMessage = components["schemas"]["Message"];
type Conversation = components["schemas"]["Conversation"];

const MAX_LENGTH = 2000;
// A new timestamp divider appears when messages are this far apart.
const GAP_MS = 15 * 60 * 1000;

function stamp(value: string) {
  const date = new Date(value);
  const sameDay = date.toDateString() === new Date().toDateString();
  return new Intl.DateTimeFormat(undefined, sameDay ? { hour: "numeric", minute: "2-digit" } : { month: "short", day: "numeric", hour: "numeric", minute: "2-digit" }).format(date);
}

function startsNewBlock(messages: ChatMessage[], index: number) {
  if (index === 0) return true;
  return Date.parse(messages[index].created_at) - Date.parse(messages[index - 1].created_at) > GAP_MS;
}

function mergeMessages(current: ChatMessage[], incoming: ChatMessage[]) {
  const byId = new Map(current.map((message) => [message.id, message]));
  incoming.forEach((message) => byId.set(message.id, message));
  return [...byId.values()].sort((left, right) => left.id - right.id);
}

export function ChatClient({ conversationId }: { conversationId: number }) {
  const [conversation, setConversation] = useState<Conversation | null>();
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [body, setBody] = useState("");
  const [pending, setPending] = useState(false);
  const [error, setError] = useState("");
  const [hasMore, setHasMore] = useState(false);
  const [loadingOlder, setLoadingOlder] = useState(false);
  const threadRef = useRef<HTMLDivElement>(null);
  const latestMessageIdRef = useRef(0);
  const lastMarkedReadIdRef = useRef(0);
  const refreshingRef = useRef(false);
  const loadingOlderRef = useRef(false);
  const stickToBottomRef = useRef(true);
  const prependAnchorRef = useRef<{ height: number; top: number } | null>(null);

  useEffect(() => {
    let active = true;
    async function refresh(initial = false) {
      if (refreshingRef.current) return;
      refreshingRef.current = true;
      try {
        const [thread, page] = await Promise.all([
          getConversation(conversationId),
          listMessages(conversationId, initial || !latestMessageIdRef.current ? {} : { afterId: latestMessageIdRef.current }),
        ]);
        if (!active) return;
        setConversation(thread);
        if (initial) {
          setMessages(page.messages);
          setHasMore(page.has_more);
        } else if (page.messages.length) {
          setMessages((current) => mergeMessages(current, page.messages));
        }
        const latest = page.messages.at(-1);
        if (latest) latestMessageIdRef.current = Math.max(latestMessageIdRef.current, latest.id);
        if (latest && !latest.is_mine && latest.id > lastMarkedReadIdRef.current) {
          try {
            await markConversationRead(conversationId, latest.id);
            lastMarkedReadIdRef.current = latest.id;
          } catch {
            // Reading messages should still succeed if the read-receipt request is interrupted.
          }
        }
      } catch {
        if (active && initial) setConversation(null);
      } finally {
        refreshingRef.current = false;
      }
    }
    refresh(true);
    const timer = window.setInterval(() => refresh(false), 4_000);
    return () => { active = false; window.clearInterval(timer); };
  }, [conversationId]);

  // Scroll the thread itself, not the page, so the header stays in view.
  useEffect(() => {
    const thread = threadRef.current;
    if (!thread) return;
    const anchor = prependAnchorRef.current;
    if (anchor) {
      thread.scrollTop = thread.scrollHeight - anchor.height + anchor.top;
      prependAnchorRef.current = null;
    } else if (stickToBottomRef.current) {
      thread.scrollTop = thread.scrollHeight;
    }
  }, [messages.length, conversation]);

  async function loadOlder() {
    const thread = threadRef.current;
    const oldest = messages[0];
    if (!thread || !oldest || !hasMore || loadingOlderRef.current) return;
    loadingOlderRef.current = true;
    setLoadingOlder(true);
    try {
      const page = await listMessages(conversationId, { beforeId: oldest.id });
      prependAnchorRef.current = { height: thread.scrollHeight, top: thread.scrollTop };
      setMessages((current) => mergeMessages(current, page.messages));
      setHasMore(page.has_more);
    } catch {
      setError("Older messages could not be loaded. Try again.");
    } finally {
      loadingOlderRef.current = false;
      setLoadingOlder(false);
    }
  }

  function onThreadScroll() {
    const thread = threadRef.current;
    if (!thread) return;
    stickToBottomRef.current = thread.scrollHeight - thread.scrollTop - thread.clientHeight < 80;
    if (thread.scrollTop < 64) void loadOlder();
  }

  async function submit(event?: FormEvent) {
    event?.preventDefault();
    const text = body.trim();
    if (!text || pending) return;
    setPending(true); setError("");
    try {
      const message = await sendMessage(conversationId, text);
      latestMessageIdRef.current = Math.max(latestMessageIdRef.current, message.id);
      lastMarkedReadIdRef.current = Math.max(lastMarkedReadIdRef.current, message.id);
      stickToBottomRef.current = true;
      setMessages((current) => mergeMessages(current, [message])); setBody("");
    } catch (caught) { setError(caught instanceof Error ? caught.message : "Message not sent. Try again."); }
    finally { setPending(false); }
  }

  function onKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key === "Enter" && !event.shiftKey && !event.nativeEvent.isComposing) {
      event.preventDefault();
      submit();
    }
  }

  if (conversation === undefined) return <main className="mx-auto min-h-[70vh] max-w-2xl animate-pulse px-4 py-6 sm:px-6"><div className="flex items-center gap-3"><div className="size-9 rounded-full bg-surface" /><div className="h-5 w-32 rounded bg-surface" /></div><div className="mt-8 space-y-3"><div className="h-10 w-48 rounded-2xl bg-surface" /><div className="ml-auto h-10 w-40 rounded-2xl bg-surface" /></div></main>;
  if (conversation === null) return <main className="mx-auto grid min-h-[70vh] max-w-xl place-items-center px-4 text-center"><div><h1 className="type-wide text-3xl font-black">Conversation not found</h1><p className="mt-3 text-muted">It may have been removed, or it belongs to another account.</p><Link href="/inbox" className="btn btn-primary mt-6">Back to inbox</Link></div></main>;

  const user = conversation.other_user;
  const nearLimit = body.length > MAX_LENGTH - 200;

  return <main className="mx-auto flex h-[calc(100dvh-8rem-env(safe-area-inset-bottom))] max-w-2xl flex-col desktop:h-[calc(100dvh-4rem)] desktop:border-x desktop:border-line">
    <header className="flex items-center gap-3 border-b border-line px-2 py-2.5 sm:px-4">
      <Link href="/inbox" aria-label="Back to inbox" className="grid size-10 place-items-center rounded-lg text-ink transition hover:bg-surface"><svg viewBox="0 0 24 24" className="size-5" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><path d="M15 18l-6-6 6-6" /></svg></Link>
      <Link href={`/users/${user.username}`} className="flex min-w-0 items-center gap-3 rounded-lg py-1 pr-3 transition hover:bg-surface">
        <Avatar user={user} size="sm" />
        <div className="min-w-0"><p className="truncate font-bold leading-tight">{user.first_name || `@${user.username}`}</p><p className="truncate text-xs text-muted">@{user.username}{user.school ? `, ${user.school.short_name}` : ""}</p></div>
      </Link>
    </header>

    <div ref={threadRef} onScroll={onThreadScroll} className="flex flex-1 flex-col overflow-y-auto px-4 py-5 sm:px-6" aria-live="polite">
      {hasMore && <button type="button" onClick={loadOlder} disabled={loadingOlder} className="mx-auto mb-4 text-xs font-semibold text-brand hover:underline disabled:text-muted">{loadingOlder ? "Loading older messages…" : "Load older messages"}</button>}
      {messages.length ? messages.map((message, index) => {
        const newBlock = startsNewBlock(messages, index);
        const next = messages[index + 1];
        const sameSenderAsPrev = !newBlock && messages[index - 1]?.is_mine === message.is_mine;
        const lastInRun = !next || next.is_mine !== message.is_mine || startsNewBlock(messages, index + 1);
        const tail = lastInRun ? (message.is_mine ? "rounded-br-md" : "rounded-bl-md") : "";
        return <div key={message.id}>
          {newBlock && <p className={`mb-3 text-center text-xs font-medium text-muted ${index === 0 ? "" : "mt-5"}`}>{stamp(message.created_at)}</p>}
          <div className={`flex ${message.is_mine ? "justify-end" : "justify-start"} ${sameSenderAsPrev ? "mt-1" : newBlock ? "" : "mt-3"}`}>
            <p title={stamp(message.created_at)} className={`max-w-[78%] whitespace-pre-wrap break-words rounded-2xl px-3.5 py-2 text-[15px] leading-snug ${tail} ${message.is_mine ? "bg-brand text-white" : "bg-surface text-ink"}`}>{message.body}</p>
          </div>
        </div>;
      }) : <div className="m-auto max-w-xs text-center"><Avatar user={user} /><p className="mt-3 font-bold">Say hi to {user.first_name || `@${user.username}`}</p><p className="mt-1 text-sm text-muted">Ask about an item, make an offer, or pick a place to meet on campus.</p></div>}
    </div>

    <form onSubmit={submit} className="border-t border-line px-3 py-3 sm:px-4">
      {error && <p role="alert" className="mb-2 text-sm text-[var(--danger)]">{error}</p>}
      <div className="flex items-end gap-2">
        <textarea value={body} onChange={(event) => setBody(event.target.value)} onKeyDown={onKeyDown} maxLength={MAX_LENGTH} rows={1} placeholder="Message" aria-label="Message" className="field max-h-36 min-h-11 flex-1 resize-none rounded-[1.375rem] px-4 py-2.5 text-[15px] leading-snug [field-sizing:content]" />
        <button disabled={pending || !body.trim()} aria-label={pending ? "Sending" : "Send message"} className="grid size-11 shrink-0 place-items-center rounded-full bg-brand text-white transition hover:bg-brand-strong disabled:bg-surface disabled:text-muted">
          <svg viewBox="0 0 24 24" className="size-5" fill="none" stroke="currentColor" strokeWidth={2.2} strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><path d="M12 19V5M5 12l7-7 7 7" /></svg>
        </button>
      </div>
      {nearLimit && <p className="mt-1.5 text-right text-xs text-muted">{MAX_LENGTH - body.length} characters left</p>}
    </form>
  </main>;
}
