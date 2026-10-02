# Tanu web app

Next.js + TypeScript, managed with [pnpm](https://pnpm.io). See the root `AGENTS.md` for project rules.

```bash
pnpm install      # install dependencies
pnpm dev          # http://localhost:3000 (expects the API from `docker compose up` on :8000)
pnpm lint
pnpm typecheck
pnpm build
pnpm api:types    # regenerate src/lib/api/schema.d.ts from ../contracts/openapi.yaml
```
