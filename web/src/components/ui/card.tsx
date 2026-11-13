import type { ReactNode } from "react";

/**
 * A white panel. Pages with listing photos are flat and white, so a Card there is a hairline
 * box (tone "line"); on the grey account and settings pages it lifts off the page (tone "lifted").
 */
export function Card({ tone = "lifted", className = "", children }: { tone?: "lifted" | "line"; className?: string; children: ReactNode }) {
  return <div className={`rounded-xl bg-background ${tone === "lifted" ? "shadow-card" : "border border-line"} ${className}`}>{children}</div>;
}

/** A grey loading placeholder with a soft shimmer (still under reduced motion). */
export function Skeleton({ className = "" }: { className?: string }) {
  return <div aria-hidden="true" className={`skeleton rounded-xl ${className}`} />;
}
