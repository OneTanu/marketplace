"use client";

import { useRouter } from "next/navigation";
import { FormEvent, useState } from "react";
import { authRequest, errorsFrom, pendingFlow, type AuthError } from "@/lib/auth";
import { Field, FormAlert, SubmitButton } from "./form-parts";
import { SupportedSchoolsNote } from "./supported-schools-note";

export function SignupForm() {
  const router = useRouter();
  const [pending, setPending] = useState(false);
  const [errors, setErrors] = useState<AuthError[]>([]);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setPending(true); setErrors([]);
    const data = new FormData(event.currentTarget);
    const password = String(data.get("password"));
    if (password !== String(data.get("confirm"))) { setErrors([{ field: "confirm", message: "The passwords do not match." }]); setPending(false); return; }
    try {
      const { response, body } = await authRequest("auth/signup", {
        method: "POST",
        body: JSON.stringify({
          email: String(data.get("email")).trim(),
          username: String(data.get("username")).trim(),
          first_name: String(data.get("first_name")).trim(),
          last_name: String(data.get("last_name")).trim(),
          password,
        }),
      });
      if (response.ok) { router.push("/"); router.refresh(); }
      else if (response.status === 401 && pendingFlow(body, "verify_email")) router.push(`/account/verify-email?email=${encodeURIComponent(String(data.get("email")))}`);
      else setErrors(errorsFrom(body, "We couldn’t create your account. Please check your details and try again."));
    } catch { setErrors([{ message: "Tanu couldn’t reach the server. Check your connection and try again." }]); }
    finally { setPending(false); }
  }
  const fieldError = (name: string) => errors.find((error) => error.field === name)?.message;
  return <form onSubmit={submit} className="space-y-5" noValidate>
    {errors.filter((error) => !error.field).map((error) => <FormAlert key={error.message}>{error.message}</FormAlert>)}
    <div className="grid gap-5 sm:grid-cols-2">
      <Field label="First name" name="first_name" autoComplete="given-name" required error={fieldError("first_name")} />
      <Field label="Last name" hint="Kept private" name="last_name" autoComplete="family-name" required error={fieldError("last_name")} />
    </div>
    <Field label="Username" hint="Permanent and publicly visible" name="username" autoComplete="username" minLength={3} maxLength={30} required error={fieldError("username")} />
    <Field label="School email" name="email" type="email" autoComplete="email" placeholder="you@umd.edu" required error={fieldError("email")} />
    <Field label="Password" hint="8+ characters" name="password" type="password" autoComplete="new-password" minLength={8} required error={fieldError("password")} />
    <Field label="Confirm password" name="confirm" type="password" autoComplete="new-password" minLength={8} required error={fieldError("confirm")} />
    <SupportedSchoolsNote />
    <SubmitButton pending={pending} pendingText="Creating your account…">Create student account</SubmitButton>
    <p className="text-center text-xs leading-5 text-muted">By joining, you agree to Tanu’s Terms and Privacy Policy.</p>
  </form>;
}
