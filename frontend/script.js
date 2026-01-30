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
    settingsModal.style.display = 'flex';
    setTimeout(() => {
        settingsModal.style.opacity = '1';
    }, 10);
    loadSettings();
});

closeModal.addEventListener('click', () => {
    settingsModal.style.opacity = '0';
    setTimeout(() => {
        settingsModal.style.display = 'none';
    }, 200);
});

settingsModal.addEventListener('click', (e) => {
    if (e.target === settingsModal) {
        settingsModal.style.opacity = '0';
        setTimeout(() => {
            settingsModal.style.display = 'none';
        }, 200);
    }
});

saveSettings.addEventListener('click', async () => {
    await saveSettingsToServer();
    settingsModal.style.opacity = '0';
    setTimeout(() => {
        settingsModal.style.display = 'none';
    }, 200);
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
    historyModal.style.display = 'flex';
    setTimeout(() => {
        historyModal.style.opacity = '1';
    }, 10);
    loadHistory();
});

closeHistoryModal.addEventListener('click', () => {
    historyModal.style.opacity = '0';
    setTimeout(() => {
        historyModal.style.display = 'none';
    }, 200);
});

historyModal.addEventListener('click', (e) => {
    if (e.target === historyModal) {
        historyModal.style.opacity = '0';
        setTimeout(() => {
            historyModal.style.display = 'none';
        }, 200);
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
let wsClientId = null;  // Store WebSocket client ID for targeted progress updates

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
                client_id: wsClientId,  // Send client ID for targeted progress updates
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

            if (data.type === 'connection') {
                // Store client ID for targeted progress updates
                wsClientId = data.client_id;
                console.log('🆔 Received client ID:', wsClientId);
            } else if (data.type === 'progress') {
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
                    historyModal.style.opacity = '0';
                    setTimeout(() => {
                        historyModal.style.display = 'none';
                    }, 200);
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
                ai_strategy: selectedStrategy,
                client_id: wsClientId  // Send client ID for targeted progress updates
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

// Helper function to format seconds to HH:MM:SS
function formatTimeHMS(seconds) {
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    const secs = Math.floor(seconds % 60);
    return `${hours.toString().padStart(2, '0')}:${minutes.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
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

        // Check if this is a multi-part clip
        const isMultiPart = clip.parts && clip.parts.length > 0;

        let transcriptHTML = '';
        if (isMultiPart) {
            // Multi-part clip: show each part with timing
            transcriptHTML = '<div class="clip-transcript">';
            clip.parts.forEach((part, partIndex) => {
                const partNum = partIndex + 1;
                const startTime = formatTimeHMS(part.start);
                const endTime = formatTimeHMS(part.end);
                const partDuration = (part.end - part.start).toFixed(1);

                transcriptHTML += `
                    <div class="clip-part">
                        <div class="clip-part-header">
                            [${startTime} - ${endTime}] Part ${partNum} (${partDuration}s)
                        </div>
                        <div class="clip-part-text">
                            ${part.text || '(No transcript available)'}
                        </div>
                    </div>
                `;
            });
            transcriptHTML += '</div>';
        } else {
            // Single-part clip: show as before
            transcriptHTML = `<div class="clip-transcript">${clip.text}</div>`;
        }

        // Determine validation state (backward compatible - defaults to valid)
        const validationLevel = clip.validation_level || 'valid';
        const isValid = clip.is_valid !== undefined ? clip.is_valid : true;

        // Determine if clip should be checked by default
        const shouldBeChecked = validationLevel !== 'error';

        // Create validation indicator HTML
        let validationIndicatorHTML = '';
        let validationMessageHTML = '';

        if (validationLevel === 'valid') {
            validationIndicatorHTML = `<div class="validation-indicator validation-valid" data-tooltip="No validation errors">✓</div>`;
            validationMessageHTML = `<div class="validation-message validation-valid">No validation errors - clip is good to use</div>`;
        } else if (validationLevel === 'warning') {
            const warningMsg = clip.validation_warnings && clip.validation_warnings.length > 0
                ? clip.validation_warnings[0].message
                : 'Chronological warning';
            validationIndicatorHTML = `<div class="validation-indicator validation-warning" data-tooltip="${warningMsg}">⚠</div>`;
            validationMessageHTML = `<div class="validation-message validation-warning">Chronological warning - clip appears out of order but doesn't overlap. May still be usable.</div>`;
        } else if (validationLevel === 'error') {
            const errorMsg = clip.validation_warnings && clip.validation_warnings.length > 0
                ? clip.validation_warnings[0].message
                : 'Overlap detected';
            validationIndicatorHTML = `<div class="validation-indicator validation-error" data-tooltip="${errorMsg}">✗</div>`;
            validationMessageHTML = `<div class="validation-message validation-error">Overlap detected - this clip overlaps with another clip and may have quality issues.</div>`;
        }

        clipElement.innerHTML = `
            <div class="clip-header">
                <input type="checkbox" class="clip-checkbox" data-index="${index}" ${shouldBeChecked ? 'checked' : ''}>
                ${validationIndicatorHTML}
                <div class="clip-title">${clip.title}</div>
                <div class="clip-duration">${clip.duration.toFixed(1)}s</div>
                <button class="clip-edit-btn" data-clip-index="${index}" title="Edit clip">
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"></path>
                        <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"></path>
                    </svg>
                </button>
            </div>
            ${validationMessageHTML}
            <div class="clip-reason">${clip.reason}</div>
            ${transcriptHTML}
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

        // Add edit button handler
        const editBtn = clipElement.querySelector('.clip-edit-btn');
        editBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            openClipEditor(index);
        });

        // Mark as selected if checked by default
        if (shouldBeChecked) {
            selectedClipIndices.push(index);
            clipElement.classList.add('selected');
        }

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
                preanalyzed_clips: selectedClipsData,  // Pass the full clip data to skip re-analysis
                client_id: wsClientId  // Send client ID for targeted progress updates
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

// ========================================
// CLIP SCRIPT EDITOR
// ========================================

// State for clip editor
let editorState = {
    isOpen: false,
    clips: [],
    originalClips: [],
    transcriptSegments: [],
    transcriptWords: [], // NEW: Array of {word, start, end, charStart, charEnd}
    transcriptFullText: '', // NEW: Complete paragraph text
    selectedClipIndex: null,
    isAddingClip: false,
    draggedClipIndex: null,
    clipModifications: {}, // NEW: Track which clips have been modified {clipIndex: {start, end}}
    isDraggingHandle: false, // NEW: Track if user is dragging a handle
    dragHandleType: null // NEW: 'start' or 'end'
};

// DOM elements for editor
const clipEditorModal = document.getElementById('clipEditorModal');
const closeClipEditorModal = document.getElementById('closeClipEditorModal');
const editorClipsList = document.getElementById('editorClipsList');
const editorTranscript = document.getElementById('editorTranscript');
const editorClipCount = document.getElementById('editorClipCount');
const addClipBtn = document.getElementById('addClipBtn');
const editorCancelBtn = document.getElementById('editorCancelBtn');
const editorSaveBtn = document.getElementById('editorSaveBtn');

// Split multi-part clips into individual clips for editor
function splitMultiPartClips(clips) {
    const splitClips = [];
    let clipCounter = 0;

    clips.forEach((clip) => {
        // Check if this is a multi-part clip
        if (clip.parts && clip.parts.length > 1) {
            // Split into individual clips - one per part
            clip.parts.forEach((part, partIndex) => {
                const newClip = {
                    index: clipCounter++,
                    start: part.start,
                    end: part.end,
                    duration: part.end - part.start,
                    title: `${clip.title} - Part ${partIndex + 1}`,
                    reason: clip.reason,
                    text: part.text || clip.text,
                    youtube_link: clip.youtube_link ? clip.youtube_link.split('&t=')[0] + `&t=${Math.floor(part.start)}` : '',
                    keywords: clip.keywords || [],
                    words: part.words || [],
                    parts: [{
                        start: part.start,
                        end: part.end,
                        text: part.text || '',
                        words: part.words || []
                    }],
                    is_valid: clip.is_valid,
                    validation_warnings: clip.validation_warnings || [],
                    validation_level: clip.validation_level || 'valid'
                };
                splitClips.push(newClip);
            });
        } else {
            // Single-part clip or no parts array - keep as is
            clip.index = clipCounter++;
            splitClips.push(clip);
        }
    });

    return splitClips;
}

// Open Clip Script Editor
function openClipEditor(clipIndex = null) {
    if (!analyzedClips || analyzedClips.length === 0) {
        showToast('No clips available to edit', 'error');
        return;
    }

    // Deep clone clips to avoid mutating original data
    let clonedClips = JSON.parse(JSON.stringify(analyzedClips));

    // Split multi-part clips into individual clips
    editorState.clips = splitMultiPartClips(clonedClips);
    editorState.originalClips = JSON.parse(JSON.stringify(editorState.clips));
    editorState.selectedClipIndex = clipIndex;
    editorState.isOpen = true;

    // Extract transcript segments from clips (word-level timing)
    editorState.transcriptSegments = extractTranscriptSegments(editorState.clips);

    // NEW: Build word mapping for character-level positioning
    const wordMapping = buildTranscriptWordMapping(editorState.clips);
    editorState.transcriptWords = wordMapping.words;
    editorState.transcriptFullText = wordMapping.fullText;

    // Render editor content
    renderEditorClips();
    renderEditorTranscript();

    // Show modal with fade-in
    clipEditorModal.style.display = 'flex';
    setTimeout(() => {
        clipEditorModal.style.opacity = '1';
    }, 10);

    // Select and scroll to clip if specified
    if (clipIndex !== null) {
        setTimeout(() => {
            selectClip(clipIndex);
        }, 100);
    }
}

// Close Clip Script Editor
function closeClipEditor() {
    editorState.isOpen = false;
    editorState.clips = [];
    editorState.originalClips = [];
    editorState.transcriptSegments = [];
    editorState.transcriptWords = []; // NEW
    editorState.transcriptFullText = ''; // NEW
    editorState.selectedClipIndex = null;
    editorState.isAddingClip = false;
    editorState.clipModifications = {}; // NEW
    editorState.isDraggingHandle = false; // NEW
    editorState.dragHandleType = null; // NEW

    clipEditorModal.style.opacity = '0';
    setTimeout(() => {
        clipEditorModal.style.display = 'none';
    }, 200);
}

// Extract transcript segments from clips
function extractTranscriptSegments(clips) {
    const segments = [];
    const segmentMap = new Map();

    // Collect all words from all clips
    clips.forEach(clip => {
        if (clip.words && clip.words.length > 0) {
            clip.words.forEach(word => {
                if (!segmentMap.has(word.start)) {
                    segmentMap.set(word.start, {
                        start: word.start,
                        end: word.end,
                        text: word.word || word.text || ''
                    });
                }
            });
        }
    });

    // Convert to array and sort by start time
    const sortedSegments = Array.from(segmentMap.values()).sort((a, b) => a.start - b.start);

    // Group words into segments (every 10 seconds or sentence-like groups)
    let currentSegment = null;
    const SEGMENT_DURATION = 10; // seconds

    sortedSegments.forEach(word => {
        if (!currentSegment || word.start - currentSegment.start >= SEGMENT_DURATION) {
            if (currentSegment) {
                segments.push(currentSegment);
            }
            currentSegment = {
                start: word.start,
                end: word.end,
                text: word.text
            };
        } else {
            currentSegment.end = word.end;
            currentSegment.text += ' ' + word.text;
        }
    });

    if (currentSegment) {
        segments.push(currentSegment);
    }

    return segments;
}

// NEW: Build character-level word mapping from transcript
// Creates array of words with their time and character positions in the full text
function buildTranscriptWordMapping(clips) {
    const words = [];
    const wordMap = new Map();

    // Collect all words from all clips
    clips.forEach(clip => {
        if (clip.words && clip.words.length > 0) {
            clip.words.forEach(word => {
                const wordText = (word.word || word.text || '').trim();
                if (wordText && !wordMap.has(word.start)) {
                    wordMap.set(word.start, {
                        word: wordText,
                        start: word.start,
                        end: word.end
                    });
                }
            });
        }
    });

    // Convert to array and sort by start time
    const sortedWords = Array.from(wordMap.values()).sort((a, b) => a.start - b.start);

    // Build full text paragraph and assign character positions
    let charPosition = 0;
    let fullText = '';

    sortedWords.forEach((word, index) => {
        const charStart = charPosition;
        const charEnd = charPosition + word.word.length;

        words.push({
            word: word.word,
            start: word.start,
            end: word.end,
            charStart: charStart,
            charEnd: charEnd
        });

        fullText += word.word;
        charPosition = charEnd;

        // Add space after each word except the last
        if (index < sortedWords.length - 1) {
            fullText += ' ';
            charPosition += 1;
        }
    });

    return { words, fullText };
}

// NEW: Get absolute character position in the paragraph from a DOM node and offset
function getAbsoluteCharPosition(paragraphEl, targetNode, targetOffset) {
    // Walk the DOM tree to calculate absolute position
    let charCount = 0;

    function walk(node) {
        if (node === targetNode) {
            return charCount + targetOffset;
        }

        if (node.nodeType === Node.TEXT_NODE) {
            if (node === targetNode) {
                return charCount + targetOffset;
            }
            charCount += node.textContent.length;
        } else if (node.nodeType === Node.ELEMENT_NODE) {
            for (let child of node.childNodes) {
                const result = walk(child);
                if (result !== null) {
                    return result;
                }
            }
        }

        return null;
    }

    const result = walk(paragraphEl);
    return result !== null ? result : -1;
}

// NEW: Find word index by character position in text
function findWordIndexByCharPosition(charPos) {
    for (let i = 0; i < editorState.transcriptWords.length; i++) {
        const word = editorState.transcriptWords[i];
        if (charPos >= word.charStart && charPos <= word.charEnd) {
            return i;
        }
    }
    return -1;
}

// NEW: Find word index by time
function findWordIndexByTime(time) {
    for (let i = 0; i < editorState.transcriptWords.length; i++) {
        const word = editorState.transcriptWords[i];
        if (time >= word.start && time <= word.end) {
            return i;
        }
        if (time < word.start) {
            return Math.max(0, i - 1);
        }
    }
    return editorState.transcriptWords.length - 1;
}

// Render clips in editor
function renderEditorClips() {
    editorClipsList.innerHTML = '';

    if (editorState.clips.length === 0) {
        editorClipsList.innerHTML = `
            <div class="editor-empty-state">
                <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <rect x="2" y="2" width="20" height="20" rx="2"></rect>
                    <line x1="12" y1="8" x2="12" y2="16"></line>
                    <line x1="8" y1="12" x2="16" y2="12"></line>
                </svg>
                <p>No clips yet. Click the + button below to add a clip from the transcript.</p>
            </div>
        `;
        editorClipCount.textContent = '0 clips';
        return;
    }

    editorState.clips.forEach((clip, index) => {
        const clipCard = createEditorClipCard(clip, index);
        editorClipsList.appendChild(clipCard);
    });

    editorClipCount.textContent = `${editorState.clips.length} clip${editorState.clips.length !== 1 ? 's' : ''}`;
}

// Create editor clip card
function createEditorClipCard(clip, index) {
    const card = document.createElement('div');
    card.className = 'editor-clip-card';
    card.setAttribute('data-clip-index', index);
    card.setAttribute('draggable', 'true');

    const startTime = formatTime(clip.start);
    const endTime = formatTime(clip.end);
    const text = clip.text || 'No transcript available';

    const isModified = editorState.clipModifications[index] !== undefined;

    card.innerHTML = `
        <div class="editor-clip-header">
            <div class="clip-drag-handle" title="Drag to reorder">☰</div>
            <div class="editor-clip-time">Clip ${index + 1} - ${startTime} - ${endTime}</div>
            <button class="clip-confirm-btn ${isModified ? 'visible active' : ''}" title="Confirm changes">✓</button>
            <button class="clip-delete-btn" title="Delete clip">✕</button>
        </div>
        <div class="editor-clip-text">${text}</div>
    `;

    // Confirm button handler - apply cached modifications to clip
    const confirmBtn = card.querySelector('.clip-confirm-btn');
    confirmBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        if (editorState.clipModifications[index]) {
            const mod = editorState.clipModifications[index];
            editorState.clips[index].start = mod.start;
            editorState.clips[index].end = mod.end;
            editorState.clips[index].duration = mod.end - mod.start;

            // Clear modification
            delete editorState.clipModifications[index];

            // Re-render clips to update display
            renderEditorClips();

            // Re-select the clip to update highlight
            selectClip(index);

            showToast('Clip boundaries updated');
        }
    });

    // Delete button handler
    const deleteBtn = card.querySelector('.clip-delete-btn');
    deleteBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        deleteClip(index);
    });

    // Drag handlers
    card.addEventListener('dragstart', (e) => {
        editorState.draggedClipIndex = index;
        card.classList.add('dragging');
        e.dataTransfer.effectAllowed = 'move';
    });

    card.addEventListener('dragend', () => {
        card.classList.remove('dragging');
        editorState.draggedClipIndex = null;

        // Remove all drag-over classes
        document.querySelectorAll('.editor-clip-card').forEach(c => {
            c.classList.remove('drag-over');
        });
    });

    card.addEventListener('dragover', (e) => {
        e.preventDefault();

        if (editorState.draggedClipIndex !== null && editorState.draggedClipIndex !== index) {
            card.classList.add('drag-over');
        }
    });

    card.addEventListener('dragleave', () => {
        card.classList.remove('drag-over');
    });

    card.addEventListener('drop', (e) => {
        e.preventDefault();
        card.classList.remove('drag-over');

        if (editorState.draggedClipIndex !== null && editorState.draggedClipIndex !== index) {
            reorderClip(editorState.draggedClipIndex, index);
        }
    });

    // Click to select
    card.addEventListener('click', () => {
        selectClip(index);
    });

    return card;
}

// Format time as HH:MM:SS
function formatTime(seconds) {
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    const secs = Math.floor(seconds % 60);

    if (hours > 0) {
        return `${hours}:${minutes.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
    }
    return `${minutes}:${secs.toString().padStart(2, '0')}`;
}

// NEW: Render transcript as continuous paragraph (no timestamps)
function renderEditorTranscript() {
    editorTranscript.innerHTML = '';

    if (editorState.transcriptWords.length === 0) {
        editorTranscript.innerHTML = `
            <div class="editor-empty-state">
                <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
                    <polyline points="14 2 14 8 20 8"></polyline>
                    <line x1="16" y1="13" x2="8" y2="13"></line>
                    <line x1="16" y1="17" x2="8" y2="17"></line>
                </svg>
                <p>No transcript available</p>
            </div>
        `;
        return;
    }

    // Create continuous paragraph
    const paragraphEl = document.createElement('div');
    paragraphEl.className = 'transcript-paragraph';
    paragraphEl.id = 'transcriptParagraph';
    paragraphEl.textContent = editorState.transcriptFullText;

    editorTranscript.appendChild(paragraphEl);

    // Enable text selection for creating clips (if in add mode)
    enableTranscriptSelection();
}

// NEW: Enable transcript selection for creating new clips (word-boundary based)
function enableTranscriptSelection() {
    const paragraphEl = document.getElementById('transcriptParagraph');
    if (!paragraphEl) return;

    // Show handles during selection (mouseup event)
    paragraphEl.addEventListener('mouseup', () => {
        if (!editorState.isAddingClip) return;

        const selection = window.getSelection();
        if (!selection || selection.rangeCount === 0) return;

        const range = selection.getRangeAt(0);
        if (range.collapsed) return;

        // Get character positions of selection
        const startOffset = range.startOffset;
        const endOffset = range.endOffset;

        // Find corresponding words
        const startWordIndex = findWordIndexByCharPosition(startOffset);
        const endWordIndex = findWordIndexByCharPosition(endOffset);

        if (startWordIndex !== -1 && endWordIndex !== -1) {
            const startWord = editorState.transcriptWords[startWordIndex];
            const endWord = editorState.transcriptWords[endWordIndex];
            const selectedText = selection.toString().trim();

            if (selectedText && startWord.start < endWord.end) {
                // Show preview with handles before creating clip
                showSelectionPreview(startWord.start, endWord.end, startWordIndex, endWordIndex, selectedText);
                selection.removeAllRanges();
            }
        }
    });
}

// NEW: Show selection preview with drag handles before creating clip
function showSelectionPreview(startTime, endTime, startWordIndex, endWordIndex, text) {
    // Highlight the selected range
    highlightTranscriptRange(startTime, endTime);

    // Store the selection data for later use
    editorState.pendingClipSelection = {
        startTime,
        endTime,
        text,
        startWordIndex,
        endWordIndex
    };

    // Show a confirm button or toast message
    showToast('Drag handles to adjust, then click + again to confirm', 'info');
}

// Create new clip from selection
function createNewClipFromSelection(startTime, endTime, text) {
    const newClip = {
        index: editorState.clips.length,
        start: startTime,
        end: endTime,
        duration: endTime - startTime,
        title: `Clip ${editorState.clips.length + 1}`,
        reason: 'Manually added clip',
        text: text,
        youtube_link: analyzedClips[0]?.youtube_link?.split('&t=')[0] + `&t=${Math.floor(startTime)}` || '',
        keywords: [],
        words: [],
        parts: [],
        is_valid: true,
        validation_warnings: [],
        validation_level: 'valid'
    };

    editorState.clips.push(newClip);
    renderEditorClips();

    // Toggle add mode off
    editorState.isAddingClip = false;
    addClipBtn.classList.remove('active');

    // Show success feedback
    showToast('Clip added successfully');

    // Scroll to new clip
    setTimeout(() => {
        const clipCard = editorClipsList.querySelector(`[data-clip-index="${editorState.clips.length - 1}"]`);
        if (clipCard) {
            clipCard.scrollIntoView({ behavior: 'smooth', block: 'center' });
            clipCard.classList.add('selected');
        }
    }, 100);
}

// Delete clip
function deleteClip(index) {
    if (confirm(`Delete Clip ${index + 1}?`)) {
        editorState.clips.splice(index, 1);

        // Update indices
        editorState.clips.forEach((clip, i) => {
            clip.index = i;
        });

        renderEditorClips();
        showToast('Clip deleted');
    }
}

// Reorder clip
function reorderClip(fromIndex, toIndex) {
    if (fromIndex === toIndex) return;

    const clip = editorState.clips.splice(fromIndex, 1)[0];
    editorState.clips.splice(toIndex, 0, clip);

    // Update indices
    editorState.clips.forEach((clip, i) => {
        clip.index = i;
    });

    renderEditorClips();
    showToast('Clip reordered');
}

// NEW: Select clip (highlight text range with iOS/Android-style handles)
function selectClip(index) {
    editorState.selectedClipIndex = index;

    // Remove selection from all cards
    document.querySelectorAll('.editor-clip-card').forEach(card => {
        card.classList.remove('selected');
    });

    // Add selection to clicked card
    const selectedCard = editorClipsList.querySelector(`[data-clip-index="${index}"]`);
    if (selectedCard) {
        selectedCard.classList.add('selected');
    }

    // Get clip times (use modifications if available)
    const clip = editorState.clips[index];
    if (!clip) return;

    const mod = editorState.clipModifications[index];
    const startTime = mod ? mod.start : clip.start;
    const endTime = mod ? mod.end : clip.end;

    // Highlight corresponding text range
    highlightTranscriptRange(startTime, endTime);
}

// NEW: Highlight transcript range with text highlighting and drag handles
function highlightTranscriptRange(startTime, endTime) {
    const paragraphEl = document.getElementById('transcriptParagraph');
    if (!paragraphEl) return;

    // Remove any existing highlights and handles
    clearTranscriptHighlight();

    // Find word indices for start and end times
    const startWordIndex = findWordIndexByTime(startTime);
    const endWordIndex = findWordIndexByTime(endTime);

    if (startWordIndex === -1 || endWordIndex === -1) return;

    const startWord = editorState.transcriptWords[startWordIndex];
    const endWord = editorState.transcriptWords[endWordIndex];

    // Create highlighted text using Range API
    const range = document.createRange();
    const textNode = paragraphEl.firstChild;

    if (!textNode) return;

    try {
        range.setStart(textNode, startWord.charStart);
        range.setEnd(textNode, endWord.charEnd);

        // Wrap highlighted text in a span
        const highlightSpan = document.createElement('span');
        highlightSpan.className = 'transcript-highlight';
        highlightSpan.id = 'transcriptHighlight';
        range.surroundContents(highlightSpan);

        // Create and position drag handles
        createSelectionHandles(highlightSpan, startWordIndex, endWordIndex);

        // Scroll to highlight
        setTimeout(() => {
            highlightSpan.scrollIntoView({ behavior: 'smooth', block: 'center' });
        }, 100);
    } catch (e) {
        console.error('Error creating highlight:', e);
    }
}

// NEW: Clear transcript highlight and handles
function clearTranscriptHighlight() {
    // Remove existing highlight
    const existingHighlight = document.getElementById('transcriptHighlight');
    if (existingHighlight) {
        const parent = existingHighlight.parentNode;
        while (existingHighlight.firstChild) {
            parent.insertBefore(existingHighlight.firstChild, existingHighlight);
        }
        parent.removeChild(existingHighlight);
        parent.normalize(); // Merge text nodes
    }

    // Remove existing handles
    const existingHandles = document.querySelectorAll('.selection-handle');
    existingHandles.forEach(handle => handle.remove());
}

// NEW: Create iOS/Android-style selection handles with PRECISE positioning
function createSelectionHandles(highlightSpan, startWordIndex, endWordIndex) {
    const paragraphEl = document.getElementById('transcriptParagraph');
    if (!paragraphEl) {
        console.error('❌ Paragraph element not found');
        return;
    }

    const startWord = editorState.transcriptWords[startWordIndex];
    const endWord = editorState.transcriptWords[endWordIndex];

    if (!startWord || !endWord) {
        console.error('❌ Start or end word not found', { startWordIndex, endWordIndex });
        return;
    }

    console.log('🎯 Creating handles for:', {
        startWord: startWord.word,
        endWord: endWord.word,
        charStart: startWord.charStart,
        charEnd: endWord.charEnd
    });

    // Get the text node inside the highlight span
    const textNode = highlightSpan.firstChild;
    if (!textNode) {
        console.error('❌ No text node in highlight span');
        return;
    }

    // Create ranges for PRECISE character-level positioning
    const startRange = document.createRange();
    const endRange = document.createRange();

    // Get the actual character positions within the highlight span
    // The highlightSpan contains text from startWord.charStart to endWord.charEnd
    const spanStartChar = startWord.charStart;
    const spanEndChar = endWord.charEnd;
    const textLength = textNode.textContent.length;

    console.log('📝 Text info:', {
        spanStartChar,
        spanEndChar,
        textLength,
        text: textNode.textContent.substring(0, 50)
    });

    // Create range for first character (start handle)
    startRange.setStart(textNode, 0);
    startRange.setEnd(textNode, 1);

    // Create range for last character (end handle)
    endRange.setStart(textNode, Math.max(0, textLength - 1));
    endRange.setEnd(textNode, textLength);

    const startRect = startRange.getBoundingClientRect();
    const endRect = endRange.getBoundingClientRect();
    const paragraphRect = paragraphEl.getBoundingClientRect();

    console.log('📐 Rectangles:', {
        start: { left: startRect.left, top: startRect.top },
        end: { left: endRect.right, top: endRect.top },
        paragraph: { left: paragraphRect.left, top: paragraphRect.top }
    });

    // Create start handle
    const startHandle = document.createElement('div');
    startHandle.className = 'selection-handle selection-handle-start';
    startHandle.id = 'selectionHandleStart';
    startHandle.innerHTML = `
        <div class="selection-handle-knob"></div>
        <div class="selection-handle-bar"></div>
    `;

    // Create end handle
    const endHandle = document.createElement('div');
    endHandle.className = 'selection-handle selection-handle-end';
    endHandle.id = 'selectionHandleEnd';
    endHandle.innerHTML = `
        <div class="selection-handle-knob"></div>
        <div class="selection-handle-bar"></div>
    `;

    // Position handles at EXACT character boundaries
    // Both handles are centered on their respective boundaries
    // Knob width is 20px + 3px border = 26px total, so we offset by 13px to center it horizontally
    const knobRadius = 13; // Half of 26px total knob width (20px + 3px border on each side)
    const knobHeight = 26; // Total knob height (20px + 3px border top + 3px border bottom)

    // Position handles so the knob is ABOVE the text and the bar extends DOWN to the text
    // We offset vertically by knobHeight so the bar touches the top of the text

    // Start handle: center the knob on the LEFT edge of the first character
    const startLeft = (startRect.left - paragraphRect.left) - knobRadius;
    const startTop = (startRect.top - paragraphRect.top) - knobHeight;

    // End handle: center the knob on the RIGHT edge of the last character
    const endLeft = (endRect.right - paragraphRect.left) - knobRadius;
    const endTop = (endRect.top - paragraphRect.top) - knobHeight;

    console.log('📍 Handle positions:', {
        start: { left: startLeft, top: startTop },
        end: { left: endLeft, top: endTop }
    });

    startHandle.style.left = startLeft + 'px';
    startHandle.style.top = startTop + 'px';

    endHandle.style.left = endLeft + 'px';
    endHandle.style.top = endTop + 'px';

    // Add handles to paragraph element (so they scroll with the text)
    paragraphEl.appendChild(startHandle);
    paragraphEl.appendChild(endHandle);

    console.log('✅ Handles added to DOM');

    // Attach drag event handlers
    attachHandleDragListeners(startHandle, 'start', startWordIndex, endWordIndex);
    attachHandleDragListeners(endHandle, 'end', startWordIndex, endWordIndex);
}

// NEW: Attach drag event listeners to selection handles (supports mouse and touch)
function attachHandleDragListeners(handle, type, initialStartIndex, initialEndIndex) {
    let isDragging = false;
    let currentStartIndex = initialStartIndex;
    let currentEndIndex = initialEndIndex;

    // Mouse events
    handle.addEventListener('mousedown', (e) => {
        e.preventDefault();
        isDragging = true;
        editorState.isDraggingHandle = true;
        editorState.dragHandleType = type;
        handle.style.cursor = 'grabbing';

        const highlightSpan = document.getElementById('transcriptHighlight');
        if (highlightSpan) {
            highlightSpan.classList.add('active');
        }
    });

    document.addEventListener('mousemove', (e) => {
        if (!isDragging) return;

        handleDragMove(e.clientX, e.clientY, type, currentStartIndex, currentEndIndex);
    });

    document.addEventListener('mouseup', () => {
        if (!isDragging) return;

        isDragging = false;
        editorState.isDraggingHandle = false;
        editorState.dragHandleType = null;
        handle.style.cursor = 'grab';

        const highlightSpan = document.getElementById('transcriptHighlight');
        if (highlightSpan) {
            highlightSpan.classList.remove('active');
        }

        // Update clip modification in state (cached, not saved yet)
        updateClipModification();
    });

    // Touch events
    handle.addEventListener('touchstart', (e) => {
        e.preventDefault();
        isDragging = true;
        editorState.isDraggingHandle = true;
        editorState.dragHandleType = type;

        const highlightSpan = document.getElementById('transcriptHighlight');
        if (highlightSpan) {
            highlightSpan.classList.add('active');
        }
    });

    document.addEventListener('touchmove', (e) => {
        if (!isDragging) return;
        e.preventDefault();

        const touch = e.touches[0];
        handleDragMove(touch.clientX, touch.clientY, type, currentStartIndex, currentEndIndex);
    });

    document.addEventListener('touchend', () => {
        if (!isDragging) return;

        isDragging = false;
        editorState.isDraggingHandle = false;
        editorState.dragHandleType = null;

        const highlightSpan = document.getElementById('transcriptHighlight');
        if (highlightSpan) {
            highlightSpan.classList.remove('active');
        }

        // Update clip modification in state (cached, not saved yet)
        updateClipModification();
    });

    // Handle drag move logic
    function handleDragMove(clientX, clientY, handleType, startIdx, endIdx) {
        const paragraphEl = document.getElementById('transcriptParagraph');
        if (!paragraphEl) return;

        // Get character position at cursor location
        const range = document.caretRangeFromPoint(clientX, clientY);
        if (!range) return;

        // Calculate absolute character position in the full text (handles wrapped elements)
        const charPos = getAbsoluteCharPosition(paragraphEl, range.startContainer, range.startOffset);
        if (charPos === -1) return;

        const wordIndex = findWordIndexByCharPosition(charPos);
        if (wordIndex === -1) return;

        // Update indices based on handle type
        if (handleType === 'start') {
            // Don't allow start to go past end
            if (wordIndex < endIdx) {
                currentStartIndex = wordIndex;
            }
        } else {
            // Don't allow end to go before start
            if (wordIndex > startIdx) {
                currentEndIndex = wordIndex;
            }
        }

        // Get new times
        const newStartWord = editorState.transcriptWords[currentStartIndex];
        const newEndWord = editorState.transcriptWords[currentEndIndex];

        if (!newStartWord || !newEndWord) return;

        // Update highlight in real-time
        highlightTranscriptRange(newStartWord.start, newEndWord.end);

        // Store updated indices for next drag event
        if (handleType === 'start') {
            initialStartIndex = currentStartIndex;
        } else {
            initialEndIndex = currentEndIndex;
        }
    }

    // Update clip modification (cache, don't save to clip yet)
    function updateClipModification() {
        if (editorState.selectedClipIndex === null) return;

        const newStartWord = editorState.transcriptWords[currentStartIndex];
        const newEndWord = editorState.transcriptWords[currentEndIndex];

        if (!newStartWord || !newEndWord) return;

        // Cache modification (user must click confirm button to apply)
        editorState.clipModifications[editorState.selectedClipIndex] = {
            start: newStartWord.start,
            end: newEndWord.end
        };

        // Re-render clips to show confirm button
        renderEditorClips();

        // Re-select the clip to maintain selection
        selectClip(editorState.selectedClipIndex);
    }
}

// Save changes
function saveEditorChanges() {
    // Update analyzedClips with edited clips
    analyzedClips = JSON.parse(JSON.stringify(editorState.clips));

    // Re-render clip selection UI
    displayClipSelection(analyzedClips);

    // Close editor
    closeClipEditor();

    // Show success message
    showToast('Clips updated successfully');
}

// Cancel changes
function cancelEditorChanges() {
    if (JSON.stringify(editorState.clips) !== JSON.stringify(editorState.originalClips)) {
        if (confirm('You have unsaved changes. Are you sure you want to discard them?')) {
            closeClipEditor();
        }
    } else {
        closeClipEditor();
    }
}

// Show toast notification
function showToast(message, type = 'success') {
    const toast = document.createElement('div');
    toast.className = 'toast-notification';
    toast.textContent = message;

    if (type === 'error') {
        toast.style.background = '#ef4444';
    } else if (type === 'info') {
        toast.style.background = '#8b5cf6';
    }

    document.body.appendChild(toast);

    setTimeout(() => {
        toast.style.opacity = '0';
        setTimeout(() => {
            document.body.removeChild(toast);
        }, 300);
    }, 3000);
}

// Event listeners for editor
if (closeClipEditorModal) {
    closeClipEditorModal.addEventListener('click', cancelEditorChanges);
}

if (editorCancelBtn) {
    editorCancelBtn.addEventListener('click', cancelEditorChanges);
}

if (editorSaveBtn) {
    editorSaveBtn.addEventListener('click', saveEditorChanges);
}

if (addClipBtn) {
    addClipBtn.addEventListener('click', () => {
        // If there's a pending selection, confirm it
        if (editorState.pendingClipSelection) {
            const { startTime, endTime, text } = editorState.pendingClipSelection;
            createNewClipFromSelection(startTime, endTime, text);
            clearTranscriptHighlight();
            delete editorState.pendingClipSelection;
            editorState.isAddingClip = false;
            addClipBtn.classList.remove('active');
            return;
        }

        // Toggle add mode
        editorState.isAddingClip = !editorState.isAddingClip;
        addClipBtn.classList.toggle('active');

        if (editorState.isAddingClip) {
            showToast('Select text in transcript to create a new clip');
        } else {
            // Cancel selection preview
            clearTranscriptHighlight();
            delete editorState.pendingClipSelection;
        }
    });
}

// Close on background click
if (clipEditorModal) {
    clipEditorModal.addEventListener('click', (e) => {
        if (e.target === clipEditorModal) {
            cancelEditorChanges();
        }
    });
}

// Keyboard shortcuts
document.addEventListener('keydown', (e) => {
    if (!editorState.isOpen) return;

    // Escape to close
    if (e.key === 'Escape') {
        e.preventDefault();
        cancelEditorChanges();
    }

    // Ctrl/Cmd + S to save
    if ((e.ctrlKey || e.metaKey) && e.key === 's') {
        e.preventDefault();
        saveEditorChanges();
    }
});
