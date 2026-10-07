import type { Metadata } from "next";

import { Placeholder } from "@/components/placeholder";

export const metadata: Metadata = { title: "Terms of Service" };

export default function TermsPage() {
  return <Placeholder title="Terms of Service" note="Our terms are being written and will be posted here before launch." />;
}
