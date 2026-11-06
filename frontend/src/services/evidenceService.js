import api from './api';

const inFlightEvidencePromises = new Map();
const evidenceCache = new Map();
const CACHE_TTL_MS = 5 * 60 * 1000;

export const evidenceService = {
  /**
   * Retrieve all supporting, contradictory, and missing evidence items for an investigation.
   * Deduplicates identical concurrent in-flight requests and caches fresh results.
   */
  async listEvidence(investigationId, options = {}) {
    if (!investigationId) throw new Error('Investigation ID is required');
    const key = String(investigationId);

    if (!options.force && evidenceCache.has(key)) {
      const entry = evidenceCache.get(key);
      if (Date.now() - entry.timestamp < CACHE_TTL_MS) {
        return entry.data;
      }
      evidenceCache.delete(key);
    }

    if (inFlightEvidencePromises.has(key)) {
      return inFlightEvidencePromises.get(key);
    }

    const promise = api
      .get(`/investigations/${encodeURIComponent(investigationId)}/evidence`)
      .then((res) => {
        evidenceCache.set(key, { data: res.data, timestamp: Date.now() });
        return res.data;
      })
      .finally(() => {
        inFlightEvidencePromises.delete(key);
      });

    inFlightEvidencePromises.set(key, promise);
    return promise;
  },

  /**
   * Attach a new evidence record to an investigation.
   */
  async createEvidence(investigationId, payload) {
    if (!investigationId) throw new Error('Investigation ID is required');
    const key = String(investigationId);
    evidenceCache.delete(key);
    inFlightEvidencePromises.delete(key);
    const response = await api.post(`/investigations/${encodeURIComponent(investigationId)}/evidence`, payload);
    return response.data;
  },

  /**
   * Update evidence review status or notes in PostgreSQL.
   */
  async updateEvidence(investigationId, evidenceId, payload) {
    if (!investigationId || !evidenceId) throw new Error('Investigation ID and Evidence ID are required');
    const key = String(investigationId);
    evidenceCache.delete(key);
    inFlightEvidencePromises.delete(key);
    const response = await api.patch(
      `/investigations/${encodeURIComponent(investigationId)}/evidence/${encodeURIComponent(evidenceId)}`,
      payload
    );
    return response.data;
  },

  /**
   * Reset internal in-flight and cached maps.
   */
  clearCache() {
    inFlightEvidencePromises.clear();
    evidenceCache.clear();
  },
};

export default evidenceService;


