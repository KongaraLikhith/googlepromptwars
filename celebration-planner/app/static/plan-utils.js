/** Shared formatting and validation, independent of the page and browser storage. */
export const EVENT_NAMES = Object.freeze({ wedding: 'Wedding', birthday: 'Birthday', community: 'Community' });
export const CURRENCY_SYMBOLS = Object.freeze({ INR: '₹', USD: '$', EUR: '€', GBP: '£' });

// Rendering a plan formats the same currencies and three date shapes repeatedly.
// Bound both caches so even unexpected callers cannot retain unlimited formats.
const moneyFormats = new Map();
const dateFormats = new Map();
function cachedFormat(cache, key, create) {
  if (!cache.has(key)) {
    if (cache.size >= 8) cache.delete(cache.keys().next().value);
    cache.set(key, create());
  }
  return cache.get(key);
}

export function dateKey(value) {
  const year = value.getFullYear();
  const month = String(value.getMonth() + 1).padStart(2, '0');
  const day = String(value.getDate()).padStart(2, '0');
  return `${year}-${month}-${day}`;
}

export function isDateKey(value) {
  if (typeof value !== 'string' || !/^\d{4}-\d{2}-\d{2}$/.test(value)) return false;
  const parsed = new Date(`${value}T12:00:00Z`);
  return Number.isFinite(parsed.getTime()) && parsed.toISOString().slice(0, 10) === value;
}

export function dateLabel(value, options = { day: 'numeric', month: 'short', year: 'numeric' }) {
  const formatter = cachedFormat(dateFormats, JSON.stringify(options), () => new Intl.DateTimeFormat(undefined, options));
  return formatter.format(new Date(`${value}T12:00:00`));
}

export function daysUntil(value, today = new Date()) {
  return Math.round((Date.parse(`${value}T12:00:00Z`) - Date.parse(`${dateKey(today)}T12:00:00Z`)) / 86400000);
}

export function formatMoney(value, currency) {
  const minimumFractionDigits = Number.isInteger(Number(value)) ? 0 : 2;
  const formatter = cachedFormat(moneyFormats, `${currency}:${minimumFractionDigits}`, () =>
    new Intl.NumberFormat(currency === 'INR' ? 'en-IN' : undefined, {
      style: 'currency', currency, minimumFractionDigits, maximumFractionDigits: 2,
    }));
  return formatter.format(Number(value));
}

export function budgetTotals(items, budget) {
  const allocatedCents = items.reduce((sum, item) => sum + Math.round(item.amount * 100), 0);
  return { allocated: allocatedCents / 100, difference: (Math.round(budget * 100) - allocatedCents) / 100 };
}

const text = (value, maximum, minimum = 0) => typeof value === 'string' && value.length >= minimum && value.length <= maximum;
const amount = value => typeof value === 'number' && Number.isFinite(value) && value >= 0 && value <= 100000000;
const records = (value, maximum, validate, minimum = 0) => Array.isArray(value)
  && value.length >= minimum && value.length <= maximum && value.every(item => item && typeof item === 'object' && validate(item));

/** Validate every value the renderer consumes, including browser-local data. */
export function validPlan(plan) {
  if (!plan || typeof plan !== 'object') return false;
  return Object.hasOwn(EVENT_NAMES, plan.event_type)
    && Object.hasOwn(CURRENCY_SYMBOLS, plan.currency)
    && isDateKey(plan.event_date)
    && amount(plan.budget) && plan.budget >= 100
    && Number.isInteger(plan.guest_count) && plan.guest_count >= 1 && plan.guest_count <= 10000
    && text(plan.summary, 3000, 1)
    && ['local', 'gemini'].includes(plan.source)
    && text(plan.source_note, 2000)
    && records(plan.budget_items, 20, item => text(item.category, 200, 1)
      && amount(item.amount) && text(item.note, 2000), 1)
    && records(plan.timeline, 20, item => text(item.id, 100, 1) && isDateKey(item.date)
      && text(item.title, 200, 1) && text(item.phase, 100) && text(item.note, 2000), 1)
    && records(plan.vendors, 30, item => text(item.id, 100, 1) && text(item.title, 200, 1)
      && text(item.category, 200) && text(item.note, 2000) && typeof item.essential === 'boolean', 1)
    && new Set(plan.vendors.map(item => item.id)).size === plan.vendors.length
    && records(plan.ideas, 10, item => text(item.title, 200, 1) && text(item.description, 2000, 1), 1)
    && Array.isArray(plan.tips) && plan.tips.length <= 10 && plan.tips.every(tip => text(tip, 2000));
}

export function validBrief(brief, plan) {
  return brief && typeof brief === 'object'
    && brief.event_type === plan.event_type && brief.event_date === plan.event_date
    && brief.budget === plan.budget && brief.currency === plan.currency && brief.guest_count === plan.guest_count
    && text(brief.location, 100) && text(brief.style, 80) && text(brief.preferences, 500)
    && Array.isArray(brief.priorities) && brief.priorities.length <= 3
    && new Set(brief.priorities).size === brief.priorities.length
    && brief.priorities.every(value => ['food', 'decor', 'entertainment', 'photography', 'venue', 'accessibility'].includes(value));
}

export function retryMessage(retryAfter) {
  const seconds = Number(retryAfter);
  if (!retryAfter || !Number.isFinite(seconds) || seconds <= 0) return 'There are a few plans in progress. Please try again in a moment.';
  const minutes = Math.max(1, Math.ceil(seconds / 60));
  return `You’ve reached the planning limit. Please try again in about ${minutes} ${minutes === 1 ? 'minute' : 'minutes'}. Your current plan is safe.`;
}
