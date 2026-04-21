/**
 * API Client for TraceNet Backend
 * Frontend flow: parse text -> if complete call generate endpoint with normalized JSON only.
 */

import { API_BASE_URL } from '@/config';

export interface ParseNetworkResponse {
  intent: 'not_network' | 'incomplete' | 'complete';
  missing: string[];
  json: Record<string, unknown>;
}

export interface PktAnalysisIssue {
  severity: 'error' | 'warning';
  code: string;
  title: string;
  message: string;
  device?: string | null;
  interface?: string | null;
  suggestion?: string | null;
}

export interface PktAnalysisResponse {
  success: boolean;
  filename?: string | null;
  summary?: string | null;
  report?: string | null;
  device_count: number;
  link_count: number;
  issue_count: number;
  issues: PktAnalysisIssue[];
  error?: string | null;
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

  async analyzePktFile(file: File) {
    const formData = new FormData();
    formData.append('file', file);

    const response = await fetch(`${API_BASE_URL}/api/analyze-pkt`, {
      method: 'POST',
      body: formData,
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: response.statusText }));
      throw new Error(error.error || error.detail || 'Packet analysis failed');
    }

    return (await response.json()) as PktAnalysisResponse;
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
