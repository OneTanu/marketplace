import type * as Sentry from "@sentry/nextjs";

/** Sentry options shared by the server and the browser: errors only (no performance tracing,
 * no session replays), and none of a student's personal data. User details, cookies, headers,
 * request and response bodies, and URL query strings (which can hold search terms) stay out. */
export function sentryOptions(dsn: string, environment: string): Parameters<typeof Sentry.init>[0] {
  return {
    dsn,
    environment,
    tracesSampleRate: 0,
    dataCollection: {
      userInfo: false,
      cookies: false,
      httpHeaders: false,
      httpBodies: [],
      urlQueryParams: false,
    },
  };
}
