// API functions for backend communication

export async function fetchThumbnail(url) {
    try {
        const response = await fetch('/api/thumbnail', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ url })
        });

        if (!response.ok) {
            throw new Error('Failed to fetch thumbnail');
        }

        const data = await response.json();
        return data.thumbnail_url;
    } catch (error) {
        console.error('Error fetching thumbnail:', error);
        return null;
    }
}

export async function processVideo(videoUrl, selectedStrategy) {
    const response = await fetch('/api/process', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            url: videoUrl,
            selected_strategy: selectedStrategy
        })
    });

    if (!response.ok) {
        const errorData = await response.json().catch(() => ({ detail: 'Failed to process video' }));
        throw new Error(errorData.detail || errorData.message || 'Failed to process video');
    }

    return await response.json();
}

export async function analyzeVideo() {
    const response = await fetch('/api/analyze', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        }
    });

    if (!response.ok) {
        const errorData = await response.json().catch(() => ({ detail: 'Failed to analyze video' }));
        throw new Error(errorData.detail || errorData.message || 'Failed to analyze clips');
    }

    return await response.json();
}

export async function generateClips(selectedIndices) {
    const response = await fetch('/api/process', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            selected_clips: selectedIndices
        })
    });

    if (!response.ok) {
        const errorData = await response.json().catch(() => ({ detail: 'Failed to process video' }));
        throw new Error(errorData.detail || errorData.message || 'Failed to generate clips');
    }

    return await response.json();
}

export async function loadSettings() {
    const response = await fetch('/api/config');
    if (response.ok) {
        return await response.json();
    }
    throw new Error('Failed to load settings');
}

export async function saveSettings(settings) {
    const response = await fetch('/api/config', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(settings)
    });

    if (!response.ok) {
        throw new Error('Failed to save settings');
    }

    return await response.json();
}

export async function loadHistory() {
    const response = await fetch('/api/history');
    if (response.ok) {
        return await response.json();
    }
    return [];
}

export async function clearHistory() {
    const response = await fetch('/api/history', {
        method: 'DELETE'
    });

    if (!response.ok) {
        throw new Error('Failed to clear history');
    }
}

export async function loadStrategies() {
    const response = await fetch('/api/strategies');
    if (response.ok) {
        return await response.json();
    }
    return [];
}
