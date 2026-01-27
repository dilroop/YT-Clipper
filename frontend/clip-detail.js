// clip-detail.js - Clip Detail Page

let currentClip = null;

// DOM Elements
const loadingIndicator = document.getElementById('loadingIndicator');
const clipContainer = document.getElementById('clipContainer');
const clipPlayer = document.getElementById('clipPlayer');
const videoSource = document.getElementById('videoSource');
const downloadBtn = document.getElementById('downloadBtn');
const backBtn = document.getElementById('backBtn');
const homeBtn = document.getElementById('homeBtn');

// Copyable content elements
const contentTitle = document.getElementById('contentTitle');
const contentDescription = document.getElementById('contentDescription');
const contentTags = document.getElementById('contentTags');

// Info elements
const clipFilename = document.getElementById('clipFilename');
const clipProject = document.getElementById('clipProject');
const clipFormat = document.getElementById('clipFormat');
const clipSize = document.getElementById('clipSize');
const clipCreated = document.getElementById('clipCreated');
const metadataSection = document.getElementById('metadataSection');
const metadataContent = document.getElementById('metadataContent');

// Event Listeners
backBtn.addEventListener('click', () => {
    window.location.href = '/gallery.html';
});

homeBtn.addEventListener('click', () => {
    window.location.href = '/';
});

downloadBtn.addEventListener('click', () => {
    if (currentClip) {
        downloadClip();
    }
});

// Copy button handlers for individual sections
document.querySelectorAll('.copy-btn').forEach(btn => {
    btn.addEventListener('click', (e) => {
        e.stopPropagation();
        const target = e.currentTarget.dataset.target;
        let textToCopy = '';

        if (target === 'title') {
            textToCopy = contentTitle.textContent;
        } else if (target === 'description') {
            textToCopy = contentDescription.textContent;
        } else if (target === 'tags') {
            textToCopy = contentTags.textContent;
        }

        if (textToCopy && textToCopy !== 'Loading...' && textToCopy !== 'N/A') {
            copyToClipboard(textToCopy, 'Copied!');
        }
    });
});

// Load clip on page load
document.addEventListener('DOMContentLoaded', () => {
    const params = new URLSearchParams(window.location.search);
    const project = params.get('project');
    const format = params.get('format');
    const filename = params.get('filename');

    if (project && format && filename) {
        loadClipDetails(project, format, filename);
    } else {
        showError('Missing clip parameters');
    }
});

// Functions
async function loadClipDetails(project, format, filename) {
    try {
        showLoading();

        const response = await fetch(`/api/clips/${encodeURIComponent(project)}/${encodeURIComponent(format)}/${encodeURIComponent(filename)}`);
        const data = await response.json();

        if (data.success) {
            currentClip = data.clip;
            renderClipDetails();
        } else {
            showError('Failed to load clip details');
        }

    } catch (error) {
        console.error('Error loading clip details:', error);
        showError('Error loading clip: ' + error.message);
    }
}

function showLoading() {
    loadingIndicator.style.display = 'flex';
    clipContainer.style.display = 'none';
}

function showError(message) {
    loadingIndicator.style.display = 'none';
    clipContainer.style.display = 'block';
    alert(message);
    window.location.href = '/gallery.html';
}

function parseInfoFile(infoText) {
    const parsed = {
        title: 'N/A',
        description: 'N/A',
        caption: 'N/A',
        tags: []
    };

    if (!infoText) return parsed;

    // Parse title (single line)
    const titleMatch = infoText.match(/Title:\s*(.+?)(?:\n|$)/);
    if (titleMatch) {
        parsed.title = titleMatch[1].trim();
    }

    // Parse description (single line only, not multiline)
    const descMatch = infoText.match(/Description:\s*(.+?)(?:\n|$)/);
    if (descMatch) {
        parsed.description = descMatch[1].trim();
    }

    // Parse caption (everything after "Caption:" until end or separator)
    const captionMatch = infoText.match(/Caption:\s*\n(.+?)(?:\n={20,}|$)/s);
    if (captionMatch) {
        parsed.caption = captionMatch[1].trim();
    }

    // Extract potential tags from caption text (words in ALL CAPS or hashtags)
    const capsWords = parsed.caption.match(/\b[A-Z]{2,}\b/g) || [];
    const hashtags = parsed.caption.match(/#\w+/g) || [];
    parsed.tags = [...new Set([...capsWords, ...hashtags])].slice(0, 10); // Limit to 10 unique tags

    return parsed;
}

function renderClipDetails() {
    loadingIndicator.style.display = 'none';
    clipContainer.style.display = 'block';

    // Set video source
    const videoUrl = `/clips/${currentClip.project}/${currentClip.format}/${currentClip.filename}`;
    videoSource.src = videoUrl;
    clipPlayer.load();

    // Update info
    clipFilename.textContent = currentClip.filename;
    clipProject.textContent = currentClip.project;
    clipFormat.textContent = currentClip.format.toUpperCase();
    clipSize.textContent = formatFileSize(currentClip.size);

    const date = new Date(currentClip.created);
    clipCreated.textContent = date.toLocaleString();

    // Parse and populate copyable content
    if (currentClip.has_info && currentClip.info_text) {
        const parsed = parseInfoFile(currentClip.info_text);

        contentTitle.textContent = parsed.title;
        contentDescription.textContent = parsed.description;

        // Format tags as comma-separated or hashtags
        if (parsed.tags.length > 0) {
            contentTags.textContent = parsed.tags.join(', ');
        } else {
            contentTags.textContent = 'No tags available';
        }

        // Show metadata
        metadataSection.style.display = 'block';
        metadataContent.textContent = currentClip.info_text;
    } else {
        contentTitle.textContent = 'N/A';
        contentDescription.textContent = 'N/A';
        contentTags.textContent = 'N/A';
        metadataSection.style.display = 'none';
    }

    // Update page title
    document.title = `${currentClip.filename} - YTClipper`;
}

function downloadClip() {
    const videoUrl = `/clips/${currentClip.project}/${currentClip.format}/${currentClip.filename}`;

    // Create temporary link and trigger download
    const a = document.createElement('a');
    a.href = videoUrl;
    a.download = currentClip.filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
}

function copyToClipboard(text, successMessage) {
    if (navigator.clipboard) {
        navigator.clipboard.writeText(text).then(() => {
            showToast(successMessage);
        }).catch(err => {
            console.error('Failed to copy:', err);
            fallbackCopyToClipboard(text, successMessage);
        });
    } else {
        fallbackCopyToClipboard(text, successMessage);
    }
}

function fallbackCopyToClipboard(text, successMessage) {
    const textArea = document.createElement('textarea');
    textArea.value = text;
    textArea.style.position = 'fixed';
    textArea.style.left = '-9999px';
    document.body.appendChild(textArea);
    textArea.focus();
    textArea.select();

    try {
        document.execCommand('copy');
        showToast(successMessage);
    } catch (err) {
        console.error('Fallback copy failed:', err);
        showToast('Failed to copy');
    }

    document.body.removeChild(textArea);
}

function showToast(message) {
    // Create toast element
    const toast = document.createElement('div');
    toast.textContent = message;
    toast.style.cssText = `
        position: fixed;
        bottom: 80px;
        left: 50%;
        transform: translateX(-50%);
        background: var(--primary-color);
        color: white;
        padding: 12px 24px;
        border-radius: 8px;
        font-size: 14px;
        font-weight: 600;
        z-index: 10000;
        animation: slideUp 0.3s ease-out;
    `;

    document.body.appendChild(toast);

    // Remove after 2 seconds
    setTimeout(() => {
        toast.style.animation = 'fadeOut 0.3s ease-out';
        setTimeout(() => {
            document.body.removeChild(toast);
        }, 300);
    }, 2000);
}

function formatClipInfo(clip) {
    const lines = [
        `Filename: ${clip.filename}`,
        `Project: ${clip.project}`,
        `Format: ${clip.format}`,
        `Size: ${formatFileSize(clip.size)}`,
        `Created: ${new Date(clip.created).toLocaleString()}`,
        `Path: /clips/${clip.project}/${clip.format}/${clip.filename}`,
    ];

    if (clip.has_info && clip.info_text) {
        lines.push('');
        lines.push('--- Metadata ---');
        lines.push(clip.info_text);
    }

    return lines.join('\n');
}

function formatFileSize(bytes) {
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(2) + ' KB';
    if (bytes < 1024 * 1024 * 1024) return (bytes / (1024 * 1024)).toFixed(2) + ' MB';
    return (bytes / (1024 * 1024 * 1024)).toFixed(2) + ' GB';
}

// Add CSS animations
const style = document.createElement('style');
style.textContent = `
    @keyframes slideUp {
        from {
            opacity: 0;
            transform: translateX(-50%) translateY(20px);
        }
        to {
            opacity: 1;
            transform: translateX(-50%) translateY(0);
        }
    }

    @keyframes fadeOut {
        from { opacity: 1; }
        to { opacity: 0; }
    }
`;
document.head.appendChild(style);
