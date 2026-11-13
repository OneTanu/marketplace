import type { Metadata } from "next";
import { Suspense } from "react";

import { ProfileClient } from "@/components/profile/profile-client";

export const metadata: Metadata = { title: "Your profile" };

export default function ProfilePage() {
  // ProfileClient reads the URL (to redirect the old ?tab=bookmarks link), which needs a
  // Suspense boundary.
  return <Suspense><ProfileClient /></Suspense>;
}
