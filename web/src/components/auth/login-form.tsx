"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { FormEvent, useState } from "react";
import { reactivateAccount } from "@/lib/account";
import { authRequest, errorsFrom, pendingFlow, type AuthError, type AllauthResponse } from "@/lib/auth";
import { homeMarketplacePath } from "@/lib/platform";
import { Field, FormAlert, SubmitButton } from "./form-parts";

/** allauth answers a correct password for a switched-off account with 401 and no step to
 * finish (an unverified email has a pending "verify_email" step instead). Wrong passwords are
 * a 400, so this only shows to someone who knows the password. */
function isInactiveAccount(response: Response, body: AllauthResponse) {
  return response.status === 401 && !body.data?.flows?.some((flow) => flow.is_pending);
}

export function LoginForm() {
  const router = useRouter(); const [pending, setPending] = useState(false); const [errors, setErrors] = useState<AuthError[]>([]);
  // Set when the account is deactivated, so it can be reactivated with the same details.
  const [inactive, setInactive] = useState<{ email: string; password: string } | null>(null);

  async function logIn(email: string, password: string) {
    const { response, body } = await authRequest("auth/login", { method: "POST", body: JSON.stringify({ email, password }) });
    if (response.ok) { router.push(await homeMarketplacePath()); router.refresh(); }
    else if (response.status === 401 && pendingFlow(body, "verify_email")) router.push(`/account/verify-email?email=${encodeURIComponent(email)}`);
    else if (isInactiveAccount(response, body)) setInactive({ email, password });
    else setErrors(errorsFrom(body, "That email and password combination didn’t work."));
  }

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setPending(true); setErrors([]); setInactive(null); const data = new FormData(event.currentTarget);
    try { await logIn(String(data.get("email")).trim(), String(data.get("password"))); }
    catch { setErrors([{ message: "Tanu couldn’t reach the server. Check your connection and try again." }]); }
    finally { setPending(false); }
  }

  async function reactivate() {
    if (!inactive) return;
    setPending(true); setErrors([]);
    try { await reactivateAccount(inactive.email, inactive.password); setInactive(null); await logIn(inactive.email, inactive.password); }
    catch (caught) { setInactive(null); setErrors([{ message: caught instanceof Error ? caught.message : "Your account couldn’t be reactivated. Try again." }]); }
    finally { setPending(false); }
  }

  return <form method="post" onSubmit={submit} className="space-y-5" noValidate>
    {errors.map((error) => <FormAlert key={`${error.field}-${error.message}`}>{error.message}</FormAlert>)}
    {inactive && <div role="status" className="rounded-xl border border-line bg-surface p-4 text-sm">
      <p className="font-bold">This account is deactivated</p>
      <p className="mt-1 text-muted">Reactivate it to bring back your profile and listings.</p>
      <button type="button" onClick={reactivate} disabled={pending} className="btn btn-primary mt-3 w-full">{pending ? "Reactivating…" : "Reactivate and log in"}</button>
    </div>}
    <Field label="School email" name="email" type="email" autoComplete="email" placeholder="you@umd.edu" required />
    <div>
      <Field label="Password" name="password" type="password" autoComplete="current-password" required />
      <Link href="/account/forgot-password" className="mt-2 inline-block text-sm font-semibold text-muted hover:text-foreground hover:underline">Forgot password?</Link>
    </div>
    <SubmitButton pending={pending} pendingText="Logging you in…">Log in</SubmitButton>
  </form>;
}
