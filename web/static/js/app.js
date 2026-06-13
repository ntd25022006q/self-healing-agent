let currentTab = 'impl';
let implCode = '// Chưa có code sinh ra.';
let testCode = '// Chưa có test suite sinh ra.';
let socket = null;

// Load initial data on page load
window.addEventListener('DOMContentLoaded', () => {
    fetchExperiences();
    fetchScore();
    connectWebSocket();
});

function fetchExperiences() {
    fetch(`/api/experiences?token=${window.SESSION_TOKEN}`)
        .then(res => res.json())
        .then(data => {
            const list = document.getElementById('experience-list');
            if (data.length === 0) {
                list.innerHTML = '<div class="exp-item empty">Chưa có bài học kinh nghiệm nào được lưu trữ.</div>';
                return;
            }
            
            list.innerHTML = '';
            data.forEach(exp => {
                const item = document.createElement('div');
                item.className = 'exp-item';
                item.innerHTML = `
                    <strong>Yêu cầu:</strong> ${exp.task_description}<br>
                    <strong>Trạng thái:</strong> <span style="color:#10b981">Đã kiểm chứng thành công</span><br>
                    <pre style="background:rgba(0,0,0,0.3); padding:8px; margin-top:5px; border-radius:6px; font-family: monospace; font-size: 11px; max-height:100px; overflow:auto;">${exp.fix_code}</pre>
                `;
                list.appendChild(item);
            });
        })
        .catch(err => console.error("Error fetching experiences:", err));
}

function fetchScore() {
    fetch(`/api/score?token=${window.SESSION_TOKEN}`)
        .then(res => res.json())
        .then(data => {
            document.getElementById('agent-score').innerText = data.score;
        });
}

function connectWebSocket() {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/ws?token=${window.SESSION_TOKEN}`;
    
    socket = new WebSocket(wsUrl);
    
    socket.onmessage = function(event) {
        const data = jsonParse(event.data);
        if (!data) return;
        
        if (data.type === 'log') {
            appendLog(data.message, data.level);
        } else if (data.type === 'code') {
            implCode = data.impl_code || '// Rỗng';
            testCode = data.test_code || '// Rỗng';
            updateCodeViewer();
            fetchExperiences(); // Refresh experiences DB list
        } else if (data.type === 'score') {
            document.getElementById('agent-score').innerText = data.score;
        }
    };
    
    socket.onclose = function() {
        appendLog('Mất kết nối với máy chủ Localhost. Thử kết nối lại...', 'error');
        setTimeout(connectWebSocket, 3000);
    };
}

function jsonParse(str) {
    try {
        return JSON.parse(str);
    } catch (e) {
        return null;
    }
}

function appendLog(message, level = 'system') {
    const term = document.getElementById('logs-terminal');
    const line = document.createElement('div');
    line.className = `log-line ${level}`;
    
    // Add prefix timestamp
    const now = new Date().toLocaleTimeString();
    line.innerText = `[${now}] ${message}`;
    term.appendChild(line);
    
    // Auto scroll to bottom
    term.scrollTop = term.scrollHeight;
}

function startAgent() {
    const input = document.getElementById('prompt-input');
    const prompt = input.value.strip ? input.value.strip() : input.value.trim();
    
    if (!prompt) {
        alert("Vui lòng nhập yêu cầu lập trình trước khi chạy!");
        return;
    }
    
    appendLog(`Gửi lệnh lập trình: "${prompt}"`, 'system');
    
    if (socket && socket.readyState === WebSocket.OPEN) {
        socket.send(JSON.stringify({
            action: 'run_task',
            prompt: prompt
        }));
    } else {
        appendLog('Lỗi: Cổng kết nối WebSocket chưa sẵn sàng!', 'error');
    }
}

function switchTab(tab) {
    currentTab = tab;
    document.querySelectorAll('.tab-btn').forEach(btn => btn.classList.remove('active'));
    
    if (tab === 'impl') {
        document.querySelector('.tab-btn:nth-child(1)').classList.add('active');
    } else {
        document.querySelector('.tab-btn:nth-child(2)').classList.add('active');
    }
    
    updateCodeViewer();
}

function updateCodeViewer() {
    const viewer = document.getElementById('code-viewer');
    if (currentTab === 'impl') {
        viewer.textContent = implCode;
    } else {
        viewer.textContent = testCode;
    }
}
