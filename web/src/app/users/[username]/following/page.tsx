import type { Metadata } from "next";

import { FollowList } from "@/components/profile/follow-list";

export const metadata: Metadata = { title: "Following" };

export default async function FollowingPage({ params }: PageProps<"/users/[username]/following">) {
  const { username } = await params;
  return <FollowList username={username} direction="following" />;
}
