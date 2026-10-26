import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { chromium } from 'playwright';
import AxeBuilder from '@axe-core/playwright';

// Start the app without GEMINI_API_KEY before running this local integration suite.
// Samples and reset must never trigger a paid planning request. The four real
// user-requested plans stay below the per-worker limit; the 429 case is mocked.
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
  const requests = { sample: 0, plan: 0 };
  page.on('pageerror', error => errors.push(error.message));
  page.on('request', request => {
    const path = new URL(request.url()).pathname;
    if (path === '/api/sample') requests.sample += 1;
    if (path === '/api/plan' && request.method() === 'POST') requests.plan += 1;
  });
  await page.addInitScript(() => {
    const observer = new MutationObserver(() => {
      if (document.querySelector('#plan-workspace[aria-busy="false"]')) {
        window.__workspaceReadyAt = performance.now();
        observer.disconnect();
      }
    });
    observer.observe(document, {
      childList: true, subtree: true, attributes: true, attributeFilter: ['aria-busy'],
    });
  });

  const planResponse = () => page.waitForResponse(response =>
    new URL(response.url()).pathname === '/api/plan'
      && response.request().method() === 'POST');
  const sampleResponse = () => page.waitForResponse(response =>
    new URL(response.url()).pathname === '/api/sample'
      && response.request().method() === 'GET');
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

  const initial = sampleResponse();
  await page.goto('/', { waitUntil: 'domcontentloaded' });
  const initialResponse = await initial;
  assert.equal(initialResponse.status(), 200);
  const initialSample = await initialResponse.json();
  await ready();
  assert.match(await page.locator('#source-badge').innerText(), /Local planning mode/);
  assert.match(await page.locator('#plan-title').innerText(), /Birthday/i);
  assert.equal(await page.locator('.budget-item').count(), 7);
  assert.equal(requests.plan, 0, 'Opening the app must not trigger Gemini generation');
  assert.equal(requests.sample, 1);
  assert.equal(await page.evaluate(() => localStorage.getItem('gatherly.plan.v1')), null,
    'An unrequested sample stays in memory until the user saves an edit or creates a plan');
  const startup = await page.evaluate(() => ({
    workspace_ready_ms: Math.round(window.__workspaceReadyAt),
    resource_body_bytes: performance.getEntriesByType('resource')
      .reduce((sum, entry) => sum + entry.encodedBodySize, 0),
  }));
  console.log('Fresh-load observations:', JSON.stringify({ ...startup, ...requests }));
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
  assert.equal(requests.plan, 0, 'Tabs, edits, checklist, reload, and export must not generate AI');
  assert.equal(requests.sample, 1, 'Reload restores an edited saved plan without fetching a sample');
  console.log('Keyboard navigation, checklist persistence, allocation edits, and export passed.');

  for (const event of ['birthday', 'wedding', 'community']) {
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
    assert.equal(await page.locator('.vendor-item input').first().isChecked(), event === 'birthday',
      'Refining the same event keeps checklist progress; changing event type resets it');
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

  const plansBeforeClear = requests.plan;
  const cleared = sampleResponse();
  await page.getByRole('button', { name: 'Clear saved plan' }).click();
  assert.equal((await cleared).status(), 200);
  await ready();
  assert.equal(await page.evaluate(() => localStorage.getItem('gatherly.plan.v1')), null);
  assert.equal(requests.plan, plansBeforeClear, 'Reset must not trigger AI generation');
  assert.equal(requests.sample, 2);
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
  assert.equal(requests.plan, 5, 'Only four explicit plans and the mocked 429 should POST');
  console.log('Rate-limit recovery, reset, print, responsive layout, and four accessibility scans passed.');

  // Delay the real sample response to exercise typing during startup. Its
  // response body is unchanged; user input must not be replaced by defaults.
  const typingContext = await browser.newContext({ baseURL });
  const typingPage = await typingContext.newPage();
  let releaseSample;
  let sampleStarted;
  let typingPlans = 0;
  const sampleGate = new Promise(resolve => { releaseSample = resolve; });
  const sampleRequested = new Promise(resolve => { sampleStarted = resolve; });
  typingPage.on('request', request => {
    if (new URL(request.url()).pathname === '/api/plan') typingPlans += 1;
  });
  await typingPage.route('**/api/sample', async route => {
    sampleStarted();
    const response = await route.fetch();
    await sampleGate;
    await route.fulfill({ response });
  });
  await typingPage.goto('/', { waitUntil: 'domcontentloaded' });
  await sampleRequested;
  await typingPage.locator('#location').fill('My own garden');
  releaseSample();
  await typingPage.waitForSelector('#plan-workspace[aria-busy="false"]');
  assert.equal(await typingPage.locator('#location').inputValue(), 'My own garden');
  assert.equal(typingPlans, 0, 'Typing while a sample loads must not generate AI');
  await typingContext.close();
  console.log('Typing during a pending sample preserves the user’s details without AI work.');

  // Explicit fixtures below test failure-state labels only. They do not claim
  // to verify live Gemini: budgets and dates come from the real sample above.
  const mockIdeaTitle = 'Mock Gemini idea for reset regression';
  const mockGeminiPlan = {
    ...initialSample.plan,
    source: 'gemini',
    source_note: 'Mock Gemini result for failure-state regression.',
    ideas: [{ ...initialSample.plan.ideas[0], title: mockIdeaTitle }, ...initialSample.plan.ideas.slice(1)],
  };
  const mockPlan = route => route.fulfill({
    status: 200, contentType: 'application/json', body: JSON.stringify(mockGeminiPlan),
  });
  const unavailableSample = route => route.fulfill({
    status: 503, contentType: 'application/json', body: JSON.stringify({ detail: 'Unavailable sample fixture.' }),
  });
  const failureContext = await browser.newContext({ baseURL });
  const failurePage = await failureContext.newPage();
  await failurePage.route('**/api/plan', mockPlan);
  await failurePage.goto('/', { waitUntil: 'networkidle' });
  await failurePage.waitForSelector('#plan-workspace[aria-busy="false"]');
  await failurePage.getByRole('button', { name: 'Create my celebration plan' }).click();
  await failurePage.waitForSelector('#plan-workspace[aria-busy="false"]');
  assert.match(await failurePage.locator('#source-badge').innerText(), /Gemini/);
  assert.match(await failurePage.locator('#source-note').innerText(), /Mock Gemini/);
  assert.match(await failurePage.locator('#idea-grid').innerText(), new RegExp(mockIdeaTitle));
  const edited = failurePage.locator('.allocation-edit input').first();
  await edited.fill(String(Number(await edited.inputValue()) + 100));
  await edited.blur();
  assert.match(await failurePage.locator('#balance-message').innerText(), /over your budget/);
  await failurePage.getByRole('tab', { name: /Checklist/ }).click();
  await failurePage.locator('.vendor-item input').first().check();
  assert.match(await failurePage.locator('#checklist-progress').innerText(), /1 OF 7/);
  await failurePage.route('**/api/sample', unavailableSample);
  await failurePage.getByRole('button', { name: 'Clear saved plan' }).click();
  await failurePage.waitForSelector('#plan-workspace[aria-busy="false"]');
  assert.equal(await failurePage.evaluate(() => localStorage.getItem('gatherly.plan.v1')), null);
  assert.equal(await failurePage.locator('#source-badge').innerText(), 'Waiting for your plan');
  assert.doesNotMatch(await failurePage.locator('#source-note').innerText(), /Gemini|Mock/);
  assert.equal(await failurePage.locator('#ideas-label').innerText(), 'Ideas appear with your plan');
  assert.equal(await failurePage.locator('#idea-grid').innerText(), '');
  for (const selector of ['.budget-item', '.timeline-item', '.vendor-item', '#tips-list li']) {
    assert.equal(await failurePage.locator(selector).count(), 0, `${selector} must not show the cleared plan`);
  }
  assert.equal(await failurePage.locator('#tips-box').isVisible(), false);
  assert.equal(await failurePage.locator('#budget-metric').innerText(), '—');
  assert.equal(await failurePage.locator('#balance-message').innerText(), 'Create a plan to see your allocations.');
  assert.equal(await failurePage.locator('#balance-message').evaluate(node => node.classList.contains('over')), false);
  assert.equal(await failurePage.locator('#checklist-count').innerText(), '0');
  assert.equal(await failurePage.locator('#checklist-progress').innerText(), '0 COMPLETE');
  assert.equal(await failurePage.locator('#checklist-bar').getAttribute('aria-valuetext'), 'No checklist items available.');
  assert.match(await failurePage.locator('#save-status').innerText(), /No active plan/);
  assert.equal(await failurePage.locator('#export-button').isDisabled(), true);
  assert.equal(await failurePage.locator('#print-button').isDisabled(), true);
  await failureContext.close();

  const recoveryContext = await browser.newContext({ baseURL });
  const recoveryPage = await recoveryContext.newPage();
  await recoveryPage.route('**/api/sample', unavailableSample);
  await recoveryPage.route('**/api/plan', mockPlan);
  await recoveryPage.goto('/', { waitUntil: 'networkidle' });
  await recoveryPage.waitForSelector('#plan-workspace[aria-busy="false"]');
  assert.equal(await recoveryPage.locator('#export-button').isDisabled(), true);
  assert.match(await recoveryPage.locator('#save-status').innerText(), /No active plan/);
  await recoveryPage.getByRole('button', { name: 'Create my celebration plan' }).click();
  await recoveryPage.waitForSelector('#plan-workspace[aria-busy="false"]');
  assert.match(await recoveryPage.locator('#source-badge').innerText(), /Gemini/);
  assert.equal(await recoveryPage.locator('#export-button').isEnabled(), true);
  assert.match(await recoveryPage.locator('#idea-grid').innerText(), new RegExp(mockIdeaTitle));
  await recoveryContext.close();
  console.log('Failed reset removes stale plan claims; failed startup still permits explicit generation.');
} finally {
  await browser.close();
}
