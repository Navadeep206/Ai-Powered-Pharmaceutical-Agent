import api from './api';

export const evidenceService = {
  /**
   * Retrieve all supporting, contradictory, and missing evidence items for an investigation.
   */
  async listEvidence(investigationId) {
    if (!investigationId) throw new Error('Investigation ID is required');
    const response = await api.get(`/investigations/${encodeURIComponent(investigationId)}/evidence`);
    return response.data;
  },

  /**
   * Attach a new evidence record to an investigation.
   */
  async createEvidence(investigationId, payload) {
    if (!investigationId) throw new Error('Investigation ID is required');
    const response = await api.post(`/investigations/${encodeURIComponent(investigationId)}/evidence`, payload);
    return response.data;
  },
};

export default evidenceService;

