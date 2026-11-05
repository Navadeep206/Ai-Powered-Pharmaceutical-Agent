import api from './api';

export const dashboardService = {
  /**
   * Retrieve aggregated portfolio indicators (total, open, under investigation, pending CAPA, completed).
   */
  async getSummary() {
    const response = await api.get('/dashboard/summary');
    return response.data;
  },

  /**
   * Retrieve recent audit trail activity records across all investigations.
   */
  async getActivities(limit = 10) {
    const response = await api.get('/dashboard/activities', { params: { limit } });
    return response.data;
  },
};

export default dashboardService;

