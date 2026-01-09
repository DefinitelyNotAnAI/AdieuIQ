/**
 * API client for backend communication with token injection.
 * Constitutional Principle II: Security via token authentication
 */

import axios, { AxiosInstance, AxiosError, AxiosRequestConfig } from 'axios';
import { acquireToken } from './auth-service';

// API configuration
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1';

/**
 * Create axios instance with default configuration
 */
const createAxiosInstance = (): AxiosInstance => {
  const instance = axios.create({
    baseURL: API_BASE_URL,
    timeout: 30000, // 30 seconds
    headers: {
      'Content-Type': 'application/json',
    },
  });

  // Request interceptor: Add authorization token
  instance.interceptors.request.use(
    async (config) => {
      try {
        const token = await acquireToken();
        config.headers.Authorization = `Bearer ${token}`;
      } catch (error) {
        console.error('Failed to acquire token:', error);
        // Let request proceed without token - API will return 401
      }
      return config;
    },
    (error) => {
      return Promise.reject(error);
    }
  );

  // Response interceptor: Handle errors globally
  instance.interceptors.response.use(
    (response) => response,
    (error: AxiosError) => {
      if (error.response) {
        const status = error.response.status;
        
        // Handle specific error codes
        switch (status) {
          case 401:
            console.error('Unauthorized - token expired or invalid');
            // Could trigger re-authentication here
            break;
          case 403:
            console.error('Forbidden - insufficient permissions');
            break;
          case 404:
            console.error('Resource not found');
            break;
          case 500:
            console.error('Internal server error');
            break;
          default:
            console.error(`API error ${status}:`, error.response.data);
        }
      } else if (error.request) {
        console.error('Network error - no response received');
      } else {
        console.error('Request setup error:', error.message);
      }
      
      return Promise.reject(error);
    }
  );

  return instance;
};

// Create singleton instance
const apiClient = createAxiosInstance();

/**
 * API client methods
 */
export const api = {
  /**
   * GET request
   */
  get: <T>(url: string, config?: AxiosRequestConfig) => {
    return apiClient.get<T>(url, config);
  },

  /**
   * POST request
   */
  post: <T>(url: string, data?: any, config?: AxiosRequestConfig) => {
    return apiClient.post<T>(url, data, config);
  },

  /**
   * PUT request
   */
  put: <T>(url: string, data?: any, config?: AxiosRequestConfig) => {
    return apiClient.put<T>(url, data, config);
  },

  /**
   * DELETE request
   */
  delete: <T>(url: string, config?: AxiosRequestConfig) => {
    return apiClient.delete<T>(url, config);
  },

  /**
   * PATCH request
   */
  patch: <T>(url: string, data?: any, config?: AxiosRequestConfig) => {
    return apiClient.patch<T>(url, data, config);
  },
};

/**
 * API error handler with user-friendly messages
 */
export function getErrorMessage(error: unknown): string {
  if (axios.isAxiosError(error)) {
    if (error.response) {
      const data = error.response.data as any;
      return data?.detail || data?.message || 'An error occurred';
    } else if (error.request) {
      return 'Unable to connect to server. Please check your network connection.';
    }
  }
  return 'An unexpected error occurred';
}

/**
 * Get recommendation explainability with agent contributions (T060)
 */
export async function getExplainability(recommendationId: string): Promise<{
  recommendation: any;
  agent_contributions: any[];
}> {
  try {
    const response = await api.get(`/recommendations/${recommendationId}/explainability`);
    return response.data;
  } catch (error) {
    console.error('Failed to fetch explainability:', error);
    throw error;
  }
}

export default api;
