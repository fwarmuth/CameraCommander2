export class ApiClient {
  private baseUrl: string;
  constructor(baseUrl: string = "/api") { this.baseUrl = baseUrl; }
  async getHealth() { return fetch(`${this.baseUrl}/health`).then(r => r.json()); }
  async getHardwareStatus() { return fetch(`${this.baseUrl}/hardware/status`).then(r => r.json()); }
}
export const api = new ApiClient();
