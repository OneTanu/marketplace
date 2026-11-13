import Image from "next/image";

/** A student's profile photo, or the first letter of their name when they haven't added one.
 * Size, shape and text size come from `className` (e.g. "size-11 rounded-full text-base"). */
export function Avatar({ photoUrl, firstName, username, className = "" }: { photoUrl?: string | null; firstName?: string; username: string; className?: string }) {
  if (photoUrl) {
    // Stored as a square of at most 512 px, served straight from media storage.
    return <Image src={photoUrl} alt="" width={512} height={512} unoptimized className={`shrink-0 bg-surface object-cover ${className}`} />;
  }
  const initial = (firstName?.[0] || username[0] || "T").toUpperCase();
  return <div className={`type-wide grid shrink-0 place-items-center bg-[var(--brand-soft)] font-extrabold text-brand ${className}`} aria-hidden="true">{initial}</div>;
}
