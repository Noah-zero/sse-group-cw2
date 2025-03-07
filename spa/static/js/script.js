let currentChatName = '';

async function hashPassword(password) {
    const encoder = new TextEncoder();
    const data = encoder.encode(password);
    const hashBuffer = await crypto.subtle.digest("SHA-256", data);
    return Array.from(new Uint8Array(hashBuffer)).map(byte => byte.toString(16).padStart(2, "0")).join("");
}

// register
async function registerUser() {
    const username = document.getElementById('username').value;
    const password = document.getElementById('password').value;

    const hashedPassword = await hashPassword(password);

    try {
        const response = await fetch('/api/register', {
            method: 'POST',
            body: JSON.stringify({ username, hashedPassword }),
            headers: { 'Content-Type': 'application/json' }
        });

        const data = await response.json();
        document.getElementById('error-message').innerText = data.message;
    } catch (error) {
        console.error("Registration error:", error);
    }
}

// login
async function loginUser() {
    const username = document.getElementById('username').value;
    const password = document.getElementById('password').value;

    const hashedPassword = await hashPassword(password);

    try {
        const response = await fetch('/api/login', {
            method: 'POST',
            body: JSON.stringify({ username, hashedPassword }),
            headers: { 'Content-Type': 'application/json' }
        });

        const data = await response.json();
        if (response.ok) {
            localStorage.setItem('token', data.token);
            document.getElementById('login-register-form').style.display = 'none';
            document.getElementById('selection-container').style.display = 'block';
        } else {
            document.getElementById('error-message').innerText = data.message;
        }
    } catch (error) {
        console.error("Login error:", error);
    }
}

// show chat name
function showChatNaming() {
    document.getElementById('selection-container').style.display = 'none';
    document.getElementById('chat-naming-container').style.display = 'block';
}

// start new chat
async function startChat() {
    const chatName = document.getElementById('chat-name').value.trim();
    if (!chatName) return alert("Chat name cannot be empty!");

    currentChatName = chatName;
    document.getElementById('chat-box').innerHTML = "";

    const response = await fetch('/api/start_chat', {
        method: 'POST',
        body: JSON.stringify({ chat_name: chatName }),
        headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${localStorage.getItem('token')}`
        }
    });

    const data = await response.json();
    if (response.ok) {
        document.getElementById('chat-title').innerText = `Chat: ${chatName}`;
        document.getElementById('chat-naming-container').style.display = 'none';
        document.getElementById('chat-container').style.display = 'block';
        fetchChatHistory(chatName);
    } else {
        alert(data.message);
    }
}

// get historical chat name
async function fetchChatHistoryList() {
    try {
        const response = await fetch('/api/chat_list', {
            method: 'GET',
            headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` }
        });

        const data = await response.json();
        if (response.ok) {
            document.getElementById('selection-container').style.display = 'none';
            document.getElementById('history-container').style.display = 'block';

            const historyList = document.getElementById('history-list');
            historyList.innerHTML = '';

            data.chats.forEach(chat => {
                const li = document.createElement('li');
                li.innerHTML = `<a href="#" onclick="resumeChat('${chat}')">${chat}</a>`;
                historyList.appendChild(li);
            });
        } else {
            alert(data.message);
        }
    } catch (error) {
        console.error("Error fetching chat history:", error);
    }
}

// get conversation history
async function fetchChatHistory(chatName) {
    try {
        const response = await fetch(`/api/chat_history?chat_name=${encodeURIComponent(chatName)}`, {
            method: 'GET',
            headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` }
        });

        const data = await response.json();
        console.log("[DEBUG] Chat history:", data);

        if (response.ok && data.messages) {
            const chatBox = document.getElementById('chat-box');
            chatBox.innerHTML = "";

            data.messages.forEach(msg => {
                const sender = msg.role || "Unknown"; 
                const message = msg.content || "[Empty Message]";
                updateChatBox(sender, message);
            });
        } else {
            alert(data.message);
        }
    } catch (error) {
        console.error("Error fetching chat history:", error);
    }
}


// send message and get response 
async function sendMessage() {
    const message = document.getElementById('message').value.trim();
    if (!message) return;

    // show user's latest message
    updateChatBox('User', message);
    // clear input box
    document.getElementById('message').value = '';

    try {
        const response = await fetch('/api/send_message', {
            method: 'POST',
            body: JSON.stringify({ message, chat_name: currentChatName }),
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${localStorage.getItem('token')}`
            }
        });

        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let done = false;
        let assistantMessage = '';

        // show deepseek's message
        updateChatBox('DeepSeek', '');

        while (!done) {
            const { value, done: readerDone } = await reader.read();
            done = readerDone;
            if (value) {
                // update chunk content
                const chunk = decoder.decode(value, { stream: true });
                console.log("[DEBUG] chunk in front-end:", chunk);

                // add chunk to assistantMessage
                assistantMessage += chunk;

                updateLastChatBubble('DeepSeek', assistantMessage);
            }
        }

    } catch (error) {
        console.error("Send message error:", error);
    }
}

function mapRoleToDisplayName(role) {
    if (role === 'assistant') return 'DeepSeek';
    if (role === 'user') return 'User';
    return 'unidentified';
}
// update chatbox
function updateChatBox(sender, message) {
    const chatBox = document.getElementById('chat-box');
    const messageDiv = document.createElement('div');

    messageDiv.classList.add('chat-message', sender.toLowerCase() === 'user' ? 'user' : 'assistant');

    messageDiv.innerHTML = `<p><strong>${sender}:</strong> ${message}</p>`;

    chatBox.appendChild(messageDiv);

    MathJax.typesetPromise();

    chatBox.scrollTop = chatBox.scrollHeight;
}



// Update only the text of the "last line" specified sender
function updateLastChatBubble(sender, newContent) {
    const chatBox = document.getElementById('chat-box');
    const paragraphs = chatBox.getElementsByTagName('p');

    // 从后往前找，匹配 “sender:”
    for (let i = paragraphs.length - 1; i >= 0; i--) {
        const p = paragraphs[i];
        if (p.textContent.startsWith(`${sender}:`)) {
            // 找到最后一个同样sender的行，更新其内容
            p.innerHTML = `<strong>${sender}:</strong> ${newContent}`;
            MathJax.typesetPromise();
            return;
        }
    }
}

// continue history conversation
function resumeChat(chatName) {
    currentChatName = chatName;
    document.getElementById('history-container').style.display = 'none';
    document.getElementById('chat-title').innerText = `Chat: ${chatName}`;
    document.getElementById('chat-container').style.display = 'block';

    document.getElementById('chat-box').innerHTML = "";
    fetchChatHistory(chatName);
}

// go back to menu
function returnToSelection() {
    document.getElementById('chat-container').style.display = 'none';
    document.getElementById('history-container').style.display = 'none';
    document.getElementById('selection-container').style.display = 'block';
}

// go back to chat name interface
function goBack() {
    document.getElementById('chat-naming-container').style.display = 'none';
    document.getElementById('selection-container').style.display = 'block';
}

// log out
function logoutUser() {
    localStorage.removeItem('token');
    document.getElementById('selection-container').style.display = 'none';
    document.getElementById('login-register-form').style.display = 'block';
}