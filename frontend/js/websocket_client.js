class RESQWebSocketClient {
  constructor() {
    this.socket = null;
    this.listeners = new Map();
    this.reconnectInterval = 3000;
    this.isConnected = false;
  }

  connect() {
    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    const host = window.location.host || "localhost:8000";
    const wsUrl = `${protocol}//${host}/ws/live`;

    console.log(`Connecting to RESQ-AI Live WebSocket at ${wsUrl}...`);
    try {
      this.socket = new WebSocket(wsUrl);

      this.socket.onopen = () => {
        console.log("RESQ-AI WebSocket Connected.");
        this.isConnected = true;
        this._notify("status_change", { connected: true });
      };

      this.socket.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          if (data.event) {
            this._notify(data.event, data);
          }
          this._notify("all", data);
        } catch (err) {
          console.debug("WS parse error:", err);
        }
      };

      this.socket.onclose = () => {
        this.isConnected = false;
        this._notify("status_change", { connected: false });
        setTimeout(() => this.connect(), this.reconnectInterval);
      };

      this.socket.onerror = (err) => {
        console.warn("WebSocket Error:", err);
        this.socket.close();
      };
    } catch (err) {
      console.warn("WebSocket connection initialization failed:", err);
      setTimeout(() => this.connect(), this.reconnectInterval);
    }
  }

  on(event, callback) {
    if (!this.listeners.has(event)) {
      this.listeners.set(event, []);
    }
    this.listeners.get(event).push(callback);
  }

  _notify(event, data) {
    const callbacks = this.listeners.get(event) || [];
    callbacks.forEach((cb) => {
      try {
        cb(data);
      } catch (e) {
        console.error(`Error in WS listener for ${event}:`, e);
      }
    });
  }

  send(data) {
    if (this.socket && this.socket.readyState === WebSocket.OPEN) {
      this.socket.send(JSON.stringify(data));
    }
  }
}

window.resqWS = new RESQWebSocketClient();
