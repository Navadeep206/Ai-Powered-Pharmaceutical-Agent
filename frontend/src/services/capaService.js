import api from './api';

export const capaService = {
  /**
   * Retrieve all corrective and preventive actions for an investigation.
   */
  async listCAPA(investigationId) {
    if (!investigationId) throw new Error('Investigation ID is required');
    const response = await api.get(`/investigations/${encodeURIComponent(investigationId)}/capa`);
    return response.data;
  },

  /**
   * Record a new CAPA remediation action.
   */
  async createCAPA(investigationId, payload) {
    if (!investigationId) throw new Error('Investigation ID is required');
    const response = await api.post(`/investigations/${encodeURIComponent(investigationId)}/capa`, payload);
    return response.data;
  },

  /**
   * Transition CAPA status adhering to GxP lifecycle gates.
   */
  async updateCAPAStatus(investigationId, capaId, payload) {
    if (!investigationId || !capaId) throw new Error('Investigation ID and CAPA ID are required');
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
    const response = await api.post(
      `/investigations/${encodeURIComponent(investigationId)}/capa/resume`,
      payload
    );
    return response.data;
  },
};

export default capaService;
