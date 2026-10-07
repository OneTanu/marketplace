import type { Metadata } from "next";

import { Placeholder } from "@/components/placeholder";

export const metadata: Metadata = { title: "Privacy Policy" };

export default function PrivacyPage() {
  return <Placeholder title="Privacy Policy" note="Our privacy policy is being written and will be posted here before launch." />;
}
