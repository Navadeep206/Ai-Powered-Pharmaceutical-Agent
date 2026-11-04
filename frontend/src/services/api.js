import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api';

/**
 * Reusable Axios client instance configured for the RootIQ platform.
 * Supports GxP audit header attachment, bearer tokens, and standardized error handling.
 */
export const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
    Accept: 'application/json',
  },
});

// Request interceptor: attach bearer token and client audit headers
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('rootiq_auth_token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    // GxP traceability headers
    config.headers['X-Client-Timestamp'] = new Date().toISOString();
    return config;
  },
  (error) => Promise.reject(error)
);

// Response interceptor: centralized error handling
api.interceptors.response.use(
  (response) => response,
  (error) => {
    // Standardized API error extraction
    const message =
      error.response?.data?.detail ||
      error.response?.data?.message ||
      error.message ||
      'An unexpected network error occurred';

    return Promise.reject(new Error(message));
  }
);

export default api;

