import type { Metadata } from "next";

import { FollowList } from "@/components/profile/follow-list";

export const metadata: Metadata = { title: "Followers" };

export default async function FollowersPage({ params }: PageProps<"/users/[username]/followers">) {
  const { username } = await params;
  return <FollowList username={username} direction="followers" />;
}
