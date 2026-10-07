"use client";

import { useEffect, useState } from "react";

import { getUnreadCount } from "@/lib/messaging";

export function UnreadBadge() {
  const [count, setCount] = useState(0);

  useEffect(() => {
    let active = true;
    const refresh = () => getUnreadCount().then((result) => active && setCount(result.unread_count)).catch(() => active && setCount(0));
    refresh();
    const timer = window.setInterval(refresh, 20_000);
    return () => { active = false; window.clearInterval(timer); };
  }, []);

  if (!count) return null;
  return <span className="ml-1 inline-grid min-w-5 place-items-center rounded-full bg-brand px-1.5 py-0.5 text-[10px] font-black text-white" aria-label={`${count} unread messages`}>{count > 99 ? "99+" : count}</span>;
}
