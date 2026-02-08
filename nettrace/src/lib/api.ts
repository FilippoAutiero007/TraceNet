/**
 * API Client for TraceNet Backend
 * Centralized API configuration and utility functions
 */

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

/**
 * API client with type-safe methods for backend communication
 */
export const apiClient = {
  /**
   * Generate network configuration from natural language description
   * @param description Natural language network description
   * @returns Promise with generation results
   */
  async generateNetwork(description: string) {
    const response = await fetch(`${API_BASE_URL}/api/generate-pkt`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ description }),
    });
    
    if (!response.ok) {
      const error = await response.json().catch(() => ({ message: response.statusText }));
      throw new Error(`API error: ${error.message || response.statusText}`);
    }
    
    return response.json();
  },
  
  /**
   * Get download URL for generated file
   * @param filename Generated file name
   * @returns Full download URL
   */
  downloadFile(filename: string): string {
    return `${API_BASE_URL}/api/download/${filename}`;
  },
  
  /**
   * Check backend health status
   * @returns Promise with health check results
   */
  async healthCheck() {
    const response = await fetch(`${API_BASE_URL}/api/health`);
    
    if (!response.ok) {
      throw new Error('Backend health check failed');
    }
    
    return response.json();
  },
};

/**
 * Get the configured API base URL
 * @returns Current API base URL
 */
export const getApiBaseUrl = (): string => API_BASE_URL;
