import type { Metadata } from "next";
import { AuthShell } from "@/components/auth/auth-shell";
import { ResetPasswordForm } from "@/components/auth/reset-password-form";

export const metadata: Metadata = { title: "Reset password" };

export default async function ResetPasswordPage({ params }: PageProps<"/account/password/reset/[key]">) {
  const { key } = await params;
  return <AuthShell eyebrow="Password help" title="Choose a new password." description="Pick a password you don’t use anywhere else. Resetting it logs you out on every device."><ResetPasswordForm resetKey={key} /></AuthShell>;
}
