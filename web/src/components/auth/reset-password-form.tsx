"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { FormEvent, useEffect, useState } from "react";
import { authRequest, errorsFrom, resetKeyStatus, type AuthError, type ResetKeyStatus } from "@/lib/auth";
import { Field, FormAlert, SubmitButton } from "./form-parts";

type State = "checking" | "ready" | "success" | Exclude<ResetKeyStatus, "valid">;

const BROKEN_LINKS: Record<Exclude<ResetKeyStatus, "valid">, { title: string; detail: string }> = {
  expired: { title: "This reset link has expired.", detail: "Reset links only work for a few days. Request a new one and use it soon." },
  used: { title: "This reset link has already been used.", detail: "A link stops working once your password changes or you log in. If you didn’t just reset it, request a new link." },
  invalid: { title: "This reset link isn’t valid.", detail: "It may be incomplete. Copy the whole link from the email, or request a new one." },
};

export function ResetPasswordForm({ resetKey }: { resetKey: string }) {
  // Next.js leaves dynamic params URL-encoded.
  const key = decodeURIComponent(resetKey);
  const router = useRouter();
  const [state, setState] = useState<State>("checking"); const [email, setEmail] = useState("");
  const [pending, setPending] = useState(false); const [errors, setErrors] = useState<AuthError[]>([]);

  async function explainBrokenKey() {
    const status = await resetKeyStatus(key);
    setState(status === "valid" ? "invalid" : status);
  }

  useEffect(() => {
    let active = true;
    // allauth reads the key from this header on GET; 200 means the link can still be used.
    authRequest("auth/password/reset", { headers: { "X-Password-Reset-Key": key } }).then(async ({ response, body }) => {
      if (!active) return;
      if (response.ok) { setEmail(body.data?.user?.email ?? ""); setState("ready"); }
      else if (response.status === 400) { const status = await resetKeyStatus(key); if (active) setState(status === "valid" ? "invalid" : status); }
      else setErrors([{ message: "We couldn’t check this link right now. Refresh the page to try again." }]);
    }).catch(() => active && setErrors([{ message: "Tanu couldn’t reach the server. Check your connection and refresh the page." }]));
    return () => { active = false; };
  }, [key]);

  useEffect(() => {
    if (state !== "success") return;
    const timer = setTimeout(() => router.push("/account/login"), 4000);
    return () => clearTimeout(timer);
  }, [router, state]);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setPending(true); setErrors([]);
    const data = new FormData(event.currentTarget); const password = String(data.get("password"));
    if (!password) { setErrors([{ field: "password", message: "Enter a new password." }]); setPending(false); return; }
    if (password !== String(data.get("confirm"))) { setErrors([{ field: "confirm", message: "The passwords do not match." }]); setPending(false); return; }
    try {
      const { response, body } = await authRequest("auth/password/reset", { method: "POST", body: JSON.stringify({ key, password }) });
      // 401 is success: the password changed, and allauth doesn't sign the student in afterwards.
      if (response.ok || response.status === 401) setState("success");
      else if (body.errors?.some((error) => error.param === "key")) await explainBrokenKey();
      else if (response.status === 429) setErrors([{ message: "Too many attempts. Wait a few minutes, then try again." }]);
      else setErrors(errorsFrom(body, "We couldn’t update your password. Please try again."));
    } catch { setErrors([{ message: "Tanu couldn’t reach the server. Check your connection and try again." }]); }
    finally { setPending(false); }
  }

  if (state === "checking") return errors.length ? <FormAlert>{errors[0].message}</FormAlert> : <div role="status" className="rounded-2xl border border-line bg-white p-6 text-center text-sm text-muted">Checking your reset link…</div>;
  if (state === "success") return <div role="status" className="rounded-2xl bg-surface p-6 text-center"><div className="mx-auto grid size-12 place-items-center rounded-full bg-ink text-xl text-white" aria-hidden="true">✓</div><p className="mt-4 font-bold text-ink">Your password has been reset.</p><p className="mt-1 text-sm leading-6 text-muted">You’ve been logged out everywhere. Log in with your new password; taking you there now…</p><Link href="/account/login" className="mt-5 inline-flex btn btn-primary">Log in</Link></div>;
  if (state !== "ready") {
    const { title, detail } = BROKEN_LINKS[state];
    return <div role="alert" className="rounded-2xl border border-[var(--danger)]/25 bg-[var(--danger-soft)] p-6 text-center"><p className="font-bold text-[var(--danger)]">{title}</p><p className="mt-2 text-sm leading-6 text-muted">{detail}</p><div className="mt-5 flex flex-col gap-2 sm:flex-row sm:justify-center"><Link href="/account/forgot-password" className="btn btn-primary">Request a new link</Link><Link href="/account/login" className="btn btn-quiet">Return to login</Link></div></div>;
  }
  const fieldError = (name: string) => errors.find((error) => error.field === name)?.message;
  return <form method="post" onSubmit={submit} className="space-y-5" noValidate>
    {errors.filter((error) => error.field !== "password" && error.field !== "confirm").map((error) => <FormAlert key={error.message}>{error.message}</FormAlert>)}
    {/* Tells password managers which account the new password belongs to. */}
    <input type="email" name="username" autoComplete="username" value={email} readOnly hidden />
    {email && <p className="rounded-xl border border-line bg-white px-4 py-3 text-sm">Resetting the password for <strong className="break-all font-semibold">{email}</strong></p>}
    <Field label="New password" hint="8+ characters" name="password" type="password" autoComplete="new-password" minLength={8} required error={fieldError("password")} />
    <Field label="Confirm new password" name="confirm" type="password" autoComplete="new-password" minLength={8} required error={fieldError("confirm")} />
    <SubmitButton pending={pending} pendingText="Updating your password…">Reset password</SubmitButton>
  </form>;
}
