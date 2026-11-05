import api from './api';

export const investigationService = {
  /**
   * Retrieve paginated investigations with search and filters.
   */
  async listInvestigations(params = {}) {
    const cleanParams = {};
    if (params.page) cleanParams.page = params.page;
    if (params.limit) cleanParams.limit = params.limit;
    if (params.search && params.search.trim()) cleanParams.search = params.search.trim();
    if (params.status && params.status !== 'ALL') cleanParams.status = params.status;
    if (params.severity && params.severity !== 'ALL') cleanParams.severity = params.severity;
    if (params.department && params.department !== 'ALL') cleanParams.department = params.department;

    const response = await api.get('/investigations', { params: cleanParams });
    return response.data;
  },

  /**
   * Retrieve single investigation by UUID or tracking number (INV-YYYY-XXXX).
   */
  async getInvestigation(id) {
    if (!id) throw new Error('Investigation ID is required');
    const response = await api.get(`/investigations/${encodeURIComponent(id)}`);
    return response.data;
  },

  /**
   * Create a new quality deviation investigation.
   */
  async createInvestigation(payload) {
    const response = await api.post('/investigations', payload);
    return response.data;
  },

  /**
   * Partially update an active investigation.
   */
  async updateInvestigation(id, payload) {
    if (!id) throw new Error('Investigation ID is required');
    const response = await api.patch(`/investigations/${encodeURIComponent(id)}`, payload);
    return response.data;
  },

  /**
   * List document metadata associated with an investigation.
   */
  async listDocuments(id) {
    if (!id) throw new Error('Investigation ID is required');
    const response = await api.get(`/investigations/${encodeURIComponent(id)}/documents`);
    return response.data;
  },
};

export default investigationService;
