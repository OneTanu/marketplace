import type { Metadata } from "next";
import Link from "next/link";
import { AuthShell } from "@/components/auth/auth-shell";
import { LoginForm } from "@/components/auth/login-form";

export const metadata: Metadata = { title: "Log in" };

export default function LoginPage() {
  return <AuthShell eyebrow="Welcome back" title="Good to see you." description="Log in to browse your campus, manage listings, and pick up where you left off." footer={<>New to Tanu? <Link href="/account/signup" className="font-bold text-foreground hover:underline">Create an account</Link></>}><LoginForm /></AuthShell>;
}
