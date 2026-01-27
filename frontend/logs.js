/**
 * YTClipper Log Viewer
 * Live streaming log viewer with auto-scroll like GitHub workflow logs
 */

let ws = null;
let autoScroll = true;
let lineCount = 0;

const logViewer = document.getElementById('logViewer');
const statusIndicator = document.getElementById('statusIndicator');
const statusDot = statusIndicator.querySelector('.status-dot');
const statusText = statusIndicator.querySelector('.status-text');
const lineCountEl = document.getElementById('lineCount');
const backBtn = document.getElementById('backBtn');
const clearBtn = document.getElementById('clearBtn');
const scrollBtn = document.getElementById('scrollBtn');

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    connectWebSocket();
    setupEventListeners();
    showEmptyState();
});

function setupEventListeners() {
    // Back button
    backBtn.addEventListener('click', () => {
        window.location.href = '/';
    });

    // Footer toolbar back to home button (desktop)
    const backToHomeBtn = document.getElementById('backToHomeBtn');
    if (backToHomeBtn) {
        backToHomeBtn.addEventListener('click', () => {
            window.location.href = '/';
        });
    }

    // Clear display button
    clearBtn.addEventListener('click', () => {
        logViewer.innerHTML = '';
        lineCount = 0;
        updateLineCount();
        showEmptyState();
    });

    // Auto-scroll toggle
    scrollBtn.addEventListener('click', () => {
        autoScroll = !autoScroll;
        scrollBtn.title = autoScroll ? 'Auto-scroll: ON' : 'Auto-scroll: OFF';
        scrollBtn.style.opacity = autoScroll ? '1' : '0.5';
        if (autoScroll) {
            scrollToBottom();
        }
    });

    // Detect manual scroll
    logViewer.addEventListener('scroll', () => {
        const isAtBottom = logViewer.scrollHeight - logViewer.scrollTop <= logViewer.clientHeight + 100;
        if (!isAtBottom && autoScroll) {
            // User scrolled up, disable auto-scroll
            autoScroll = false;
            scrollBtn.style.opacity = '0.5';
            scrollBtn.title = 'Auto-scroll: OFF';
        }
    });
}

function connectWebSocket() {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/ws/logs`;

    updateStatus('connecting', 'Connecting...');

    ws = new WebSocket(wsUrl);

    ws.onopen = () => {
        console.log('WebSocket connected');
        updateStatus('connected', 'Connected');
    };

    ws.onmessage = (event) => {
        try {
            const data = JSON.parse(event.data);
            if (data.line) {
                addLogLine(data.line, data.type === 'new');
            }
        } catch (error) {
            console.error('Error parsing WebSocket message:', error);
        }
    };

    ws.onerror = (error) => {
        console.error('WebSocket error:', error);
        updateStatus('disconnected', 'Connection error');
    };

    ws.onclose = () => {
        console.log('WebSocket closed');
        updateStatus('disconnected', 'Disconnected');

        // Attempt reconnection after 3 seconds
        setTimeout(() => {
            if (ws.readyState === WebSocket.CLOSED) {
                connectWebSocket();
            }
        }, 3000);
    };
}

function addLogLine(line, isNew = false) {
    // Remove empty state if it exists
    const emptyState = logViewer.querySelector('.empty-state');
    if (emptyState) {
        emptyState.remove();
    }

    const logLine = document.createElement('div');
    logLine.className = 'log-line';

    // Detect log level from the line
    const level = detectLogLevel(line);
    if (level) {
        logLine.classList.add(level);
    }

    // Add new animation for live logs
    if (isNew) {
        logLine.classList.add('new');
    }

    logLine.textContent = line;
    logViewer.appendChild(logLine);

    lineCount++;
    updateLineCount();

    // Auto-scroll to bottom if enabled
    if (autoScroll) {
        scrollToBottom();
    }
}

function detectLogLevel(line) {
    const lowerLine = line.toLowerCase();

    // Check for emoji indicators
    if (line.includes('✅') || lowerLine.includes('success')) return 'success';
    if (line.includes('❌') || lowerLine.includes('error') || lowerLine.includes('critical')) return 'error';
    if (line.includes('⚠️') || lowerLine.includes('warning')) return 'warning';
    if (line.includes('ℹ️') || lowerLine.includes('info')) return 'info';
    if (line.includes('🔍') || lowerLine.includes('debug')) return 'debug';

    // Check for log level keywords
    if (lowerLine.includes(' error:') || lowerLine.includes(' critical:')) return 'error';
    if (lowerLine.includes(' warning:')) return 'warning';
    if (lowerLine.includes(' info:')) return 'info';
    if (lowerLine.includes(' debug:')) return 'debug';

    return null;
}

function scrollToBottom() {
    logViewer.scrollTop = logViewer.scrollHeight;
}

function updateStatus(state, text) {
    statusDot.className = `status-dot ${state}`;
    statusText.textContent = text;
}

function updateLineCount() {
    lineCountEl.textContent = `${lineCount.toLocaleString()} lines`;
}

function showEmptyState() {
    if (lineCount === 0) {
        logViewer.innerHTML = `
            <div class="empty-state">
                <div class="empty-state-icon">📜</div>
                <div class="empty-state-text">Waiting for logs...</div>
            </div>
        `;
    }
}

// Cleanup on page unload
window.addEventListener('beforeunload', () => {
    if (ws) {
        ws.close();
    }
});
