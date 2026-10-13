import type { Metadata } from "next";

import { AccountStanding } from "@/components/trust/account-standing";

export const metadata: Metadata = { title: "Account status" };

export default function AccountStandingPage() {
  return <AccountStanding />;
}
