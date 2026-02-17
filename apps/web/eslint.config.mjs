import { defineConfig, globalIgnores } from "eslint/config";
import nextVitals from "eslint-config-next/core-web-vitals";
import nextTs from "eslint-config-next/typescript";

/** @type {import('eslint').Rule.RuleModule} */
const noDirectFetchToApi = {
  meta: {
    type: "suggestion",
    docs: {
      description: "Disallow direct fetch() calls to /api/* endpoints",
      recommended: true,
    },
    messages: {
      useAuthenticatedFetch: "Use authenticatedFetch from @/lib/apiClient for API endpoints. This ensures Authorization headers and tenant isolation are properly handled.",
    },
    schema: [],
  },
  create(context) {
    return {
      CallExpression(node) {
        if (
          node.callee.type === "Identifier" &&
          node.callee.name === "fetch" &&
          node.arguments.length > 0
        ) {
          const arg = node.arguments[0];
          let url = null;

          // Handle string literals: fetch("/api/...")
          if (arg.type === "Literal" && typeof arg.value === "string") {
            url = arg.value;
          }
          // Handle template literals: fetch(`/api/...`)
          else if (
            arg.type === "TemplateLiteral" &&
            arg.quasis.length > 0 &&
            arg.quasis[0].value.raw
          ) {
            url = arg.quasis[0].value.raw;
          }

          // Check if URL starts with /api/
          if (url && url.startsWith("/api/")) {
            context.report({
              node,
              messageId: "useAuthenticatedFetch",
            });
          }
        }
      },
    };
  },
};

const eslintConfig = defineConfig([
  ...nextVitals,
  ...nextTs,
  {
    rules: {
      "@typescript-eslint/no-explicit-any": "warn",
      "react-hooks/set-state-in-effect": "off",
      "react-hooks/preserve-manual-memoization": "warn",
      "react/no-unescaped-entities": "off",
      "react-hooks/exhaustive-deps": "warn",
      // Disable rule that causes false positives on TypeScript union type definitions
      "@typescript-eslint/no-unused-expressions": "off",
    },
  },
  {
    // Custom rule: Warn about direct fetch() calls to /api/ endpoints
    files: ["src/**/*.{ts,tsx}"],
    plugins: {
      "tobit-custom": {
        rules: {
          "no-direct-fetch-to-api": noDirectFetchToApi,
        },
      },
    },
    rules: {
      "tobit-custom/no-direct-fetch-to-api": "warn",
    },
  },
  // Override default ignores of eslint-config-next.
  globalIgnores([
    // Default ignores of eslint-config-next:
    ".next/**",
    "out/**",
    "build/**",
    "next-env.d.ts",
    // Ignore PDF worker file (external library)
    "public/pdf.worker.min.mjs",
    // Ignore E2E test files (they use Playwright, not React)
    "tests-e2e/**",
  ]),
]);

export default eslintConfig;
