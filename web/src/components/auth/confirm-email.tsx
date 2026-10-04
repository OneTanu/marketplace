"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { authRequest } from "@/lib/auth";
import { homeMarketplacePath } from "@/lib/platform";

export function ConfirmEmail({ verificationKey }: { verificationKey: string }) {
  const router = useRouter(); const [state, setState] = useState<"loading" | "success" | "error">("loading");
  useEffect(() => {
    let active = true;
    authRequest("auth/email/verify", { headers: { "X-Email-Verification-Key": verificationKey } }).then(async ({ response }) => { if (!active) return; setState(response.ok ? "success" : "error"); if (response.ok) { const path = await homeMarketplacePath(); setTimeout(() => router.push(path), 1400); } }).catch(() => active && setState("error"));
    return () => { active = false; };
  }, [router, verificationKey]);
  if (state === "loading") return <div role="status" className="rounded-2xl border border-line bg-white p-6 text-center text-sm text-muted">Verifying your school email…</div>;
  if (state === "success") return <div role="status" className="rounded-2xl bg-[var(--forest-soft)] p-6 text-center"><div className="mx-auto grid size-12 place-items-center rounded-full bg-forest text-xl text-white">✓</div><p className="mt-4 font-bold text-forest">You’re verified and ready to go.</p><p className="mt-1 text-sm text-muted">Taking you to Tanu…</p></div>;
  return <div role="alert" className="rounded-2xl border border-[#f3c7c2] bg-[var(--danger-soft)] p-6 text-center"><p className="font-bold text-[var(--danger)]">That verification link isn’t valid anymore.</p><p className="mt-2 text-sm leading-6 text-muted">It may have expired or already been used.</p><Link href="/account/login" className="mt-5 inline-flex rounded-full bg-foreground px-5 py-3 text-sm font-bold text-white">Return to login</Link></div>;
}
