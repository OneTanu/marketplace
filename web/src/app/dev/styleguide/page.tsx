import type { Metadata } from "next";
import { notFound } from "next/navigation";

import { Styleguide } from "./styleguide";

export const metadata: Metadata = { title: "Styleguide", robots: { index: false } };

// The design system's tokens and shared parts in one place (DESIGN.md explains them).
// A development page: never served in production.
export default function StyleguidePage() {
  if (process.env.NODE_ENV === "production") notFound();
  return <Styleguide />;
}
