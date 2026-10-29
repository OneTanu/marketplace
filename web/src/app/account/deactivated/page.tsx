import type { Metadata } from "next";
import Link from "next/link";

export const metadata: Metadata = { title: "Account deactivated" };

export default function AccountDeactivatedPage() {
  return (
    <main className="mx-auto grid min-h-[70vh] max-w-xl place-items-center px-4 text-center">
      <div>
        <h1 className="type-wide text-3xl font-black">Your account is deactivated</h1>
        <p className="mt-3 leading-7 text-muted">
          Your profile and listings are hidden, and you&apos;ve been signed out everywhere. We&apos;ve emailed you a confirmation.
        </p>
        <p className="mt-2 leading-7 text-muted">Changed your mind? Log in again with your school email and password to reactivate it.</p>
        <div className="mt-6 flex justify-center gap-2">
          <Link href="/" className="btn btn-secondary">Back to Tanu</Link>
          <Link href="/account/login" className="btn btn-primary">Log in</Link>
        </div>
      </div>
    </main>
  );
}
