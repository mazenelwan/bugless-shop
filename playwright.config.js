const { defineConfig } = require("@playwright/test");

module.exports = defineConfig({
  testDir: "./tests/e2e",
  fullyParallel: false,
  workers: 1,
  timeout: 45_000,
  expect: { timeout: 8_000 },
  reporter: [["list"]],
  outputDir: ".phase6/playwright-results",
  use: {
    baseURL: "http://127.0.0.1:8010",
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
    video: "off"
  },
  webServer: {
    command: "python scripts/run_e2e_server.py",
    url: "http://127.0.0.1:8010/health/",
    reuseExistingServer: false,
    timeout: 120_000,
    stdout: "pipe",
    stderr: "pipe"
  },
  projects: [
    {
      name: "desktop-chromium",
      use: { browserName: "chromium", viewport: { width: 1440, height: 1200 } }
    },
    {
      name: "mobile-chromium",
      use: { browserName: "chromium", viewport: { width: 390, height: 844 } }
    }
  ]
});
