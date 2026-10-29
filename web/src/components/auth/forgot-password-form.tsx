"use client";

import Link from "next/link";
import { FormEvent, useState } from "react";
import { authRequest, errorsFrom, type AuthError } from "@/lib/auth";
import { Field, FormAlert, SubmitButton } from "./form-parts";

export function ForgotPasswordForm() {
  const [pending, setPending] = useState(false); const [errors, setErrors] = useState<AuthError[]>([]); const [sentTo, setSentTo] = useState<string | null>(null);
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setPending(true); setErrors([]);
    const email = String(new FormData(event.currentTarget).get("email")).trim();
    if (!email) { setErrors([{ field: "email", message: "Enter your school email." }]); setPending(false); return; }
    try {
      // allauth answers 200 whether or not the address has an account (ACCOUNT_PREVENT_ENUMERATION),
      // so the confirmation below never says which. A 400 is only a malformed address; 429 is its rate limit.
      const { response, body } = await authRequest("auth/password/request", { method: "POST", body: JSON.stringify({ email }) });
      if (response.ok) setSentTo(email);
      else if (response.status === 429) setErrors([{ message: "Too many reset requests. Wait a few minutes, then try again." }]);
      else setErrors(errorsFrom(body, "We couldn’t send a reset link. Check the email address and try again."));
    } catch { setErrors([{ message: "Tanu couldn’t reach the server. Check your connection and try again." }]); }
    finally { setPending(false); }
  }
  if (sentTo) return <div className="space-y-5">
    <div role="status" className="rounded-2xl bg-surface p-6">
      <div className="grid size-12 place-items-center rounded-full bg-[var(--brand-soft)] text-xl" aria-hidden="true">✉</div>
      <p className="mt-4 font-bold text-ink">Check your inbox.</p>
      <p className="mt-2 text-sm leading-6 text-muted">If <strong className="break-all font-semibold text-ink">{sentTo}</strong> belongs to a Tanu account, we’ve sent it a link to reset your password. The link works once and expires after a few days.</p>
      <p className="mt-2 text-sm leading-6 text-muted">Nothing there after a few minutes? Check your spam folder.</p>
    </div>
    <button type="button" onClick={() => setSentTo(null)} className="btn btn-secondary h-12 w-full">Use a different email</button>
  </div>;
  const fieldError = errors.find((error) => error.field === "email")?.message;
  return <form method="post" onSubmit={submit} className="space-y-5" noValidate>
    {errors.filter((error) => error.field !== "email").map((error) => <FormAlert key={error.message}>{error.message}</FormAlert>)}
    <Field label="School email" name="email" type="email" autoComplete="email" inputMode="email" placeholder="you@umd.edu" required error={fieldError} />
    <SubmitButton pending={pending} pendingText="Sending reset link…">Send reset link</SubmitButton>
    <p className="text-center text-sm text-muted">Remembered it? <Link href="/account/login" className="font-bold text-foreground hover:underline">Back to login</Link></p>
  </form>;
}
