import type { Metadata } from "next";

import { Placeholder } from "@/components/placeholder";

export const metadata: Metadata = { title: "Profile" };

export default function ProfilePage() {
  return <Placeholder title="Profile" note="Your profile, listings, and bookmarks (workstreams 1 and 3)." />;
}
