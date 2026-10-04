import type { Metadata } from "next";

import { PublicProfile } from "@/components/profile/public-profile";

export const metadata: Metadata = { title: "Student profile" };

export default async function UserProfilePage({ params }: PageProps<"/users/[username]">) {
  const { username } = await params;
  return <PublicProfile username={username} />;
}
