import type { Metadata } from "next";
import { AuthShell } from "@/components/auth/auth-shell";
import { ForgotPasswordForm } from "@/components/auth/forgot-password-form";

export const metadata: Metadata = { title: "Forgot password" };

export default function ForgotPasswordPage() {
  return <AuthShell eyebrow="Password help" title="Forgot your password?" description="Enter your school email and we’ll send you a link to choose a new one."><ForgotPasswordForm /></AuthShell>;
}
