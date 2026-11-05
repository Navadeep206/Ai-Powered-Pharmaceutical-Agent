import api from './api';

export const rcaService = {
  /**
   * Retrieve active 5-Whys causal chain and 6M Ishikawa causes for an investigation.
   */
  async getRCA(investigationId) {
    if (!investigationId) throw new Error('Investigation ID is required');
    const response = await api.get(`/investigations/${encodeURIComponent(investigationId)}/rca`);
    return response.data;
  },

  /**
   * Persist 5-Whys and Fishbone analyses.
   */
  async saveRCA(investigationId, payload) {
    if (!investigationId) throw new Error('Investigation ID is required');
    const response = await api.post(`/investigations/${encodeURIComponent(investigationId)}/rca`, payload);
    return response.data;
  },
};

export default rcaService;
