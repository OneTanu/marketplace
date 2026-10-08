import { execFileSync } from "node:child_process";

import { API_CONTAINER } from "./slot";

/**
 * Killing `docker compose run` (which is what Playwright does to stop a web server) leaves
 * its container running, so remove the local E2E API container explicitly.
 */
export default function globalTeardown() {
  try {
    execFileSync("docker", ["rm", "-f", API_CONTAINER], { stdio: "ignore" });
  } catch {
    // Already gone.
  }
}
