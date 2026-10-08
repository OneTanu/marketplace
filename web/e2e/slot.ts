/**
 * E2E_SLOT=n (default 0) gives a run its own ports, database and API container, so checkouts
 * running E2E at the same time (e.g. parallel agents in git worktrees) don't collide. Slot 0
 * is what CI and a plain `pnpm e2e` use.
 */
const raw = process.env.E2E_SLOT ?? "0";
const SLOT = Number(raw);
if (!Number.isInteger(SLOT) || SLOT < 0 || SLOT > 99) {
  throw new Error(`E2E_SLOT must be a whole number from 0 to 99 (got "${raw}").`);
}

export const WEB_PORT = 3100 + SLOT;
export const API_PORT = 8100 + SLOT;
// backend/scripts/e2e_server.sh only recreates databases whose name ends in "_e2e".
export const POSTGRES_DB = SLOT ? `tanu_${SLOT}_e2e` : "tanu_e2e";
/** Name of the local E2E API container (started by playwright.config.ts). */
export const API_CONTAINER = SLOT ? `tanu-e2e-backend-${SLOT}` : "tanu-e2e-backend";
