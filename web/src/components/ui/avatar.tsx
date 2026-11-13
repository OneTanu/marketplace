/** Five soft tints, so people are told apart in Inbox and Deals at a glance (spec 1c, H1). */
const TINTS = [
  "bg-tint-1 text-tint-1-ink",
  "bg-tint-2 text-tint-2-ink",
  "bg-tint-3 text-tint-3-ink",
  "bg-tint-4 text-tint-4-ink",
  "bg-tint-5 text-tint-5-ink",
];

const SIZES = {
  sm: "size-9 text-label",
  md: "size-11 text-body",
  lg: "size-19 text-display desktop:size-22",
};

/** The same person always gets the same tint, wherever they appear. */
export function tintFor(username: string) {
  let hash = 0;
  for (const char of username) hash = (hash * 31 + char.charCodeAt(0)) >>> 0;
  return TINTS[hash % TINTS.length];
}

/**
 * A round avatar. Accounts have no profile photo yet, so it shows the first initial (or the
 * username's) on a tint picked from the username. Decorative: the name is always beside it.
 */
export function Avatar({ user, size = "md", className = "" }: {
  user: { first_name?: string; username: string };
  size?: keyof typeof SIZES;
  className?: string;
}) {
  const initial = (user.first_name?.[0] || user.username[0] || "?").toUpperCase();
  return (
    <span aria-hidden="true" className={`type-wide grid shrink-0 place-items-center rounded-full font-extrabold leading-none ${SIZES[size]} ${tintFor(user.username)} ${className}`}>
      {initial}
    </span>
  );
}
