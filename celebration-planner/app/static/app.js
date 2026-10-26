import { EVENT_NAMES as eventNames, dateKey, formatMoney } from './plan-utils.js';
import { requestPlan, requestSample } from './plan-api.js';
import { createPlanView } from './plan-view.js';
import { createPlanStore } from './plan-storage.js';

const planStore = createPlanStore();
const planView = createPlanView(savePlan);
const form = document.querySelector('#event-form');
const workspace = document.querySelector('#plan-workspace');
const generateButton = document.querySelector('#generate-button');
const generateLabel = document.querySelector('#generate-label');
const message = document.querySelector('#form-message');
const announcement = document.querySelector('#plan-announcement');
let currentPlan = null;
let currentBrief = null;
let completed = new Set();
let isLoading = false;

function inform(text, error = false) {
  message.textContent = text;
  message.classList.toggle('error', error);
}

function captureBrief() {
  return {
    event_type: form.elements.event_type.value,
    event_date: form.elements.event_date.value,
    budget: Number(form.elements.budget.value),
    currency: form.elements.currency.value,
    guest_count: Number(form.elements.guest_count.value),
    location: form.elements.location.value.trim(),
    style: form.elements.style.value,
    priorities: [...form.querySelectorAll('[name="priorities"]:checked')].map(input => input.value),
    preferences: form.elements.preferences.value.trim(),
  };
}

function restoreBrief(brief) {
  if (!brief || typeof brief !== 'object') return;
  for (const name of ['event_type', 'event_date', 'budget', 'currency', 'guest_count', 'location', 'style', 'preferences']) {
    if (typeof brief[name] === 'string' || typeof brief[name] === 'number') {
      form.elements[name].value = String(brief[name]);
    }
  }
  if (Array.isArray(brief.priorities)) {
    const choices = new Set(brief.priorities.slice(0, 3));
    form.querySelectorAll('[name="priorities"]').forEach(input => { input.checked = choices.has(input.value); });
  }
}

function setDefaults() {
  form.reset();
  const today = new Date();
  const maximum = new Date(today);
  maximum.setDate(maximum.getDate() + 730);
  const occasion = new Date(today);
  occasion.setDate(occasion.getDate() + 90);
  form.elements.event_date.min = dateKey(today);
  form.elements.event_date.max = dateKey(maximum);
  form.elements.event_date.value = dateKey(occasion);
}

function savePlan() {
  if (!currentPlan || !currentBrief) return;
  const saved = planStore.save({ brief: currentBrief, plan: currentPlan, completed });
  document.querySelector('#save-status').textContent = saved
    ? '◈  Saved only in this browser'
    : '◈  Browser storage unavailable — download to keep your plan';
}

function restoreSaved() {
  const saved = planStore.load();
  if (!saved) return false;
  restoreBrief(saved.brief);
  currentBrief = saved.brief;
  currentPlan = saved.plan;
  completed = new Set(saved.completed);
  renderPlan();
  document.querySelector('#save-status').textContent = '◈  Saved only in this browser';
  if (currentPlan.event_date < form.elements.event_date.min) {
    inform('Your saved celebration date has passed. Choose a new date to refresh the plan.');
  } else {
    inform('Welcome back. Your plan and checklist are right where you left them.');
  }
  return true;
}

function renderPlan() {
  planView.render(currentPlan, completed);
  workspace.setAttribute('aria-busy', 'false');
}

function setLoading(loading) {
  isLoading = loading;
  workspace.setAttribute('aria-busy', String(loading));
  generateButton.disabled = loading;
  generateButton.classList.toggle('loading', loading);
  generateLabel.textContent = loading ? 'Bringing it all together…' : 'Create my celebration plan';
}

async function generatePlan(event) {
  if (event) event.preventDefault();
  if (isLoading || !form.reportValidity()) return;
  const brief = captureBrief();
  if (brief.priorities.length > 3) {
    inform('Choose up to three priorities so your budget has a clear focus.', true);
    return;
  }
  setLoading(true);
  inform('A little thought for every detail. Your plan is coming together.');
  try {
    const nextPlan = await requestPlan(brief);
    const sameEvent = currentBrief && currentBrief.event_type === brief.event_type && currentBrief.event_date === brief.event_date;
    if (!sameEvent) completed = new Set();
    currentBrief = brief;
    currentPlan = nextPlan;
    renderPlan();
    savePlan();
    inform(currentPlan.source === 'gemini' ? 'Your plan is ready, with personalized ideas from Gemini.' : 'Your plan is ready in local mode. Ideas are curated; budget allocations are estimates.');
    announcement.textContent = `${eventNames[brief.event_type]} plan ready: ${formatMoney(brief.budget, brief.currency)}, ${brief.guest_count} guests, ${currentPlan.vendors.length} checklist items. ${currentPlan.source === 'gemini' ? 'Ideas powered by Gemini.' : 'Local planning mode.'}`;
  } catch (error) {
    inform(error.message || 'We couldn’t reach the planner. Please try again.', true);
    if (!currentPlan) planView.showUnavailable();
  } finally {
    setLoading(false);
  }
}

async function loadSample(cleared = false) {
  const originalInputs = JSON.stringify(captureBrief());
  setLoading(true);
  inform('Preparing a sample celebration. Add your details to make it yours.');
  try {
    const sample = await requestSample();
    currentBrief = sample.brief;
    currentPlan = sample.plan;
    completed = new Set();
    // Preserve details typed while the sample request was in flight.
    if (JSON.stringify(captureBrief()) === originalInputs) restoreBrief(currentBrief);
    renderPlan();
    document.querySelector('#save-status').textContent = '◈  Sample plan — saved only when you make changes';
    inform(cleared ? 'Your saved plan was cleared. This fresh sample has not been saved.'
      : 'Explore this sample, then add your details and create a plan with personalized ideas.');
    announcement.textContent = 'Sample birthday plan ready. Customize the details and create your own celebration plan.';
  } catch (error) {
    inform(error.message || 'The sample is unavailable. Enter your details and create your own plan.', true);
    if (!currentPlan) planView.showUnavailable();
  } finally {
    setLoading(false);
  }
}

function activateTab(tab) {
  document.querySelectorAll('[role="tab"]').forEach(button => {
    const selected = button === tab;
    button.setAttribute('aria-selected', String(selected));
    button.tabIndex = selected ? 0 : -1;
    button.classList.toggle('active', selected);
    document.querySelector(`#${button.getAttribute('aria-controls')}`).hidden = !selected;
  });
}

document.querySelectorAll('[role="tab"]').forEach((tab, index, tabs) => {
  tab.addEventListener('click', () => activateTab(tab));
  tab.addEventListener('keydown', event => {
    let next;
    if (event.key === 'ArrowRight') next = (index + 1) % tabs.length;
    if (event.key === 'ArrowLeft') next = (index + tabs.length - 1) % tabs.length;
    if (event.key === 'Home') next = 0;
    if (event.key === 'End') next = tabs.length - 1;
    if (next !== undefined) {
      event.preventDefault();
      activateTab(tabs[next]);
      tabs[next].focus();
    }
  });
});

form.addEventListener('submit', generatePlan);
form.querySelectorAll('[name="priorities"]').forEach(input => {
  input.addEventListener('change', () => {
    const count = form.querySelectorAll('[name="priorities"]:checked').length;
    if (count > 3) {
      input.checked = false;
      inform('Choose up to three things that matter most. Uncheck one to make room for another.');
    } else {
      document.querySelector('#priorities-note').textContent = `${count} of 3 priorities selected. Your choices help shape the budget.`;
    }
  });
});

form.addEventListener('input', () => {
  if (currentPlan && !isLoading) inform('Details changed. Create your plan again to apply them.');
});

document.querySelector('#currency').addEventListener('change', () => {
  inform('Currency changes the budget unit, not the amount. Enter your budget in the selected currency, then create your plan.');
});

document.querySelector('#export-button').addEventListener('click', () => {
  if (!currentPlan) return;
  const exported = {
    ...currentPlan,
    budget_items: currentPlan.budget_items.map(item => ({ ...item })),
    vendors: currentPlan.vendors.map(item => ({ ...item, completed: completed.has(item.id) })),
    exported_at: new Date().toISOString(),
    planning_note: 'Planning estimates, not vendor quotes or bookings. Currency selection does not convert values.',
  };
  const url = URL.createObjectURL(new Blob([JSON.stringify(exported, null, 2)], { type: 'application/json' }));
  const anchor = document.createElement('a');
  anchor.href = url;
  anchor.download = `gatherly-${currentPlan.event_type}-${currentPlan.event_date}.json`;
  document.body.append(anchor);
  anchor.click();
  anchor.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
  announcement.textContent = 'Your celebration plan has been downloaded as a JSON file.';
});

document.querySelector('#print-button').addEventListener('click', () => {
  if (currentPlan) window.print();
});

document.querySelector('#reset-button').addEventListener('click', () => {
  if (isLoading) return;
  if (!planStore.clear()) {
    inform('Browser storage is unavailable. Your saved plan could not be cleared; download your plan or update browser storage permissions.', true);
    return;
  }
  completed = new Set();
  currentPlan = null;
  currentBrief = null;
  setDefaults();
  activateTab(document.querySelector('#tab-budget'));
  loadSample(true);
  announcement.textContent = 'Your saved plan has been cleared. A fresh sample plan is being prepared.';
});

setDefaults();
if (!restoreSaved()) loadSample();
