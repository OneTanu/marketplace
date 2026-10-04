import type { Metadata } from "next";
import { AuthShell } from "@/components/auth/auth-shell";
import { ConfirmEmail } from "@/components/auth/confirm-email";

export const metadata: Metadata = { title: "Confirm school email" };

export default async function ConfirmEmailPage({ params }: PageProps<"/account/verify-email/[key]">) {
  const { key } = await params;
  return <AuthShell eyebrow="Email verification" title="Confirming it’s you." description="We’re securely confirming your school email with Tanu."><ConfirmEmail verificationKey={key} /></AuthShell>;
}
