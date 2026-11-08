"use client";

import * as Sentry from "@sentry/nextjs";
import { useEffect } from "react";

import "./globals.css";

/** Last-resort page when the app itself crashes (the root layout replaced). Reports the error,
 * then offers a way back. */
export default function GlobalError({ error, reset }: { error: Error & { digest?: string }; reset: () => void }) {
  useEffect(() => {
    Sentry.captureException(error);
  }, [error]);

  return <html lang="en">
    <body className="flex min-h-screen items-center justify-center bg-background px-4 font-sans text-ink">
      <section className="max-w-md text-center">
        <p className="type-wide text-[1.625rem] font-black leading-none">tanu</p>
        <h1 className="type-wide mt-8 text-3xl font-black leading-tight">Something went wrong.</h1>
        <p className="mt-3 leading-7 text-muted">Tanu hit an unexpected error. We’ve been notified. Try again, or come back in a few minutes.</p>
        <div className="mt-8 flex flex-col justify-center gap-3 sm:flex-row">
          <button type="button" onClick={reset} className="btn btn-primary h-12 px-6 text-[15px]">Try again</button>
          {/* A plain link: the app's router may be what crashed. */}
          {/* eslint-disable-next-line @next/next/no-html-link-for-pages */}
          <a href="/" className="btn btn-secondary h-12 px-6 text-[15px]">Go home</a>
        </div>
      </section>
    </body>
  </html>;
}
