"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";

import { getUnreadNotificationCount } from "@/lib/notifications";

/** Header bell with the unread count. Refreshes on navigation and every 30 seconds. */
export function NotificationBell() {
  const pathname = usePathname();
  const [unread, setUnread] = useState(0);

  useEffect(() => {
    let active = true;
    function refresh() {
      getUnreadNotificationCount()
        .then((data) => active && setUnread(data.unread))
        .catch(() => {});
    }
    refresh();
    const timer = window.setInterval(refresh, 30_000);
    return () => {
      active = false;
      window.clearInterval(timer);
    };
  }, [pathname]);

  const label = unread ? `Notifications, ${unread} unread` : "Notifications";
  return (
    <Link href="/notifications" aria-label={label} className="relative grid size-9 place-items-center rounded-lg text-ink transition hover:bg-surface">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round" className="size-5" aria-hidden="true">
        <path d="M6 8a6 6 0 0 1 12 0c0 7 3 9 3 9H3s3-2 3-9" />
        <path d="M10.3 21a1.94 1.94 0 0 0 3.4 0" />
      </svg>
      {unread > 0 && (
        <span className="absolute -right-0.5 -top-0.5 grid min-w-5 place-items-center rounded-full bg-signal px-1 text-[11px] font-bold leading-5 text-white" aria-hidden="true">
          {unread > 9 ? "9+" : unread}
        </span>
      )}
    </Link>
  );
}
