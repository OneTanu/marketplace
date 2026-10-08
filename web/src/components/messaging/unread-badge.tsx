"use client";

import { useSyncExternalStore } from "react";

import { getUnreadCount } from "@/lib/messaging";

// One poller per tab, shared by every mounted badge (the desktop and mobile navs each mount
// one). It runs while at least one badge is subscribed.
let unreadCount = 0;
let timer: number | undefined;
const listeners = new Set<() => void>();

function publish(count: number) {
  unreadCount = count;
  listeners.forEach((listener) => listener());
}

function refresh() {
  getUnreadCount().then((result) => publish(result.unread_count)).catch(() => publish(0));
}

function subscribe(listener: () => void) {
  listeners.add(listener);
  if (listeners.size === 1) {
    refresh();
    timer = window.setInterval(refresh, 20_000);
  }
  return () => {
    listeners.delete(listener);
    if (!listeners.size) {
      window.clearInterval(timer);
      timer = undefined;
    }
  };
}

export function UnreadBadge() {
  const count = useSyncExternalStore(subscribe, () => unreadCount, () => 0);

  if (!count) return null;
  return <span className="ml-1 inline-grid min-w-5 place-items-center rounded-full bg-signal px-1.5 py-0.5 text-[10px] font-black text-white" aria-label={`${count} unread messages`}>{count > 99 ? "99+" : count}</span>;
}
