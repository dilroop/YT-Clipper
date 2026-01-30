// Video Input Component
// Handles YouTube URL input, thumbnail preview, and format selection

import { formatDuration, showElement, hideElement } from '../../shared/utils.js';
import { fetchThumbnail } from '../../shared/api.js';

// Component state
let currentVideoData = null;
let selectedFormat = 'vertical_9x16';  // Default to vertical 9:16 format

// DOM elements
let urlInput, clearBtn, loadingIndicator, previewSection;
let thumbnail, videoTitle, channelName, videoDuration;
let formatBtns, autoCreateBtn, manualChooseBtn;

// Callbacks
let onAutoCreate = null;
let onManualChoose = null;

export function initVideoInput(callbacks = {}) {
    // Store callbacks
    onAutoCreate = callbacks.onAutoCreate;
    onManualChoose = callbacks.onManualChoose;

    // Get DOM elements
    urlInput = document.getElementById('urlInput');
    clearBtn = document.getElementById('clearBtn');
    loadingIndicator = document.getElementById('loadingIndicator');
    previewSection = document.getElementById('previewSection');
    thumbnail = document.getElementById('thumbnail');
    videoTitle = document.getElementById('videoTitle');
    channelName = document.getElementById('channelName');
    videoDuration = document.getElementById('videoDuration');
    formatBtns = document.querySelectorAll('.format-btn, .format-btn-icon');
    autoCreateBtn = document.getElementById('autoCreateBtn');
    manualChooseBtn = document.getElementById('manualChooseBtn');

    // Attach event listeners
    attachEventListeners();

    console.log('✅ Video Input component initialized');
}

function attachEventListeners() {
    // URL input handler
    urlInput.addEventListener('input', (e) => {
        const value = e.target.value.trim();

        // Show/hide clear button
        if (value) {
            clearBtn.classList.add('visible');
        } else {
            clearBtn.classList.remove('visible');
        }
    });

    // Paste handler - auto-fetch thumbnail
    urlInput.addEventListener('paste', async (e) => {
        // Wait for paste to complete
        setTimeout(async () => {
            const url = urlInput.value.trim();
            if (url) {
                await loadVideoPreview(url);
            }
        }, 100);
    });

    // Clear button
    clearBtn.addEventListener('click', () => {
        clearInput();
    });

    // Format selection buttons
    formatBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            formatBtns.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            selectedFormat = btn.dataset.format;
            console.log('Format selected:', selectedFormat);
        });
    });

    // Auto Create button (original workflow)
    autoCreateBtn.addEventListener('click', async () => {
        if (!currentVideoData) return;
        if (onAutoCreate) {
            await onAutoCreate(currentVideoData, selectedFormat);
        }
    });

    // Manual Choose button (clip selection workflow)
    manualChooseBtn.addEventListener('click', async () => {
        if (!currentVideoData) return;
        if (onManualChoose) {
            await onManualChoose(currentVideoData);
        }
    });
}

async function loadVideoPreview(url) {
    try {
        showElement(loadingIndicator);
        hideElement(previewSection);

        const thumbnailUrl = await fetchThumbnail(url);

        if (thumbnailUrl) {
            thumbnail.src = thumbnailUrl;
            thumbnail.alt = 'Video thumbnail';

            // Extract video title from URL if possible
            // This is a placeholder - actual title would come from API
            videoTitle.textContent = 'YouTube Video';
            channelName.textContent = 'Loading...';
            videoDuration.textContent = '';

            currentVideoData = {
                url: url,
                thumbnail: thumbnailUrl
            };

            hideElement(loadingIndicator);
            showElement(previewSection);
        } else {
            hideElement(loadingIndicator);
            alert('Failed to load video preview. Please check the URL.');
        }
    } catch (error) {
        console.error('Error loading video preview:', error);
        hideElement(loadingIndicator);
        alert('Failed to load video preview: ' + error.message);
    }
}

export function clearInput() {
    urlInput.value = '';
    clearBtn.classList.remove('visible');
    hideElement(loadingIndicator);
    hideElement(previewSection);
    currentVideoData = null;

    // Reset format selection to default
    formatBtns.forEach(btn => {
        btn.classList.remove('active');
        if (btn.dataset.format === 'vertical_9x16') {
            btn.classList.add('active');
        }
    });
    selectedFormat = 'vertical_9x16';
}

export function getCurrentVideoData() {
    return currentVideoData;
}

export function getSelectedFormat() {
    return selectedFormat;
}

export function setVideoData(data) {
    currentVideoData = data;

    if (data) {
        thumbnail.src = data.thumbnail;
        videoTitle.textContent = data.title || 'YouTube Video';
        channelName.textContent = data.channel || '';
        videoDuration.textContent = data.duration ? formatDuration(data.duration) : '';

        showElement(previewSection);
    }
}
