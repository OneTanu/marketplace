"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";

import { getUnreadNotificationCount } from "@/lib/notifications";
import { CountBadge } from "@/components/ui/badge";
import { BellIcon } from "@/components/ui/icons";

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
    <Link href="/notifications" aria-label={label} className="relative grid size-11 shrink-0 place-items-center rounded-lg text-ink transition hover:bg-surface">
      <BellIcon className="size-6" aria-hidden="true" />
      {unread > 0 && (
        <CountBadge count={unread} className="absolute right-0 top-0.5" />
      )}
    </Link>
  );
}
