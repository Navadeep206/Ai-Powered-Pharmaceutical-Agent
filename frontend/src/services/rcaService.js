import api from './api';

const inFlightRcaPromises = new Map();
const rcaCache = new Map();
const CACHE_TTL_MS = 5 * 60 * 1000;

export const rcaService = {
  /**
   * Retrieve active 5-Whys causal chain and 6M Ishikawa causes for an investigation.
   * Deduplicates identical concurrent in-flight requests and caches fresh results.
   */
  async getRCA(investigationId, options = {}) {
    if (!investigationId) throw new Error('Investigation ID is required');
    const key = String(investigationId);

    if (!options.force && rcaCache.has(key)) {
      const entry = rcaCache.get(key);
      if (Date.now() - entry.timestamp < CACHE_TTL_MS) {
        return entry.data;
      }
      rcaCache.delete(key);
    }

    if (inFlightRcaPromises.has(key)) {
      return inFlightRcaPromises.get(key);
    }

    const promise = api
      .get(`/investigations/${encodeURIComponent(investigationId)}/rca`)
      .then((res) => {
        rcaCache.set(key, { data: res.data, timestamp: Date.now() });
        return res.data;
      })
      .finally(() => {
        inFlightRcaPromises.delete(key);
      });

    inFlightRcaPromises.set(key, promise);
    return promise;
  },

  /**
   * Persist 5-Whys and Fishbone analyses.
   */
  async saveRCA(investigationId, payload) {
    if (!investigationId) throw new Error('Investigation ID is required');
    const key = String(investigationId);
    rcaCache.delete(key);
    inFlightRcaPromises.delete(key);
    const response = await api.post(`/investigations/${encodeURIComponent(investigationId)}/rca`, payload);
    return response.data;
  },

  /**
   * Execute AI-assisted RCA reasoning workflow (5-Whys, 6M Fishbone, Evidence Analysis).
   */
  async generateRCA(investigationId, payload = {}) {
    if (!investigationId) throw new Error('Investigation ID is required');
    const key = String(investigationId);
    rcaCache.delete(key);
    inFlightRcaPromises.delete(key);
    const response = await api.post(
      `/investigations/${encodeURIComponent(investigationId)}/rca/generate`,
      payload,
      { timeout: 90000 } // Extended timeout for multi-agent LLM reasoning
    );
    return response.data;
  },

  /**
   * Reset internal in-flight and cached maps.
   */
  clearCache() {
    inFlightRcaPromises.clear();
    rcaCache.clear();
  },
};

export default rcaService;

