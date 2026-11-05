import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import { Provider } from 'react-redux';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { configureStore } from '@reduxjs/toolkit';

import appReducer from '../redux/slices/appSlice';
import investigationReducer from '../redux/slices/investigationSlice';
import dashboardReducer from '../redux/slices/dashboardSlice';

import investigationService from '../services/investigationService';
import documentService from '../services/documentService';
import rcaService from '../services/rcaService';
import evidenceService from '../services/evidenceService';
import capaService from '../services/capaService';
import dashboardService from '../services/dashboardService';

import NewInvestigationPage from '../pages/Investigations/NewInvestigation';
import InvestigationDetailPage from '../pages/Investigations/InvestigationDetail';
import InvestigationsRegistryPage from '../pages/Investigations/index';

function createFullStore(preloadedState = {}) {
  return configureStore({
    reducer: {
      app: appReducer,
      investigations: investigationReducer,
      dashboard: dashboardReducer,
    },
    preloadedState,
  });
}

describe('RootIQ Full Lifecycle Integration: Intake -> RCA -> Evidence -> CAPA -> Retrieval', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it('executes the full investigation lifecycle seamlessly', async () => {
    const mockInvestigationId = 'INV-2026-9001';

    // 1. Mock Extraction API
    const mockExtractionResult = {
      analysis_id: 'EXT-9001',
      workflow_id: 'WF-EXT-9001',
      extraction_status: 'NEEDS_REVIEW',
      completeness_score: 92.0,
      overall_confidence: 0.96,
      extracted_data: {
        incident_title: {
          field_name: 'incident_title',
          value: 'Temperature excursion in Crystallizer CR-101',
          ai_extracted_value: 'Temperature excursion in Crystallizer CR-101',
          confidence_score: 0.98,
        },
        batch_number: {
          field_name: 'batch_number',
          value: 'BATCH-CR-8812',
          ai_extracted_value: 'BATCH-CR-8812',
          confidence_score: 0.99,
        },
        product_name: {
          field_name: 'product_name',
          value: 'Atorvastatin Calcium API',
          ai_extracted_value: 'Atorvastatin Calcium API',
          confidence_score: 0.95,
        },
        department: {
          field_name: 'department',
          value: 'Purification & Isolation',
          ai_extracted_value: 'Purification & Isolation',
          confidence_score: 0.94,
        },
        equipment_id: {
          field_name: 'equipment_id',
          value: 'CR-101',
          ai_extracted_value: 'CR-101',
          confidence_score: 0.97,
        },
        incident_description: {
          field_name: 'incident_description',
          value: 'During crystallization hold period at 10C, coolant valve V-204 failed to modulate.',
          confidence_score: 0.93,
        },
        immediate_action_taken: {
          field_name: 'immediate_action_taken',
          value: 'Switched to manual bypass chiller loop.',
          confidence_score: 0.91,
        },
      },
      critical_gaps: [],
      possible_contradictions: [],
      investigator_questions: ['Verify RTD calibration log from previous shift.'],
    };

    vi.spyOn(documentService, 'extractDocument').mockResolvedValue(mockExtractionResult);

    // 2. Mock Investigation Creation API
    const createdInvestigationData = {
      investigation_id: mockInvestigationId,
      incident_title: 'Temperature excursion in Crystallizer CR-101',
      batch_number: 'BATCH-CR-8812',
      product_name: 'Atorvastatin Calcium API',
      department: 'Purification & Isolation',
      equipment: 'CR-101',
      severity: 'Critical',
      investigation_status: 'Under Investigation',
      incident_date: '2026-11-05',
      incident_description: 'During crystallization hold period at 10C, coolant valve V-204 failed to modulate.',
      immediate_action_taken: 'Switched to manual bypass chiller loop.',
    };

    vi.spyOn(investigationService, 'createInvestigation').mockResolvedValue(createdInvestigationData);
    vi.spyOn(investigationService, 'getInvestigation').mockResolvedValue(createdInvestigationData);
    vi.spyOn(investigationService, 'listDocuments').mockResolvedValue([]);

    // 3. Mock RCA APIs
    const initialRCA = {
      five_whys: [
        {
          level: 1,
          question: 'Why did crystallizer temperature rise to 22C?',
          answer: 'Coolant circulation stopped.',
          status: 'Evidence-Supported',
          is_root_cause: false,
        },
      ],
      fishbone_causes: [
        {
          cause_id: 'C-M1',
          category: 'Machine',
          cause_description: 'Chilled water supply valve V-204 actuator diaphragm ruptured',
          status: 'Evidence-Supported',
        },
      ],
    };

    vi.spyOn(rcaService, 'getRCA').mockResolvedValue(initialRCA);
    vi.spyOn(rcaService, 'saveRCA').mockResolvedValue({ message: 'RCA findings recorded' });
    vi.spyOn(rcaService, 'generateRCA').mockResolvedValue({
      five_whys_analysis: [
        { level: 1, why_question: 'Why did temperature rise?', answer: 'Coolant stopped' },
        { level: 2, why_question: 'Why did coolant stop?', answer: 'Actuator diaphragm burst', is_root_cause: true },
      ],
      fishbone_analysis: [
        { cause_id: 'C-M2', category: 'Machine', cause_description: 'Valve diaphragm wear' },
      ],
      evidence_assessment: [],
    });

    // 4. Mock Evidence APIs
    const initialEvidence = [
      {
        evidence_id: 'EVID-001',
        description: 'SCADA Historian Temperature Profile: Shows spike from 10.2C to 22.4C over 45 minutes.',
        evidence_type: 'Supporting',
        source_reference: 'TAG:TI-CR101-01',
        review_status: 'Verified',
        created_at: '2026-11-05T08:00:00Z',
      },
    ];

    vi.spyOn(evidenceService, 'listEvidence').mockResolvedValue(initialEvidence);
    vi.spyOn(evidenceService, 'createEvidence').mockResolvedValue({
      evidence_id: 'EVID-002',
      description: 'Maintenance Work Order #8821: Valve diaphragm inspection report.',
      evidence_type: 'Supporting',
      source_reference: 'WO-8821.pdf',
      review_status: 'Pending Review',
      created_at: '2026-11-05T09:00:00Z',
    });

    // 5. Mock CAPA APIs
    const initialCAPA = [
      {
        action_id: 'CAPA-REC-01',
        action_type: 'Corrective Action',
        description: 'Replace actuator diaphragm on V-204 with reinforced EPDM specification.',
        action_owner: 'Maintenance Lead',
        target_date: '2026-11-20',
        effectiveness_verification_method: 'Cycle test valve 100 times under full differential pressure.',
        status: 'Pending Review',
      },
    ];

    vi.spyOn(capaService, 'listCAPA').mockResolvedValue(initialCAPA);
    vi.spyOn(capaService, 'generateCAPA').mockResolvedValue({
      capa_recommendations: initialCAPA,
    });
    vi.spyOn(capaService, 'createCAPA').mockResolvedValue({
      action_id: 'CAPA-MAN-02',
      action_type: 'Preventive Action',
      description: 'Update crystallizer preventive maintenance SOP to replace diaphragms every 12 months.',
      action_owner: 'Engineering Supervisor',
      target_date: '2026-12-15',
      effectiveness_verification_method: 'Audit maintenance compliance in subsequent annual reviews.',
      status: 'Proposed',
    });
    vi.spyOn(capaService, 'reviewCAPA').mockResolvedValue({
      workflow_id: 'WF-REV-9001',
      capa_review_status: 'REVIEWED',
      capa_recommendations: [
        {
          ...initialCAPA[0],
          status: 'Approved',
        },
      ],
    });
    vi.spyOn(capaService, 'updateCAPAStatus').mockResolvedValue({
      ...initialCAPA[0],
      status: 'Approved',
    });

    // 6. Mock Dashboard APIs
    vi.spyOn(dashboardService, 'getSummary').mockResolvedValue({
      total_investigations: 1,
      open_investigations: 1,
      investigations_under_investigation: 1,
      investigations_pending_capa: 0,
      completed_investigations: 0,
    });
    vi.spyOn(dashboardService, 'getActivities').mockResolvedValue([]);

    // Initialize Store
    const store = createFullStore();

    // Render the App with Routing
    render(
      <Provider store={store}>
        <MemoryRouter initialEntries={[`/investigations/${mockInvestigationId}`]}>
          <Routes>
            <Route path="/investigations/:id" element={<InvestigationDetailPage />} />
          </Routes>
        </MemoryRouter>
      </Provider>
    );

    // STEP 1: Verify Overview Tab is loaded with PostgreSQL persisted data
    await waitFor(() => {
      expect(screen.getByDisplayValue('BATCH-CR-8812')).toBeDefined();
      expect(screen.getByDisplayValue('Atorvastatin Calcium API')).toBeDefined();
      expect(screen.getByDisplayValue('CR-101')).toBeDefined();
    });

    expect(screen.getByText('Manufacturing Incident Record')).toBeDefined();
    expect(screen.getByText(/Modifications persist in PostgreSQL/i)).toBeDefined();

    // STEP 2: Navigate to RCA Tab and verify 5-Whys and Fishbone
    const rcaTabBtns = screen.getAllByRole('button', { name: /rca analysis/i });
    fireEvent.click(rcaTabBtns[0]);

    await waitFor(() => {
      expect(screen.getByText('Linear Causal Drilldown (5-Whys Methodology)')).toBeDefined();
      expect(screen.getByText('Why did crystallizer temperature rise to 22C?')).toBeDefined();
    });

    // Test AI 5-Whys Generation Trigger
    const aiRcaBtn = screen.getByRole('button', { name: /generate ai 5-whys/i });
    fireEvent.click(aiRcaBtn);

    await waitFor(() => {
      expect(rcaService.generateRCA).toHaveBeenCalledWith(
        mockInvestigationId,
        expect.objectContaining({
          problem_statement: expect.any(String),
        })
      );
    });

    // Switch to Fishbone Sub-method
    const fishboneMethodBtn = screen.getByRole('button', { name: /6m ishikawa/i });
    fireEvent.click(fishboneMethodBtn);

    await waitFor(() => {
      expect(screen.getByText('6M Multi-Factor Causal Analysis Matrix')).toBeDefined();
      expect(screen.getByText('Valve diaphragm wear')).toBeDefined();
    });

    // STEP 3: Navigate to Evidence & Gaps Tab
    const evidenceTabBtns = screen.getAllByRole('button', { name: /evidence/i });
    fireEvent.click(evidenceTabBtns[0]);

    await waitFor(() => {
      expect(screen.getByText('Evidence Repository & Gap Analysis')).toBeDefined();
      expect(screen.getByText(/TAG:TI-CR101-01/i)).toBeDefined();
    });

    // Add new evidence artifact
    const addEvidenceBtn = screen.getByRole('button', { name: /add evidence item/i });
    fireEvent.click(addEvidenceBtn);

    expect(screen.getByText('Link New Evidence or Inquiry')).toBeDefined();
    const titleInput = screen.getByPlaceholderText(/Chiller secondary flow transmitter/i);
    fireEvent.change(titleInput, { target: { value: 'Maintenance Work Order #8821' } });

    const linkBtn = screen.getByRole('button', { name: /link evidence/i });
    fireEvent.click(linkBtn);

    await waitFor(() => {
      expect(evidenceService.createEvidence).toHaveBeenCalledWith(
        mockInvestigationId,
        expect.objectContaining({
          description: expect.stringContaining('Maintenance Work Order #8821'),
        })
      );
    });

    // STEP 4: Navigate to CAPA Tab
    const capaTabBtns = screen.getAllByRole('button', { name: /capa/i });
    fireEvent.click(capaTabBtns[0]);

    await waitFor(() => {
      expect(screen.getByText('Corrective & Preventive Actions (CAPA) Workspace')).toBeDefined();
      expect(screen.getByText(/Replace actuator diaphragm on V-204 with reinforced EPDM specification/i)).toBeDefined();
    });

    // Perform QA Human Approval Gate
    const approveActionBtn = screen.getByRole('button', { name: /approve action/i });
    fireEvent.click(approveActionBtn);

    await waitFor(() => {
      expect(capaService.updateCAPAStatus).toHaveBeenCalledWith(
        mockInvestigationId,
        'CAPA-REC-01',
        { status: 'Approved', notes: null }
      );
    });

    // Propose Manual Action
    const proposeBtn = screen.getByRole('button', { name: /propose action/i });
    fireEvent.click(proposeBtn);

    await waitFor(() => {
      expect(screen.getByText(/Propose New CAPA Remediation Action/i)).toBeDefined();
    });
  });
});
