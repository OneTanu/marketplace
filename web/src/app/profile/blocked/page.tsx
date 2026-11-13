import type { Metadata } from "next";

import { BlockedAccounts } from "@/components/profile/blocked-accounts";

export const metadata: Metadata = { title: "Blocked accounts" };

export default function BlockedAccountsPage() {
  return <BlockedAccounts />;
}
