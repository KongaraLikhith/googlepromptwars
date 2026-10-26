import test from 'node:test';
import assert from 'node:assert/strict';
import { budgetTotals, dateKey, daysUntil, isDateKey, retryMessage, validBrief, validPlan } from '../../app/static/plan-utils.js';

import { sample } from './fixtures.js';

test('budget arithmetic preserves cents and distinguishes over-allocation', () => {
  assert.deepEqual(budgetTotals([{ amount: 0.1 }, { amount: 0.2 }], 0.3), { allocated: 0.3, difference: 0 });
  assert.deepEqual(budgetTotals([{ amount: 1000.01 }], 1000), { allocated: 1000.01, difference: -0.01 });
  assert.deepEqual(budgetTotals([{ amount: 900 }], 1000), { allocated: 900, difference: 100 });
});

test('calendar dates reject impossible dates and countdown ignores daylight-saving length', () => {
  assert.equal(isDateKey('2028-02-29'), true);
  for (const date of ['2027-02-29', '2027-04-31', '2027-13-01', 'nonsense', null]) assert.equal(isDateKey(date), false);
  const today = new Date(2027, 2, 13, 23, 50);
  assert.equal(dateKey(today), '2027-03-13');
  assert.equal(daysUntil('2027-03-15', today), 2);
  assert.equal(daysUntil('2027-03-12', today), -1);
});

test('plan validation covers nested values before rendering browser-local content', () => {
  assert.equal(validPlan(sample().plan), true);
  const mutations = [
    plan => { plan.budget = Infinity; },
    plan => { plan.currency = '__proto__'; },
    plan => { plan.event_date = '2027-02-30'; },
    plan => { plan.budget_items[0].amount = -1; },
    plan => { plan.timeline[0].date = '2027-02-30'; },
    plan => { plan.timeline = []; },
    plan => { plan.vendors = []; },
    plan => { plan.ideas = []; },
    plan => { plan.timeline[0].title = {}; },
    plan => { plan.vendors.push({ ...plan.vendors[0] }); },
    plan => { plan.vendors[0].essential = 'yes'; },
    plan => { plan.ideas[0].description = null; },
    plan => { plan.tips = [{ text: 'wrong shape' }]; },
    plan => { plan.source = 'unknown'; },
    plan => { plan.summary = 'x'.repeat(3001); },
  ];
  for (const mutate of mutations) {
    const { plan } = sample();
    mutate(plan);
    assert.equal(validPlan(plan), false, mutate.toString());
  }
});

test('editable allocations may exceed the budget while remaining safe numeric values', () => {
  const { plan } = sample();
  plan.budget_items[0].amount = 2000;
  assert.equal(validPlan(plan), true);
});

test('saved brief must describe the same event with supported unique priorities', () => {
  const { plan, brief } = sample();
  assert.equal(validBrief(brief, plan), true);
  assert.equal(validBrief({ ...brief, event_date: '2027-01-02' }, plan), false);
  assert.equal(validBrief({ ...brief, priorities: ['food', 'food'] }, plan), false);
  assert.equal(validBrief({ ...brief, priorities: ['unsupported'] }, plan), false);
});

test('rate-limit feedback rounds Retry-After up and handles absent or invalid values', () => {
  assert.match(retryMessage('61'), /2 minutes/);
  assert.match(retryMessage('1'), /1 minute/);
  for (const value of [null, '', 'invalid', '-5', 'Infinity']) assert.match(retryMessage(value), /in a moment/);
});

test('repeated rendering reuses locale formatters without changing displayed values', async t => {
  const utils = await import('../../app/static/plan-utils.js?formatter-reuse-test');
  const NumberFormat = Intl.NumberFormat;
  const DateTimeFormat = Intl.DateTimeFormat;
  const money = t.mock.method(Intl, 'NumberFormat', function (...args) { return new NumberFormat(...args); });
  const dates = t.mock.method(Intl, 'DateTimeFormat', function (...args) { return new DateTimeFormat(...args); });
  for (let index = 0; index < 100; index += 1) {
    assert.equal(utils.formatMoney(1234, 'INR'), new NumberFormat('en-IN', {
      style: 'currency', currency: 'INR', minimumFractionDigits: 0, maximumFractionDigits: 2,
    }).format(1234));
    assert.equal(utils.formatMoney(1234.25, 'INR'), new NumberFormat('en-IN', {
      style: 'currency', currency: 'INR', minimumFractionDigits: 2, maximumFractionDigits: 2,
    }).format(1234.25));
    assert.equal(utils.dateLabel('2027-01-01', { year: 'numeric' }), '2027');
  }
  assert.equal(money.mock.calls.length, 2);
  assert.equal(dates.mock.calls.length, 1);
});
