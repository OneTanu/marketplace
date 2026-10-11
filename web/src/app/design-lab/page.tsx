import type { Metadata } from "next";
import { notFound } from "next/navigation";

import { DesignLab } from "@/components/design-lab/design-lab";

export const metadata: Metadata = { title: "Design lab", robots: { index: false } };

// A sandbox for trying visual directions on real components. Never served in production.
export default function DesignLabPage() {
  if (process.env.NODE_ENV === "production") notFound();
  return <DesignLab />;
}
