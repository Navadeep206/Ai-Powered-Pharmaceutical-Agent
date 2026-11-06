import api from './api';

const inFlightInvPromises = new Map();
const inFlightDocPromises = new Map();
const inFlightListPromises = new Map();
const listCache = new Map();
const invCache = new Map();
const docCache = new Map();
const CACHE_TTL_MS = 5 * 60 * 1000;

export const investigationService = {
  /**
   * Retrieve paginated investigations with search and filters.
   * Deduplicates identical concurrent in-flight requests and caches fresh results.
   */
  async listInvestigations(params = {}, options = {}) {
    const cleanParams = {};
    if (params.page) cleanParams.page = params.page;
    if (params.limit) cleanParams.limit = params.limit;
    if (params.search && params.search.trim()) cleanParams.search = params.search.trim();
    if (params.status && params.status !== 'ALL') cleanParams.status = params.status;
    if (params.severity && params.severity !== 'ALL') cleanParams.severity = params.severity;
    if (params.department && params.department !== 'ALL') cleanParams.department = params.department;

    const key = JSON.stringify(cleanParams);

    if (!options.force && listCache.has(key)) {
      const entry = listCache.get(key);
      if (Date.now() - entry.timestamp < CACHE_TTL_MS) {
        return entry.data;
      }
      listCache.delete(key);
    }

    if (inFlightListPromises.has(key)) {
      return inFlightListPromises.get(key);
    }

    const promise = api
      .get('/investigations', { params: cleanParams })
      .then((res) => {
        listCache.set(key, { data: res.data, timestamp: Date.now() });
        return res.data;
      })
      .finally(() => {
        inFlightListPromises.delete(key);
      });

    inFlightListPromises.set(key, promise);
    return promise;
  },

  /**
   * Retrieve single investigation by UUID or tracking number (INV-YYYY-XXXX).
   * Deduplicates identical concurrent in-flight requests and caches fresh results.
   */
  async getInvestigation(id, options = {}) {
    if (!id) throw new Error('Investigation ID is required');
    const key = String(id);

    if (!options.force && invCache.has(key)) {
      const entry = invCache.get(key);
      if (Date.now() - entry.timestamp < CACHE_TTL_MS) {
        return entry.data;
      }
      invCache.delete(key);
    }

    if (inFlightInvPromises.has(key)) {
      return inFlightInvPromises.get(key);
    }

    const promise = api
      .get(`/investigations/${encodeURIComponent(id)}`)
      .then((res) => {
        invCache.set(key, { data: res.data, timestamp: Date.now() });
        return res.data;
      })
      .finally(() => {
        inFlightInvPromises.delete(key);
      });

    inFlightInvPromises.set(key, promise);
    return promise;
  },

  /**
   * Create a new quality deviation investigation.
   */
  async createInvestigation(payload) {
    listCache.clear();
    inFlightListPromises.clear();
    invCache.clear();
    const response = await api.post('/investigations', payload);
    return response.data;
  },

  /**
   * Partially update an active investigation.
   */
  async updateInvestigation(id, payload) {
    if (!id) throw new Error('Investigation ID is required');
    const key = String(id);
    invCache.delete(key);
    inFlightInvPromises.delete(key);
    listCache.clear();
    inFlightListPromises.clear();
    const response = await api.patch(`/investigations/${encodeURIComponent(id)}`, payload);
    return response.data;
  },

  /**
   * List document metadata associated with an investigation.
   * Deduplicates identical concurrent in-flight requests and caches fresh results.
   */
  async listDocuments(id, options = {}) {
    if (!id) throw new Error('Investigation ID is required');
    const key = String(id);

    if (!options.force && docCache.has(key)) {
      const entry = docCache.get(key);
      if (Date.now() - entry.timestamp < CACHE_TTL_MS) {
        return entry.data;
      }
      docCache.delete(key);
    }

    if (inFlightDocPromises.has(key)) {
      return inFlightDocPromises.get(key);
    }

    const promise = api
      .get(`/investigations/${encodeURIComponent(id)}/documents`)
      .then((res) => {
        docCache.set(key, { data: res.data, timestamp: Date.now() });
        return res.data;
      })
      .finally(() => {
        inFlightDocPromises.delete(key);
      });

    inFlightDocPromises.set(key, promise);
    return promise;
  },

  /**
   * Reset internal in-flight and cached maps.
   */
  clearCache() {
    inFlightInvPromises.clear();
    inFlightDocPromises.clear();
    inFlightListPromises.clear();
    listCache.clear();
    invCache.clear();
    docCache.clear();
  },
};

export default investigationService;
