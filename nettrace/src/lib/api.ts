/**
 * API Client for TraceNet Backend
 * Frontend flow: parse text -> if complete call generate endpoint with normalized JSON only.
 */

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export interface ParseNetworkResponse {
  intent: 'not_network' | 'incomplete' | 'complete';
  missing: string[];
  json: Record<string, unknown>;
}

export const apiClient = {
  async parseNetworkRequest(userInput: string, currentState: Record<string, unknown> = {}) {
    const response = await fetch(`${API_BASE_URL}/api/parse-network-request`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ user_input: userInput, current_state: currentState }),
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ message: response.statusText }));
      throw new Error(`Parser API error: ${error.message || response.statusText}`);
    }

    return (await response.json()) as ParseNetworkResponse;
  },

  async generateNetwork(normalizedPayload: Record<string, unknown>) {
    const response = await fetch(`${API_BASE_URL}/api/generate-pkt`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(normalizedPayload),
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ message: response.statusText }));
      throw new Error(`Generate API error: ${error.message || response.statusText}`);
    }

    return response.json();
  },

  downloadFile(filename: string): string {
    return `${API_BASE_URL}/api/download/${filename}`;
  },

  async healthCheck() {
    const response = await fetch(`${API_BASE_URL}/api/health`);

    if (!response.ok) {
      throw new Error('Backend health check failed');
    }

    return response.json();
  },
};

export const getApiBaseUrl = (): string => API_BASE_URL;
