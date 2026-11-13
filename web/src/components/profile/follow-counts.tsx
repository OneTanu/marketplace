import Link from "next/link";

/** "12 followers · 4 following" on a profile, each opening its list. */
export function FollowCounts({ username, followers, following }: { username: string; followers: number; following: number }) {
  const link = "inline-flex min-h-11 items-center gap-1 underline-offset-4 decoration-ink/30 hover:underline";
  return <div className="flex gap-5">
    <Link href={`/users/${username}/followers`} className={link}><b className="text-body tabular-nums">{followers}</b> <span className="text-muted">{followers === 1 ? "follower" : "followers"}</span></Link>
    <Link href={`/users/${username}/following`} className={link}><b className="text-body tabular-nums">{following}</b> <span className="text-muted">following</span></Link>
  </div>;
}
