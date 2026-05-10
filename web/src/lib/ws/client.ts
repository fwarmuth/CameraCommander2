export interface EventFrame<T = unknown> {
  topic: string;
  payload: T;
}

type Handler = (frame: EventFrame) => void;

export class EventClient {
  private socket: WebSocket | null = null;
  private handlers = new Set<Handler>();
  private reconnectTimer: number | null = null;

  constructor() {
    this.connect();
  }

  connect() {
    if (this.socket) return;

    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    const url = `${protocol}//${window.location.host}/ws/events`;
    this.socket = new WebSocket(url);

    this.socket.onmessage = (event) => {
      try {
        const frame = JSON.parse(event.data) as EventFrame;
        for (const handler of this.handlers) {
          handler(frame);
        }
      } catch (e) {
        console.error("Failed to parse event frame", e);
      }
    };

    this.socket.onopen = () => {
      console.log("WebSocket connected");
      if (this.reconnectTimer) {
        window.clearTimeout(this.reconnectTimer);
        this.reconnectTimer = null;
      }
      this.resubscribe();
    };

    this.socket.onclose = () => {
      console.log("WebSocket disconnected, retrying...");
      this.socket = null;
      this.reconnectTimer = window.setTimeout(() => this.connect(), 1000);
    };
  }

  subscribe(patterns: string[], handler: Handler) {
    this.handlers.add(handler);
    if (this.socket?.readyState === WebSocket.OPEN) {
      this.socket.send(JSON.stringify({ action: "subscribe", topics: patterns }));
    }
  }

  unsubscribe(patterns: string[], handler: Handler) {
    this.handlers.delete(handler);
    if (this.socket?.readyState === WebSocket.OPEN) {
      this.socket.send(JSON.stringify({ action: "unsubscribe", topics: patterns }));
    }
  }

  private resubscribe() {
    // This client uses a simplified broadcast approach.
    // In a real multi-client app, we'd track patterns per handler.
    // For now, we just tell the server to send everything relevant.
    if (this.socket?.readyState === WebSocket.OPEN) {
      this.socket.send(JSON.stringify({ action: "subscribe", topics: ["*"] }));
    }
  }
}

export const events = new EventClient();
