import Link from "next/link";

/** "12 Followers · 4 Following" on a profile, each opening its list. */
export function FollowCounts({ username, followers, following }: { username: string; followers: number; following: number }) {
  const link = "rounded hover:underline hover:decoration-kraft hover:decoration-2 hover:underline-offset-4";
  return <div className="flex gap-6">
    <Link href={`/users/${username}/followers`} className={link}><strong className="text-base">{followers}</strong> <span className="text-muted">{followers === 1 ? "Follower" : "Followers"}</span></Link>
    <Link href={`/users/${username}/following`} className={link}><strong className="text-base">{following}</strong> <span className="text-muted">Following</span></Link>
  </div>;
}
