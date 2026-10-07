import type { MessagingUser } from "@/lib/messaging";

export function Avatar({ user, size = "md" }: { user: Pick<MessagingUser, "first_name" | "username">; size?: "sm" | "md" }) {
  const initial = (user.first_name[0] || user.username[0]).toUpperCase();
  return <div aria-hidden="true" className={`type-wide grid shrink-0 place-items-center rounded-full bg-[var(--brand-soft)] font-extrabold text-brand ${size === "sm" ? "size-9 text-sm" : "size-12 text-base"}`}>{initial}</div>;
}
