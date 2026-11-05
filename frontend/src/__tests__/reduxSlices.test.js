import { describe, it, expect } from 'vitest';
import dashboardReducer, {
  fetchDashboardSummary,
  fetchDashboardActivities,
} from '../redux/slices/dashboardSlice';
import investigationReducer, {
  fetchInvestigations,
  fetchInvestigationById,
} from '../redux/slices/investigationSlice';
import { normalizeInvestigation, normalizeActivity } from '../utils/normalizers';

describe('Redux Slices & Normalizers', () => {
  describe('normalizers', () => {
    it('normalizes snake_case backend investigation data with safe fallbacks', () => {
      const raw = {
        investigation_id: 'INV-2026-1001',
        incident_title: 'Reactor cooling malfunction',
        incident_description: 'Coolant valve jammed for 20 minutes.',
        batch_number: 'BATCH-882',
        product_name: 'Atorvastatin',
        department: 'Synthesis',
        equipment: 'R-101',
        severity: 'High',
        investigation_status: 'Under Investigation',
        incident_date: '2026-11-01',
        immediate_action_taken: 'Manual bypass engaged',
      };

      const normalized = normalizeInvestigation(raw);
      expect(normalized.id).toBe('INV-2026-1001');
      expect(normalized.title).toBe('Reactor cooling malfunction');
      expect(normalized.batch).toBe('BATCH-882');
      expect(normalized.severity).toBe('High');
      expect(normalized.status).toBe('Under Investigation');
      expect(normalized.incidentInfo.incidentDescription).toBe('Coolant valve jammed for 20 minutes.');
      expect(normalized.incidentInfo.immediateActionTaken).toBe('Manual bypass engaged');
      expect(normalized.fiveWhys).toEqual([]);
      expect(normalized.evidence).toEqual([]);
    });

    it('normalizes activity events with relative time and styling', () => {
      const act = {
        activity_id: 'act-1',
        investigation_id: 'inv-uuid-12345678',
        activity_type: 'INVESTIGATION_CREATED',
        description: 'Quality deviation registered',
        actor_identifier: 'QA Officer',
        created_at: new Date(Date.now() - 5 * 60 * 1000).toISOString(), // 5 minutes ago
      };

      const normalized = normalizeActivity(act);
      expect(normalized.id).toBe('act-1');
      expect(normalized.iconName).toBe('PlusCircle');
      expect(normalized.time).toBe('5m ago');
      expect(normalized.detail).toContain('QA Officer');
    });
  });

  describe('dashboardSlice state transitions', () => {
    it('handles fetchDashboardSummary lifecycle: pending -> fulfilled', () => {
      const initialState = {
        summary: null,
        summaryLoading: false,
        summaryError: null,
        activities: [],
        activitiesLoading: false,
        activitiesError: null,
      };

      // 1. Pending
      const pendingState = dashboardReducer(initialState, {
        type: fetchDashboardSummary.pending.type,
      });
      expect(pendingState.summaryLoading).toBe(true);
      expect(pendingState.summaryError).toBeNull();

      // 2. Fulfilled
      const mockSummary = {
        total_investigations: 15,
        open_investigations: 5,
        investigations_under_investigation: 7,
        investigations_pending_capa: 2,
        completed_investigations: 1,
        total_capa_actions: 8,
        capa_actions_pending_review: 3,
      };
      const fulfilledState = dashboardReducer(pendingState, {
        type: fetchDashboardSummary.fulfilled.type,
        payload: mockSummary,
      });
      expect(fulfilledState.summaryLoading).toBe(false);
      expect(fulfilledState.summary).toEqual(mockSummary);
      expect(fulfilledState.summaryError).toBeNull();
    });

    it('handles fetchDashboardSummary lifecycle: rejected', () => {
      const initialState = {
        summary: null,
        summaryLoading: true,
        summaryError: null,
        activities: [],
        activitiesLoading: false,
        activitiesError: null,
      };

      const rejectedState = dashboardReducer(initialState, {
        type: fetchDashboardSummary.rejected.type,
        payload: 'Cannot connect to RootIQ backend',
      });
      expect(rejectedState.summaryLoading).toBe(false);
      expect(rejectedState.summaryError).toBe('Cannot connect to RootIQ backend');
    });
  });

  describe('investigationSlice state transitions', () => {
    it('handles fetchInvestigations lifecycle: pending -> fulfilled', () => {
      const initialState = {
        investigations: [],
        pagination: null,
        listLoading: false,
        listError: null,
      };

      const pendingState = investigationReducer(initialState, {
        type: fetchInvestigations.pending.type,
      });
      expect(pendingState.listLoading).toBe(true);

      const mockPayload = {
        items: [{ id: 'INV-1', title: 'Test Inv' }],
        pagination: { page: 1, limit: 10, total: 1, total_pages: 1 },
      };

      const fulfilledState = investigationReducer(pendingState, {
        type: fetchInvestigations.fulfilled.type,
        payload: mockPayload,
      });
      expect(fulfilledState.listLoading).toBe(false);
      expect(fulfilledState.investigations).toHaveLength(1);
      expect(fulfilledState.pagination.total).toBe(1);
    });

    it('handles fetchInvestigationById 404 response capturing statusCode', () => {
      const initialState = {
        currentInvestigation: { id: 'OLD-INV' },
        detailLoading: true,
        detailError: null,
        detailStatusCode: null,
      };

      const rejectedState = investigationReducer(initialState, {
        type: fetchInvestigationById.rejected.type,
        payload: {
          message: "Investigation 'INV-DOES-NOT-EXIST' not found.",
          statusCode: 404,
          isNetworkError: false,
        },
      });

      expect(rejectedState.detailLoading).toBe(false);
      expect(rejectedState.currentInvestigation).toBeNull();
      expect(rejectedState.detailStatusCode).toBe(404);
      expect(rejectedState.detailError).toContain('not found');
    });
  });
});
