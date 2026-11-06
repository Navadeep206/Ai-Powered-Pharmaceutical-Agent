import api from './api';

const inFlightCapaPromises = new Map();
const inFlightAllCapaPromises = new Map();
const allCapaCache = new Map();
const capaCache = new Map();
const CACHE_TTL_MS = 5 * 60 * 1000;

export const capaService = {
  /**
   * Retrieve all CAPA actions across all investigations.
   * Deduplicates identical concurrent in-flight requests and caches fresh results.
   */
  async listAllCAPA(params = {}, options = {}) {
    const key = JSON.stringify(params);

    if (!options.force && allCapaCache.has(key)) {
      const entry = allCapaCache.get(key);
      if (Date.now() - entry.timestamp < CACHE_TTL_MS) {
        return entry.data;
      }
      allCapaCache.delete(key);
    }

    if (inFlightAllCapaPromises.has(key)) {
      return inFlightAllCapaPromises.get(key);
    }

    const promise = api
      .get('/capa', { params })
      .then((res) => {
        allCapaCache.set(key, { data: res.data, timestamp: Date.now() });
        return res.data;
      })
      .finally(() => {
        inFlightAllCapaPromises.delete(key);
      });

    inFlightAllCapaPromises.set(key, promise);
    return promise;
  },

  /**
   * Retrieve all corrective and preventive actions for an investigation.
   * Deduplicates identical concurrent in-flight requests and caches fresh results.
   */
  async listCAPA(investigationId, options = {}) {
    if (!investigationId) throw new Error('Investigation ID is required');
    const key = String(investigationId);

    if (!options.force && capaCache.has(key)) {
      const entry = capaCache.get(key);
      if (Date.now() - entry.timestamp < CACHE_TTL_MS) {
        return entry.data;
      }
      capaCache.delete(key);
    }

    if (inFlightCapaPromises.has(key)) {
      return inFlightCapaPromises.get(key);
    }

    const promise = api
      .get(`/investigations/${encodeURIComponent(investigationId)}/capa`)
      .then((res) => {
        capaCache.set(key, { data: res.data, timestamp: Date.now() });
        return res.data;
      })
      .finally(() => {
        inFlightCapaPromises.delete(key);
      });

    inFlightCapaPromises.set(key, promise);
    return promise;
  },

  /**
   * Record a new CAPA remediation action.
   */
  async createCAPA(investigationId, payload) {
    if (!investigationId) throw new Error('Investigation ID is required');
    const key = String(investigationId);
    capaCache.delete(key);
    inFlightCapaPromises.delete(key);
    allCapaCache.clear();
    inFlightAllCapaPromises.clear();
    const response = await api.post(`/investigations/${encodeURIComponent(investigationId)}/capa`, payload);
    return response.data;
  },

  /**
   * Transition CAPA status adhering to GxP lifecycle gates.
   */
  async updateCAPAStatus(investigationId, capaId, payload) {
    if (!investigationId || !capaId) throw new Error('Investigation ID and CAPA ID are required');
    const key = String(investigationId);
    capaCache.delete(key);
    inFlightCapaPromises.delete(key);
    allCapaCache.clear();
    inFlightAllCapaPromises.clear();
    const response = await api.patch(
      `/investigations/${encodeURIComponent(investigationId)}/capa/${encodeURIComponent(capaId)}`,
      payload
    );
    return response.data;
  },

  /**
   * Generate AI-assisted CAPA recommendations using LangGraph workflow.
   */
  async generateCAPA(investigationId, payload = {}) {
    if (!investigationId) throw new Error('Investigation ID is required');
    const key = String(investigationId);
    capaCache.delete(key);
    inFlightCapaPromises.delete(key);
    allCapaCache.clear();
    inFlightAllCapaPromises.clear();
    const response = await api.post(
      `/investigations/${encodeURIComponent(investigationId)}/capa/generate`,
      payload,
      { timeout: 90000 }
    );
    return response.data;
  },

  /**
   * Submit human QA review decisions for CAPA recommendations (approve, reject, edit).
   */
  async reviewCAPA(investigationId, payload) {
    if (!investigationId) throw new Error('Investigation ID is required');
    const key = String(investigationId);
    capaCache.delete(key);
    inFlightCapaPromises.delete(key);
    allCapaCache.clear();
    inFlightAllCapaPromises.clear();
    const response = await api.post(
      `/investigations/${encodeURIComponent(investigationId)}/capa/review`,
      payload
    );
    return response.data;
  },

  /**
   * Resume paused LangGraph thread waiting at human review gate.
   */
  async resumeCAPA(investigationId, payload) {
    if (!investigationId) throw new Error('Investigation ID is required');
    const key = String(investigationId);
    capaCache.delete(key);
    inFlightCapaPromises.delete(key);
    allCapaCache.clear();
    inFlightAllCapaPromises.clear();
    const response = await api.post(
      `/investigations/${encodeURIComponent(investigationId)}/capa/resume`,
      payload
    );
    return response.data;
  },

  /**
   * Reset internal in-flight and cached maps.
   */
  clearCache() {
    inFlightCapaPromises.clear();
    inFlightAllCapaPromises.clear();
    allCapaCache.clear();
    capaCache.clear();
  },
};

export default capaService;
