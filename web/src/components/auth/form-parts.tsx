import type { InputHTMLAttributes, ReactNode } from "react";

export function Field({ label, hint, error, ...props }: InputHTMLAttributes<HTMLInputElement> & { label: string; hint?: string; error?: string }) {
  return <label className="block"><span className="flex items-center justify-between text-label font-semibold">{label}{hint && <span className="font-normal text-muted">{hint}</span>}</span><input {...props} aria-invalid={Boolean(error)} className="field mt-2 placeholder:text-muted aria-[invalid=true]:border-danger" />{error && <span className="mt-1.5 block text-label text-danger">{error}</span>}</label>;
}

export function FormAlert({ children }: { children: ReactNode }) {
  return <div role="alert" className="rounded-xl border border-danger/25 bg-danger-soft px-4 py-3 text-label leading-6 text-danger">{children}</div>;
}

export function SubmitButton({ pending, children, pendingText }: { pending: boolean; children: ReactNode; pendingText: string }) {
  return <button disabled={pending} className="btn btn-primary h-12 w-full text-body">{pending ? pendingText : children}</button>;
}
