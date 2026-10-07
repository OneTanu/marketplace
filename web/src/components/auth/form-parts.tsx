import type { InputHTMLAttributes, ReactNode } from "react";

export function Field({ label, hint, error, ...props }: InputHTMLAttributes<HTMLInputElement> & { label: string; hint?: string; error?: string }) {
  return <label className="block"><span className="flex items-center justify-between text-sm font-bold">{label}{hint && <span className="font-normal text-muted">{hint}</span>}</span><input {...props} aria-invalid={Boolean(error)} className="field mt-2 text-[15px] placeholder:text-muted aria-[invalid=true]:border-[var(--danger)]" />{error && <span className="mt-1.5 block text-sm text-[var(--danger)]">{error}</span>}</label>;
}

export function FormAlert({ children }: { children: ReactNode }) {
  return <div role="alert" className="rounded-xl border border-[var(--danger)]/25 bg-[var(--danger-soft)] px-4 py-3 text-sm leading-6 text-[var(--danger)]">{children}</div>;
}

export function SubmitButton({ pending, children, pendingText }: { pending: boolean; children: ReactNode; pendingText: string }) {
  return <button disabled={pending} className="btn btn-primary h-12 w-full text-[15px]">{pending ? pendingText : children}</button>;
}
