import { defineConfig, devices } from '@playwright/test';
export default defineConfig({
  testDir: './tests/e2e',
  fullyParallel: false,
  use: {baseURL:'http://127.0.0.1:3041'},
  projects:[{name:'desktop',use:{...devices['Desktop Chrome']}},{name:'mobile',use:{...devices['iPhone 13'],defaultBrowserType:'chromium'}}],
  webServer:{command:'pnpm exec next start --hostname 127.0.0.1 --port 3041',url:'http://127.0.0.1:3041',reuseExistingServer:!process.env.CI,env:{API_INTERNAL_URL:'http://127.0.0.1:4041/api/v1'}},
});
