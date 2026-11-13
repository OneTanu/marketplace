"use client";

import { useSyncExternalStore } from "react";

import { getUnreadCount } from "@/lib/messaging";
import { CountBadge } from "@/components/ui/badge";

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
    timer = window.setInterval(refresh, 8_000);
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

  return <CountBadge count={count} label={`${count} unread ${count === 1 ? "message" : "messages"}`} className="ml-1" />;
}
