import { defineConfig, globalIgnores } from "eslint/config";
import nextVitals from "eslint-config-next/core-web-vitals";
import nextTs from "eslint-config-next/typescript";

import tanu from "./eslint-rules/design-tokens.mjs";

const eslintConfig = defineConfig([
  ...nextVitals,
  ...nextTs,
  {
    files: ["src/**/*.{ts,tsx}"],
    plugins: { tanu },
    rules: {
      "tanu/design-tokens": "error",
      // One icon family: icons come through components/ui/icons.tsx (types may come from Lucide).
      "@typescript-eslint/no-restricted-imports": ["error", { paths: [{ name: "lucide-react", message: "Import icons from @/components/ui/icons.", allowTypeImports: true }] }],
    },
  },
  {
    // Exceptions, each with a reason:
    // - icons.tsx is where icons are drawn; the share image is rendered to a PNG by next/og.
    // - the design lab is a sandbox of old visual directions, never served in production.
    files: [
      "src/components/ui/icons.tsx",
      "src/app/opengraph-image.tsx",
      "src/components/design-lab/**",
    ],
    rules: { "tanu/design-tokens": "off", "@typescript-eslint/no-restricted-imports": "off" },
  },
  // Override default ignores of eslint-config-next.
  globalIgnores([
    // Default ignores of eslint-config-next:
    ".next/**",
    "out/**",
    "build/**",
    "next-env.d.ts",
    // Playwright output.
    "playwright-report/**",
    "test-results/**",
    "blob-report/**",
  ]),
]);

export default eslintConfig;
