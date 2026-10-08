import { defineConfig, devices } from "@playwright/test";

import { API_CONTAINER, API_PORT, POSTGRES_DB, WEB_PORT } from "./e2e/slot";
import { TEST_USER } from "./e2e/test-user";

// E2E runs its own servers on their own ports and database, so it never clashes with
// `pnpm dev` (3000), the compose API (8000), or the dev database (tanu). E2E_SLOT picks
// which ports and database (see e2e/slot.ts).
const WEB_URL = `http://localhost:${WEB_PORT}`;
// 127.0.0.1, not localhost: Django listens on IPv4 only.
const API_URL = `http://127.0.0.1:${API_PORT}`;

const isCI = !!process.env.CI;

const backendEnv = {
  POSTGRES_DB,
  PORT: String(API_PORT),
  WEB_APP_URL: WEB_URL,
  E2E_USER_EMAIL: TEST_USER.email,
  E2E_USER_PASSWORD: TEST_USER.password,
  // So runserver's startup line reaches Playwright through the pipe right away.
  PYTHONUNBUFFERED: "1",
};

// CI runs Django with uv against the Postgres service on localhost:5433. Locally it runs in
// the compose "backend" image against the running db container, reached through its host
// port (not the compose network) so it also works from a git worktree. A container left
// over from an interrupted run is removed first.
const backendCommand = isCI
  ? "uv run --frozen sh scripts/e2e_server.sh"
  : [
      `docker rm -f ${API_CONTAINER} &&`,
      `docker compose run --rm --no-deps --build --quiet-build -T --name ${API_CONTAINER}`,
      `-p 127.0.0.1:${API_PORT}:${API_PORT}`,
      "-e POSTGRES_HOST=host.docker.internal -e POSTGRES_PORT=5433",
      // Values come from webServer.env below, so nothing is quoted through the shell.
      ...Object.keys(backendEnv).map((key) => `-e ${key}`),
      "backend sh scripts/e2e_server.sh",
    ].join(" ");

export default defineConfig({
  testDir: "./e2e",
  fullyParallel: true,
  forbidOnly: isCI,
  retries: isCI ? 1 : 0,
  reporter: [[isCI ? "github" : "list"], ["html", { open: "never" }]],
  // Removes the API container after a run (stopping `docker compose run` leaves it running).
  globalTeardown: isCI ? undefined : "./e2e/global-teardown.ts",
  use: {
    baseURL: WEB_URL,
    trace: "retain-on-failure",
  },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
  webServer: [
    {
      name: "api",
      command: backendCommand,
      cwd: "../backend",
      env: backendEnv,
      // Wait for runserver's startup line instead of polling a URL. With a URL, Playwright
      // would silently reuse a leftover API (old code, database not reset).
      wait: { stdout: /development server at/ },
      // The first local run builds the backend image.
      timeout: 300_000,
      stdout: "pipe",
    },
    {
      name: "web",
      // Production build, as the Next.js testing guide recommends. next.config.ts reads
      // API_URL at build time, so this leaves a .next build that proxies to the E2E API;
      // rerun `pnpm build` before using `pnpm start` yourself.
      command: `pnpm exec next build && pnpm exec next start --port ${WEB_PORT}`,
      env: { API_URL, NEXT_TELEMETRY_DISABLED: "1" },
      url: WEB_URL,
      timeout: 300_000,
      reuseExistingServer: !isCI,
    },
  ],
});
