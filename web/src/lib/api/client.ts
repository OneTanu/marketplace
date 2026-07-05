import createClient from "openapi-fetch";

import type { paths } from "./schema";

// Typed API client. Paths and response types come from contracts/openapi.yaml
// (regenerate with `npm run api:types`). Requests are relative ("/api/..."), so they go
// through the Next.js proxy; use this from client components.
export const api = createClient<paths>({ baseUrl: "" });
