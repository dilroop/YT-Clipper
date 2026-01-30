// WebSocket connection handler

export class WebSocketManager {
    constructor() {
        this.ws = null;
        this.onProgressCallback = null;
        this.onCompleteCallback = null;
        this.onErrorCallback = null;
    }

    connect() {
        return new Promise((resolve, reject) => {
            const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
            const wsUrl = `${protocol}//${window.location.host}/ws`;

            console.log('Connecting to WebSocket:', wsUrl);

            this.ws = new WebSocket(wsUrl);

            this.ws.onopen = () => {
                console.log('✅ WebSocket connected successfully');
                resolve(this.ws);
            };

            this.ws.onmessage = (event) => {
                const message = JSON.parse(event.data);
                console.log('📨 WebSocket message:', message);

                if (message.type === 'progress' && this.onProgressCallback) {
                    this.onProgressCallback(message.percent, message.message, message.stage);
                } else if (message.type === 'complete' && this.onCompleteCallback) {
                    this.onCompleteCallback(message.data);
                } else if (message.type === 'error' && this.onErrorCallback) {
                    this.onErrorCallback(message.message, message.stage);
                }
            };

            this.ws.onerror = (error) => {
                console.error('❌ WebSocket error:', error);
                reject(error);
            };

            this.ws.onclose = (event) => {
                console.log('WebSocket closed:', event.code, event.reason);
            };
        });
    }

    onProgress(callback) {
        this.onProgressCallback = callback;
    }

    onComplete(callback) {
        this.onCompleteCallback = callback;
    }

    onError(callback) {
        this.onErrorCallback = callback;
    }

    close() {
        if (this.ws) {
            this.ws.close();
            this.ws = null;
        }
    }
}
