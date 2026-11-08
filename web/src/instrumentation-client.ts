import * as Sentry from "@sentry/nextjs";

import { sentryOptions } from "@/lib/sentry";

// Browser errors go to Sentry when NEXT_PUBLIC_SENTRY_DSN is set (Vercel Production only).
const dsn = process.env.NEXT_PUBLIC_SENTRY_DSN;
if (dsn) Sentry.init(sentryOptions(dsn, process.env.NEXT_PUBLIC_VERCEL_ENV ?? "development"));
