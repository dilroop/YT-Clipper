// YTClipper - Mobile-First JavaScript

// State
let currentVideoData = null;
let selectedFormat = 'reels';
let analyzedClips = null;
let selectedClipIndices = [];

// DOM Elements
const urlInput = document.getElementById('urlInput');
const clearBtn = document.getElementById('clearBtn');
const loadingIndicator = document.getElementById('loadingIndicator');
const previewSection = document.getElementById('previewSection');
const thumbnail = document.getElementById('thumbnail');
const videoTitle = document.getElementById('videoTitle');
const channelName = document.getElementById('channelName');
const videoDuration = document.getElementById('videoDuration');
const formatBtns = document.querySelectorAll('.format-btn');
const burnCaptionsToggle = document.getElementById('burnCaptionsToggle');
const progressSection = document.getElementById('progressSection');
const progressFill = document.getElementById('progressFill');
const progressText = document.getElementById('progressText');
const cancelBtn = document.getElementById('cancelBtn');
const resultsSection = document.getElementById('resultsSection');
const galleryBtn = document.getElementById('galleryBtn');
const settingsBtn = document.getElementById('settingsBtn');
const settingsModal = document.getElementById('settingsModal');
const closeModal = document.getElementById('closeModal');
const saveSettings = document.getElementById('saveSettings');
const historyBtn = document.getElementById('historyBtn');
const historyModal = document.getElementById('historyModal');
const closeHistoryModal = document.getElementById('closeHistoryModal');
const historyList = document.getElementById('historyList');
const emptyHistory = document.getElementById('emptyHistory');
const clearHistoryBtn = document.getElementById('clearHistoryBtn');
const autoCreateBtn = document.getElementById('autoCreateBtn');
const manualChooseBtn = document.getElementById('manualChooseBtn');
const clipSelectionSection = document.getElementById('clipSelectionSection');
const clipsList = document.getElementById('clipsList');
const generateBtn = document.getElementById('generateBtn');

// Settings sliders
const fontSizeSlider = document.getElementById('fontSize');
const fontSizeValue = document.getElementById('fontSizeValue');
const verticalPosSlider = document.getElementById('verticalPosition');
const verticalPosValue = document.getElementById('verticalPosValue');

// Utility Functions
function formatDuration(seconds) {
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    const secs = Math.floor(seconds % 60);

    if (hours > 0) {
        return `${hours}:${minutes.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
    }
    return `${minutes}:${secs.toString().padStart(2, '0')}`;
}

function showElement(element) {
    element.style.display = 'block';
}

function hideElement(element) {
    element.style.display = 'none';
}

// Event Listeners
urlInput.addEventListener('input', (e) => {
    const value = e.target.value.trim();

    // Show/hide clear button
    if (value) {
        clearBtn.classList.add('visible');
    } else {
        clearBtn.classList.remove('visible');
    }
});

urlInput.addEventListener('paste', async (e) => {
    // Wait for paste to complete
    setTimeout(async () => {
        const url = urlInput.value.trim();
        if (url) {
            await fetchThumbnail(url);
        }
    }, 100);
});

clearBtn.addEventListener('click', () => {
    urlInput.value = '';
    clearBtn.classList.remove('visible');
    hideElement(loadingIndicator);
    hideElement(previewSection);
    hideElement(progressSection);
    hideElement(resultsSection);
    currentVideoData = null;
});

// Format selection
formatBtns.forEach(btn => {
    btn.addEventListener('click', () => {
        formatBtns.forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        selectedFormat = btn.dataset.format;
    });
});

// Auto Create button (original workflow)
autoCreateBtn.addEventListener('click', async () => {
    if (!currentVideoData) return;
    await processVideo();
});

// Manual Choose button
manualChooseBtn.addEventListener('click', async () => {
    if (!currentVideoData) return;
    await analyzeAndShowClips();
});

// Generate button (for selected clips)
generateBtn.addEventListener('click', async () => {
    await generateSelectedClips();
});

// Cancel button
cancelBtn.addEventListener('click', () => {
    if (confirm('Are you sure you want to cancel processing?')) {
        cancelProcessing();
    }
});

// Gallery button
galleryBtn.addEventListener('click', () => {
    window.location.href = '/gallery.html';
});

// Settings modal
settingsBtn.addEventListener('click', () => {
    showElement(settingsModal);
    loadSettings();
});

closeModal.addEventListener('click', () => {
    hideElement(settingsModal);
});

settingsModal.addEventListener('click', (e) => {
    if (e.target === settingsModal) {
        hideElement(settingsModal);
    }
});

saveSettings.addEventListener('click', async () => {
    await saveSettingsToServer();
    hideElement(settingsModal);
});

// View Logs button
const viewLogsBtn = document.getElementById('viewLogsBtn');
if (viewLogsBtn) {
    viewLogsBtn.addEventListener('click', () => {
        window.location.href = '/logs.html';
    });
}

// History modal
historyBtn.addEventListener('click', () => {
    showElement(historyModal);
    loadHistory();
});

closeHistoryModal.addEventListener('click', () => {
    hideElement(historyModal);
});

historyModal.addEventListener('click', (e) => {
    if (e.target === historyModal) {
        hideElement(historyModal);
    }
});

clearHistoryBtn.addEventListener('click', async () => {
    if (confirm('Are you sure you want to clear all history?')) {
        await clearHistoryFromServer();
        await loadHistory();
    }
});

// Settings sliders
fontSizeSlider.addEventListener('input', (e) => {
    fontSizeValue.textContent = e.target.value;
});

verticalPosSlider.addEventListener('input', (e) => {
    verticalPosValue.textContent = e.target.value;
});

// API Functions
async function fetchThumbnail(url) {
    try {
        // Show loading indicator
        showElement(loadingIndicator);
        hideElement(previewSection);

        const response = await fetch('/api/thumbnail', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ url: url }),
        });

        if (!response.ok) {
            throw new Error('Failed to fetch video information');
        }

        const data = await response.json();
        currentVideoData = data;

        // Update preview
        thumbnail.src = data.thumbnail;
        thumbnail.onerror = () => {
            thumbnail.src = data.thumbnail_fallback;
        };
        videoTitle.textContent = data.title;
        channelName.textContent = data.channel;
        videoDuration.textContent = `Duration: ${formatDuration(data.duration)}`;

        // Hide loading, show preview section
        hideElement(loadingIndicator);
        showElement(previewSection);

        // Scroll to preview
        previewSection.scrollIntoView({ behavior: 'smooth', block: 'nearest' });

    } catch (error) {
        console.error('Error fetching thumbnail:', error);
        hideElement(loadingIndicator);
        alert('Error: ' + error.message);
    }
}

let ws = null;
let isProcessing = false;

async function processVideo() {
    try {
        isProcessing = true;

        // Hide preview, show progress
        hideElement(previewSection);
        showElement(progressSection);
        hideElement(resultsSection);

        // Connect to WebSocket for real-time progress
        connectWebSocket();

        // Start processing
        updateProgress(0, 'Starting...');

        const response = await fetch('/api/process', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                url: urlInput.value.trim(),
                format: selectedFormat,
                burn_captions: burnCaptionsToggle.checked,
            }),
        });

        if (!response.ok) {
            // Extract error message from response
            const errorData = await response.json().catch(() => ({ detail: 'Failed to process video' }));
            throw new Error(errorData.detail || 'Failed to process video');
        }

        const data = await response.json();

        // Processing complete
        isProcessing = false;
        showResults(data);

    } catch (error) {
        console.error('Error processing video:', error);

        // Check for OpenAI quota error
        const errorMsg = error.message || '';
        if (errorMsg.includes('OPENAI_QUOTA_ERROR') || errorMsg.includes('Insufficient OpenAI credits')) {
            alert('⚠️ OpenAI Credits Exhausted\n\n' +
                  'Your OpenAI API credits have been exhausted or exceeded the quota.\n\n' +
                  'Please add credits to your OpenAI account at:\n' +
                  'https://platform.openai.com/account/billing\n\n' +
                  'After adding credits, try processing the video again.');
        } else {
            alert('Error: ' + error.message);
        }

        hideElement(progressSection);
        showElement(previewSection);
        isProcessing = false;
        if (ws) ws.close();
    }
}

function connectWebSocket() {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/ws`;

    ws = new WebSocket(wsUrl);

    ws.onopen = () => {
        console.log('WebSocket connected');
    };

    ws.onmessage = (event) => {
        const data = JSON.parse(event.data);

        if (data.type === 'progress') {
            const percent = data.percent || 0;
            const message = data.message || 'Processing...';
            updateProgress(percent, message);
        }
    };

    ws.onerror = (error) => {
        console.error('WebSocket error:', error);
    };

    ws.onclose = () => {
        console.log('WebSocket closed');
        ws = null;
    };
}

function cancelProcessing() {
    isProcessing = false;

    // Close WebSocket
    if (ws) {
        ws.close();
        ws = null;
    }

    // Reset UI
    hideElement(progressSection);
    hideElement(clipSelectionSection);
    showElement(previewSection);

    // Note: Server-side cleanup would need to be implemented
    // by adding a cancel endpoint that kills the processing job
    alert('Processing cancelled. Note: Downloaded files may remain in downloads folder.');
}

function updateProgress(percent, text) {
    progressFill.style.width = percent + '%';
    progressText.textContent = text;
}

function showResults(data) {
    hideElement(progressSection);
    showElement(resultsSection);

    const clipsGrid = document.getElementById('clipsGrid');

    if (data.success) {
        // Format summary if it's provided
        let summaryHtml = '';
        if (data.summary) {
            // Handle if summary is a string or object
            const summaryText = typeof data.summary === 'string'
                ? data.summary
                : JSON.stringify(data.summary, null, 2);

            summaryHtml = `
                <div style="color: var(--text-secondary); margin-top: 12px; font-size: 14px;">
                    ${summaryText}
                </div>
            `;
        }

        clipsGrid.innerHTML = `
            <div class="clip-card">
                <h4>✅ Processing Complete!</h4>
                <p style="color: var(--text-secondary); margin-bottom: 12px;">
                    Successfully processed ${data.clips_created || 0} clips!
                </p>
                <div style="color: var(--text-secondary); margin-bottom: 12px;">
                    <strong>Project Folder:</strong><br>
                    <code style="background: rgba(255,255,255,0.1); padding: 4px 8px; border-radius: 4px; font-size: 11px; display: block; margin-top: 4px; word-break: break-all; white-space: pre-wrap; overflow-wrap: anywhere;">
                        ${data.project_folder || 'N/A'}
                    </code>
                </div>
                ${summaryHtml}
            </div>
        `;
    } else {
        clipsGrid.innerHTML = `
            <div class="clip-card">
                <h4>❌ Processing Failed</h4>
                <p style="color: var(--error-color);">
                    ${data.message || 'An error occurred during processing'}
                </p>
            </div>
        `;
    }

    if (ws) ws.close();

    resultsSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

async function loadSettings() {
    try {
        const response = await fetch('/api/config');
        const config = await response.json();

        if (config.caption_settings) {
            const cs = config.caption_settings;
            document.getElementById('wordsPerCaption').value = cs.words_per_caption || 2;
            document.getElementById('fontFamily').value = cs.font_family || 'Impact';
            fontSizeSlider.value = cs.font_size || 48;
            fontSizeValue.textContent = cs.font_size || 48;
            verticalPosSlider.value = cs.vertical_position || 80;
            verticalPosValue.textContent = cs.vertical_position || 80;
        }
    } catch (error) {
        console.error('Error loading settings:', error);
    }
}

async function saveSettingsToServer() {
    try {
        const captionSettings = {
            words_per_caption: parseInt(document.getElementById('wordsPerCaption').value),
            font_family: document.getElementById('fontFamily').value,
            font_size: parseInt(fontSizeSlider.value),
            vertical_position: parseInt(verticalPosSlider.value),
        };

        const response = await fetch('/api/config', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                caption_settings: captionSettings,
            }),
        });

        if (!response.ok) {
            throw new Error('Failed to save settings');
        }

        // Settings saved silently - no alert needed

    } catch (error) {
        console.error('Error saving settings:', error);
        alert('Error saving settings: ' + error.message);
    }
}

async function loadHistory() {
    try {
        const response = await fetch('/api/history');
        const data = await response.json();

        if (data.history && data.history.length > 0) {
            historyList.innerHTML = data.history.map(item => {
                const date = new Date(item.timestamp);
                const timeAgo = formatTimeAgo(date);

                return `
                    <div class="history-item" data-url="${item.url}">
                        <img class="history-thumbnail" src="${item.thumbnail}" alt="${item.title}" onerror="this.src='${item.thumbnail}'">
                        <div class="history-info">
                            <div class="history-title">${item.title}</div>
                            <div class="history-meta">${item.channel} • ${formatDuration(item.duration)}</div>
                            <div class="history-time">${timeAgo}</div>
                        </div>
                    </div>
                `;
            }).join('');

            // Add click handlers to history items
            document.querySelectorAll('.history-item').forEach(item => {
                item.addEventListener('click', () => {
                    const url = item.dataset.url;
                    urlInput.value = url;
                    hideElement(historyModal);
                    fetchThumbnail(url);
                });
            });

            hideElement(emptyHistory);
            showElement(historyList);
        } else {
            hideElement(historyList);
            showElement(emptyHistory);
        }

    } catch (error) {
        console.error('Error loading history:', error);
        alert('Error loading history: ' + error.message);
    }
}

async function clearHistoryFromServer() {
    try {
        const response = await fetch('/api/history', {
            method: 'DELETE',
        });

        if (!response.ok) {
            throw new Error('Failed to clear history');
        }

    } catch (error) {
        console.error('Error clearing history:', error);
        alert('Error clearing history: ' + error.message);
    }
}

function formatTimeAgo(date) {
    const seconds = Math.floor((new Date() - date) / 1000);

    if (seconds < 60) return 'Just now';

    const minutes = Math.floor(seconds / 60);
    if (minutes < 60) return `${minutes}m ago`;

    const hours = Math.floor(minutes / 60);
    if (hours < 24) return `${hours}h ago`;

    const days = Math.floor(hours / 24);
    if (days < 7) return `${days}d ago`;

    const weeks = Math.floor(days / 7);
    if (weeks < 4) return `${weeks}w ago`;

    const months = Math.floor(days / 30);
    if (months < 12) return `${months}mo ago`;

    const years = Math.floor(days / 365);
    return `${years}y ago`;
}

// Manual Workflow: Analyze and show clips
async function analyzeAndShowClips() {
    try {
        // Show progress section with cancel button
        hideElement(previewSection);
        hideElement(clipSelectionSection);
        showElement(progressSection);
        hideElement(resultsSection);

        // Connect to WebSocket for real-time progress
        connectWebSocket();
        updateProgress(0, 'Starting analysis...');

        const response = await fetch('/api/analyze', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ url: urlInput.value.trim() }),
        });

        if (!response.ok) {
            const errorData = await response.json().catch(() => ({ detail: 'Failed to analyze video' }));
            throw new Error(errorData.detail || 'Failed to analyze video');
        }

        const data = await response.json();
        analyzedClips = data.clips;
        selectedClipIndices = [];

        // Display clip selection UI
        displayClipSelection(data.clips);

        hideElement(progressSection);
        showElement(clipSelectionSection);

        if (ws) ws.close();

        clipSelectionSection.scrollIntoView({ behavior: 'smooth', block: 'start' });

    } catch (error) {
        console.error('Error analyzing video:', error);
        alert('Error: ' + error.message);
        hideElement(progressSection);
        showElement(previewSection);
        if (ws) ws.close();
    }
}

// Display clip selection UI
function displayClipSelection(clips) {
    clipsList.innerHTML = '';

    clips.forEach((clip, index) => {
        const clipElement = document.createElement('div');
        clipElement.className = 'clip-item';
        clipElement.dataset.index = index;

        const minutes = Math.floor(clip.start / 60);
        const seconds = Math.floor(clip.start % 60);
        const timeStr = `${minutes}:${seconds.toString().padStart(2, '0')}`;

        clipElement.innerHTML = `
            <div class="clip-header">
                <input type="checkbox" class="clip-checkbox" data-index="${index}" checked>
                <div class="clip-title">${clip.title}</div>
                <div class="clip-duration">${clip.duration.toFixed(1)}s</div>
            </div>
            <div class="clip-reason">${clip.reason}</div>
            <div class="clip-transcript">${clip.text}</div>
            <a href="${clip.youtube_link}" target="_blank" class="clip-link">
                ▶️ Watch at ${timeStr}
            </a>
        `;

        // Add checkbox handler
        const checkbox = clipElement.querySelector('.clip-checkbox');
        checkbox.addEventListener('change', () => {
            if (checkbox.checked) {
                selectedClipIndices.push(index);
                clipElement.classList.add('selected');
            } else {
                selectedClipIndices = selectedClipIndices.filter(i => i !== index);
                clipElement.classList.remove('selected');
            }
            generateBtn.disabled = selectedClipIndices.length === 0;
        });

        // Mark as selected by default
        selectedClipIndices.push(index);
        clipElement.classList.add('selected');

        clipsList.appendChild(clipElement);
    });

    generateBtn.disabled = false;
}

// Generate selected clips
async function generateSelectedClips() {
    if (selectedClipIndices.length === 0) {
        alert('Please select at least one clip to generate');
        return;
    }

    try {
        generateBtn.disabled = true;
        generateBtn.textContent = 'Processing...';

        // Hide clip selection, show progress
        hideElement(clipSelectionSection);
        showElement(progressSection);
        hideElement(resultsSection);

        // Connect to WebSocket
        connectWebSocket();
        updateProgress(0, 'Starting...');

        const response = await fetch('/api/process', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                url: urlInput.value.trim(),
                format: selectedFormat,
                burn_captions: burnCaptionsToggle.checked,
                selected_clips: selectedClipIndices
            }),
        });

        if (!response.ok) {
            const errorData = await response.json().catch(() => ({ detail: 'Failed to process video' }));
            throw new Error(errorData.detail || 'Failed to process video');
        }

        const data = await response.json();
        showResults(data);

    } catch (error) {
        console.error('Error generating clips:', error);
        alert('Error: ' + error.message);
        hideElement(progressSection);
        showElement(clipSelectionSection);
        generateBtn.disabled = false;
        generateBtn.textContent = 'Generate Selected Clips';
        if (ws) ws.close();
    }
}

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    console.log('YTClipper loaded! 🎬');

    // Center input section on initial load
    const inputSection = document.querySelector('.input-section');
    if (inputSection) {
        inputSection.classList.add('input-section-centered');
    }

    // Focus input on load
    urlInput.focus();
});

// Remove centered class when user interacts
function removeCenteredState() {
    const inputSection = document.querySelector('.input-section');
    if (inputSection) {
        inputSection.classList.remove('input-section-centered');
    }
}

// Listen for when preview section shows
const originalFetchThumbnail = fetchThumbnail;
fetchThumbnail = async function(url) {
    removeCenteredState();
    return originalFetchThumbnail.call(this, url);
};
