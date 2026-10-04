"use client";

import { useRouter } from "next/navigation";
import { FormEvent, useState } from "react";
import { authRequest, errorsFrom, pendingFlow, type AuthError } from "@/lib/auth";
import { homeMarketplacePath } from "@/lib/platform";
import { Field, FormAlert, SubmitButton } from "./form-parts";

export function LoginForm() {
  const router = useRouter(); const [pending, setPending] = useState(false); const [errors, setErrors] = useState<AuthError[]>([]);
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setPending(true); setErrors([]); const data = new FormData(event.currentTarget);
    try {
      const { response, body } = await authRequest("auth/login", { method: "POST", body: JSON.stringify({ email: String(data.get("email")).trim(), password: String(data.get("password")) }) });
      if (response.ok) { router.push(await homeMarketplacePath()); router.refresh(); }
      else if (response.status === 401 && pendingFlow(body, "verify_email")) router.push(`/account/verify-email?email=${encodeURIComponent(String(data.get("email")))}`);
      else setErrors(errorsFrom(body, "That email and password combination didn’t work."));
    } catch { setErrors([{ message: "Tanu couldn’t reach the server. Check your connection and try again." }]); }
    finally { setPending(false); }
  }
  return <form onSubmit={submit} className="space-y-5" noValidate>
    {errors.map((error) => <FormAlert key={`${error.field}-${error.message}`}>{error.message}</FormAlert>)}
    <Field label="School email" name="email" type="email" autoComplete="email" placeholder="you@umd.edu" required />
    <Field label="Password" name="password" type="password" autoComplete="current-password" required />
    <SubmitButton pending={pending} pendingText="Logging you in…">Log in</SubmitButton>
  </form>;
}
