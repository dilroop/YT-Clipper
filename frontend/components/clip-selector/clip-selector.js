// Clip Selector Component
// Handles AI-analyzed clip selection UI and clip generation

import { showElement, hideElement, formatTimeHMS } from '../../shared/utils.js';
import { analyzeVideo, generateClips } from '../../shared/api.js';

// Component state
let analyzedClips = null;
let selectedClipIndices = [];

// DOM elements
let clipSelectionSection, clipsList, generateBtn;

// Callbacks
let onGenerate = null;
let onEditClip = null;
let onAnalyzeStart = null;
let onAnalyzeComplete = null;

export function initClipSelector(callbacks = {}) {
    // Store callbacks
    onGenerate = callbacks.onGenerate;
    onEditClip = callbacks.onEditClip;
    onAnalyzeStart = callbacks.onAnalyzeStart;
    onAnalyzeComplete = callbacks.onAnalyzeComplete;

    // Get DOM elements
    clipSelectionSection = document.getElementById('clipSelectionSection');
    clipsList = document.getElementById('clipsList');
    generateBtn = document.getElementById('generateBtn');

    // Attach event listeners
    attachEventListeners();

    console.log('✅ Clip Selector component initialized');
}

function attachEventListeners() {
    // Generate button
    if (generateBtn) {
        generateBtn.addEventListener('click', handleGenerateClips);
    }
}

export async function analyzeAndShowClips(videoUrl, strategy = 'viral-moments') {
    try {
        if (onAnalyzeStart) {
            onAnalyzeStart();
        }

        const data = await analyzeVideo();
        analyzedClips = data.clips;
        selectedClipIndices = [];

        // Display clip selection UI
        displayClipSelection(data.clips);

        showElement(clipSelectionSection);

        if (onAnalyzeComplete) {
            onAnalyzeComplete(data.clips);
        }

        // Scroll to clip selection
        clipSelectionSection.scrollIntoView({ behavior: 'smooth', block: 'start' });

    } catch (error) {
        console.error('Error analyzing video:', error);
        throw error;
    }
}

function displayClipSelection(clips) {
    clipsList.innerHTML = '';

    clips.forEach((clip, index) => {
        const clipElement = createClipElement(clip, index);
        clipsList.appendChild(clipElement);
    });

    generateBtn.disabled = selectedClipIndices.length === 0;
}

function createClipElement(clip, index) {
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
        // Single-part clip
        transcriptHTML = `<div class="clip-transcript">${clip.text}</div>`;
    }

    // Determine validation state
    const validationLevel = clip.validation_level || 'valid';
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
        handleCheckboxChange(checkbox, index, clipElement);
    });

    // Add edit button handler
    const editBtn = clipElement.querySelector('.clip-edit-btn');
    editBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        if (onEditClip) {
            onEditClip(index);
        }
    });

    // Mark as selected if checked by default
    if (shouldBeChecked) {
        selectedClipIndices.push(index);
        clipElement.classList.add('selected');
    }

    return clipElement;
}

function handleCheckboxChange(checkbox, index, clipElement) {
    if (checkbox.checked) {
        selectedClipIndices.push(index);
        clipElement.classList.add('selected');
    } else {
        selectedClipIndices = selectedClipIndices.filter(i => i !== index);
        clipElement.classList.remove('selected');
    }
    generateBtn.disabled = selectedClipIndices.length === 0;
}

async function handleGenerateClips() {
    if (selectedClipIndices.length === 0) {
        alert('Please select at least one clip to generate');
        return;
    }

    try {
        generateBtn.disabled = true;
        generateBtn.textContent = 'Processing...';

        if (onGenerate) {
            await onGenerate(selectedClipIndices, analyzedClips);
        }

    } catch (error) {
        console.error('Error generating clips:', error);
        generateBtn.disabled = false;
        generateBtn.textContent = 'Generate Selected Clips';
        throw error;
    }
}

export function getSelectedClips() {
    return {
        indices: selectedClipIndices,
        clips: selectedClipIndices.map(index => analyzedClips[index])
    };
}

export function updateClips(newClips) {
    analyzedClips = newClips;
    displayClipSelection(newClips);
}

export function clearSelection() {
    selectedClipIndices = [];
    analyzedClips = null;
    if (clipsList) {
        clipsList.innerHTML = '';
    }
    if (generateBtn) {
        generateBtn.disabled = true;
        generateBtn.textContent = 'Generate Selected Clips';
    }
}

export function hideClipSelection() {
    hideElement(clipSelectionSection);
}

export function showClipSelection() {
    showElement(clipSelectionSection);
}
