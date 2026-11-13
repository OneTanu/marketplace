import type { Metadata } from "next";

import { EditProfile } from "@/components/profile/edit-profile";

export const metadata: Metadata = { title: "Edit profile" };

export default function EditProfilePage() {
  return <EditProfile />;
}
