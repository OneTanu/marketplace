import type { LucideIcon } from "lucide-react";
import Link from "next/link";
import type { ReactNode } from "react";

import { ChevronRightIcon } from "./icons";

const ROW = "flex min-h-14 w-full items-center gap-3 text-left text-body font-semibold text-ink transition-colors";

function Inner({ icon: Icon, children, value, chevron }: { icon?: LucideIcon; children: ReactNode; value?: ReactNode; chevron: boolean }) {
  return <>
    {Icon && <Icon className="size-5.5 shrink-0" aria-hidden="true" />}
    <span className="min-w-0 flex-1 truncate">{children}</span>
    {value !== undefined && value !== null && value !== "" && <span className="shrink-0 text-label font-normal text-muted tabular-nums">{value}</span>}
    {chevron && <ChevronRightIcon className="size-4.5 shrink-0 text-muted" aria-hidden="true" />}
  </>;
}

/** A row in a list of pages (the account hub, settings): optional icon, label, optional value
 * ("4", "Good") and a chevron. Rows sit in a <ul> with dividers (see ListGroup). */
export function ListRow({ href, icon, value, children }: { href: string; icon?: LucideIcon; value?: ReactNode; children: ReactNode }) {
  return <li><Link href={href} className={`${ROW} hover:text-muted`}><Inner icon={icon} value={value} chevron>{children}</Inner></Link></li>;
}

/** The same row as a button, for an action rather than a page (Log out). No chevron. */
export function ListButton({ onClick, icon, disabled, tone = "ink", children }: { onClick: () => void; icon?: LucideIcon; disabled?: boolean; tone?: "ink" | "muted"; children: ReactNode }) {
  return <li><button type="button" onClick={onClick} disabled={disabled} className={`${ROW} disabled:opacity-50 ${tone === "muted" ? "text-muted hover:text-ink" : "hover:text-muted"}`}><Inner icon={icon} chevron={false}>{children}</Inner></button></li>;
}

/** A white card of rows with hairlines between them. On the grey account pages it lifts off the page. */
export function ListGroup({ label, children, className = "" }: { label?: string; children: ReactNode; className?: string }) {
  return <ul aria-label={label} className={`divide-y divide-line rounded-xl bg-background px-4 shadow-card ${className}`}>{children}</ul>;
}
