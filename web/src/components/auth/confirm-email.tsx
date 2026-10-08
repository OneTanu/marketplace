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
    // Next.js leaves dynamic params URL-encoded, and allauth keys contain ":" (sent as %3A).
    // POST confirms the address (GET only looks the key up). 200 means verified and signed in;
    // 401 means verified, but this browser has no pending signup, so the user still has to log in.
    authRequest("auth/email/verify", { method: "POST", body: JSON.stringify({ key: decodeURIComponent(verificationKey) }) }).then(async ({ response }) => { if (!active) return; const verified = response.ok || response.status === 401; setState(verified ? "success" : "error"); if (verified) { const path = response.ok ? await homeMarketplacePath() : "/account/login"; setTimeout(() => router.push(path), 1400); } }).catch(() => active && setState("error"));
    return () => { active = false; };
  }, [router, verificationKey]);
  if (state === "loading") return <div role="status" className="rounded-2xl border border-line bg-white p-6 text-center text-sm text-muted">Verifying your school email…</div>;
  if (state === "success") return <div role="status" className="rounded-2xl bg-surface p-6 text-center"><div className="mx-auto grid size-12 place-items-center rounded-full bg-ink text-xl text-white">✓</div><p className="mt-4 font-bold text-ink">You’re verified and ready to go.</p><p className="mt-1 text-sm text-muted">Taking you to Tanu…</p></div>;
  return <div role="alert" className="rounded-2xl border border-[var(--danger)]/25 bg-[var(--danger-soft)] p-6 text-center"><p className="font-bold text-[var(--danger)]">That verification link isn’t valid anymore.</p><p className="mt-2 text-sm leading-6 text-muted">It may have expired or already been used.</p><Link href="/account/login" className="mt-5 inline-flex btn btn-primary">Return to login</Link></div>;
}
