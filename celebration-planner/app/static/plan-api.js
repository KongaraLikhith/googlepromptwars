import { validBrief, validPlan, retryMessage } from './plan-utils.js';

/** Each request has one deadline; a failed request never replaces the visible plan. */
async function requestJSON(path, options, timeoutMilliseconds) {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), timeoutMilliseconds);
  try {
    const response = await fetch(path, { ...options, signal: controller.signal });
    if (response.status === 422) throw new Error('Please check your date, budget, guest count, and other details, then try again.');
    if (response.status === 429) throw new Error(retryMessage(response.headers.get('Retry-After')));
    if (!response.ok) throw new Error('Your plan couldn’t be created just yet. Please try again in a moment.');
    return await response.json();
  } catch (error) {
    if (error.name === 'AbortError') throw new Error('This is taking longer than expected. Your previous plan is safe; please try again.');
    if (error instanceof SyntaxError) throw new Error('The planner returned an incomplete response. Please try again.');
    if (error instanceof TypeError) throw new Error('We couldn’t reach the planner. Please check your connection and try again.');
    throw error;
  } finally {
    clearTimeout(timeout);
  }
}

export async function requestPlan(brief) {
  const plan = await requestJSON('/api/plan', {
    method: 'POST', headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
    body: JSON.stringify(brief),
  }, 60000);
  if (!validPlan(plan)) throw new Error('The plan response was incomplete. Please try again.');
  return plan;
}

export async function requestSample() {
  const sample = await requestJSON('/api/sample', { headers: { Accept: 'application/json' } }, 10000);
  // Accept numeric budgets and Decimal strings from compatible earlier API builds.
  const brief = sample?.brief && { ...sample.brief, budget: Number(sample.brief.budget) };
  if (!validPlan(sample?.plan) || !validBrief(brief, sample.plan) || sample.plan.source !== 'local') {
    throw new Error('The sample plan could not be loaded. Enter your details and create your own plan.');
  }
  return { brief, plan: sample.plan };
}
