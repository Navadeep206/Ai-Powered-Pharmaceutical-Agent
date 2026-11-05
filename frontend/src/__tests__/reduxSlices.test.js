import { describe, it, expect } from 'vitest';
import dashboardReducer, {
  fetchDashboardSummary,
  fetchDashboardActivities,
} from '../redux/slices/dashboardSlice';
import investigationReducer, {
  fetchInvestigations,
  fetchInvestigationById,
  analyzeIncidentIntake,
  updateExtractedField,
  revertExtractedField,
  resetDraftIntake,
} from '../redux/slices/investigationSlice';
import {
  normalizeInvestigation,
  normalizeActivity,
  normalizeExtractedField,
  normalizeExtractionResponse,
  buildInvestigationPayloadFromReviewedData,
} from '../utils/normalizers';

describe('Redux Slices & Normalizers', () => {
  describe('investigation normalizers', () => {
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

  describe('extraction normalizers', () => {
    it('normalizes rich ExtractedField preserving AI value and provenance', () => {
      const rawField = {
        field_name: 'batch_number',
        value: 'BATCH-2026-9921',
        ai_extracted_value: 'BATCH-2026-9921',
        human_edited_value: null,
        is_human_modified: false,
        confidence_score: 0.98,
        source_reference: {
          source_type: 'Document',
          page_number: 2,
          excerpt: 'Batch identifier: BATCH-2026-9921',
          is_traceable: true,
        },
        extraction_status: 'EXTRACTED',
        review_status: 'AI_SUGGESTED',
        validation_warnings: [],
      };

      const normalized = normalizeExtractedField(rawField, 'batch_number');
      expect(normalized.fieldName).toBe('batch_number');
      expect(normalized.value).toBe('BATCH-2026-9921');
      expect(normalized.ai_extracted_value).toBe('BATCH-2026-9921');
      expect(normalized.confidence_score).toBe(0.98);
      expect(normalized.source_reference.page_number).toBe(2);
      expect(normalized.source_reference.excerpt).toContain('BATCH-2026-9921');
    });

    it('normalizes full backend ExtractionAnalysisResponse', () => {
      const backendResponse = {
        analysis_id: 'EXT-1234',
        workflow_id: 'WF-EXT-5678',
        extraction_status: 'NEEDS_REVIEW',
        completeness_score: 87.5,
        overall_confidence: 0.94,
        disclaimer: 'Human review required prior to RCA.',
        extracted_data: {
          incident_title: {
            field_name: 'incident_title',
            value: 'Thermal excursion during crystallization',
            ai_extracted_value: 'Thermal excursion during crystallization',
            confidence_score: 0.99,
          },
          batch_number: {
            field_name: 'batch_number',
            value: 'BATCH-99',
            confidence_score: 0.95,
          },
          equipment_id: {
            field_name: 'equipment_id',
            value: 'R-102',
            confidence_score: 0.92,
          },
        },
        critical_gaps: [
          {
            field_name: 'detection_date',
            category: 'Critical GxP',
            rationale: 'Required for deviation filing deadline.',
          },
        ],
        possible_contradictions: [
          {
            field_name: 'batch_number',
            conflicting_values: ['BATCH-99', 'BATCH-99A'],
            description: 'Discrepancy between header and page 2',
          },
        ],
        investigator_questions: ['What was the operator log entry at 04:00 UTC?'],
      };

      const normalized = normalizeExtractionResponse(backendResponse);
      expect(normalized.analysisId).toBe('EXT-1234');
      expect(normalized.completenessScore).toBe(87.5);
      expect(normalized.overallConfidence).toBe(0.94);
      expect(normalized.incidentInfo.incidentTitle).toBe('Thermal excursion during crystallization');
      expect(normalized.incidentInfo.batchNumber).toBe('BATCH-99');
      expect(normalized.incidentInfo.equipment).toBe('R-102');
      expect(normalized.fieldMeta.equipment_id.value).toBe('R-102');
      expect(normalized.criticalGaps).toHaveLength(1);
      expect(normalized.possibleContradictions).toHaveLength(1);
      expect(normalized.investigatorQuestions).toHaveLength(1);
    });

    it('builds compliant InvestigationCreate payload from reviewed form data', () => {
      const extractedData = {
        incidentInfo: {
          incidentTitle: 'Impurity Spike in Drying Phase',
          incidentDescription: 'Chromatography showed 0.4% unknown peak.',
          severity: 'Critical',
          batchNumber: 'LOT-5541',
          productName: 'Metformin HCl',
          department: 'Purification',
          equipment: 'DRY-01',
          incidentDate: '2026-03-15',
          detectionDate: '2026-03-15',
          immediateActionTaken: 'Lot quarantined in warehouse',
        },
        context: {
          expectedCondition: 'Impurity < 0.1%',
          actualCondition: 'Impurity at 0.4%',
          observedImpact: 'Batch quarantined pending OOS investigation',
          affectedProcess: 'Fluid Bed Drying',
          initialObservations: 'Filter bag showed minor tear',
        },
      };

      const payload = buildInvestigationPayloadFromReviewedData(extractedData);
      expect(payload.incident_title).toBe('Impurity Spike in Drying Phase');
      expect(payload.incident_description).toBe('Chromatography showed 0.4% unknown peak.');
      expect(payload.severity).toBe('Critical');
      expect(payload.batch_number).toBe('LOT-5541');
      expect(payload.product_name).toBe('Metformin HCl');
      expect(payload.equipment).toBe('DRY-01');
      expect(payload.incident_date).toBe('2026-03-15');
      expect(payload.immediate_action_taken).toBe('Lot quarantined in warehouse');
      expect(payload.expected_condition).toBe('Impurity < 0.1%');
      expect(payload.actual_condition).toBe('Impurity at 0.4%');
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

      const pendingState = dashboardReducer(initialState, {
        type: fetchDashboardSummary.pending.type,
      });
      expect(pendingState.summaryLoading).toBe(true);
      expect(pendingState.summaryError).toBeNull();

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

    it('handles analyzeIncidentIntake lifecycle: pending -> fulfilled', () => {
      const initialState = {
        draftIntake: {
          method: 'upload',
          extractionState: 'idle',
          analysisProgress: 'idle',
          extractedData: null,
          isEdited: false,
        },
      };

      const pendingState = investigationReducer(initialState, {
        type: analyzeIncidentIntake.pending.type,
      });
      expect(pendingState.draftIntake.extractionState).toBe('analyzing');

      const mockResponse = {
        analysisId: 'EXT-TEST',
        completenessScore: 80,
        incidentInfo: { incidentTitle: 'Test Anomaly' },
        context: {},
        fieldMeta: {},
      };

      const fulfilledState = investigationReducer(pendingState, {
        type: analyzeIncidentIntake.fulfilled.type,
        payload: mockResponse,
      });
      expect(fulfilledState.draftIntake.extractionState).toBe('extracted');
      expect(fulfilledState.draftIntake.analysisProgress).toBe('completed');
      expect(fulfilledState.draftIntake.extractedData.incidentInfo.incidentTitle).toBe('Test Anomaly');
      expect(fulfilledState.draftIntake.isEdited).toBe(false);
    });

    it('supports field editing and reverting to original AI value', () => {
      const initialState = {
        draftIntake: {
          extractionState: 'extracted',
          isEdited: false,
          extractedData: {
            incidentInfo: {
              batchNumber: 'AI-ORIGINAL-BATCH',
            },
            context: {},
            fieldMeta: {
              batch_number: {
                fieldName: 'batch_number',
                value: 'AI-ORIGINAL-BATCH',
                ai_extracted_value: 'AI-ORIGINAL-BATCH',
                human_edited_value: null,
                is_human_modified: false,
                review_status: 'AI_SUGGESTED',
              },
            },
          },
        },
      };

      // 1. Edit field
      const editedState = investigationReducer(
        initialState,
        updateExtractedField({
          section: 'incidentInfo',
          field: 'batchNumber',
          value: 'HUMAN-CORRECTED-BATCH',
          canonicalKey: 'batch_number',
        })
      );

      expect(editedState.draftIntake.extractedData.incidentInfo.batchNumber).toBe('HUMAN-CORRECTED-BATCH');
      expect(editedState.draftIntake.extractedData.fieldMeta.batch_number.value).toBe('HUMAN-CORRECTED-BATCH');
      expect(editedState.draftIntake.extractedData.fieldMeta.batch_number.human_edited_value).toBe('HUMAN-CORRECTED-BATCH');
      expect(editedState.draftIntake.extractedData.fieldMeta.batch_number.is_human_modified).toBe(true);
      expect(editedState.draftIntake.extractedData.fieldMeta.batch_number.review_status).toBe('HUMAN_REVIEWED');
      expect(editedState.draftIntake.extractedData.fieldMeta.batch_number.ai_extracted_value).toBe('AI-ORIGINAL-BATCH');
      expect(editedState.draftIntake.isEdited).toBe(true);

      // 2. Revert field back to AI extraction
      const revertedState = investigationReducer(
        editedState,
        revertExtractedField({
          section: 'incidentInfo',
          field: 'batchNumber',
          canonicalKey: 'batch_number',
        })
      );

      expect(revertedState.draftIntake.extractedData.incidentInfo.batchNumber).toBe('AI-ORIGINAL-BATCH');
      expect(revertedState.draftIntake.extractedData.fieldMeta.batch_number.value).toBe('AI-ORIGINAL-BATCH');
      expect(revertedState.draftIntake.extractedData.fieldMeta.batch_number.is_human_modified).toBe(false);
      expect(revertedState.draftIntake.extractedData.fieldMeta.batch_number.review_status).toBe('AI_SUGGESTED');
    });

    it('handles resetDraftIntake restoring pristine intake form', () => {
      const dirtyState = {
        draftIntake: {
          method: 'text',
          rawText: 'Some long text',
          extractionState: 'extracted',
          extractedData: { incidentInfo: {} },
          isEdited: true,
        },
      };

      const resetState = investigationReducer(dirtyState, resetDraftIntake());
      expect(resetState.draftIntake.method).toBe('upload');
      expect(resetState.draftIntake.rawText).toBe('');
      expect(resetState.draftIntake.extractionState).toBe('idle');
      expect(resetState.draftIntake.extractedData).toBeNull();
      expect(resetState.draftIntake.isEdited).toBe(false);
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
