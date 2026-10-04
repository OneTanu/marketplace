import type { Metadata } from "next";
import Link from "next/link";
import { AuthShell } from "@/components/auth/auth-shell";
import { SignupForm } from "@/components/auth/signup-form";

export const metadata: Metadata = { title: "Join" };

export default function SignupPage() {
  return <AuthShell eyebrow="Student access" title="Join your campus marketplace." description="Your school email keeps the community local and gives every buyer and seller a layer of trust." footer={<>Already on Tanu? <Link href="/account/login" className="font-bold text-foreground hover:underline">Log in</Link></>}><SignupForm /></AuthShell>;
}
