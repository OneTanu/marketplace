import type { Metadata } from "next";

import { DeactivateAccount } from "@/components/profile/deactivate-account";

export const metadata: Metadata = { title: "Deactivate account" };

export default function DeactivateAccountPage() {
  return <DeactivateAccount />;
}
