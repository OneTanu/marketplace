import type { ReactNode } from "react";

const TONES = {
  /** Something waiting on the viewer. The only use of signal pink besides counts. */
  needs: "bg-signal-soft text-signal-ink",
  pending: "bg-warning-soft text-warning",
  ok: "bg-success-soft text-success",
  sold: "bg-ink text-white",
  neutral: "bg-surface text-ink",
  danger: "bg-danger-soft text-danger",
};

/** A short status label: "Pending", "Sold", "Needs you". One per item (spec principle 6). */
export function Badge({ tone = "neutral", children, className = "" }: { tone?: keyof typeof TONES; children: ReactNode; className?: string }) {
  return (
    <span className={`inline-flex h-6 shrink-0 items-center gap-1.5 rounded-full px-2.5 text-fine font-semibold leading-none ${TONES[tone]} ${className}`}>
      {tone === "needs" && <span aria-hidden="true" className="size-1.5 rounded-full bg-signal" />}
      {children}
    </span>
  );
}

/** An unread count on Inbox or the bell. Caps at 99+. `label` is read instead of the bare
 * number; without one the count is hidden from screen readers (the link says it). */
export function CountBadge({ count, label, className = "" }: { count: number; label?: string; className?: string }) {
  if (count <= 0) return null;
  return <>
    <span aria-hidden="true" className={`inline-grid h-5 min-w-5 place-items-center rounded-full bg-signal px-1.5 text-fine font-semibold leading-none text-white tabular-nums ${className}`}>
      {count > 99 ? "99+" : count}
    </span>
    {label && <span className="sr-only"> ({label})</span>}
  </>;
}
