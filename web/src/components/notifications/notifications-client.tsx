"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import type { components } from "@/lib/api/schema";
import { listNotifications, markNotificationsRead } from "@/lib/notifications";
import { formatDateTime } from "@/lib/time";

type Notification = components["schemas"]["Notification"];

export function NotificationsClient() {
  const [items, setItems] = useState<Notification[] | null>();

  useEffect(() => {
    let active = true;
    listNotifications()
      .then((data) => {
        if (!active) return;
        setItems(data);
        // Seeing the list counts as reading it; the unread styling stays for this visit.
        if (data.some((item) => !item.read_at)) void markNotificationsRead().catch(() => {});
      })
      .catch(() => active && setItems(null));
    return () => {
      active = false;
    };
  }, []);

  return (
    <main className="mx-auto min-h-[70vh] max-w-2xl px-4 py-8 pb-28 sm:px-6 desktop:pb-12">
      <h1 className="type-wide text-3xl font-black">Notifications</h1>
      {items === undefined && <div className="mt-6 space-y-2">{[0, 1, 2].map((i) => <div key={i} className="h-20 animate-pulse rounded-xl bg-surface" />)}</div>}
      {items === null && <p className="mt-6 rounded-xl bg-surface p-6 text-center text-sm text-muted">Log in to see your notifications.</p>}
      {items && items.length === 0 && <p className="mt-6 rounded-xl bg-surface p-8 text-center text-sm text-muted">You&apos;re all caught up.</p>}
      {items && items.length > 0 && (
        <ul className="mt-6 space-y-2">
          {items.map((item) => {
            const content = (
              <>
                <div className="flex items-start justify-between gap-3">
                  <p className="font-bold">{item.title}</p>
                  {!item.read_at && <span className="mt-1.5 size-2 shrink-0 rounded-full bg-signal" aria-label="Unread" />}
                </div>
                {item.body && <p className="mt-1 whitespace-pre-line text-sm text-muted">{item.body}</p>}
                <p className="mt-2 text-xs text-muted">{formatDateTime(item.created_at)}</p>
              </>
            );
            const box = `block rounded-xl border p-4 ${item.read_at ? "border-line" : "border-signal bg-[var(--brand-soft)]/25"}`;
            return (
              <li key={item.id}>
                {item.link ? <Link href={item.link} className={`${box} transition hover:border-ink`}>{content}</Link> : <div className={box}>{content}</div>}
              </li>
            );
          })}
        </ul>
      )}
    </main>
  );
}
