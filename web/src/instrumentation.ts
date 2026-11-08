import * as Sentry from "@sentry/nextjs";

import { sentryOptions } from "@/lib/sentry";

// Server-side errors (server components, route handlers, proxying) go to Sentry when
// NEXT_PUBLIC_SENTRY_DSN is set, which is only in Vercel's Production environment.
export function register() {
  const dsn = process.env.NEXT_PUBLIC_SENTRY_DSN;
  if (dsn) Sentry.init(sentryOptions(dsn, process.env.VERCEL_ENV ?? "development"));
}

export const onRequestError = Sentry.captureRequestError;
