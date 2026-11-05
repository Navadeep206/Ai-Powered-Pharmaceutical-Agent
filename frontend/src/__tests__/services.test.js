import { describe, it, expect, vi, beforeEach } from 'vitest';
import api from '../services/api';
import investigationService from '../services/investigationService';
import documentService from '../services/documentService';
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

  describe('documentService', () => {
    it('calls POST /documents/upload with FormData and optional investigation_id', async () => {
      const mockFile = new File(['%PDF-1.4 dummy content'], 'bmr_report.pdf', {
        type: 'application/pdf',
      });
      const spy = vi.spyOn(api, 'post').mockResolvedValueOnce({
        data: {
          document_id: 'DOC-12345',
          original_filename: 'bmr_report.pdf',
          extraction_status: 'Success',
          extracted_text: 'Extracted PDF text content',
        },
      });

      const res = await documentService.uploadDocument(mockFile, 'INV-2026-001');
      expect(spy).toHaveBeenCalledTimes(1);
      const [url, formData, config] = spy.mock.calls[0];
      expect(url).toBe('/documents/upload');
      expect(formData instanceof FormData).toBe(true);
      expect(config.params).toEqual({ investigation_id: 'INV-2026-001' });
      expect(config.headers['Content-Type']).toBe('multipart/form-data');
      expect(res.document_id).toBe('DOC-12345');
    });

    it('throws error if uploadDocument is invoked without a file', async () => {
      await expect(documentService.uploadDocument(null)).rejects.toThrow(
        'A valid PDF file is required for upload.'
      );
    });

    it('calls POST /documents/extract with LangGraph extraction payload', async () => {
      const payload = {
        intake_method: 'Text',
        text_input: {
          incident_text: 'Thermal spike during crystallization batch 9921',
        },
      };

      const spy = vi.spyOn(api, 'post').mockResolvedValueOnce({
        data: {
          analysis_id: 'EXT-9988',
          extraction_status: 'NEEDS_REVIEW',
          extracted_data: {
            batch_number: { value: '9921', confidence_score: 0.95 },
          },
        },
      });

      const res = await documentService.extractDocument(payload);
      expect(spy).toHaveBeenCalledWith('/documents/extract', payload, {
        params: { raise_on_error: false },
        timeout: 90000,
      });
      expect(res.analysis_id).toBe('EXT-9988');
    });

    it('calls POST /documents/analyze with query parameters', async () => {
      const payload = {
        intake_method: 'Email',
        email_input: { subject: 'Urgent DEV', body: 'Alarm triggered' },
      };

      const spy = vi.spyOn(api, 'post').mockResolvedValueOnce({
        data: { intake_id: 'INTK-123' },
      });

      const res = await documentService.analyzeDocument(payload, false);
      expect(spy).toHaveBeenCalledWith('/documents/analyze', payload, {
        params: { extract: false },
        timeout: 15000,
      });
      expect(res.intake_id).toBe('INTK-123');
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

    it('calls POST /investigations/:id/rca to persist findings', async () => {
      const payload = { five_whys: [], fishbone_causes: [], investigator_notes: 'Notes' };
      const spy = vi.spyOn(api, 'post').mockResolvedValueOnce({
        data: { message: 'RCA findings recorded' },
      });

      const res = await rcaService.saveRCA('INV-123', payload);
      expect(spy).toHaveBeenCalledWith('/investigations/INV-123/rca', payload);
      expect(res.message).toBe('RCA findings recorded');
    });

    it('calls POST /investigations/:id/rca/generate for LangGraph AI reasoning', async () => {
      const payload = { problem_statement: 'High moisture', incident_context: {} };
      const spy = vi.spyOn(api, 'post').mockResolvedValueOnce({
        data: { five_whys_analysis: [], fishbone_analysis: [] },
      });

      const res = await rcaService.generateRCA('INV-123', payload);
      expect(spy).toHaveBeenCalledWith('/investigations/INV-123/rca/generate', payload, {
        timeout: 90000,
      });
      expect(res.five_whys_analysis).toEqual([]);
    });

    it('calls GET /investigations/:id/evidence', async () => {
      const spy = vi.spyOn(api, 'get').mockResolvedValueOnce({
        data: [{ evidence_id: 'E-1' }],
      });

      await evidenceService.listEvidence('INV-123');
      expect(spy).toHaveBeenCalledWith('/investigations/INV-123/evidence');
    });

    it('calls POST /investigations/:id/evidence to create evidence finding', async () => {
      const payload = {
        description: 'SCADA log reading',
        evidence_type: 'Supporting',
        source_reference: 'PLC-001',
      };
      const spy = vi.spyOn(api, 'post').mockResolvedValueOnce({
        data: { evidence_id: 'E-99', ...payload },
      });

      const res = await evidenceService.createEvidence('INV-123', payload);
      expect(spy).toHaveBeenCalledWith('/investigations/INV-123/evidence', payload);
      expect(res.evidence_id).toBe('E-99');
    });

    it('calls PATCH /investigations/:id/evidence/:evidence_id to update evidence status', async () => {
      const payload = { review_status: 'Verified', notes: 'QA confirmed trace' };
      const spy = vi.spyOn(api, 'patch').mockResolvedValueOnce({
        data: { evidence_id: 'E-99', ...payload },
      });

      const res = await evidenceService.updateEvidence('INV-123', 'E-99', payload);
      expect(spy).toHaveBeenCalledWith('/investigations/INV-123/evidence/E-99', payload);
      expect(res.review_status).toBe('Verified');
    });

    it('calls GET /capa to list all CAPA actions across portfolio', async () => {
      const spy = vi.spyOn(api, 'get').mockResolvedValueOnce({
        data: [{ action_id: 'C-ALL-1', description: 'Enterprise CAPA action' }],
      });

      const res = await capaService.listAllCAPA({ status: 'In Progress' });
      expect(spy).toHaveBeenCalledWith('/capa', { params: { status: 'In Progress' } });
      expect(res).toHaveLength(1);
      expect(res[0].action_id).toBe('C-ALL-1');
    });

    it('calls GET /investigations/:id/capa', async () => {
      const spy = vi.spyOn(api, 'get').mockResolvedValueOnce({
        data: [{ action_id: 'C-1' }],
      });

      await capaService.listCAPA('INV-123');
      expect(spy).toHaveBeenCalledWith('/investigations/INV-123/capa');
    });

    it('calls POST /investigations/:id/capa to create a manual CAPA action', async () => {
      const payload = {
        action_type: 'Corrective Action',
        description: 'Recalibrate RTD sensor',
        action_owner: 'John Doe',
        target_date: '2026-12-01',
        effectiveness_verification_method: 'Test 3 lots',
      };
      const spy = vi.spyOn(api, 'post').mockResolvedValueOnce({
        data: { action_id: 'C-99', ...payload },
      });

      const res = await capaService.createCAPA('INV-123', payload);
      expect(spy).toHaveBeenCalledWith('/investigations/INV-123/capa', payload);
      expect(res.action_id).toBe('C-99');
    });

    it('calls POST /investigations/:id/capa/generate for AI recommendations', async () => {
      const payload = { problem_statement: 'High temperature excursion' };
      const spy = vi.spyOn(api, 'post').mockResolvedValueOnce({
        data: { capa_recommendations: [] },
      });

      const res = await capaService.generateCAPA('INV-123', payload);
      expect(spy).toHaveBeenCalledWith('/investigations/INV-123/capa/generate', payload, {
        timeout: 90000,
      });
      expect(res.capa_recommendations).toEqual([]);
    });

    it('calls POST /investigations/:id/capa/review with human review decisions', async () => {
      const payload = {
        decisions: [{ capa_id: 'C-1', decision: 'Approved' }],
        general_comments: 'Verified by QA Lead',
      };
      const spy = vi.spyOn(api, 'post').mockResolvedValueOnce({
        data: { capa_review_status: 'REVIEWED' },
      });

      const res = await capaService.reviewCAPA('INV-123', payload);
      expect(spy).toHaveBeenCalledWith('/investigations/INV-123/capa/review', payload);
      expect(res.capa_review_status).toBe('REVIEWED');
    });

    it('calls PATCH /investigations/:id/capa/:capa_id to transition status', async () => {
      const payload = { status: 'In Progress', notes: 'Execution started' };
      const spy = vi.spyOn(api, 'patch').mockResolvedValueOnce({
        data: { action_id: 'C-1', status: 'In Progress' },
      });

      const res = await capaService.updateCAPAStatus('INV-123', 'C-1', payload);
      expect(spy).toHaveBeenCalledWith('/investigations/INV-123/capa/C-1', payload);
      expect(res.status).toBe('In Progress');
    });

    it('calls POST /investigations/:id/capa/resume to resume paused LangGraph thread', async () => {
      const payload = {
        thread_id: 'thread-xyz',
        decisions: [{ capa_id: 'C-1', decision: 'Approved' }],
      };
      const spy = vi.spyOn(api, 'post').mockResolvedValueOnce({
        data: { workflow_completion_status: 'COMPLETED' },
      });

      const res = await capaService.resumeCAPA('INV-123', payload);
      expect(spy).toHaveBeenCalledWith('/investigations/INV-123/capa/resume', payload);
      expect(res.workflow_completion_status).toBe('COMPLETED');
    });
  });
});
