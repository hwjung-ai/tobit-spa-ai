import { defineConfig, devices } from '@playwright/test';

/**
 * See https://playwright.dev/docs/test-configuration.
 */
export default defineConfig({
  testDir: './tests-e2e',
  /* Keep E2E stable against backend DB connection limits */
  fullyParallel: false,
  /* Fail the build on CI if you accidentally left test.only in the source code. */
  forbidOnly: !!process.env.CI,
  /* Retry on CI only */
  retries: process.env.CI ? 2 : 0,
  /* Opt out of parallel tests on CI. */
  workers: 1,
  /* Output directory and Reporter to use. See https://playwright.dev/docs/test-reporters */
  outputDir: '../../test-results/playwright',
  reporter: 'html',
  /* Shared settings for all of the projects below. See https://playwright.dev/docs/api/class-testoptions. */
  use: {
    /* Base URL to use in actions like `await page.goto('/')`. */
    baseURL: 'http://localhost:3000',

    /* Collect trace when retrying the failed test. See https://playwright.dev/docs/trace-viewer */
    trace: 'on-first-retry',
  },

  /* Configure projects for major browsers */
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],

  // Global test timeout
  timeout: 300000, // 5 minutes

  // Start both API and Web for reliable E2E (asset-registry/screens depend on API).
  webServer: [
    {
      command: 'cd ../api && .venv/bin/python -m uvicorn main:app --port 8000',
      url: 'http://localhost:8000/health',
      reuseExistingServer: true,
      timeout: 120000,
      stdout: 'ignore',
      stderr: 'ignore',
    },
    {
      command: 'NEXT_PUBLIC_E2E_DISABLE_REALTIME=true npm run dev -- --webpack',
      url: 'http://localhost:3000',
      reuseExistingServer: true,
      timeout: 300000,
      stdout: 'ignore',
      stderr: 'ignore',
    },
  ],
});
