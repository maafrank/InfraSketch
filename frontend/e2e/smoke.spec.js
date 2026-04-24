import { test, expect } from '@playwright/test';

test('landing page renders without runtime errors', async ({ page }) => {
  const pageErrors = [];
  const failedRequests = [];

  page.on('pageerror', (err) => pageErrors.push(String(err)));
  page.on('requestfailed', (request) => {
    failedRequests.push(`${request.method()} ${request.url()} :: ${request.failure()?.errorText ?? 'unknown'}`);
  });

  // Use domcontentloaded instead of the default 'load' so a single hanging
  // image/stylesheet does not mask the real render state of the app.
  await page.goto('/', { waitUntil: 'domcontentloaded' });

  // App shell rendered, proves React mounted and JS ran on this browser engine.
  await expect(page.getByAltText(/InfraSketch Logo/i).first()).toBeVisible({ timeout: 15_000 });

  // ErrorBoundary fallback did NOT fire.
  await expect(page.getByText(/InfraSketch hit a runtime error/i)).not.toBeVisible();

  // No uncaught JS errors during load.
  expect(
    pageErrors,
    `Uncaught page errors:\n${pageErrors.join('\n')}\n\nFailed requests:\n${failedRequests.join('\n')}`,
  ).toEqual([]);
});
