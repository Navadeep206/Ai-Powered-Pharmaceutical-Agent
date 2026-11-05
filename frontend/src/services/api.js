import axios from 'axios';

/**
 * Standardized API Error representation for RootIQ.
 * Normalizes Axios errors, network failures, timeouts, and validation errors.
 */
export class ApiError extends Error {
  constructor(message, { statusCode = null, isNetworkError = false, details = null } = {}) {
    super(message);
    this.name = 'ApiError';
    this.statusCode = statusCode;
    this.isNetworkError = isNetworkError;
    this.details = details;
  }
}

/**
 * Safely extract a clean, human-readable error message and metadata
 * without exposing internal server stack traces or credential secrets.
 */
export function normalizeApiError(error) {
  if (error instanceof ApiError) {
    return error;
  }

  // Network failures or request timeouts (no HTTP response received)
  if (!error.response) {
    const isTimeout =
      error.code === 'ECONNABORTED' ||
      (error.message && error.message.toLowerCase().includes('timeout'));

    return new ApiError(
      isTimeout
        ? 'The request timed out while communicating with the RootIQ backend server. Please try again.'
        : 'Cannot connect to the RootIQ backend API. Please verify the backend service is running.',
      {
        statusCode: null,
        isNetworkError: true,
        details: { code: error.code || 'NETWORK_FAILURE' },
      }
    );
  }

  const { status, data } = error.response;

  // Handle FastAPI 422 validation errors
  if (status === 422 && Array.isArray(data?.detail)) {
    const messages = data.detail.map((d) => {
      const field = Array.isArray(d.loc) ? d.loc.slice(1).join('.') : 'field';
      return `${field}: ${d.msg}`;
    });
    return new ApiError(`Validation error: ${messages.join(', ')}`, {
      statusCode: 422,
      isNetworkError: false,
      details: data.detail,
    });
  }

  // Handle standard RootIQ backend error envelopes: { error, message, status_code }
  let userMessage = data?.message || data?.detail;
  if (!userMessage || typeof userMessage !== 'string') {
    if (status === 404) {
      userMessage = 'The requested resource was not found on the server.';
    } else if (status === 409) {
      userMessage = 'A conflicting record already exists in the quality registry.';
    } else if (status >= 500) {
      userMessage = 'An internal server error occurred in the RootIQ backend. Please try again later.';
    } else {
      userMessage = `Request failed with HTTP status ${status}.`;
    }
  }

  return new ApiError(userMessage, {
    statusCode: status,
    isNetworkError: false,
    details: typeof data === 'object' ? data : null,
  });
}

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api';

/**
 * Centralized Axios client for RootIQ.
 * Configured with request timeout, JSON headers, and normalized error interception.
 */
export const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 15000,
  headers: {
    'Content-Type': 'application/json',
    Accept: 'application/json',
  },
});

// Request interceptor: attach audit timestamps without injecting unauthenticated bearer tokens
api.interceptors.request.use(
  (config) => {
    config.headers['X-Client-Timestamp'] = new Date().toISOString();
    return config;
  },
  (error) => Promise.reject(normalizeApiError(error))
);

// Response interceptor: centralized error handling
api.interceptors.response.use(
  (response) => response,
  (error) => Promise.reject(normalizeApiError(error))
);

export default api;
