"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useState } from "react";
import { authRequest, errorsFrom } from "@/lib/auth";
import { FormAlert } from "./form-parts";

export function VerifyEmailPrompt() {
  const params = useSearchParams(); const email = params.get("email");
  const [status, setStatus] = useState<"idle" | "sending" | "sent" | "error">("idle"); const [error, setError] = useState("");
  async function resend() {
    setStatus("sending"); setError("");
    try {
      const { response, body } = await authRequest("auth/email/verify/resend", { method: "POST" });
      if (response.ok) setStatus("sent"); else { setError(errorsFrom(body, "We couldn’t resend the email yet. Try again in a moment.")[0].message); setStatus("error"); }
    } catch { setError("Tanu couldn’t reach the server. Check your connection and try again."); setStatus("error"); }
  }
  return <div className="space-y-5">
    <div className="grid size-16 place-items-center rounded-xl bg-brand-soft text-display">✉</div>
    {email && <p className="rounded-xl border border-line bg-white px-4 py-3 text-label font-semibold">{email}</p>}
    <ol className="space-y-3 text-label leading-6 text-muted"><li className="flex gap-3"><span className="font-mono font-semibold text-brand">1.</span>Open the verification email from Tanu.</li><li className="flex gap-3"><span className="font-mono font-semibold text-brand">2.</span>Click the secure link inside.</li><li className="flex gap-3"><span className="font-mono font-semibold text-brand">3.</span>Come back and start exploring your campus.</li></ol>
    {status === "sent" && <div role="status" className="rounded-xl bg-surface px-4 py-3 text-label text-ink">A fresh verification email is on its way.</div>}
    {status === "error" && <FormAlert>{error}</FormAlert>}
    <button onClick={resend} disabled={status === "sending"} className="btn btn-secondary h-12 w-full">{status === "sending" ? "Sending…" : "Resend verification email"}</button>
    <p className="text-center text-label text-muted">Already verified? <Link href="/account/login" className="font-semibold text-foreground hover:underline">Log in</Link></p>
  </div>;
}
