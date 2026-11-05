import { describe, it, expect, vi } from 'vitest';
import { api, ApiError, normalizeApiError } from '../services/api';

describe('Centralized Axios Client & Error Normalization', () => {
  it('configures default timeout and JSON headers', () => {
    expect(api.defaults.timeout).toBe(15000);
    expect(api.defaults.headers['Content-Type']).toBe('application/json');
    expect(api.defaults.headers['Accept']).toBe('application/json');
  });

  it('normalizes network errors when backend is unreachable', () => {
    const networkError = {
      message: 'Network Error',
      code: 'ERR_NETWORK',
      response: undefined,
    };

    const normalized = normalizeApiError(networkError);
    expect(normalized).toBeInstanceOf(ApiError);
    expect(normalized.isNetworkError).toBe(true);
    expect(normalized.statusCode).toBeNull();
    expect(normalized.message).toContain('Cannot connect to the RootIQ backend API');
  });

  it('normalizes timeout errors properly', () => {
    const timeoutError = {
      message: 'timeout of 15000ms exceeded',
      code: 'ECONNABORTED',
      response: undefined,
    };

    const normalized = normalizeApiError(timeoutError);
    expect(normalized).toBeInstanceOf(ApiError);
    expect(normalized.isNetworkError).toBe(true);
    expect(normalized.message).toContain('request timed out');
  });

  it('normalizes HTTP 404 Not Found error responses', () => {
    const notFoundError = {
      response: {
        status: 404,
        data: {
          error: 'HTTPException',
          message: "Investigation 'INV-MISSING' not found.",
          status_code: 404,
        },
      },
    };

    const normalized = normalizeApiError(notFoundError);
    expect(normalized).toBeInstanceOf(ApiError);
    expect(normalized.isNetworkError).toBe(false);
    expect(normalized.statusCode).toBe(404);
    expect(normalized.message).toBe("Investigation 'INV-MISSING' not found.");
  });

  it('normalizes FastAPI 422 validation errors with field specifics', () => {
    const valError = {
      response: {
        status: 422,
        data: {
          detail: [
            { loc: ['body', 'incident_title'], msg: 'Field required', type: 'missing' },
            { loc: ['body', 'severity'], msg: 'Input should be Critical, High, Medium or Low', type: 'enum' },
          ],
        },
      },
    };

    const normalized = normalizeApiError(valError);
    expect(normalized).toBeInstanceOf(ApiError);
    expect(normalized.statusCode).toBe(422);
    expect(normalized.message).toContain('incident_title: Field required');
    expect(normalized.message).toContain('severity: Input should be Critical, High, Medium or Low');
  });

  it('safely handles 500 server errors without leaking internal stack traces', () => {
    const serverError = {
      response: {
        status: 500,
        data: {
          error: 'InternalServerError',
          message: 'An unexpected error occurred while processing your request. Please contact the administrator.',
          status_code: 500,
        },
      },
    };

    const normalized = normalizeApiError(serverError);
    expect(normalized).toBeInstanceOf(ApiError);
    expect(normalized.statusCode).toBe(500);
    expect(normalized.message).toContain('An unexpected error occurred');
    expect(normalized.message).not.toContain('Traceback');
    expect(normalized.message).not.toContain('/usr/');
  });

  it('does not double-wrap an existing ApiError instance', () => {
    const original = new ApiError('Custom error', { statusCode: 400 });
    const normalized = normalizeApiError(original);
    expect(normalized).toBe(original);
  });
});
