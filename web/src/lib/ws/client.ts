export class WebSocketClient {
  private url: string;
  constructor(url: string = "/ws/events") { this.url = url; }
  connect() { /* ... */ }
}
export const ws = new WebSocketClient();
