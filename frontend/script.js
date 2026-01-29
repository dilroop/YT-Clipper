// YTClipper - Mobile-First JavaScript

// State
let currentVideoData = null;
let selectedFormat = 'vertical_9x16';  // Default to vertical 9:16 format
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
const formatBtns = document.querySelectorAll('.format-btn, .format-btn-icon');  // Support both old and new classes
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
const minDurationSlider = document.getElementById('minDuration');
const minDurationValue = document.getElementById('minDurationValue');
const maxDurationSlider = document.getElementById('maxDuration');
const maxDurationValue = document.getElementById('maxDurationValue');

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

minDurationSlider.addEventListener('input', (e) => {
    minDurationValue.textContent = e.target.value;
});

maxDurationSlider.addEventListener('input', (e) => {
    maxDurationValue.textContent = e.target.value;
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

        // Reset progress stages
        resetProgressStages();

        // Reset cancel button to default handler
        cancelBtn.textContent = 'Cancel Processing';
        cancelBtn.onclick = () => {
            if (confirm('Are you sure you want to cancel processing?')) {
                cancelProcessing();
            }
        };

        // Connect to WebSocket for real-time progress
        await connectWebSocketAndWait();

        // Start processing
        updateProgress(0, 'Starting...');

        // Get selected AI strategy
        const strategyDropdown = document.getElementById('aiStrategySelect');
        const selectedStrategy = strategyDropdown ? strategyDropdown.value : 'viral-moments';

        const response = await fetch('/api/process', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                url: urlInput.value.trim(),
                format: selectedFormat,
                burn_captions: burnCaptionsToggle.checked,
                ai_strategy: selectedStrategy,
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
        isProcessing = false;
        if (ws) ws.close();

        // Show error in progress UI
        showProcessingError(error.message, 'analyzing');
    }
}

function connectWebSocketAndWait() {
    return new Promise((resolve, reject) => {
        // Close existing connection if any
        if (ws && ws.readyState !== WebSocket.CLOSED) {
            console.log('🔄 Closing existing WebSocket connection');
            ws.close();
            ws = null;
        }

        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}/ws`;

        console.log('🔌 Connecting to WebSocket:', wsUrl);
        ws = new WebSocket(wsUrl);

        ws.onopen = () => {
            console.log('✅ WebSocket connected successfully');
            resolve(); // Resolve promise when connection is established
        };

        ws.onmessage = (event) => {
            console.log('📨 WebSocket message received:', event.data);
            const data = JSON.parse(event.data);
            console.log('📦 Parsed data:', data);

            if (data.type === 'progress') {
                const percent = data.percent || 0;
                const message = data.message || 'Processing...';
                const stage = data.stage || null;
                console.log('🎯 Progress update:', { percent, message, stage });
                updateProgress(percent, message, stage);
            }
        };

        ws.onerror = (error) => {
            console.error('❌ WebSocket error:', error);
            reject(error);
        };

        ws.onclose = (event) => {
            console.log('🔌 WebSocket closed', { code: event.code, reason: event.reason });
            ws = null;
        };

        // Add timeout to prevent hanging forever
        setTimeout(() => {
            if (ws.readyState !== WebSocket.OPEN) {
                reject(new Error('WebSocket connection timeout'));
            }
        }, 5000); // 5 second timeout
    });
}

function cancelProcessing() {
    isProcessing = false;

    // Close WebSocket
    if (ws) {
        ws.close();
        ws = null;
    }

    // Reset progress stages
    resetProgressStages();

    // Reset UI
    hideElement(progressSection);
    hideElement(clipSelectionSection);
    hideElement(resultsSection);
    showElement(previewSection);

    // Reset cancel button
    cancelBtn.textContent = 'Cancel Processing';
    cancelBtn.onclick = () => {
        if (confirm('Are you sure you want to cancel processing?')) {
            cancelProcessing();
        }
    };

    console.log('Processing cancelled');
}

// Track progress state
let currentStage = null;
let completedStages = new Set();

function updateProgress(percent, message, stage) {
    console.log('🔄 updateProgress called:', { percent, message, stage });

    // Update overall progress bar
    progressFill.style.width = percent + '%';
    document.getElementById('progressPercent').textContent = Math.round(percent) + '%';

    // Update stage-based progress
    if (stage) {
        console.log('🎬 Stage detected:', stage);
        currentStage = stage;

        // Mark previous stages as completed
        const stageOrder = ['downloading', 'transcribing', 'analyzing', 'clipping', 'organizing'];
        const currentIndex = stageOrder.indexOf(stage);

        stageOrder.forEach((s, index) => {
            const stageElem = document.querySelector(`[data-stage="${s}"]`);
            if (!stageElem) {
                console.warn(`⚠️ Stage element not found: ${s}`);
                return;
            }

            if (index < currentIndex) {
                // Previous stages - mark as completed
                console.log(`✅ Marking stage as completed: ${s}`);
                stageElem.classList.remove('active');
                stageElem.classList.add('completed');
                completedStages.add(s);
                document.getElementById(`status-${s}`).textContent = 'Completed ✓';
            } else if (index === currentIndex) {
                // Current stage - mark as active
                console.log(`⚡ Marking stage as active: ${s}`);
                stageElem.classList.add('active');
                stageElem.classList.remove('completed');
                updateStageStatus(stage, message);
            } else {
                // Future stages - reset
                stageElem.classList.remove('active', 'completed');
                document.getElementById(`status-${s}`).textContent = 'Waiting...';
                document.getElementById(`details-${s}`).textContent = '';
            }
        });
    }

    // Handle completion
    if (percent >= 100 || stage === 'complete') {
        const stageOrder = ['downloading', 'transcribing', 'analyzing', 'clipping', 'organizing'];
        stageOrder.forEach(s => {
            const stageElem = document.querySelector(`[data-stage="${s}"]`);
            if (stageElem) {
                stageElem.classList.remove('active');
                stageElem.classList.add('completed');
                document.getElementById(`status-${s}`).textContent = 'Completed ✓';
            }
        });
    }
}

function updateStageStatus(stage, message) {
    console.log(`📋 updateStageStatus called for stage: ${stage}, message: ${message}`);
    const statusElem = document.getElementById(`status-${stage}`);
    const detailsElem = document.getElementById(`details-${stage}`);

    if (!statusElem || !detailsElem) {
        console.warn(`⚠️ Status/details element not found for stage: ${stage}`);
        return;
    }

    // Extract meaningful status from message
    if (stage === 'downloading') {
        statusElem.textContent = 'Downloading...';
        // Show download details (size, speed, etc.)
        detailsElem.textContent = message;
    } else if (stage === 'transcribing') {
        statusElem.textContent = 'Transcribing...';
        detailsElem.textContent = message;
    } else if (stage === 'analyzing') {
        statusElem.textContent = 'Analyzing...';
        if (message.includes('OpenAI') || message.includes('AI') || message.includes('GPT')) {
            detailsElem.textContent = 'Using AI to find interesting clips...';
        } else {
            detailsElem.textContent = message;
        }
    } else if (stage === 'clipping') {
        statusElem.textContent = 'Processing...';
        // Parse clip number from message
        const clipMatch = message.match(/clip (\d+)\/(\d+)/i);
        if (clipMatch) {
            detailsElem.textContent = `Processing clip ${clipMatch[1]} of ${clipMatch[2]}`;
        } else {
            detailsElem.textContent = message;
        }
    } else if (stage === 'organizing') {
        statusElem.textContent = 'Organizing...';
        detailsElem.textContent = message;
    } else {
        statusElem.textContent = 'Processing...';
        detailsElem.textContent = message;
    }
}

function resetProgressStages() {
    // Reset all stages to initial state
    const stages = ['downloading', 'transcribing', 'analyzing', 'clipping', 'organizing'];
    stages.forEach(stage => {
        const stageElem = document.querySelector(`[data-stage="${stage}"]`);
        if (stageElem) {
            stageElem.classList.remove('active', 'completed');
            document.getElementById(`status-${stage}`).textContent = 'Waiting...';
            document.getElementById(`details-${stage}`).textContent = '';
        }
    });
    currentStage = null;
    completedStages.clear();
}

function showProcessingError(errorMessage, failedStage, onRetry = null) {
    // Mark the failed stage as error
    const stageElem = document.querySelector(`[data-stage="${failedStage}"]`);
    if (stageElem) {
        stageElem.classList.add('error');
        stageElem.classList.remove('active', 'completed');

        const statusElem = document.getElementById(`status-${failedStage}`);
        const detailsElem = document.getElementById(`details-${failedStage}`);

        if (statusElem) {
            statusElem.textContent = 'Failed ✗';
        }

        if (detailsElem) {
            // Format error message nicely
            let errorHTML = `<div style="color: #ef4444; margin-top: 8px;">
                <strong>Error:</strong> ${errorMessage}
            </div>`;

            // Add helpful tips for common errors
            if (errorMessage.includes('Could not find any interesting clips')) {
                errorHTML += `<div style="margin-top: 8px; color: var(--text-secondary); font-size: 12px;">
                    <strong>Tip:</strong> Try adjusting the duration settings in Settings, or use a different AI strategy.
                </div>`;
            } else if (errorMessage.includes('OPENAI_QUOTA_ERROR') || errorMessage.includes('Insufficient OpenAI credits')) {
                errorHTML += `<div style="margin-top: 8px; color: var(--text-secondary); font-size: 12px;">
                    <strong>Tip:</strong> Add credits at <a href="https://platform.openai.com/account/billing" target="_blank" style="color: var(--primary-color);">OpenAI Billing</a>
                </div>`;
            }

            detailsElem.innerHTML = errorHTML;
        }
    }

    // Update cancel button to "Back" or custom action
    cancelBtn.textContent = onRetry ? 'Back to Selection' : 'Back to Start';
    cancelBtn.onclick = () => {
        if (onRetry) {
            onRetry();
        } else {
            hideElement(progressSection);
            showElement(previewSection);
        }
    };
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
            <div class="clip-card clip-card-full-width">
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
            <div class="clip-card clip-card-full-width">
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

        if (config.ai_validation) {
            const av = config.ai_validation;
            minDurationSlider.value = av.min_clip_duration || 15;
            minDurationValue.textContent = av.min_clip_duration || 15;
            maxDurationSlider.value = av.max_clip_duration || 60;
            maxDurationValue.textContent = av.max_clip_duration || 60;
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

        const aiValidationSettings = {
            min_clip_duration: parseInt(minDurationSlider.value),
            max_clip_duration: parseInt(maxDurationSlider.value),
        };

        const response = await fetch('/api/config', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                caption_settings: captionSettings,
                ai_validation: aiValidationSettings,
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
                const date = new Date(item.last_viewed);
                const timeAgo = formatTimeAgo(date);
                const viewCount = item.view_count || 1;
                const viewBadge = viewCount > 1 ? `<span class="view-count-badge" title="Viewed ${viewCount} times">👁️ ${viewCount}</span>` : '';

                return `
                    <div class="history-item" data-url="${item.url}">
                        <img class="history-thumbnail" src="${item.thumbnail}" alt="${item.title}" onerror="this.src='${item.thumbnail}'">
                        <div class="history-info">
                            <div class="history-title">${item.title} ${viewBadge}</div>
                            <div class="history-meta">${item.channel} • ${formatDuration(item.duration)}</div>
                            <div class="history-time">${timeAgo}</div>
                        </div>
                        <button class="history-copy-btn" data-url="${item.url}" title="Copy link" aria-label="Copy link">
                            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                <rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect>
                                <path d="M5 15H4a2 2 0 0 1-2-2V4a2 4 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path>
                            </svg>
                        </button>
                    </div>
                `;
            }).join('');

            // Add click handlers to history items
            document.querySelectorAll('.history-item').forEach(item => {
                item.addEventListener('click', (e) => {
                    // Don't trigger if clicking the copy button
                    if (e.target.closest('.history-copy-btn')) {
                        return;
                    }
                    const url = item.dataset.url;
                    urlInput.value = url;
                    hideElement(historyModal);
                    fetchThumbnail(url);
                });
            });

            // Add click handlers to copy buttons
            document.querySelectorAll('.history-copy-btn').forEach(btn => {
                btn.addEventListener('click', async (e) => {
                    e.stopPropagation(); // Prevent history item click
                    const url = btn.dataset.url;
                    try {
                        await navigator.clipboard.writeText(url);
                        // Visual feedback
                        const originalHTML = btn.innerHTML;
                        btn.innerHTML = `
                            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                <polyline points="20 6 9 17 4 12"></polyline>
                            </svg>
                        `;
                        btn.style.color = 'var(--success-color)';
                        setTimeout(() => {
                            btn.innerHTML = originalHTML;
                            btn.style.color = '';
                        }, 1500);
                    } catch (err) {
                        console.error('Failed to copy:', err);
                        alert('Failed to copy link');
                    }
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

        // Reset progress stages
        resetProgressStages();

        // Reset cancel button to default handler
        cancelBtn.textContent = 'Cancel Processing';
        cancelBtn.onclick = () => {
            if (confirm('Are you sure you want to cancel processing?')) {
                cancelProcessing();
            }
        };

        // Connect to WebSocket for real-time progress
        await connectWebSocketAndWait();
        updateProgress(0, 'Starting analysis...');

        // Get selected AI strategy
        const strategyDropdown = document.getElementById('aiStrategySelect');
        const selectedStrategy = strategyDropdown ? strategyDropdown.value : 'viral-moments';

        const response = await fetch('/api/analyze', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                url: urlInput.value.trim(),
                ai_strategy: selectedStrategy
            }),
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
        if (ws) ws.close();

        // Show error in progress UI
        showProcessingError(error.message, 'analyzing');
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

        // Reset progress stages
        resetProgressStages();

        // Reset cancel button to default handler
        cancelBtn.textContent = 'Cancel Processing';
        cancelBtn.onclick = () => {
            if (confirm('Are you sure you want to cancel processing?')) {
                cancelProcessing();
            }
        };

        // Connect to WebSocket
        await connectWebSocketAndWait();
        updateProgress(0, 'Starting...');

        // Get the selected clips data (not just indices)
        const selectedClipsData = selectedClipIndices.map(index => analyzedClips[index]);

        const response = await fetch('/api/process', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                url: urlInput.value.trim(),
                format: selectedFormat,
                burn_captions: burnCaptionsToggle.checked,
                selected_clips: selectedClipIndices,
                preanalyzed_clips: selectedClipsData  // Pass the full clip data to skip re-analysis
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
        if (ws) ws.close();
        generateBtn.disabled = false;
        generateBtn.textContent = 'Generate Selected Clips';

        // Show error in progress UI with return to selection option
        showProcessingError(error.message, 'clipping', () => {
            hideElement(progressSection);
            showElement(clipSelectionSection);
        });
    }
}

// Load AI strategies from server
async function loadStrategies() {
    try {
        const response = await fetch('/api/strategies');
        const data = await response.json();

        if (data.success && data.strategies) {
            const dropdown = document.getElementById('aiStrategySelect');
            if (dropdown) {
                // Clear existing options
                dropdown.innerHTML = '';

                // Add strategies as options with nice labels
                data.strategies.forEach(strategy => {
                    const option = document.createElement('option');
                    option.value = strategy;
                    // Convert kebab-case to Title Case
                    option.textContent = strategy
                        .split('-')
                        .map(word => word.charAt(0).toUpperCase() + word.slice(1))
                        .join(' ');
                    dropdown.appendChild(option);
                });

                // Load last selected strategy from localStorage
                const lastStrategy = localStorage.getItem('ytclipper_ai_strategy');
                if (lastStrategy && data.strategies.includes(lastStrategy)) {
                    dropdown.value = lastStrategy;
                }

                // Save selection when changed
                dropdown.addEventListener('change', () => {
                    localStorage.setItem('ytclipper_ai_strategy', dropdown.value);
                    console.log('AI Strategy changed to:', dropdown.value);
                });
            }
        }
    } catch (error) {
        console.error('Error loading strategies:', error);
    }
}

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    console.log('YTClipper loaded! 🎬');

    // Load available AI strategies
    loadStrategies();

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
