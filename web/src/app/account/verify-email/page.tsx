import type { Metadata } from "next";
import { Suspense } from "react";
import { AuthShell } from "@/components/auth/auth-shell";
import { VerifyEmailPrompt } from "@/components/auth/verify-email";

export const metadata: Metadata = { title: "Verify your email" };

export default function VerifyEmailPage() {
  return <AuthShell eyebrow="One last step" title="Check your inbox." description="We sent a verification link to your school email. It confirms that you belong to your campus community."><Suspense fallback={<div className="h-64 animate-pulse rounded-2xl bg-white/50" />}><VerifyEmailPrompt /></Suspense></AuthShell>;
}
