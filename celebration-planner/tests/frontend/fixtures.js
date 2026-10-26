export function sample() {
  const plan = {
    event_type: 'birthday', event_date: '2027-01-01', budget: 1000, currency: 'INR', guest_count: 20,
    summary: 'A joyful garden birthday.', source: 'local', source_note: 'Planning estimates.',
    budget_items: [{ category: 'Food', amount: 900, note: 'Confirm dietary requirements.' }, { category: 'Contingency', amount: 100, note: 'Keep a reserve.' }],
    timeline: [{ id: 'confirm', date: '2026-12-01', title: 'Confirm guests', phase: 'Prepare', note: 'Allow time for replies.' }],
    vendors: [{ id: 'catering', category: 'Food', title: 'Compare caterers', note: 'Ask for quotes.', essential: true }],
    ideas: [{ title: 'Shared memories', description: 'Invite guests to share a favorite memory.' }], tips: ['Check step-free access.'],
  };
  const brief = { event_type: plan.event_type, event_date: plan.event_date, budget: plan.budget, currency: plan.currency,
    guest_count: plan.guest_count, location: 'Garden', style: 'Relaxed', preferences: '', priorities: ['food'] };
  return { plan, brief, completed: new Set(['catering']) };
}
