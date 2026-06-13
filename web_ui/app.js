// Global State
let sessionId = localStorage.getItem('sessionId') || null;
let currentUser = JSON.parse(localStorage.getItem('currentUser')) || null;
let currentRoom = localStorage.getItem('currentRoom') || null;
let currentPmUser = null;
let isRegistering = false;

// DOM Elements
const views = {
    auth: document.getElementById('view-auth'),
    dashboard: document.getElementById('view-dashboard'),
    room: document.getElementById('view-room'),
};

const UI = {
    navUserInfo: document.getElementById('nav-user-info'),
    navUsername: document.getElementById('nav-username'),
    listOnlineUsers: document.getElementById('list-online-users'),
    listRooms: document.getElementById('list-rooms'),
    pmView: document.getElementById('pm-view'),
    pmHistory: document.getElementById('pm-history'),
    pmTitle: document.getElementById('pm-title'),
    roomChatHistory: document.getElementById('room-chat-history'),
    roomTitle: document.getElementById('room-title'),
    toastContainer: document.getElementById('toast-container'),
    modalCreateRoom: document.getElementById('modal-create-room'),
    modalRoomFiles: document.getElementById('modal-room-files'),
    listRoomFiles: document.getElementById('list-room-files'),
};

// --- Utilities ---
function showView(viewName) {
    Object.values(views).forEach(v => v.classList.add('hidden'));
    views[viewName].classList.remove('hidden');
    if (viewName !== 'auth') {
        UI.navUserInfo.classList.remove('hidden');
    } else {
        UI.navUserInfo.classList.add('hidden');
    }
}

// Check session on load
window.addEventListener('DOMContentLoaded', () => {
    if (sessionId && currentUser) {
        UI.navUsername.textContent = currentUser.display_name;
        if (currentRoom) {
            joinRoom(currentRoom);
        } else {
            showView('dashboard');
            refreshDashboard();
        }
        startPolling();
    }
});

function showToast(message, type = 'info') {
    const toast = document.createElement('div');
    const color = type === 'error' ? 'bg-red-500' : (type === 'success' ? 'bg-green-500' : 'bg-primary');
    toast.className = `${color} text-white px-4 py-2 rounded shadow-lg text-sm mb-2 opacity-0 transition-opacity duration-300`;
    toast.textContent = message;
    UI.toastContainer.appendChild(toast);
    
    setTimeout(() => toast.classList.remove('opacity-0'), 10);
    setTimeout(() => {
        toast.classList.add('opacity-0');
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}

function formatBytes(bytes, decimals = 2) {
    if (!+bytes) return '0 Bytes';
    const k = 1024;
    const dm = decimals < 0 ? 0 : decimals;
    const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB', 'PB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return `${parseFloat((bytes / Math.pow(k, i)).toFixed(dm))} ${sizes[i]}`;
}

// --- API Client ---
async function apiCall(path, method = 'GET', body = null) {
    const headers = {};
    if (body instanceof FormData) {
        // browser sets content type and boundary automatically
    } else {
        headers['Content-Type'] = 'application/json';
    }
    if (sessionId) headers['Session-Id'] = sessionId;
    
    const options = { method, headers };
    if (body) {
        options.body = body instanceof FormData ? body : JSON.stringify(body);
    }
    
    try {
        const res = await fetch(`/api${path}`, options);
        if (res.status === 401) {
            document.getElementById('btn-logout').click();
            throw new Error('Session expired');
        }
        if (res.headers.get('content-type')?.includes('application/json')) {
            const data = await res.json();
            if (!res.ok) throw new Error(data.error || 'API Error');
            return data;
        } else {
            if (!res.ok) throw new Error('API Error');
            return res.blob();
        }
    } catch (err) {
        if (err.message !== 'Session expired') {
            showToast(err.message, 'error');
        }
        throw err;
    }
}

// ... auth and dashboard unchanged ...
// To save space I will re-implement the DOM bindings below keeping the rest identical

// --- Auth Flow ---
document.getElementById('link-toggle-auth').addEventListener('click', (e) => {
    e.preventDefault();
    isRegistering = !isRegistering;
    document.getElementById('auth-title').textContent = isRegistering ? 'Register' : 'Login';
    document.getElementById('btn-auth-submit').textContent = isRegistering ? 'Register' : 'Login';
    document.getElementById('auth-display-name-group').classList.toggle('hidden', !isRegistering);
    e.target.textContent = isRegistering ? 'Already have an account? Login' : 'Need an account? Register';
});

document.getElementById('auth-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    const username = document.getElementById('auth-username').value;
    const password = document.getElementById('auth-password').value;
    const display_name = document.getElementById('auth-display-name').value || username;
    
    if (isRegistering) {
        try {
            await apiCall('/register', 'POST', { username, password, display_name });
            showToast('Registration successful! Please login.', 'success');
            document.getElementById('link-toggle-auth').click(); // Switch to login
        } catch (e) {}
    } else {
        try {
            const data = await apiCall('/login', 'POST', { username, password });
            sessionId = data.session_id;
            currentUser = data.user;
            localStorage.setItem('sessionId', sessionId);
            localStorage.setItem('currentUser', JSON.stringify(currentUser));
            UI.navUsername.textContent = currentUser.display_name;
            showView('dashboard');
            startPolling();
            refreshDashboard();
        } catch (e) {}
    }
});

document.getElementById('btn-logout').addEventListener('click', () => {
    sessionId = null;
    currentUser = null;
    currentRoom = null;
    localStorage.removeItem('sessionId');
    localStorage.removeItem('currentUser');
    localStorage.removeItem('currentRoom');
    showView('auth');
});

// --- Dashboard Flow ---
let dashboardRefreshInterval = null;

async function refreshDashboard() {
    if (!views.dashboard.classList.contains('hidden')) {
        try {
            const [usersData, roomsData] = await Promise.all([
                apiCall('/users'),
                apiCall('/rooms')
            ]);
            
            UI.listOnlineUsers.innerHTML = '';
            usersData.users.forEach(u => {
                if (u.username === currentUser.username) return;
                const div = document.createElement('div');
                div.className = 'flex items-center justify-between p-2 hover:bg-gray-800 rounded cursor-pointer transition-colors group';
                div.innerHTML = `
                    <div class="flex items-center">
                        <div class="w-2 h-2 rounded-full bg-green-500 mr-2"></div>
                        <span class="text-sm">${u.username}</span>
                    </div>
                    <button class="opacity-0 group-hover:opacity-100 text-xs bg-primary hover:bg-secondary px-2 py-1 rounded transition-all">Chat</button>
                `;
                div.addEventListener('click', () => openPM(u.username));
                UI.listOnlineUsers.appendChild(div);
            });

            UI.listRooms.innerHTML = '';
            roomsData.rooms.forEach(r => {
                const div = document.createElement('div');
                div.className = 'bg-dark p-4 rounded border border-gray-800 hover:border-gray-600 transition-colors flex flex-col justify-between';
                div.innerHTML = `
                    <div>
                        <h4 class="font-semibold text-primary mb-1">${r.name}</h4>
                        <p class="text-xs text-gray-500 mb-2">${r.description || 'No description'}</p>
                    </div>
                    <div class="flex justify-between items-end mt-2">
                        <span class="text-xs text-gray-600">${r.members || 0} active</span>
                        <button class="bg-gray-800 hover:bg-gray-700 text-xs px-3 py-1 rounded transition-colors" onclick="joinRoom('${r.name}')">Join</button>
                    </div>
                `;
                UI.listRooms.appendChild(div);
            });
        } catch (e) {}
    }
}

// Auto refresh dashboard every 10 seconds
setInterval(refreshDashboard, 10000);

document.getElementById('btn-refresh-users').addEventListener('click', refreshDashboard);

// --- PM Flow ---
async function openPM(username) {
    currentPmUser = username;
    UI.pmTitle.textContent = `Chat with ${username}`;
    UI.pmView.classList.remove('hidden');
    UI.pmHistory.innerHTML = '<div class="text-center text-gray-500 text-sm mt-4">Loading history...</div>';
    
    try {
        const data = await apiCall(`/pm/history?other_username=${username}`);
        UI.pmHistory.innerHTML = '';
        data.messages.forEach(msg => appendMessage(UI.pmHistory, msg.sender_username, msg.content, msg.timestamp));
        UI.pmHistory.scrollTop = UI.pmHistory.scrollHeight;
    } catch(e) {}
}

document.getElementById('btn-close-pm').addEventListener('click', () => {
    UI.pmView.classList.add('hidden');
    currentPmUser = null;
});

document.getElementById('pm-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    const input = document.getElementById('pm-input');
    const content = input.value.trim();
    if (!content || !currentPmUser) return;
    
    input.value = '';
    appendMessage(UI.pmHistory, currentUser.username, content, new Date().toLocaleTimeString());
    
    try {
        await apiCall('/pm', 'POST', { recipient_username: currentPmUser, content });
    } catch(e) {}
});

// --- Room Flow ---
document.getElementById('btn-create-room').addEventListener('click', () => {
    UI.modalCreateRoom.classList.remove('hidden');
});

document.getElementById('btn-cancel-create-room').addEventListener('click', () => {
    UI.modalCreateRoom.classList.add('hidden');
});

document.getElementById('form-create-room').addEventListener('submit', async (e) => {
    e.preventDefault();
    const room_name = document.getElementById('new-room-name').value.trim();
    const description = document.getElementById('new-room-desc').value.trim();
    if(!room_name) return;
    
    try {
        await apiCall('/rooms', 'POST', { room_name, description });
        UI.modalCreateRoom.classList.add('hidden');
        showToast('Room created!', 'success');
        refreshDashboard();
    } catch(e) {}
});

window.joinRoom = async function(roomName) {
    try {
        await apiCall('/rooms/join', 'POST', { room_name: roomName });
        currentRoom = roomName;
        localStorage.setItem('currentRoom', roomName);
        UI.roomTitle.textContent = roomName;
        showView('room');
        UI.roomChatHistory.innerHTML = '<div class="text-center text-gray-500 text-sm mt-4">Loading history...</div>';
        
        const data = await apiCall(`/rooms/messages?room_name=${roomName}`);
        UI.roomChatHistory.innerHTML = '';
        data.messages.forEach(msg => appendMessage(UI.roomChatHistory, msg.sender_username, msg.message, msg.timestamp, msg.message_type));
        UI.roomChatHistory.scrollTop = UI.roomChatHistory.scrollHeight;
    } catch(e) {}
}

document.getElementById('btn-leave-room').addEventListener('click', async () => {
    try {
        await apiCall('/rooms/leave', 'POST');
        currentRoom = null;
        localStorage.removeItem('currentRoom');
        showView('dashboard');
        refreshDashboard();
    } catch(e) {}
});

document.getElementById('room-chat-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    const input = document.getElementById('room-chat-input');
    const message = input.value.trim();
    if (!message || !currentRoom) return;
    
    input.value = '';
    
    try {
        await apiCall('/rooms/messages', 'POST', { room_name: currentRoom, message });
    } catch(e) {}
});

document.getElementById('btn-chat-attach').addEventListener('click', () => {
    document.getElementById('chat-file-input').click();
});

document.getElementById('chat-file-input').addEventListener('change', async (e) => {
    if (!currentRoom) return;
    if (e.target.files.length === 0) return;
    
    const file = e.target.files[0];
    e.target.value = '';
    
    showToast(`Uploading ${file.name}...`);
    try {
        const buffer = await file.arrayBuffer();
        const headers = {
            'Session-Id': sessionId,
            'Content-Type': 'application/octet-stream'
        };
        const res = await fetch(`/api/rooms/files/upload?room_name=${encodeURIComponent(currentRoom)}&filename=${encodeURIComponent(file.name)}`, {
            method: 'POST',
            headers,
            body: buffer
        });
        
        const data = await res.json();
        if (!res.ok) throw new Error(data.error || 'Upload failed');
    } catch(err) {
        showToast(err.message, 'error');
    }
});

// --- Room Files Flow ---
document.getElementById('btn-room-files').addEventListener('click', async () => {
    if (!currentRoom) return;
    UI.modalRoomFiles.classList.remove('hidden');
    UI.listRoomFiles.innerHTML = '<div class="text-center text-sm text-gray-500 py-4">Loading files...</div>';
    
    try {
        const data = await apiCall(`/rooms/files?room_name=${encodeURIComponent(currentRoom)}`);
        UI.listRoomFiles.innerHTML = '';
        if (data.files.length === 0) {
            UI.listRoomFiles.innerHTML = '<div class="text-center text-sm text-gray-500 py-4">No files in this room.</div>';
        }
        data.files.forEach(f => {
            const div = document.createElement('div');
            div.className = 'flex justify-between items-center p-2 hover:bg-gray-800 rounded transition-colors';
            div.innerHTML = `
                <div class="flex flex-col truncate pr-2">
                    <span class="text-sm font-medium truncate">${f.original_filename}</span>
                    <span class="text-xs text-gray-500">${formatBytes(f.size_bytes)} • by ${f.uploader_username}</span>
                </div>
                <button class="bg-secondary hover:bg-primary text-xs px-3 py-1 rounded transition-colors" onclick="downloadFile(${f.file_id}, '${f.original_filename.replace(/'/g, "\\'")}')">Download</button>
            `;
            UI.listRoomFiles.appendChild(div);
        });
    } catch(e) {}
});

document.getElementById('btn-close-files').addEventListener('click', () => {
    UI.modalRoomFiles.classList.add('hidden');
});

document.getElementById('form-upload-file').addEventListener('submit', async (e) => {
    e.preventDefault();
    if (!currentRoom) return;
    
    const fileInput = document.getElementById('file-input');
    if (fileInput.files.length === 0) return;
    
    const file = fileInput.files[0];
    const btnSubmit = e.target.querySelector('button[type="submit"]');
    
    try {
        btnSubmit.textContent = 'Uploading...';
        btnSubmit.disabled = true;
        btnSubmit.classList.add('opacity-50');
        
        // We will read the file as an array buffer and send it as raw binary body
        const buffer = await file.arrayBuffer();
        
        // Use standard fetch directly to send raw ArrayBuffer easily
        const headers = {
            'Session-Id': sessionId,
            'Content-Type': 'application/octet-stream' // doesn't matter much to our custom server
        };
        const res = await fetch(`/api/rooms/files/upload?room_name=${encodeURIComponent(currentRoom)}&filename=${encodeURIComponent(file.name)}`, {
            method: 'POST',
            headers,
            body: buffer
        });
        
        const data = await res.json();
        if (!res.ok) throw new Error(data.error || 'Upload failed');
        
        showToast('File uploaded successfully!', 'success');
        fileInput.value = '';
        
        // Refresh list
        document.getElementById('btn-room-files').click();
    } catch(e) {
        showToast(e.message, 'error');
    } finally {
        btnSubmit.textContent = 'Upload';
        btnSubmit.disabled = false;
        btnSubmit.classList.remove('opacity-50');
    }
});

window.downloadFile = async function(fileId, filename) {
    showToast(`Starting download for ${filename}...`);
    try {
        const blob = await apiCall(`/rooms/files/download?file_id=${fileId}`);
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        a.remove();
        window.URL.revokeObjectURL(url);
    } catch (e) {}
}

function appendMessage(container, sender, text, time, type = 'text') {
    if (type === 'system') {
        appendSystemMessage(container, text);
        return;
    }
    
    const isMe = sender === currentUser.username;
    const div = document.createElement('div');
    div.className = `flex flex-col ${isMe ? 'items-end' : 'items-start'} mb-2`;
    
    let contentHtml = text;
    if (type === 'file') {
        try {
            const fileData = JSON.parse(text);
            contentHtml = `
                <div class="flex items-center gap-3 p-2 bg-black/20 rounded cursor-pointer hover:bg-black/30 transition-colors" onclick="downloadFile(${fileData.file_id}, '${fileData.filename.replace(/'/g, "\\'")}')">
                    <svg class="w-8 h-8 text-white shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"></path></svg>
                    <div class="flex flex-col text-sm truncate">
                        <span class="font-medium truncate underline">${fileData.filename}</span>
                        <span class="text-xs opacity-75">${formatBytes(fileData.size_bytes)} • Click to download</span>
                    </div>
                </div>
            `;
        } catch(e) {
            contentHtml = 'Invalid file data';
        }
    }

    div.innerHTML = `
        <span class="text-xs text-gray-500 mb-1 px-1">${sender} • ${time}</span>
        <div class="px-4 py-2 rounded-lg max-w-[80%] ${isMe ? 'bg-primary text-white rounded-br-none' : 'bg-gray-800 text-gray-200 rounded-bl-none'} break-words overflow-hidden">
            ${contentHtml}
        </div>
    `;
    container.appendChild(div);
    container.scrollTop = container.scrollHeight;
}

function appendSystemMessage(container, text) {
    const div = document.createElement('div');
    div.className = `flex justify-center mb-2`;
    div.innerHTML = `
        <div class="px-3 py-1 rounded-full bg-gray-800/50 text-gray-500 text-xs">
            ${text}
        </div>
    `;
    container.appendChild(div);
    container.scrollTop = container.scrollHeight;
}

// --- Event Polling ---
async function startPolling() {
    if (!sessionId) return;
    try {
        const res = await fetch(`/api/events?session_id=${sessionId}`);
        if (res.ok) {
            const data = await res.json();
            if (data.events) {
                data.events.forEach(handleEvent);
            }
        }
    } catch (e) {
        console.error("Polling error", e);
        await new Promise(r => setTimeout(r, 2000));
    }
    startPolling();
}

function handleEvent(ev) {
    console.log("Event:", ev);
    if (ev.type === "PM_RECEIVED") {
        const { sender_username, content, timestamp } = ev.payload;
        if (currentPmUser === sender_username && !UI.pmView.classList.contains('hidden')) {
            appendMessage(UI.pmHistory, sender_username, content, timestamp);
        } else {
            showToast(`New PM from ${sender_username}: ${content}`);
        }
    } else if (ev.type === "ROOM_MESSAGE") {
        const { sender_username, message, timestamp, message_type } = ev.payload;
        if (currentRoom) {
            appendMessage(UI.roomChatHistory, sender_username, message, timestamp, message_type || 'text');
        }
    } else if (ev.type === "SYSTEM_EVENT") {
        if (currentRoom) {
            // Already saved in DB on backend, so we could treat it as a room message,
            // but the SYSTEM_EVENT packet might come before ROOM_HISTORY on refresh.
            // Still safe to just append it.
            appendSystemMessage(UI.roomChatHistory, ev.payload.message);
        }
    } else if (ev.type === "DISCONNECTED") {
        showToast(`Disconnected from ${ev.server}`, 'error');
        if (ev.server === 'gateway') {
            document.getElementById('btn-logout').click();
        }
    } else if (ev.type === "ERROR") {
        showToast(ev.message, 'error');
    }
}
