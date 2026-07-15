document.getElementById('footprint-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    
    const submitBtn = document.getElementById('calculate-btn');
    const resultsContainer = document.getElementById('results-container');
    const loader = document.getElementById('loader');
    const resultsContent = document.getElementById('results-content');
    
    // Disable button and show loader
    submitBtn.disabled = true;
    submitBtn.textContent = 'Calculating & Fetching Insights...';
    resultsContainer.classList.remove('hidden');
    loader.classList.remove('hidden');
    resultsContent.classList.add('hidden');
    
    // Gather data
    const payload = {
        transport_miles_per_week: parseFloat(document.getElementById('transport_miles_per_week').value),
        mpg: parseFloat(document.getElementById('mpg').value),
        electricity_kwh_per_month: parseFloat(document.getElementById('electricity_kwh_per_month').value),
        diet_type: document.getElementById('diet_type').value
    };
    
    try {
        const response = await fetch('/api/calculate', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(payload)
        });
        
        const data = await response.json();
        
        if (response.ok) {
            // Populate metrics
            document.getElementById('res-transport').textContent = `${data.footprint.transport_co2_lbs} lbs CO₂`;
            document.getElementById('res-energy').textContent = `${data.footprint.energy_co2_lbs} lbs CO₂`;
            document.getElementById('res-diet').textContent = `${data.footprint.diet_co2_lbs} lbs CO₂`;
            document.getElementById('res-total').textContent = `${data.footprint.total_co2_lbs} lbs CO₂`;
            
            // Render markdown insights
            document.getElementById('ai-insights').innerHTML = marked.parse(data.insights);
            
            // Show content
            loader.classList.add('hidden');
            resultsContent.classList.remove('hidden');
        } else {
            alert('Error calculating footprint. Please try again.');
            resultsContainer.classList.add('hidden');
        }
    } catch (err) {
        console.error(err);
        alert('Failed to connect to the server.');
        resultsContainer.classList.add('hidden');
    } finally {
        submitBtn.disabled = false;
        submitBtn.textContent = 'Calculate Footprint & Get Insights';
    }
});

// Chatbot Logic
const chatToggle = document.getElementById('chatbot-toggle');
const chatWindow = document.getElementById('chatbot-window');
const chatClose = document.getElementById('chatbot-close');
const chatForm = document.getElementById('chatbot-form');
const chatInput = document.getElementById('chatbot-input');
const chatMessages = document.getElementById('chatbot-messages');

let chatHistory = [];

chatToggle.addEventListener('click', () => {
    chatWindow.classList.toggle('hidden');
    chatToggle.classList.add('hidden');
});

chatClose.addEventListener('click', () => {
    chatWindow.classList.add('hidden');
    chatToggle.classList.remove('hidden');
});

function appendMessage(role, content) {
    const msgDiv = document.createElement('div');
    msgDiv.classList.add('chat-message', role);
    msgDiv.innerHTML = role === 'bot' ? marked.parse(content) : content;
    chatMessages.appendChild(msgDiv);
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

chatForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    const message = chatInput.value.trim();
    if (!message) return;

    appendMessage('user', message);
    chatInput.value = '';
    
    // Add typing indicator
    const typingDiv = document.createElement('div');
    typingDiv.classList.add('chat-message', 'bot');
    typingDiv.textContent = 'Thinking...';
    chatMessages.appendChild(typingDiv);
    chatMessages.scrollTop = chatMessages.scrollHeight;

    try {
        const response = await fetch('/api/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ message: message, history: chatHistory })
        });
        
        const data = await response.json();
        
        // Remove typing indicator
        chatMessages.removeChild(typingDiv);
        
        if (response.ok) {
            appendMessage('bot', data.response);
            chatHistory.push({ role: 'user', content: message });
            chatHistory.push({ role: 'bot', content: data.response });
        } else {
            appendMessage('bot', 'Error: Could not fetch response.');
        }
    } catch (err) {
        chatMessages.removeChild(typingDiv);
        appendMessage('bot', 'Error: Connection failed.');
    }
});
