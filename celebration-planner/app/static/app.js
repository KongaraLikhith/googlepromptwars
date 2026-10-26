'use strict';

const STORAGE_KEY = 'gatherly.plan.v1';
const form = document.querySelector('#event-form');
const workspace = document.querySelector('#plan-workspace');
const generateButton = document.querySelector('#generate-button');
const generateLabel = document.querySelector('#generate-label');
const message = document.querySelector('#form-message');
const announcement = document.querySelector('#plan-announcement');
const eventNames = { wedding: 'Wedding', birthday: 'Birthday', community: 'Community' };
const currencySymbols = { INR: '₹', USD: '$', EUR: '€', GBP: '£' };
let currentPlan = null;
let currentBrief = null;
let completed = new Set();
let isLoading = false;

function element(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
}

function dateKey(value) {
  const year = value.getFullYear();
  const month = String(value.getMonth() + 1).padStart(2, '0');
  const day = String(value.getDate()).padStart(2, '0');
  return `${year}-${month}-${day}`;
}

function dateLabel(value, options = { day: 'numeric', month: 'short', year: 'numeric' }) {
  return new Intl.DateTimeFormat(undefined, options).format(new Date(`${value}T12:00:00`));
}

function money(value, currency = currentPlan?.currency || form.elements.currency.value) {
  return new Intl.NumberFormat(currency === 'INR' ? 'en-IN' : undefined, {
    style: 'currency', currency, minimumFractionDigits: Number.isInteger(Number(value)) ? 0 : 2,
    maximumFractionDigits: 2,
  }).format(Number(value));
}

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
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify({
      version: 1, brief: currentBrief, plan: currentPlan, completed: [...completed],
    }));
    document.querySelector('#save-status').textContent = '◈  Saved only in this browser';
  } catch {
    document.querySelector('#save-status').textContent = '◈  Browser storage unavailable — download to keep your plan';
  }
}

function validPlan(plan) {
  return plan && typeof plan === 'object'
    && Object.hasOwn(eventNames, plan.event_type)
    && Object.hasOwn(currencySymbols, plan.currency)
    && /^\d{4}-\d{2}-\d{2}$/.test(plan.event_date)
    && Number.isFinite(Number(plan.budget)) && Number(plan.budget) >= 100
    && Number.isInteger(plan.guest_count) && plan.guest_count > 0
    && ['budget_items', 'timeline', 'vendors', 'ideas', 'tips'].every(key => Array.isArray(plan[key]))
    && plan.budget_items.length > 0 && plan.budget_items.length <= 20
    && plan.budget_items.every(item => item && typeof item.category === 'string' && Number.isFinite(Number(item.amount)) && Number(item.amount) >= 0)
    && plan.timeline.every(item => item && /^\d{4}-\d{2}-\d{2}$/.test(item.date))
    && plan.vendors.every(item => item && typeof item.id === 'string');
}

function restoreSaved() {
  try {
    const saved = JSON.parse(localStorage.getItem(STORAGE_KEY) || 'null');
    if (saved?.version !== 1 || !validPlan(saved.plan)) return false;
    restoreBrief(saved.brief);
    currentBrief = saved.brief;
    currentPlan = saved.plan;
    completed = new Set(Array.isArray(saved.completed) ? saved.completed.filter(id => typeof id === 'string') : []);
    renderPlan();
    if (currentPlan.event_date < form.elements.event_date.min) {
      inform('Your saved celebration date has passed. Choose a new date to refresh the plan.');
    } else {
      inform('Welcome back. Your plan and checklist are right where you left them.');
    }
    return true;
  } catch {
    return false;
  }
}

function updateBudgetTotals() {
  const cents = currentPlan.budget_items.reduce((sum, item) => sum + Math.round(Number(item.amount) * 100), 0);
  const difference = Math.round(Number(currentPlan.budget) * 100) - cents;
  document.querySelector('#allocated-total').textContent = money(cents / 100);
  const balance = document.querySelector('#balance-message');
  balance.classList.toggle('over', difference < 0);
  balance.textContent = difference === 0 ? '✓ Every bit has a purpose' : difference > 0
    ? `${money(difference / 100)} left to allocate` : `${money(Math.abs(difference) / 100)} over your budget`;
}

function renderBudget() {
  const list = document.querySelector('#budget-list');
  list.replaceChildren();
  const icons = ['⌂', '♧', '✳', '♪', '◉', '♡', '◈'];
  currentPlan.budget_items.forEach((item, index) => {
    const row = element('div', 'budget-item');
    const icon = element('span', 'category-icon', icons[index % icons.length]);
    icon.setAttribute('aria-hidden', 'true');
    const information = element('div', 'budget-info');
    information.append(element('h4', 'budget-category', item.category), element('p', 'budget-note', item.note));
    const bar = element('progress', 'allocation-bar');
    bar.max = Number(currentPlan.budget);
    bar.value = Number(item.amount);
    bar.setAttribute('aria-label', `${item.category} allocation`);
    information.append(bar);
    const edit = element('div', 'allocation-edit');
    const symbol = element('span', 'currency-symbol', currencySymbols[currentPlan.currency]);
    symbol.setAttribute('aria-hidden', 'true');
    const input = element('input');
    input.type = 'number';
    input.min = '0';
    input.max = '100000000';
    input.step = '0.01';
    input.value = Number(item.amount).toFixed(Number.isInteger(Number(item.amount)) ? 0 : 2);
    input.setAttribute('aria-label', `${item.category} budget allocation in ${currentPlan.currency}`);
    const percent = element('span', 'allocation-percent', `${Math.round(Number(item.amount) / Number(currentPlan.budget) * 100)}%`);
    input.addEventListener('change', () => {
      if (!input.checkValidity() || input.value === '') {
        input.reportValidity();
        input.value = String(item.amount);
        return;
      }
      item.amount = Math.round(Number(input.value) * 100) / 100;
      item.percent = Math.round(item.amount / Number(currentPlan.budget) * 100);
      bar.value = item.amount;
      percent.textContent = `${item.percent}%`;
      input.value = String(item.amount);
      updateBudgetTotals();
      savePlan();
    });
    edit.append(symbol, input, percent);
    row.append(icon, information, edit);
    list.append(row);
  });
  updateBudgetTotals();
}

function renderTimeline() {
  const list = document.querySelector('#timeline-list');
  list.replaceChildren();
  currentPlan.timeline.forEach(item => {
    const row = element('li', 'timeline-item');
    const time = element('time', 'timeline-date', dateLabel(item.date, { day: 'numeric', month: 'short' }));
    time.dateTime = item.date;
    time.append(element('span', '', dateLabel(item.date, { year: 'numeric' })));
    const content = element('div', 'timeline-content');
    content.append(element('h4', '', item.title), element('p', '', item.note), element('span', 'timeline-phase', item.phase));
    row.append(time, content);
    list.append(row);
  });
}

function updateChecklistProgress() {
  const count = currentPlan.vendors.filter(item => completed.has(item.id)).length;
  document.querySelector('#checklist-count').textContent = String(currentPlan.vendors.length);
  document.querySelector('#checklist-progress').textContent = `${count} OF ${currentPlan.vendors.length} COMPLETE`;
  const progress = document.querySelector('#checklist-bar');
  progress.max = currentPlan.vendors.length || 1;
  progress.value = count;
  progress.setAttribute('aria-valuetext', `${count} of ${currentPlan.vendors.length} checklist items complete`);
}

function renderChecklist() {
  const list = document.querySelector('#vendor-list');
  list.replaceChildren();
  currentPlan.vendors.forEach(item => {
    const label = element('label', 'vendor-item');
    const input = element('input');
    input.type = 'checkbox';
    input.checked = completed.has(item.id);
    input.setAttribute('aria-label', item.title);
    input.addEventListener('change', () => {
      if (input.checked) completed.add(item.id);
      else completed.delete(item.id);
      updateChecklistProgress();
      savePlan();
    });
    const body = element('span', 'vendor-body');
    const title = element('span', 'vendor-title', item.title);
    if (item.essential) title.append(element('span', 'essential-tag', 'Essential'));
    body.append(element('span', 'vendor-category', item.category), title, element('span', 'vendor-note', item.note));
    label.append(input, body);
    list.append(label);
  });
  updateChecklistProgress();
}

function renderIdeas() {
  const grid = document.querySelector('#idea-grid');
  grid.replaceChildren();
  currentPlan.ideas.forEach((idea, index) => {
    const card = element('article', 'idea-item');
    card.append(element('span', 'idea-number', `0${index + 1} / A LITTLE INSPIRATION`), element('h4', '', idea.title), element('p', '', idea.description));
    grid.append(card);
  });
  document.querySelector('#ideas-label').textContent = currentPlan.source === 'gemini' ? 'Ideas powered by Gemini' : 'Curated local ideas';
  document.querySelector('#source-note').textContent = currentPlan.source_note;
  const tips = document.querySelector('#tips-list');
  tips.replaceChildren(...currentPlan.tips.map(tip => element('li', '', tip)));
  document.querySelector('#tips-box').hidden = currentPlan.tips.length === 0;
}

function renderPlan() {
  const plan = currentPlan;
  document.querySelector('#plan-title').textContent = `${eventNames[plan.event_type]} plans, made simple.`;
  document.querySelector('#plan-summary').textContent = plan.summary;
  const badge = document.querySelector('#source-badge');
  badge.replaceChildren(element('span', 'status-dot'), document.createTextNode(plan.source === 'gemini' ? 'Gemini ideas' : 'Local planning mode'));
  const days = Math.round((new Date(`${plan.event_date}T12:00:00`) - new Date(`${dateKey(new Date())}T12:00:00`)) / 86400000);
  document.querySelector('#days-metric').textContent = days < 0 ? 'Past event' : days === 0 ? 'Today!' : `${days} ${days === 1 ? 'day' : 'days'}`;
  document.querySelector('#date-metric').textContent = dateLabel(plan.event_date);
  document.querySelector('#budget-metric').textContent = money(plan.budget);
  document.querySelector('#per-guest-metric').textContent = `${money(Number(plan.budget) / plan.guest_count)} per guest`;
  document.querySelector('#guests-metric').textContent = Number(plan.guest_count).toLocaleString();
  renderBudget();
  renderTimeline();
  renderChecklist();
  renderIdeas();
  document.querySelector('#export-button').disabled = false;
  document.querySelector('#print-button').disabled = false;
  workspace.setAttribute('aria-busy', 'false');
}

function setLoading(loading) {
  isLoading = loading;
  workspace.setAttribute('aria-busy', String(loading));
  generateButton.disabled = loading;
  generateButton.classList.toggle('loading', loading);
  generateLabel.textContent = loading ? 'Bringing it all together…' : 'Create my celebration plan';
}

async function generatePlan(event, persist = true) {
  if (event) event.preventDefault();
  if (isLoading || !form.reportValidity()) return;
  const brief = captureBrief();
  if (brief.priorities.length > 3) {
    inform('Choose up to three priorities so your budget has a clear focus.', true);
    return;
  }
  setLoading(true);
  inform('A little thought for every detail. Your plan is coming together.');
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 25000);
  try {
    const response = await fetch('/api/plan', {
      method: 'POST', headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
      body: JSON.stringify(brief), signal: controller.signal,
    });
    if (!response.ok) {
      if (response.status === 422) throw new Error('Please check your date, budget, guest count, and other details, then try again.');
      if (response.status === 429) throw new Error('There are a few plans in progress. Please try again in a moment.');
      throw new Error('Your plan couldn’t be created just yet. Please try again in a moment.');
    }
    const nextPlan = await response.json();
    if (!validPlan(nextPlan)) throw new Error('The plan response was incomplete. Please try again.');
    const sameEvent = currentBrief && currentBrief.event_type === brief.event_type && currentBrief.event_date === brief.event_date;
    if (!sameEvent) completed = new Set();
    currentBrief = brief;
    currentPlan = nextPlan;
    renderPlan();
    if (persist) {
      savePlan();
      inform(currentPlan.source === 'gemini' ? 'Your plan is ready, with personalized ideas from Gemini.' : 'Your plan is ready in local mode. Ideas are curated; budget allocations are estimates.');
    } else {
      document.querySelector('#save-status').textContent = '◈  Fresh sample — not saved until you make changes';
      inform('Your saved plan was cleared. This fresh sample has not been saved.');
    }
    announcement.textContent = `${eventNames[brief.event_type]} plan ready: ${money(brief.budget, brief.currency)}, ${brief.guest_count} guests, ${currentPlan.vendors.length} checklist items. ${currentPlan.source === 'gemini' ? 'Ideas powered by Gemini.' : 'Local planning mode.'}`;
  } catch (error) {
    inform(error.name === 'AbortError' ? 'This is taking longer than expected. Your previous plan is safe; please try again.' : error.message || 'We couldn’t reach the planner. Please try again.', true);
    if (!currentPlan) {
      document.querySelector('#source-badge').textContent = 'Waiting for your plan';
      document.querySelector('#budget-list').replaceChildren(element('p', 'empty-state', 'The planner is unavailable right now. Check your details and try creating your plan again.'));
    }
  } finally {
    clearTimeout(timeout);
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
  const anchor = element('a');
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
  try { localStorage.removeItem(STORAGE_KEY); } catch { /* Continue in memory when storage is unavailable. */ }
  completed = new Set();
  currentPlan = null;
  currentBrief = null;
  setDefaults();
  activateTab(document.querySelector('#tab-budget'));
  generatePlan(null, false);
  announcement.textContent = 'Your saved plan has been cleared. A fresh sample plan is being prepared.';
});

setDefaults();
if (!restoreSaved()) generatePlan();
