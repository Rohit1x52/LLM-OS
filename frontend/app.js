const API_URL = 'http://localhost:8000';
const messagesContainer = document.getElementById('messages');
const userInput = document.getElementById('userInput');
const sendBtn = document.getElementById('sendBtn');

sendBtn.addEventListener('click', processQuery);
userInput.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') processQuery();
});

document.querySelectorAll('.example-btn').forEach(btn => {
    btn.addEventListener('click', () => {
        userInput.value = btn.dataset.text;
        processQuery();
    });
});

async function processQuery() {
    const text = userInput.value.trim();
    if (!text) return;

    addUserMessage(text);
    userInput.value = '';
    
    sendBtn.disabled = true;
    sendBtn.innerHTML = '<span class="loading"></span>';

    try {
        const response = await fetch(`${API_URL}/api/process`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ text })
        });

        const result = await response.json();
        addAssistantMessage(result);
    } catch (error) {
        addErrorMessage(error.message);
    } finally {
        sendBtn.disabled = false;
        sendBtn.textContent = 'Process';
    }
}

function addUserMessage(text) {
    const messageDiv = document.createElement('div');
    messageDiv.className = 'message';
    messageDiv.innerHTML = `
        <div class="user-message">${escapeHtml(text)}</div>
    `;
    messagesContainer.appendChild(messageDiv);
    scrollToBottom();
}

function addAssistantMessage(result) {
    const messageDiv = document.createElement('div');
    messageDiv.className = 'message';
    
    let html = '<div class="assistant-message">';
    
    html += `
        <div class="intent-box">
            <strong>Intent:</strong> ${result.intent.action} 
            <span style="color: #666;">(${result.intent.category || 'unknown'})</span>
        </div>
    `;
    
    const confidence = result.confidence.overall_confidence;
    const confidenceClass = confidence >= 0.7 ? 'high' : confidence >= 0.5 ? 'medium' : 'low';
    
    html += `
        <div class="confidence-box">
            <strong>Confidence:</strong> ${(confidence * 100).toFixed(1)}%
            <div class="confidence-bar">
                <div class="confidence-fill confidence-${confidenceClass}" 
                     style="width: ${confidence * 100}%"></div>
            </div>
        </div>
    `;
    
    const entitiesFound = Object.entries(result.entities)
        .filter(([_, entities]) => entities.length > 0);
    
    if (entitiesFound.length > 0) {
        html += '<div class="entities-box"><strong>Entities:</strong><br>';
        entitiesFound.forEach(([type, entities]) => {
            entities.forEach(entity => {
                html += `<span class="entity-tag">${type}: ${entity.text || entity}</span>`;
            });
        });
        html += '</div>';
    }
    
    if (result.multi_intent.is_compound) {
        html += `
            <div class="intent-box">
                <strong>Compound Request:</strong> ${result.multi_intent.intent_count} sub-tasks
                <br><small>Execution: ${result.multi_intent.execution_order}</small>
                <ul style="margin-top: 8px;">
                    ${result.multi_intent.sub_intents.map((intent, i) => 
                        `<li>${i + 1}. ${intent.action}</li>`
                    ).join('')}
                </ul>
            </div>
        `;
    }
    
    if (result.needs_clarification) {
        html += `
            <div class="warning-box">
                <strong>⚠️ Clarification Needed:</strong><br>
                ${result.clarification_message}
            </div>
        `;
    }
    
    html += '</div>';
    messageDiv.innerHTML = html;
    messagesContainer.appendChild(messageDiv);
    scrollToBottom();
}

function addErrorMessage(error) {
    const messageDiv = document.createElement('div');
    messageDiv.className = 'message';
    messageDiv.innerHTML = `
        <div class="warning-box">
            <strong>Error:</strong> ${escapeHtml(error)}
        </div>
    `;
    messagesContainer.appendChild(messageDiv);
    scrollToBottom();
}

function scrollToBottom() {
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
}

function escapeHtml(text) {
    const map = {
        '&': '&amp;',
        '<': '&lt;',
        '>': '&gt;',
        '"': '&quot;',
        "'": '&#039;'
    };
    return text.replace(/[&<>"']/g, m => map[m]);
}