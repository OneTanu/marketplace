import type { InputHTMLAttributes, ReactNode } from "react";

export function Field({ label, hint, error, ...props }: InputHTMLAttributes<HTMLInputElement> & { label: string; hint?: string; error?: string }) {
  return <label className="block"><span className="flex items-center justify-between text-sm font-bold">{label}{hint && <span className="font-normal text-muted">{hint}</span>}</span><input {...props} aria-invalid={Boolean(error)} className="mt-2 h-12 w-full rounded-xl border border-line bg-white px-4 text-[15px] outline-none transition placeholder:text-[#9ba49f] focus:border-forest focus:ring-4 focus:ring-forest/10 aria-[invalid=true]:border-[var(--danger)]" />{error && <span className="mt-1.5 block text-sm text-[var(--danger)]">{error}</span>}</label>;
}

export function FormAlert({ children }: { children: ReactNode }) {
  return <div role="alert" className="rounded-xl border border-[#f3c7c2] bg-[var(--danger-soft)] px-4 py-3 text-sm leading-6 text-[var(--danger)]">{children}</div>;
}

export function SubmitButton({ pending, children, pendingText }: { pending: boolean; children: ReactNode; pendingText: string }) {
  return <button disabled={pending} className="flex h-12 w-full items-center justify-center rounded-full bg-foreground px-5 text-sm font-bold text-white shadow-sm transition hover:-translate-y-0.5 hover:bg-forest disabled:cursor-wait disabled:opacity-65 disabled:hover:translate-y-0">{pending ? pendingText : children}</button>;
}
