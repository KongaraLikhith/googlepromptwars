import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { chromium } from 'playwright';
import AxeBuilder from '@axe-core/playwright';

// Start the app without GEMINI_API_KEY before running this local integration suite.
// The five real planning requests stay below the per-worker rate limit.
const baseURL = process.env.BASE_URL || 'http://127.0.0.1:8087';
const browser = await chromium.launch({
  headless: true,
  ...(process.env.CHROMIUM_PATH ? { executablePath: process.env.CHROMIUM_PATH } : {}),
});

try {
  const context = await browser.newContext({
    baseURL,
    viewport: { width: 1440, height: 1100 },
    acceptDownloads: true,
  });
  const page = await context.newPage();
  const errors = [];
  page.on('pageerror', error => errors.push(error.message));

  const planResponse = () => page.waitForResponse(response =>
    new URL(response.url()).pathname === '/api/plan'
      && response.request().method() === 'POST');
  const ready = () => page.waitForSelector('#plan-workspace[aria-busy="false"]');
  const createPlan = async () => {
    const response = planResponse();
    await page.getByRole('button', { name: 'Create my celebration plan' }).click();
    assert.equal((await response).status(), 200, 'Planning request succeeds');
    await ready();
  };
  const checkAccessibility = async state => {
    const result = await new AxeBuilder({ page })
      .withTags(['wcag2a', 'wcag2aa', 'wcag21aa']).analyze();
    assert.deepEqual(result.violations.map(violation => ({
      id: violation.id,
      impact: violation.impact,
      targets: violation.nodes.map(node => node.target),
    })), [], `${state} accessibility violations`);
  };

  const initial = planResponse();
  await page.goto('/', { waitUntil: 'networkidle' });
  assert.equal((await initial).status(), 200);
  await ready();
  assert.match(await page.locator('#source-badge').innerText(), /Local planning mode/);
  assert.match(await page.locator('#plan-title').innerText(), /Birthday/i);
  assert.equal(await page.locator('.budget-item').count(), 7);
  await checkAccessibility('Budget');

  await page.locator('#tab-budget').focus();
  await page.keyboard.press('ArrowRight');
  assert.equal(await page.locator('#tab-timeline').getAttribute('aria-selected'), 'true');
  assert.equal(await page.locator('#tab-timeline').evaluate(node => node === document.activeElement), true);
  assert.equal(await page.locator('.timeline-item').count(), 8);
  await checkAccessibility('Timeline');
  await page.keyboard.press('End');
  assert.equal(await page.locator('#tab-checklist').getAttribute('aria-selected'), 'true');
  await page.locator('.vendor-item input').first().check();
  assert.match(await page.locator('#checklist-progress').innerText(), /1 OF 7/);
  await checkAccessibility('Completed checklist');
  await page.reload({ waitUntil: 'networkidle' });
  await ready();
  await page.getByRole('tab', { name: /Checklist/ }).click();
  assert.equal(await page.locator('.vendor-item input').first().isChecked(), true);

  await page.getByRole('tab', { name: /Budget/ }).click();
  const allocation = page.locator('.allocation-edit input').first();
  const original = Number(await allocation.inputValue());
  await allocation.fill(String(original + 100));
  await allocation.blur();
  assert.match(await page.locator('#balance-message').innerText(), /100.*over your budget/);
  const downloadPromise = page.waitForEvent('download');
  await page.getByRole('button', { name: 'Download your plan as JSON' }).click();
  const download = await downloadPromise;
  const exported = JSON.parse(await readFile(await download.path(), 'utf8'));
  assert.equal(exported.budget_items[0].amount, original + 100);
  assert.equal(exported.vendors[0].completed, true);
  console.log('Keyboard navigation, checklist persistence, allocation edits, and export passed.');

  for (const event of ['wedding', 'community']) {
    await page.locator(`input[name="event_type"][value="${event}"]`).check();
    await page.locator('#budget').fill('125000.99');
    await page.locator('#guests').fill('125');
    await page.locator('#location').fill('Hyderabad <script>window.bad=1</script>');
    await createPlan();
    assert.match(await page.locator('#plan-title').innerText(), new RegExp(event, 'i'));
    assert.equal(await page.evaluate(() => window.bad), undefined);
    const cents = await page.locator('.allocation-edit input').evaluateAll(nodes =>
      nodes.reduce((sum, node) => sum + Math.round(Number(node.value) * 100), 0));
    assert.equal(cents, 12500099);
    await page.getByRole('tab', { name: /Checklist/ }).click();
    assert.equal(await page.locator('.vendor-item input').first().isChecked(), false);
    await page.getByRole('tab', { name: /Budget/ }).click();
  }
  await page.locator('#currency').selectOption('USD');
  await createPlan();
  assert.match(await page.locator('#budget-metric').innerText(), /\$125,000.99/);
  console.log('All event types, exact-cent totals, safe text, and currency passed.');

  // These explicit mocks exercise failure UI; the successful workflows above
  // use the real FastAPI planner and are never replaced with fixtures.
  const previousTitle = await page.locator('#plan-title').innerText();
  await page.route('**/api/plan', route => route.fulfill({
    status: 429,
    contentType: 'application/json',
    headers: { 'Retry-After': '120' },
    body: JSON.stringify({ detail: 'Too many requests.' }),
  }));
  await page.getByRole('button', { name: 'Create my celebration plan' }).click();
  await ready();
  assert.match(await page.locator('#form-message').innerText(), /try again|wait/i);
  assert.equal(await page.locator('#plan-title').innerText(), previousTitle);
  assert.equal(await page.locator('#generate-button').isEnabled(), true);
  await page.unroute('**/api/plan');

  const cleared = planResponse();
  await page.getByRole('button', { name: 'Clear saved plan' }).click();
  assert.equal((await cleared).status(), 200);
  await ready();
  assert.equal(await page.evaluate(() => localStorage.getItem('gatherly.plan.v1')), null);
  await page.emulateMedia({ media: 'print' });
  assert.equal(await page.locator('#panel-timeline').isVisible(), true);
  assert.equal(await page.locator('#panel-checklist').isVisible(), true);
  await page.emulateMedia({ media: 'screen' });
  for (const width of [1440, 1024, 768, 640, 390, 320]) {
    await page.setViewportSize({ width, height: 844 });
    const size = await page.evaluate(() => ({
      scroll: document.documentElement.scrollWidth,
      viewport: window.innerWidth,
    }));
    assert.ok(size.scroll <= size.viewport + 1, `Horizontal overflow at ${width}px: ${JSON.stringify(size)}`);
  }
  await page.setViewportSize({ width: 390, height: 844 });
  await checkAccessibility('Mobile');
  assert.deepEqual(errors, [], 'Uncaught browser errors');
  console.log('Rate-limit recovery, reset, print, responsive layout, and four accessibility scans passed.');
} finally {
  await browser.close();
}
