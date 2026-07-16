const context = () => ({
  mobility: document.querySelector('#mobility').value,
  language: document.querySelector('#language').value,
  signals: {
    northPlazaQueuePercent: 66,
    northPlazaProjectedPercent: 78,
    gateCWalkMinutes: 12,
    elevatorWaitMinutes: 3,
    transitStatus: 'on_schedule',
    wasteDiversionPercent: 76
  }
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
    const response = await fetch('/api/concierge', {
      method: 'POST', headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({message: question, context: context()})
    });
    const contentType = response.headers.get('content-type') || '';
    const data = contentType.includes('application/json')
      ? await response.json()
      : {error: 'Guidance is temporarily unavailable. Please ask a venue team member.'};
    if (!response.ok) throw new Error(data.error);
    const reasons = data.decision?.reasons?.join(' · ');
    answer.textContent = reasons ? `${data.reply}\n\nWhy: ${reasons}` : data.reply;
    answer.dataset.source = data.source;
  } catch (error) {
    answer.textContent = error.message || 'Guidance is temporarily unavailable. Please ask a venue team member.';
  }
});

document.querySelector('#resolve').addEventListener('click', event => {
  event.currentTarget.closest('.alert').innerHTML = '<strong>Action logged</strong><p>Volunteer reassignment has been recorded in this demo.</p>';
});
