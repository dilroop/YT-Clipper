// Gallery.js - Clips Gallery Page

let allClips = [];
let currentFilter = 'all';

// DOM Elements
const clipsGrid = document.getElementById('clipsGrid');
const loadingIndicator = document.getElementById('loadingIndicator');
const emptyState = document.getElementById('emptyState');
const totalClipsEl = document.getElementById('totalClips');
const totalSizeEl = document.getElementById('totalSize');
const backBtn = document.getElementById('backBtn');
const refreshBtn = document.getElementById('refreshBtn');
const goHomeBtn = document.getElementById('goHomeBtn');
const filterBtns = document.querySelectorAll('.filter-btn');

// Event Listeners
backBtn.addEventListener('click', () => {
    window.location.href = '/';
});

goHomeBtn.addEventListener('click', () => {
    window.location.href = '/';
});

refreshBtn.addEventListener('click', () => {
    loadClips();
});

filterBtns.forEach(btn => {
    btn.addEventListener('click', () => {
        // Update active button
        filterBtns.forEach(b => b.classList.remove('active'));
        btn.classList.add('active');

        // Apply filter
        currentFilter = btn.dataset.filter;
        renderClips();
    });
});

// Load clips on page load
document.addEventListener('DOMContentLoaded', () => {
    loadClips();
});

// Functions
async function loadClips() {
    try {
        showLoading();

        const response = await fetch('/api/clips');
        const data = await response.json();

        if (data.success) {
            allClips = data.clips;
            updateStats();
            renderClips();
        } else {
            showError('Failed to load clips');
        }

    } catch (error) {
        console.error('Error loading clips:', error);
        showError('Error loading clips: ' + error.message);
    }
}

function showLoading() {
    loadingIndicator.style.display = 'flex';
    clipsGrid.style.display = 'none';
    emptyState.style.display = 'none';
}

function showError(message) {
    loadingIndicator.style.display = 'none';
    clipsGrid.style.display = 'none';
    emptyState.style.display = 'block';
    emptyState.querySelector('h3').textContent = 'Error';
    emptyState.querySelector('p').textContent = message;
}

function updateStats() {
    const totalSize = allClips.reduce((sum, clip) => sum + clip.size, 0);
    const sizeInMB = (totalSize / (1024 * 1024)).toFixed(2);

    totalClipsEl.textContent = allClips.length;
    totalSizeEl.textContent = `${sizeInMB} MB`;
}

function renderClips() {
    loadingIndicator.style.display = 'none';

    // Filter clips
    const filteredClips = currentFilter === 'all'
        ? allClips
        : allClips.filter(clip => clip.format === currentFilter);

    if (filteredClips.length === 0) {
        emptyState.style.display = 'block';
        clipsGrid.style.display = 'none';
        return;
    }

    emptyState.style.display = 'none';
    clipsGrid.style.display = 'grid';
    clipsGrid.innerHTML = '';

    filteredClips.forEach(clip => {
        const clipCard = createClipCard(clip);
        clipsGrid.appendChild(clipCard);
    });
}

function createClipCard(clip) {
    const card = document.createElement('div');
    card.className = 'clip-card';

    const sizeInMB = (clip.size / (1024 * 1024)).toFixed(2);
    const date = new Date(clip.created);
    const dateStr = date.toLocaleDateString();

    // Build video URL
    const videoUrl = `/clips/${clip.project}/${clip.format}/${clip.filename}`;

    // Get title or fallback to filename
    const displayTitle = clip.title || clip.filename;

    card.innerHTML = `
        <div class="clip-thumbnail">
            <video preload="metadata" muted>
                <source src="${videoUrl}#t=0.5" type="video/mp4">
            </video>
            <div class="play-overlay">▶️</div>
        </div>
        <div class="clip-info">
            <div class="clip-title" title="${displayTitle}">${displayTitle}</div>
            <div class="clip-name" title="${clip.filename}">${clip.filename}</div>
            <div class="clip-meta">
                <span class="clip-format">${clip.format.toUpperCase()}</span>
                <span>${sizeInMB} MB</span>
                <span>${dateStr}</span>
            </div>
        </div>
    `;

    card.addEventListener('click', () => {
        // Navigate to clip detail page
        const detailUrl = `/clip-detail.html?project=${encodeURIComponent(clip.project)}&format=${encodeURIComponent(clip.format)}&filename=${encodeURIComponent(clip.filename)}`;
        window.location.href = detailUrl;
    });

    return card;
}

function formatFileSize(bytes) {
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(2) + ' KB';
    if (bytes < 1024 * 1024 * 1024) return (bytes / (1024 * 1024)).toFixed(2) + ' MB';
    return (bytes / (1024 * 1024 * 1024)).toFixed(2) + ' GB';
}
