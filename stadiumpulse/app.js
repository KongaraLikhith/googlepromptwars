const context = () => ({
  gate: 'C',
  mobility: document.querySelector('#mobility').value,
  language: document.querySelector('#language').value,
  signals: { northPlazaQueue: 'rising; projected 78% in 18 minutes', gateC: 'calmer; 12 minute walk', transit: 'rail platform 2 on schedule', elevatorWait: '3 minutes' },
  dataStatus: 'simulated demo data, refreshed manually'
});
const answer = document.querySelector('#answer');
document.querySelectorAll('[data-question]').forEach(button => button.addEventListener('click', () => {
  document.querySelector('#question').value = button.dataset.question;
  document.querySelector('#question').focus();
}));
document.querySelector('#chat-form').addEventListener('submit', async event => {
  event.preventDefault();
  const question = document.querySelector('#question').value.trim();
  if (!question) return;
  answer.textContent = 'Preparing your matchday guidance…';
  try {
    const response = await fetch('/api/concierge', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({message:question, context:context()})});
    const data = await response.json();
    if (!response.ok) throw new Error(data.error);
    answer.textContent = data.reply;
    answer.dataset.source = data.source;
  } catch (error) { answer.textContent = error.message || 'Guidance is temporarily unavailable. Please ask a venue team member.'; }
});
document.querySelector('#resolve').addEventListener('click', event => { event.currentTarget.closest('.alert').innerHTML = '<strong>Action logged</strong><p>Volunteer reassignment has been recorded in this demo.</p>'; });
