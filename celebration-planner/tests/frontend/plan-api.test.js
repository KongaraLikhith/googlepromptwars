import test from 'node:test';
import assert from 'node:assert/strict';
import { requestPlan, requestSample } from '../../app/static/plan-api.js';
import { sample } from './fixtures.js';

const json = (value, options) => new Response(JSON.stringify(value), {
  headers: { 'Content-Type': 'application/json' }, ...options,
});

test('sample loading uses a read-only endpoint and normalizes Decimal budget strings', async t => {
  const { brief, plan } = sample();
  const calls = [];
  t.mock.method(globalThis, 'fetch', async (url, options) => {
    calls.push({ url, options });
    return json({ brief: { ...brief, budget: String(brief.budget) }, plan });
  });
  assert.deepEqual(await requestSample(), { brief, plan });
  assert.equal(calls.length, 1);
  assert.equal(calls[0].url, '/api/sample');
  assert.equal(calls[0].options.method, undefined);
  assert.equal(calls[0].options.body, undefined);
});

test('explicit generation sends the brief once and validates the returned plan', async t => {
  const { brief, plan } = sample();
  t.mock.method(globalThis, 'fetch', async (url, options) => {
    assert.equal(url, '/api/plan');
    assert.equal(options.method, 'POST');
    assert.deepEqual(JSON.parse(options.body), brief);
    assert.equal(options.headers['Content-Type'], 'application/json');
    return json(plan);
  });
  assert.deepEqual(await requestPlan(brief), plan);
});

test('malformed responses and inconsistent sample briefs are rejected before rendering', async t => {
  const { brief, plan } = sample();
  const responses = [
    new Response('{'),
    json({ ...plan, ideas: [] }),
    json({ brief: { ...brief, currency: 'USD' }, plan }),
    json({ brief, plan: { ...plan, source: 'gemini' } }),
  ];
  t.mock.method(globalThis, 'fetch', async () => responses.shift());
  await assert.rejects(requestPlan(brief), /incomplete response/);
  await assert.rejects(requestPlan(brief), /incomplete/);
  await assert.rejects(requestSample(), /sample plan could not be loaded/);
  await assert.rejects(requestSample(), /sample plan could not be loaded/);
});

test('rate-limit and validation errors explain recovery without automatic retries', async t => {
  const responses = [
    json({}, { status: 429, headers: { 'Retry-After': '121' } }),
    json({}, { status: 422 }),
    json({}, { status: 503 }),
  ];
  const fetch = t.mock.method(globalThis, 'fetch', async () => responses.shift());
  await assert.rejects(requestPlan(sample().brief), /3 minutes/);
  await assert.rejects(requestPlan(sample().brief), /check your date/);
  await assert.rejects(requestPlan(sample().brief), /try again in a moment/);
  assert.equal(fetch.mock.calls.length, 3);
});

test('sample and generation requests abort at their separate total deadlines', async t => {
  t.mock.timers.enable({ apis: ['setTimeout'] });
  t.mock.method(globalThis, 'fetch', (_url, options) => new Promise((_resolve, reject) => {
    options.signal.addEventListener('abort', () => reject(new DOMException('Aborted', 'AbortError')));
  }));
  const loadingSample = requestSample();
  t.mock.timers.tick(10000);
  await assert.rejects(loadingSample, /taking longer than expected/);
  const creatingPlan = requestPlan(sample().brief);
  t.mock.timers.tick(60000);
  await assert.rejects(creatingPlan, /previous plan is safe/);
});
