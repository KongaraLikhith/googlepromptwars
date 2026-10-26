import test from 'node:test';
import assert from 'node:assert/strict';
import { createPlanStore } from '../../app/static/plan-storage.js';
import { sample } from './fixtures.js';

function memory() {
  const values = new Map();
  return { getItem: key => values.get(key) ?? null, setItem: (key, value) => values.set(key, value), removeItem: key => values.delete(key) };
}

test('storage round trip preserves allocation edits and only known checklist IDs', () => {
  const store = createPlanStore(() => memoryStorage);
  const memoryStorage = memory();
  const state = sample();
  state.plan.budget_items[0].amount = 1100.25;
  state.completed = new Set(['catering', 'unknown']);
  assert.equal(store.save(state), true);
  const saved = store.load();
  assert.equal(saved.plan.budget_items[0].amount, 1100.25);
  assert.deepEqual(saved.completed, ['catering']);
  assert.deepEqual(saved.brief, state.brief);
  assert.equal(store.clear(), true);
  assert.equal(store.load(), null);
});

test('denied storage and quota errors leave the planner usable without claiming persistence', () => {
  const denied = createPlanStore(() => { throw new Error('SecurityError'); });
  assert.equal(denied.load(), null);
  assert.equal(denied.save(sample()), false);
  assert.equal(denied.clear(), false);
  const full = createPlanStore(() => ({ setItem() { throw new Error('QuotaExceededError'); } }));
  assert.equal(full.save(sample()), false);
});

test('malformed, oversized, unsupported-version and inconsistent saved records are ignored', () => {
  const storage = memory();
  const store = createPlanStore(() => storage);
  for (const serialized of ['{', 'null', 'x'.repeat(100001), JSON.stringify({ version: 2 }),
    JSON.stringify({ version: 1, ...sample(), brief: { ...sample().brief, currency: 'USD' } }),
    JSON.stringify({ version: 1, ...sample(), plan: { ...sample().plan, timeline: [{ date: 'invalid' }] } })]) {
    storage.setItem('gatherly.plan.v1', serialized);
    assert.equal(store.load(), null);
  }
});

test('saved record size is bounded before writing', () => {
  const storage = memory();
  const store = createPlanStore(() => storage);
  const state = sample();
  state.plan.summary = 'x'.repeat(100001);
  assert.equal(store.save(state), false);
  assert.equal(store.load(), null);
});
