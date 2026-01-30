// Progress Tracker Component
// Handles video processing progress with WebSocket updates

import { showElement, hideElement } from '../../shared/utils.js';
import { processVideo as processVideoAPI } from '../../shared/api.js';
import { WebSocketManager } from '../../shared/websocket.js';

// Component state
let isProcessing = false;
let currentStage = null;
let completedStages = new Set();
let wsManager = null;
let wsClientId = null;

// DOM elements
let progressSection, progressFill, progressPercent, cancelBtn;
let resultsSection, clipsGrid;
let previewSection, clipSelectionSection;

// Callbacks
let onComplete = null;
let onError = null;

export function initProgressTracker(callbacks = {}) {
    // Store callbacks
    onComplete = callbacks.onComplete;
    onError = callbacks.onError;

    // Get DOM elements
    progressSection = document.getElementById('progressSection');
    progressFill = document.getElementById('progressFill');
    progressPercent = document.getElementById('progressPercent');
    cancelBtn = document.getElementById('cancelBtn');
    resultsSection = document.getElementById('resultsSection');
    clipsGrid = document.getElementById('clipsGrid');
    previewSection = document.getElementById('previewSection');
    clipSelectionSection = document.getElementById('clipSelectionSection');

    // Create WebSocket manager
    wsManager = new WebSocketManager();

    // Attach event listeners
    attachEventListeners();

    console.log('✅ Progress Tracker component initialized');
}

function attachEventListeners() {
    // Cancel button
    cancelBtn.addEventListener('click', () => {
        if (confirm('Are you sure you want to cancel processing?')) {
            cancelProcessing();
        }
    });
}

export async function startProcessing(videoUrl, format, options = {}) {
    try {
        isProcessing = true;

        // Hide preview, show progress
        hideElement(previewSection);
        showElement(progressSection);
        hideElement(resultsSection);
        hideElement(clipSelectionSection);

        // Reset progress stages
        resetProgressStages();

        // Reset cancel button
        cancelBtn.textContent = 'Cancel Processing';
        cancelBtn.onclick = () => {
            if (confirm('Are you sure you want to cancel processing?')) {
                cancelProcessing();
            }
        };

        // Connect to WebSocket for real-time progress
        await connectWebSocket();

        // Start processing
        updateProgress(0, 'Starting...', null);

        const response = await fetch('/api/process', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                url: videoUrl,
                format: format,
                burn_captions: options.burnCaptions || false,
                ai_strategy: options.strategy || 'viral-moments',
                client_id: wsClientId,
            }),
        });

        if (!response.ok) {
            const errorData = await response.json().catch(() => ({ detail: 'Failed to process video' }));
            throw new Error(errorData.detail || 'Failed to process video');
        }

        const data = await response.json();

        // Processing complete
        isProcessing = false;
        showResults(data);

        if (onComplete) {
            onComplete(data);
        }

    } catch (error) {
        console.error('Error processing video:', error);
        isProcessing = false;
        wsManager.close();

        showProcessingError(error.message, 'analyzing');

        if (onError) {
            onError(error);
        }
    }
}

async function connectWebSocket() {
    return new Promise((resolve, reject) => {
        wsManager.close(); // Close existing connection if any

        wsManager.onProgress((percent, message, stage) => {
            updateProgress(percent, message, stage);
        });

        wsManager.onComplete((data) => {
            console.log('WebSocket: Processing complete', data);
        });

        wsManager.onError((error) => {
            console.error('WebSocket error:', error);
        });

        wsManager.connect()
            .then((ws) => {
                // Listen for client ID
                ws.addEventListener('message', (event) => {
                    const data = JSON.parse(event.data);
                    if (data.type === 'connection') {
                        wsClientId = data.client_id;
                        console.log('🆔 Received client ID:', wsClientId);
                    }
                });
                resolve();
            })
            .catch((error) => {
                reject(error);
            });

        // Add timeout
        setTimeout(() => {
            if (!wsManager.ws || wsManager.ws.readyState !== WebSocket.OPEN) {
                reject(new Error('WebSocket connection timeout'));
            }
        }, 5000);
    });
}

export function cancelProcessing() {
    isProcessing = false;

    // Close WebSocket
    if (wsManager) {
        wsManager.close();
    }

    // Reset progress stages
    resetProgressStages();

    // Reset UI
    hideElement(progressSection);
    hideElement(clipSelectionSection);
    hideElement(resultsSection);
    showElement(previewSection);

    console.log('Processing cancelled');
}

function updateProgress(percent, message, stage) {
    console.log('🔄 updateProgress called:', { percent, message, stage });

    // Update overall progress bar
    progressFill.style.width = percent + '%';
    progressPercent.textContent = Math.round(percent) + '%';

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
                const statusElem = document.getElementById(`status-${s}`);
                if (statusElem) statusElem.textContent = 'Completed ✓';
            } else if (index === currentIndex) {
                // Current stage - mark as active
                console.log(`⚡ Marking stage as active: ${s}`);
                stageElem.classList.add('active');
                stageElem.classList.remove('completed');
                updateStageStatus(stage, message);
            } else {
                // Future stages - reset
                stageElem.classList.remove('active', 'completed');
                const statusElem = document.getElementById(`status-${s}`);
                const detailsElem = document.getElementById(`details-${s}`);
                if (statusElem) statusElem.textContent = 'Waiting...';
                if (detailsElem) detailsElem.textContent = '';
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
                const statusElem = document.getElementById(`status-${s}`);
                if (statusElem) statusElem.textContent = 'Completed ✓';
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
    const stages = ['downloading', 'transcribing', 'analyzing', 'clipping', 'organizing'];
    stages.forEach(stage => {
        const stageElem = document.querySelector(`[data-stage="${stage}"]`);
        if (stageElem) {
            stageElem.classList.remove('active', 'completed', 'error');
            const statusElem = document.getElementById(`status-${stage}`);
            const detailsElem = document.getElementById(`details-${stage}`);
            if (statusElem) statusElem.textContent = 'Waiting...';
            if (detailsElem) detailsElem.textContent = '';
        }
    });
    currentStage = null;
    completedStages.clear();
}

function showProcessingError(errorMessage, failedStage, onRetry = null) {
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
            let errorHTML = `<div style="color: #ef4444; margin-top: 8px;">
                <strong>Error:</strong> ${errorMessage}
            </div>`;

            // Add helpful tips
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

    // Update cancel button
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

    if (!clipsGrid) return;

    if (data.success) {
        // Show results
        clipsGrid.innerHTML = '';

        if (data.clips && data.clips.length > 0) {
            data.clips.forEach((clip, index) => {
                const clipCard = createClipCard(clip, index);
                clipsGrid.appendChild(clipCard);
            });
        }
    }
}

function createClipCard(clip, index) {
    const card = document.createElement('div');
    card.className = 'clip-card';
    card.innerHTML = `
        <div class="clip-thumbnail">
            <img src="${clip.thumbnail || ''}" alt="Clip ${index + 1}">
        </div>
        <div class="clip-info">
            <h3>Clip ${index + 1}</h3>
            <p>${clip.title || ''}</p>
        </div>
    `;
    return card;
}

export function isCurrentlyProcessing() {
    return isProcessing;
}
