import { describe, it, expect, vi, beforeEach } from 'vitest';
import api from '../services/api';
import investigationService from '../services/investigationService';
import dashboardService from '../services/dashboardService';
import rcaService from '../services/rcaService';
import evidenceService from '../services/evidenceService';
import capaService from '../services/capaService';

describe('API Service Modules Contract Verification', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  describe('investigationService', () => {
    it('calls GET /investigations with sanitized query parameters', async () => {
      const spy = vi.spyOn(api, 'get').mockResolvedValueOnce({
        data: { items: [], pagination: { total: 0 } },
      });

      await investigationService.listInvestigations({
        page: 2,
        limit: 10,
        search: '  Excursion  ',
        status: 'Open',
        severity: 'Critical',
        department: 'ALL',
      });

      expect(spy).toHaveBeenCalledWith('/investigations', {
        params: {
          page: 2,
          limit: 10,
          search: 'Excursion',
          status: 'Open',
          severity: 'Critical',
        },
      });
    });

    it('calls GET /investigations/:id with encoded identifier', async () => {
      const spy = vi.spyOn(api, 'get').mockResolvedValueOnce({
        data: { investigation_id: 'INV-2026-0001' },
      });

      const res = await investigationService.getInvestigation('INV-2026-0001');
      expect(spy).toHaveBeenCalledWith('/investigations/INV-2026-0001');
      expect(res.investigation_id).toBe('INV-2026-0001');
    });

    it('calls POST /investigations with valid payload', async () => {
      const payload = {
        incident_title: 'Centrifuge anomaly',
        incident_description: 'Vibration excursion during cycle.',
        severity: 'High',
      };
      const spy = vi.spyOn(api, 'post').mockResolvedValueOnce({
        data: { investigation_id: 'INV-2026-9999', ...payload },
      });

      const res = await investigationService.createInvestigation(payload);
      expect(spy).toHaveBeenCalledWith('/investigations', payload);
      expect(res.investigation_id).toBe('INV-2026-9999');
    });

    it('calls PATCH /investigations/:id with update payload', async () => {
      const spy = vi.spyOn(api, 'patch').mockResolvedValueOnce({
        data: { investigation_id: 'INV-1', incident_title: 'Updated title' },
      });

      await investigationService.updateInvestigation('INV-1', { incident_title: 'Updated title' });
      expect(spy).toHaveBeenCalledWith('/investigations/INV-1', { incident_title: 'Updated title' });
    });
  });

  describe('dashboardService', () => {
    it('calls GET /dashboard/summary', async () => {
      const spy = vi.spyOn(api, 'get').mockResolvedValueOnce({
        data: {
          total_investigations: 10,
          open_investigations: 5,
        },
      });

      const res = await dashboardService.getSummary();
      expect(spy).toHaveBeenCalledWith('/dashboard/summary');
      expect(res.total_investigations).toBe(10);
    });

    it('calls GET /dashboard/activities with limit', async () => {
      const spy = vi.spyOn(api, 'get').mockResolvedValueOnce({
        data: [{ activity_id: '1', description: 'Test activity' }],
      });

      const res = await dashboardService.getActivities(5);
      expect(spy).toHaveBeenCalledWith('/dashboard/activities', { params: { limit: 5 } });
      expect(res).toHaveLength(1);
    });
  });

  describe('rcaService, evidenceService, capaService', () => {
    it('calls GET /investigations/:id/rca', async () => {
      const spy = vi.spyOn(api, 'get').mockResolvedValueOnce({
        data: { five_whys: [], fishbone_causes: [] },
      });

      await rcaService.getRCA('INV-123');
      expect(spy).toHaveBeenCalledWith('/investigations/INV-123/rca');
    });

    it('calls GET /investigations/:id/evidence', async () => {
      const spy = vi.spyOn(api, 'get').mockResolvedValueOnce({
        data: [{ evidence_id: 'E-1' }],
      });

      await evidenceService.listEvidence('INV-123');
      expect(spy).toHaveBeenCalledWith('/investigations/INV-123/evidence');
    });

    it('calls GET /investigations/:id/capa', async () => {
      const spy = vi.spyOn(api, 'get').mockResolvedValueOnce({
        data: [{ action_id: 'C-1' }],
      });

      await capaService.listCAPA('INV-123');
      expect(spy).toHaveBeenCalledWith('/investigations/INV-123/capa');
    });
  });
});
