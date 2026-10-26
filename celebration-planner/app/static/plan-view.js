import { EVENT_NAMES as eventNames, CURRENCY_SYMBOLS as currencySymbols,
  dateLabel, daysUntil, formatMoney, budgetTotals } from './plan-utils.js';

function element(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
}

/** Render one validated plan; edits update it in place and notify the controller. */
export function createPlanView(onChange) {
  let plan;
  let completed;
  const money = value => formatMoney(value, plan.currency);
  const nodes = new Map();
  const query = selector => {
    if (!nodes.has(selector)) nodes.set(selector, document.querySelector(selector));
    return nodes.get(selector);
  };

  function updateBudgetTotals() {
    const { allocated, difference } = budgetTotals(plan.budget_items, plan.budget);
    query('#allocated-total').textContent = money(allocated);
    const balance = query('#balance-message');
    balance.classList.toggle('over', difference < 0);
    balance.textContent = difference === 0 ? '✓ Every bit has a purpose' : difference > 0
      ? `${money(difference)} left to allocate` : `${money(Math.abs(difference))} over your budget`;
  }

  function renderBudget() {
    const list = query('#budget-list');
    list.replaceChildren();
    const icons = ['⌂', '♧', '✳', '♪', '◉', '♡', '◈'];
    plan.budget_items.forEach((item, index) => {
      const row = element('div', 'budget-item');
      const icon = element('span', 'category-icon', icons[index % icons.length]);
      icon.setAttribute('aria-hidden', 'true');
      const information = element('div', 'budget-info');
      information.append(element('h4', 'budget-category', item.category), element('p', 'budget-note', item.note));
      const bar = element('progress', 'allocation-bar');
      bar.max = Number(plan.budget);
      bar.value = Number(item.amount);
      bar.setAttribute('aria-label', `${item.category} allocation`);
      information.append(bar);
      const edit = element('div', 'allocation-edit');
      const symbol = element('span', 'currency-symbol', currencySymbols[plan.currency]);
      symbol.setAttribute('aria-hidden', 'true');
      const input = element('input');
      input.type = 'number';
      input.min = '0';
      input.max = '100000000';
      input.step = '0.01';
      input.value = Number(item.amount).toFixed(Number.isInteger(Number(item.amount)) ? 0 : 2);
      input.setAttribute('aria-label', `${item.category} budget allocation in ${plan.currency}`);
      const percent = element('span', 'allocation-percent', `${Math.round(Number(item.amount) / Number(plan.budget) * 100)}%`);
      input.addEventListener('change', () => {
        if (!input.checkValidity() || input.value === '') {
          input.reportValidity();
          input.value = String(item.amount);
          return;
        }
        item.amount = Math.round(Number(input.value) * 100) / 100;
        item.percent = Math.round(item.amount / Number(plan.budget) * 100);
        bar.value = item.amount;
        percent.textContent = `${item.percent}%`;
        input.value = String(item.amount);
        updateBudgetTotals();
        onChange();
      });
      edit.append(symbol, input, percent);
      row.append(icon, information, edit);
      list.append(row);
    });
    updateBudgetTotals();
  }

  function renderTimeline() {
    const list = query('#timeline-list');
    list.replaceChildren();
    plan.timeline.forEach(item => {
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
    const count = plan.vendors.filter(item => completed.has(item.id)).length;
    query('#checklist-count').textContent = String(plan.vendors.length);
    query('#checklist-progress').textContent = `${count} OF ${plan.vendors.length} COMPLETE`;
    const progress = query('#checklist-bar');
    progress.max = plan.vendors.length || 1;
    progress.value = count;
    progress.setAttribute('aria-valuetext', `${count} of ${plan.vendors.length} checklist items complete`);
  }

  function renderChecklist() {
    const list = query('#vendor-list');
    list.replaceChildren();
    plan.vendors.forEach(item => {
      const label = element('label', 'vendor-item');
      const input = element('input');
      input.type = 'checkbox';
      input.checked = completed.has(item.id);
      input.setAttribute('aria-label', item.title);
      input.addEventListener('change', () => {
        if (input.checked) completed.add(item.id);
        else completed.delete(item.id);
        updateChecklistProgress();
        onChange();
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
    const grid = query('#idea-grid');
    grid.replaceChildren();
    plan.ideas.forEach((idea, index) => {
      const card = element('article', 'idea-item');
      card.append(element('span', 'idea-number', `0${index + 1} / A LITTLE INSPIRATION`), element('h4', '', idea.title), element('p', '', idea.description));
      grid.append(card);
    });
    query('#ideas-label').textContent = plan.source === 'gemini' ? 'Ideas powered by Gemini' : 'Curated local ideas';
    query('#source-note').textContent = plan.source_note;
    const tips = query('#tips-list');
    tips.replaceChildren(...plan.tips.map(tip => element('li', '', tip)));
    query('#tips-box').hidden = plan.tips.length === 0;
  }

  function renderPlan(nextPlan, nextCompleted) {
    plan = nextPlan;
    completed = nextCompleted;
    query('#plan-title').textContent = `${eventNames[plan.event_type]} plans, made simple.`;
    query('#plan-summary').textContent = plan.summary;
    const badge = query('#source-badge');
    badge.replaceChildren(element('span', 'status-dot'), document.createTextNode(plan.source === 'gemini' ? 'Gemini ideas' : 'Local planning mode'));
    const days = daysUntil(plan.event_date);
    query('#days-metric').textContent = days < 0 ? 'Past event' : days === 0 ? 'Today!' : `${days} ${days === 1 ? 'day' : 'days'}`;
    query('#date-metric').textContent = dateLabel(plan.event_date);
    query('#budget-metric').textContent = money(plan.budget);
    query('#per-guest-metric').textContent = `${money(Number(plan.budget) / plan.guest_count)} per guest`;
    query('#guests-metric').textContent = Number(plan.guest_count).toLocaleString();
    renderBudget();
    renderTimeline();
    renderChecklist();
    renderIdeas();
    query('#export-button').disabled = false;
    query('#print-button').disabled = false;
  }

  return {
    render: renderPlan,
    showUnavailable() {
      plan = null;
      completed = new Set();
      query('#plan-title').textContent = 'Your celebration, taking shape.';
      query('#plan-summary').textContent = 'Enter your event details and create a celebration plan.';
      query('#source-badge').textContent = 'Waiting for your plan';
      for (const selector of ['#days-metric', '#date-metric', '#budget-metric', '#per-guest-metric', '#guests-metric', '#allocated-total']) {
        query(selector).textContent = '—';
      }
      query('#budget-list').replaceChildren(element('p', 'empty-state',
        'The planner is unavailable right now. Check your details and try creating your plan again.'));
      for (const selector of ['#timeline-list', '#vendor-list', '#idea-grid', '#tips-list']) query(selector).replaceChildren();
      query('#ideas-label').textContent = 'Ideas appear with your plan';
      query('#source-note').textContent = 'Create a plan to see its planning source and guidance.';
      query('#balance-message').textContent = 'Create a plan to see your allocations.';
      query('#balance-message').classList.remove('over');
      query('#checklist-count').textContent = '0';
      query('#checklist-progress').textContent = '0 COMPLETE';
      query('#checklist-bar').value = 0;
      query('#checklist-bar').max = 1;
      query('#checklist-bar').setAttribute('aria-valuetext', 'No checklist items available.');
      query('#save-status').textContent = '◈  No active plan — create one to begin';
      query('#plan-announcement').textContent = 'No active plan. Enter your details and create a celebration plan.';
      query('#tips-box').hidden = true;
      query('#export-button').disabled = true;
      query('#print-button').disabled = true;
    },
  };
}
