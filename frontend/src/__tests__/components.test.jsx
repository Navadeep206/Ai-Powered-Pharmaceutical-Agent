import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import { Provider } from 'react-redux';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { configureStore } from '@reduxjs/toolkit';
import appReducer from '../redux/slices/appSlice';
import investigationReducer from '../redux/slices/investigationSlice';
import dashboardReducer from '../redux/slices/dashboardSlice';

import dashboardService from '../services/dashboardService';
import investigationService from '../services/investigationService';
import documentService from '../services/documentService';
import rcaService from '../services/rcaService';
import evidenceService from '../services/evidenceService';
import capaService from '../services/capaService';

import DashboardPage from '../pages/Dashboard/index';
import InvestigationsPage from '../pages/Investigations/index';
import InvestigationDetailPage from '../pages/Investigations/InvestigationDetail';
import NewInvestigationPage from '../pages/Investigations/NewInvestigation';
import ExtractionReviewForm from '../components/investigation/ExtractionReviewForm';
import FiveWhysAnalysis from '../components/investigation/FiveWhysAnalysis';
import FishboneAnalysis from '../components/investigation/FishboneAnalysis';
import EvidenceList from '../components/investigation/EvidenceList';
import CAPAForm from '../components/investigation/CAPAForm';
import CAPAManagementPage from '../pages/CAPAManagement';
import Sidebar from '../components/layout/Sidebar';
import StatusDistribution from '../components/dashboard/StatusDistribution';
import RecentInvestigations from '../components/dashboard/RecentInvestigations';
import RecentActivity from '../components/dashboard/RecentActivity';
import { normalizeExtractionResponse } from '../utils/normalizers';

function createMockStore(preloadedState = {}) {
  return configureStore({
    reducer: {
      app: appReducer,
      investigations: investigationReducer,
      dashboard: dashboardReducer,
    },
    preloadedState,
  });
}

describe('Frontend Component Integration Tests', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  describe('StatusDistribution Component', () => {
    it('computes correct percentages from backend summary', () => {
      const summary = {
        total_investigations: 100,
        open_investigations: 30,
        investigations_under_investigation: 50,
        investigations_pending_capa: 10,
        completed_investigations: 10,
      };

      render(<StatusDistribution summary={summary} />);
      expect(screen.getByText('50%')).toBeDefined();
      expect(screen.getByText('30%')).toBeDefined();
      expect(screen.getByText(/100 Total Recorded/)).toBeDefined();
    });

    it('gracefully handles empty database state without dividing by zero', () => {
      const summary = {
        total_investigations: 0,
        open_investigations: 0,
        investigations_under_investigation: 0,
        investigations_pending_capa: 0,
        completed_investigations: 0,
      };

      render(<StatusDistribution summary={summary} />);
      expect(screen.getByText('0 Records')).toBeDefined();
      expect(screen.getAllByText('0%').length).toBe(4);
    });
  });

  describe('RecentInvestigations Component', () => {
    it('displays loading spinner when loading is true', () => {
      render(
        <MemoryRouter>
          <RecentInvestigations loading={true} investigations={[]} />
        </MemoryRouter>
      );
      expect(screen.getByText(/loading recent investigations/i)).toBeDefined();
    });

    it('displays empty state when no records are present', () => {
      render(
        <MemoryRouter>
          <RecentInvestigations loading={false} investigations={[]} />
        </MemoryRouter>
      );
      expect(screen.getByText('No recent investigations')).toBeDefined();
    });

    it('renders list of investigations with proper IDs and links', () => {
      const mockItems = [
        {
          id: 'INV-2026-0001',
          title: 'Reactor cooling excursion',
          batch: 'BATCH-A1',
          department: 'Synthesis',
          severity: 'Critical',
          status: 'Under Investigation',
          date: '2026-11-01',
        },
      ];

      render(
        <MemoryRouter>
          <RecentInvestigations loading={false} investigations={mockItems} />
        </MemoryRouter>
      );

      expect(screen.getByText('INV-2026-0001')).toBeDefined();
      expect(screen.getByText('Reactor cooling excursion')).toBeDefined();
      expect(screen.getByText('Synthesis')).toBeDefined();
    });
  });

  describe('RecentActivity Component', () => {
    it('renders list of audit activities', () => {
      const activities = [
        {
          id: '1',
          description: 'Investigation initiated',
          detail: 'Logged by QA Officer',
          time: '10m ago',
          iconName: 'PlusCircle',
          iconColor: 'text-[#0F9D91]',
          iconBg: 'bg-[#E6F7F5]',
        },
      ];

      render(<RecentActivity loading={false} activities={activities} />);
      expect(screen.getByText('Investigation initiated')).toBeDefined();
      expect(screen.getByText('10m ago')).toBeDefined();
      expect(screen.getByText('Logged by QA Officer')).toBeDefined();
    });
  });

  describe('DashboardPage Integration', () => {
    it('fetches and renders dashboard metrics from backend API', async () => {
      vi.spyOn(dashboardService, 'getSummary').mockResolvedValue({
        total_investigations: 12,
        open_investigations: 4,
        investigations_under_investigation: 6,
        investigations_pending_capa: 2,
        completed_investigations: 0,
        total_capa_actions: 5,
        capa_actions_pending_review: 3,
      });

      vi.spyOn(dashboardService, 'getActivities').mockResolvedValue([
        {
          activity_id: 'act-1',
          description: 'Deviation registered',
          actor_identifier: 'QA Specialist',
          activity_type: 'INVESTIGATION_CREATED',
          created_at: new Date().toISOString(),
        },
      ]);

      vi.spyOn(investigationService, 'listInvestigations').mockResolvedValue({
        items: [
          {
            investigation_id: 'INV-2026-0001',
            incident_title: 'Centrifuge seal failure',
            batch_number: 'BATCH-99',
            department: 'Purification',
            severity: 'High',
            investigation_status: 'Open',
            incident_date: '2026-11-04',
          },
        ],
        pagination: { total: 1 },
      });

      const store = createMockStore();

      render(
        <Provider store={store}>
          <MemoryRouter>
            <DashboardPage />
          </MemoryRouter>
        </Provider>
      );

      await waitFor(() => {
        expect(screen.getAllByText('12').length).toBeGreaterThan(0);
        expect(screen.getByText('Centrifuge seal failure')).toBeDefined();
        expect(screen.getByText('Deviation registered')).toBeDefined();
      });
    });

    it('displays error banner and retry button on network failure', async () => {
      vi.spyOn(dashboardService, 'getSummary').mockRejectedValue(
        new Error('Cannot connect to the RootIQ backend API.')
      );
      vi.spyOn(dashboardService, 'getActivities').mockResolvedValue([]);
      vi.spyOn(investigationService, 'listInvestigations').mockResolvedValue({ items: [], pagination: {} });

      const store = createMockStore();

      render(
        <Provider store={store}>
          <MemoryRouter>
            <DashboardPage />
          </MemoryRouter>
        </Provider>
      );

      await waitFor(() => {
        expect(screen.getByText(/Cannot connect to the RootIQ backend API/i)).toBeDefined();
        expect(screen.getByRole('button', { name: /retry/i })).toBeDefined();
      });
    });
  });

  describe('InvestigationsPage (Registry) Integration', () => {
    it('fetches investigations list and renders table columns', async () => {
      vi.spyOn(investigationService, 'listInvestigations').mockResolvedValue({
        items: [
          {
            investigation_id: 'INV-2026-0042',
            incident_title: 'Filter membrane puncture',
            batch_number: 'BATCH-MEM-1',
            department: 'Filtration',
            severity: 'Critical',
            investigation_status: 'Open',
            incident_date: '2026-11-02',
            detection_date: '2026-11-02',
            product_name: 'Sterile Water API',
          },
        ],
        pagination: { page: 1, limit: 10, total: 1, total_pages: 1 },
      });

      const store = createMockStore();

      render(
        <Provider store={store}>
          <MemoryRouter>
            <InvestigationsPage />
          </MemoryRouter>
        </Provider>
      );

      await waitFor(() => {
        expect(screen.getByText('INV-2026-0042')).toBeDefined();
        expect(screen.getByText('Filter membrane puncture')).toBeDefined();
        expect(screen.getByText('BATCH-MEM-1')).toBeDefined();
      });
    });
  });

  describe('InvestigationDetailPage Integration', () => {
    it('renders 404 state when investigation is not found', async () => {
      const err = new Error("Investigation 'INV-MISSING' not found.");
      err.statusCode = 404;
      vi.spyOn(investigationService, 'getInvestigation').mockRejectedValue(err);
      vi.spyOn(rcaService, 'getRCA').mockResolvedValue({});
      vi.spyOn(evidenceService, 'listEvidence').mockResolvedValue([]);
      vi.spyOn(capaService, 'listCAPA').mockResolvedValue([]);

      const store = createMockStore();

      render(
        <Provider store={store}>
          <MemoryRouter initialEntries={['/investigations/INV-MISSING']}>
            <Routes>
              <Route path="/investigations/:id" element={<InvestigationDetailPage />} />
            </Routes>
          </MemoryRouter>
        </Provider>
      );

      await waitFor(() => {
        expect(screen.getByText('Investigation Not Found')).toBeDefined();
        expect(screen.getByText(/could not be found in the quality registry/i)).toBeDefined();
        expect(screen.getByRole('button', { name: /return to investigations registry/i })).toBeDefined();
      });
    });

    it('renders investigation details when retrieved from database', async () => {
      vi.spyOn(investigationService, 'getInvestigation').mockResolvedValue({
        investigation_id: 'INV-2026-8888',
        incident_title: 'Coolant temperature excursion',
        batch_number: 'BATCH-K4',
        department: 'Synthesis',
        product_name: 'Rosuvastatin',
        equipment: 'R-201',
        incident_description: 'Jacket temperature rose 14 C above limit.',
        immediate_action_taken: 'Manual bypass valve engaged.',
        severity: 'Critical',
        investigation_status: 'Under Investigation',
        incident_date: '2026-11-03',
      });
      vi.spyOn(rcaService, 'getRCA').mockResolvedValue({ five_whys: [], fishbone_causes: [] });
      vi.spyOn(evidenceService, 'listEvidence').mockResolvedValue([]);
      vi.spyOn(capaService, 'listCAPA').mockResolvedValue([]);

      const store = createMockStore();

      render(
        <Provider store={store}>
          <MemoryRouter initialEntries={['/investigations/INV-2026-8888']}>
            <Routes>
              <Route path="/investigations/:id" element={<InvestigationDetailPage />} />
            </Routes>
          </MemoryRouter>
        </Provider>
      );

      await waitFor(() => {
        expect(screen.getByText('Coolant temperature excursion')).toBeDefined();
        expect(screen.getByDisplayValue('BATCH-K4')).toBeDefined();
        expect(screen.getByDisplayValue('Synthesis')).toBeDefined();
      });
    });
  });

  describe('ExtractionReviewForm & NewInvestigationPage Integration', () => {
    it('renders ExtractionReviewForm with provenance scores and citations', () => {
      const mockExtractedData = {
        completenessScore: 88,
        overallConfidence: 0.95,
        extractionStatus: 'NEEDS_REVIEW',
        disclaimer: 'GxP verification notice',
        incidentInfo: {
          deviationId: 'DEV-2026-0891',
          batchNumber: 'BATCH-2026-9921',
          severity: 'Critical',
          incidentTitle: 'Thermal Excursion in Synthesis',
          productName: 'Atorvastatin API',
          department: 'Synthesis',
          equipment: 'R-102',
          incidentDate: '2026-03-02',
          detectionDate: '2026-03-02',
          incidentDescription: 'Vessel temperature spike reached 84.5 C.',
          immediateActionTaken: 'Glycol cooling increased to 100%.',
        },
        context: {
          expectedCondition: '65.0 - 70.0 C',
          actualCondition: '84.5 C',
          observedImpact: 'Potential polymorphic impurity',
          affectedProcess: 'Stage 3 Crystallization',
          initialObservations: 'Discoloration noted',
        },
        fieldMeta: {
          batch_number: {
            fieldName: 'batch_number',
            value: 'BATCH-2026-9921',
            confidence_score: 0.98,
            extraction_status: 'EXTRACTED',
            source_reference: {
              source_type: 'Document',
              page_number: 1,
              excerpt: 'Batch identifier BATCH-2026-9921 recorded in synthesis.',
            },
          },
          equipment_id: {
            fieldName: 'equipment_id',
            value: 'R-102',
            confidence_score: 0.65, // Low confidence
            extraction_status: 'EXTRACTED',
          },
        },
        criticalGaps: [
          {
            field_name: 'detection_method',
            category: 'Critical GxP',
            rationale: 'Mandatory detection logging.',
            suggested_action: 'Check SCADA alarm history.',
          },
        ],
        possibleContradictions: [
          {
            field_name: 'batch_number',
            conflicting_values: ['BATCH-2026-9921', 'BATCH-2026-9922'],
            description: 'Conflict in paragraph 3.',
          },
        ],
        investigatorQuestions: ['Did operator acknowledge SCADA Alarm T-HIGH-102?'],
      };

      const handleUpdate = vi.fn();
      const handleRevert = vi.fn();
      const handleSave = vi.fn();
      const handleContinue = vi.fn();

      render(
        <ExtractionReviewForm
          extractedData={mockExtractedData}
          onUpdateField={handleUpdate}
          onRevertField={handleRevert}
          onSaveDraft={handleSave}
          onContinueToRCA={handleContinue}
          isDraftSaved={false}
          isSubmitting={false}
        />
      );

      // Verify KPI Strip
      expect(screen.getByText('88%')).toBeDefined();
      expect(screen.getByText('95%')).toBeDefined();
      expect(screen.getByText('1 GxP gap(s) to address')).toBeDefined();

      // Verify Field Display
      expect(screen.getByDisplayValue('BATCH-2026-9921')).toBeDefined();
      expect(screen.getByDisplayValue('DEV-2026-0891')).toBeDefined();
      expect(screen.getByText('98%')).toBeDefined();
      expect(screen.getByText('Low: 65%')).toBeDefined();

      // Verify Citation Toggle & Content
      const citationButtons = screen.getAllByText('View citation');
      expect(citationButtons.length).toBeGreaterThan(0);
      fireEvent.click(citationButtons[0]);
      expect(screen.getByText(/Batch identifier BATCH-2026-9921 recorded in synthesis/)).toBeDefined();

      // Verify Critical Gaps Panel
      expect(screen.getByText(/Critical GxP Evidence Gaps \(1\)/i)).toBeDefined();
      expect(screen.getByText('Mandatory detection logging.')).toBeDefined();

      // Verify Contradictions Panel & Field Contradiction Alert
      expect(screen.getByText(/Conflicting Source Statements \(1\)/i)).toBeDefined();
      expect(screen.getAllByText('Conflict in paragraph 3.').length).toBeGreaterThan(0);

      // Verify Buttons
      const continueButtons = screen.getAllByRole('button', { name: /continue to rca/i });
      fireEvent.click(continueButtons[0]);
      expect(handleContinue).toHaveBeenCalled();
    });

    it('NewInvestigationPage dispatches real extraction workflow', async () => {
      const mockExtractionResult = {
        analysis_id: 'EXT-NEW-01',
        workflow_id: 'WF-01',
        extraction_status: 'NEEDS_REVIEW',
        completeness_score: 80,
        overall_confidence: 0.9,
        extracted_data: {
          incident_title: { value: 'Reactor pressure excursion' },
          incident_description: { value: 'Pressure peaked during inerting' },
          batch_number: { value: 'B-772' },
        },
      };

      vi.spyOn(documentService, 'extractDocument').mockResolvedValue(mockExtractionResult);

      const store = createMockStore();

      render(
        <Provider store={store}>
          <MemoryRouter initialEntries={['/investigations/new']}>
            <Routes>
              <Route path="/investigations/new" element={<NewInvestigationPage />} />
            </Routes>
          </MemoryRouter>
        </Provider>
      );

      // Switch to text intake
      const textMethodButton = screen.getByText(/Paste Description/i);
      fireEvent.click(textMethodButton);

      // Enter narrative text
      const textarea = screen.getByPlaceholderText(/Provide detailed incident observations/i);
      fireEvent.change(textarea, {
        target: {
          value: 'On 2026-03-24 reactor pressure peaked at 4.2 bar exceeding the 2.5 bar safety threshold during nitrogen purge of batch B-772.',
        },
      });

      // Click analyze incident
      const analyzeButton = screen.getByRole('button', { name: /analyze incident/i });
      fireEvent.click(analyzeButton);

      await waitFor(() => {
        expect(documentService.extractDocument).toHaveBeenCalledTimes(1);
        expect(screen.getByText('Verify Extracted Deviation Record')).toBeDefined();
      });
    });

    it('NewInvestigationPage keeps intake page visible during analyzing state and renders 4-step progress stepper', () => {
      const store = createMockStore({
        investigations: {
          draftIntake: {
            method: 'upload',
            fileInfo: {
              name: 'Incident_Report_BMR.pdf',
              size: '1.2 MB',
              rawBytes: 1258291,
              type: 'application/pdf',
              lastModified: '11/04/2026',
            },
            rawText: '',
            emailSubject: '',
            emailBody: '',
            extractionState: 'analyzing',
            analysisProgress: 'extracting',
            extractionError: null,
            extractedData: null,
          },
        },
      });

      render(
        <Provider store={store}>
          <MemoryRouter initialEntries={['/investigations/new']}>
            <Routes>
              <Route path="/investigations/new" element={<NewInvestigationPage />} />
            </Routes>
          </MemoryRouter>
        </Provider>
      );

      // Intake page and uploaded file card must stay visible!
      expect(screen.getByText('Incident_Report_BMR.pdf')).toBeDefined();
      expect(screen.getByText(/Analyzing Quality Incident Intake/i)).toBeDefined();

      // 4-Step progress stepper states must be present
      expect(screen.getByText(/1\. Uploading/i)).toBeDefined();
      expect(screen.getByText(/2\. Extracting document/i)).toBeDefined();
      expect(screen.getByText(/3\. AI analysis/i)).toBeDefined();
      expect(screen.getByText(/4\. Results ready/i)).toBeDefined();

      // Analyze Incident button must be disabled with spinner during analysis
      const analyzeButton = screen.getByRole('button', { name: /analyzing incident\.\.\./i });
      expect(analyzeButton.disabled).toBe(true);
    });

    it('NewInvestigationPage renders clear readable error notice on extraction failure without crashing or blanking, preserving uploaded file', () => {
      const store = createMockStore({
        investigations: {
          draftIntake: {
            method: 'upload',
            fileInfo: {
              name: 'RootIQ_Sample_Pharmaceutical_Incident_Report.pdf',
              size: '254 KB',
              rawBytes: 260000,
              type: 'application/pdf',
              lastModified: '11/04/2026',
            },
            rawText: '',
            emailSubject: '',
            emailBody: '',
            extractionState: 'failed',
            analysisProgress: 'failed',
            extractionError: 'The request timed out while communicating with the RootIQ backend server. Please try again.',
            extractedData: null,
          },
        },
      });

      render(
        <Provider store={store}>
          <MemoryRouter initialEntries={['/investigations/new']}>
            <Routes>
              <Route path="/investigations/new" element={<NewInvestigationPage />} />
            </Routes>
          </MemoryRouter>
        </Provider>
      );

      // The page must NOT be blank
      expect(screen.getByText(/AI Extraction Notice/i)).toBeDefined();
      expect(screen.getByText(/The request timed out while communicating with the RootIQ backend server/i)).toBeDefined();

      // Uploaded file info is still preserved on error
      expect(screen.getByText('RootIQ_Sample_Pharmaceutical_Incident_Report.pdf')).toBeDefined();

      // Action buttons: Retry Analysis & Proceed with Manual Entry (verifying ArrowRight renders properly)
      expect(screen.getByRole('button', { name: /retry analysis/i })).toBeDefined();
      expect(screen.getByRole('button', { name: /proceed with manual entry/i })).toBeDefined();
    });

    it('ExtractionReviewForm renders Citation unverified badge, caps confidence, and allows editing detection_method', () => {
      const handleUpdate = vi.fn();
      const mockExtractedData = {
        completenessScore: 85,
        overallConfidence: 0.88,
        extractionStatus: 'NEEDS_REVIEW',
        disclaimer: 'GxP verification notice',
        incidentInfo: {
          deviationId: 'DEV-2026-0891',
          batchNumber: 'BATCH-API-26-041',
          severity: 'Medium',
          incidentTitle: 'High Temperature Excursion in FBD-204',
          productName: 'Paracetamol High-Density Granules',
          department: 'Solid Oral Dosage',
          equipment: 'Fluid Bed Dryer FBD-204',
          incidentDate: '2026-11-04',
          detectionDate: '2026-11-04',
          incidentDescription: 'Temperature recorded at 56.8 C for 22 minutes.',
          immediateActionTaken: 'Operator paused drying cycle at 10:38',
        },
        context: {
          expectedCondition: '48-52 C',
          actualCondition: 'Peak 56.8 C',
          observedImpact: '',
          affectedProcess: 'Final drying',
          initialObservations: 'Alarm acknowledged at 10:17',
        },
        additionalContext: {
          detectionMethod: 'High-temperature alarm acknowledged by operator',
        },
        fieldMeta: {
          detection_method: {
            field_name: 'detection_method',
            value: 'High-temperature alarm acknowledged by operator',
            confidence_score: 0.95,
            extraction_status: 'EXTRACTED',
            source_reference: {
              source_type: 'Document',
              page_number: 1,
              excerpt: 'operator noticed the high-temperature alarm',
              char_offset_start: 896,
              char_offset_end: 939,
              is_traceable: true,
            },
            validation_warnings: [],
          },
          immediate_action_taken: {
            field_name: 'immediate_action_taken',
            value: 'Operator paused drying cycle at 10:38',
            confidence_score: 0.70,
            extraction_status: 'EXTRACTED',
            source_reference: {
              source_type: 'Document',
              page_number: 1,
              excerpt: 'operator paused the drying cycle ... entered a quality-hold instruction',
              char_offset_start: null,
              char_offset_end: null,
              is_traceable: false,
            },
            validation_warnings: [
              "Citation unverified — investigator review required: excerpt for 'immediate_action_taken' could not be matched at reported character offsets.",
            ],
          },
        },
        criticalGaps: [],
        possibleContradictions: [],
        investigatorQuestions: [],
      };

      render(
        <ExtractionReviewForm
          extractedData={mockExtractedData}
          onUpdateField={handleUpdate}
        />
      );

      // Verify unverified citation badge is rendered on immediate_action_taken
      expect(screen.getAllByText(/Citation unverified — investigator review required/i).length).toBeGreaterThan(0);

      // Verify verified citation badge is rendered on detection_method
      expect(screen.getByText(/Citation Verified/i)).toBeDefined();

      // Verify detection_method is rendered and editable by investigator
      const detectionInput = screen.getByDisplayValue('High-temperature alarm acknowledged by operator');
      expect(detectionInput).toBeDefined();
      fireEvent.change(detectionInput, { target: { value: 'SCADA High-Temp Alarm (FBD-204)' } });
      expect(handleUpdate).toHaveBeenCalledWith(
        'additionalContext',
        'detectionMethod',
        'SCADA High-Temp Alarm (FBD-204)',
        'detection_method'
      );
    });

    it('ExtractionReviewForm enforces unselected severity, AI Generated Summary title badge, and inferred detection date', () => {
      const mockExtractedData = {
        completenessScore: 88,
        overallConfidence: 0.92,
        extractionStatus: 'NEEDS_REVIEW',
        incidentInfo: {
          deviationId: '',
          batchNumber: 'BATCH-API-26-041',
          incidentTitle: 'Product Temperature Excursion During Final Drying',
          incidentDescription: 'During final drying in FBD-204, product temperature reached 56.8°C.',
          productName: 'Paracetamol High-Density Granules',
          department: 'Solid Oral Dosage',
          equipment: 'Fluid Bed Dryer FBD-204',
          incidentDate: '2026-11-04',
          detectionDate: '2026-11-04',
          severity: '', // Left unselected per user specification
          immediateActionTaken:
            'Operator paused drying cycle at approximately 10:38 and notified shift supervisor; production supervisor entered quality-hold instruction for batch in batch record at 10:52; material remains segregated in designated hold area.',
        },
        context: {
          expectedCondition: '48–52 °C',
          actualCondition: 'Peak 56.8 °C',
          observedImpact: '',
          affectedProcess: 'Final drying',
          initialObservations: 'Equipment historian export contains temperature trend.',
        },
        additionalContext: {
          detectionMethod: 'High-temperature alarm',
        },
        fieldMeta: {
          severity: {
            field_name: 'severity',
            value: '',
            extraction_status: 'MISSING',
            validation_warnings: [
              'Deviation severity not specified in source document — formal investigator assessment required.',
            ],
          },
          incident_title: {
            field_name: 'incident_title',
            value: 'Product Temperature Excursion During Final Drying',
            extraction_status: 'INFERRED',
            validation_warnings: [
              'AI-generated summary title synthesized from incident description — not explicitly titled in source document.',
            ],
          },
          detection_date: {
            field_name: 'detection_date',
            value: '2026-11-04',
            extraction_status: 'INFERRED',
            source_reference: {
              source_type: 'Document',
              page_number: 1,
              excerpt: 'alarm was acknowledged at 10:17',
              is_traceable: true,
            },
            validation_warnings: [
              'Inferred from documented alarm timeline (alarm acknowledged at 10:17 on 04-Nov-2026) — not explicitly designated as a formal detection date field in source document.',
            ],
          },
          immediate_action_taken: {
            field_name: 'immediate_action_taken',
            value:
              'Operator paused drying cycle at approximately 10:38 and notified shift supervisor; production supervisor entered quality-hold instruction for batch in batch record at 10:52; material remains segregated in designated hold area.',
            confidence_score: 1.0,
            extraction_status: 'EXTRACTED',
            source_reference: {
              source_type: 'Document',
              page_number: 1,
              excerpt:
                'At approximately 10:38 on 04-Nov-2026, the operator paused the drying cycle and notified the shift supervisor. At 10:52, the production supervisor entered a quality-hold instruction for the batch in the batch record. The material remains segregated in the designated hold area as of the time this notification was prepared.',
              is_traceable: true,
            },
            validation_warnings: [],
          },
        },
        criticalGaps: [],
        possibleContradictions: [],
        investigatorQuestions: [],
      };

      render(
        <ExtractionReviewForm
          extractedData={mockExtractedData}
          onUpdateField={vi.fn()}
        />
      );

      // 1. Verify severity is unselected and marked as Missing with warning
      expect(screen.getByText(/Deviation severity not specified in source document — formal investigator assessment required/i)).toBeDefined();
      const selectElement = screen.getByRole('combobox');
      expect(selectElement.value).toBe('');

      // 2. Verify AI Generated Summary badge is rendered on incident_title
      expect(screen.getByText(/AI Generated Summary/i)).toBeDefined();
      expect(screen.getByDisplayValue('Product Temperature Excursion During Final Drying')).toBeDefined();

      // 3. Verify Inferred badge and alarm timeline warning are rendered on detection_date
      expect(screen.getByText(/Inferred from documented alarm timeline/i)).toBeDefined();

      // 4. Verify comprehensive 4-part containment immediate action is present
      expect(screen.getByDisplayValue(/Operator paused drying cycle at approximately 10:38/i)).toBeDefined();
      expect(screen.getByDisplayValue(/quality-hold instruction for batch in batch record at 10:52/i)).toBeDefined();
      expect(screen.getByDisplayValue(/material remains segregated in designated hold area/i)).toBeDefined();
    });

    it('correctly maps and renders excursion condition, containment action, and impact from backend response', () => {
      const backendResponse = {
        analysis_id: 'ANALYSIS-EXCURSION-01',
        extraction_status: 'PARTIALLY_COMPLETED',
        completeness_score: 72,
        overall_confidence: 0.96,
        missing_fields: ['deviation_id', 'product_name', 'incident_date'],
        critical_gaps: ['Critical GxP Gap: Incident occurrence date is missing.'],
        extracted_data: {
          incident_title: {
            field_name: 'incident_title',
            value: 'Temperature excursion in reactor R-101',
            confidence_score: 0.95,
            extraction_status: 'EXTRACTED',
          },
          incident_description: {
            field_name: 'incident_description',
            value: 'Reaction mass reached 74°C for 18 minutes during crystallization.',
            confidence_score: 0.98,
            extraction_status: 'EXTRACTED',
          },
          batch_number: {
            field_name: 'batch_number',
            value: 'BATCH-CR-9901',
            confidence_score: 1.0,
            extraction_status: 'EXTRACTED',
          },
          equipment_id: {
            field_name: 'equipment_id',
            value: 'R-101',
            confidence_score: 1.0,
            extraction_status: 'EXTRACTED',
          },
          expected_condition: {
            field_name: 'expected_condition',
            value: '65-70°C',
            confidence_score: 1.0,
            extraction_status: 'EXTRACTED',
          },
          actual_condition: {
            field_name: 'actual_condition',
            value: '74°C for approximately 18 minutes',
            confidence_score: 1.0,
            extraction_status: 'EXTRACTED',
          },
          immediate_action_taken: {
            field_name: 'immediate_action_taken',
            value: 'Batch placed on hold pending quality unit review',
            confidence_score: 1.0,
            extraction_status: 'EXTRACTED',
          },
          potential_impact: {
            field_name: 'potential_impact',
            value: 'Product quality impact is currently under investigation',
            confidence_score: 0.90,
            extraction_status: 'EXTRACTED',
          },
          observations: {
            field_name: 'observations',
            value: 'Visual discoloration of the reaction mass',
            confidence_score: 1.0,
            extraction_status: 'EXTRACTED',
          },
          incident_date: {
            field_name: 'incident_date',
            value: null,
            confidence_score: 0.0,
            extraction_status: 'MISSING',
          },
        },
      };

      const normalized = normalizeExtractionResponse(backendResponse);

      // Verify mapping
      expect(normalized.incidentInfo.incidentDescription).toBe('Reaction mass reached 74°C for 18 minutes during crystallization.');
      expect(normalized.incidentInfo.immediateActionTaken).toBe('Batch placed on hold pending quality unit review');
      expect(normalized.context.expectedCondition).toBe('65-70°C');
      expect(normalized.context.actualCondition).toBe('74°C for approximately 18 minutes');
      expect(normalized.context.observedImpact).toBe('Product quality impact is currently under investigation');
      expect(normalized.context.initialObservations).toBe('Visual discoloration of the reaction mass');
      expect(normalized.fieldMeta.incident_date.value).toBeNull();
      expect(normalized.fieldMeta.incident_date.confidence_score).toBe(0.0);

      render(
        <ExtractionReviewForm
          extractedData={normalized}
          onUpdateField={vi.fn()}
          onRevertField={vi.fn()}
          onSaveDraft={vi.fn()}
          onContinueToRCA={vi.fn()}
          isDraftSaved={false}
          isSubmitting={false}
        />
      );

      // Verify rendered values in the form
      expect(screen.getByDisplayValue('BATCH-CR-9901')).toBeDefined();
      expect(screen.getByDisplayValue('R-101')).toBeDefined();
      expect(screen.getByDisplayValue('65-70°C')).toBeDefined();
      expect(screen.getByDisplayValue('74°C for approximately 18 minutes')).toBeDefined();
      expect(screen.getByDisplayValue('Batch placed on hold pending quality unit review')).toBeDefined();
      expect(screen.getByDisplayValue('Product quality impact is currently under investigation')).toBeDefined();
      expect(screen.getByDisplayValue('Visual discoloration of the reaction mass')).toBeDefined();
    });
  });

  describe('FiveWhysAnalysis Component', () => {
    it('renders 5-Whys levels and triggers AI generation and save', () => {
      const mockFiveWhys = [
        {
          level: 1,
          question: 'Why did reactor overheat?',
          answer: 'Cooling jacket valve remained closed.',
          evidence: 'SCADA Valve Log 04:12',
          status: 'Evidence-Supported',
          is_root_cause: false,
        },
        {
          level: 2,
          question: 'Why did the valve remain closed?',
          answer: 'Air actuator solenoid failed.',
          evidence: 'Maintenance report #892',
          status: 'Evidence-Supported',
          is_root_cause: true,
        },
      ];

      const handleSaveLevel = vi.fn();
      const handleSaveAll = vi.fn();
      const handleGenerateAI = vi.fn();

      render(
        <FiveWhysAnalysis
          fiveWhys={mockFiveWhys}
          onSaveLevel={handleSaveLevel}
          onSaveAll={handleSaveAll}
          onGenerateAI={handleGenerateAI}
        />
      );

      expect(screen.getByText('Why did reactor overheat?')).toBeDefined();
      expect(screen.getByDisplayValue('Cooling jacket valve remained closed.')).toBeDefined();
      expect(screen.getByText('Why did the valve remain closed?')).toBeDefined();

      // Trigger AI reasoning
      const aiBtn = screen.getByRole('button', { name: /generate ai 5-whys/i });
      fireEvent.click(aiBtn);
      expect(handleGenerateAI).toHaveBeenCalledTimes(1);

      // Trigger Save
      const saveBtns = screen.getAllByRole('button', { name: /save 5-whys/i });
      fireEvent.click(saveBtns[0]);
      expect(handleSaveAll).toHaveBeenCalledTimes(1);
    });
  });

  describe('FishboneAnalysis Component', () => {
    it('renders 6M Ishikawa categories and handles adding a cause', () => {
      const mockFishbone = {
        Machine: [
          {
            id: 'CAUSE-1',
            cause: 'Solenoid coil burnout',
            status: 'Evidence-Supported',
            is_root_cause: true,
          },
        ],
        Method: [],
        Manpower: [],
        Material: [],
        Measurement: [],
        Environment: [],
      };

      const handleAddCause = vi.fn();
      const handleSaveAll = vi.fn();
      const handleGenerateAI = vi.fn();

      render(
        <FishboneAnalysis
          fishbone={mockFishbone}
          onAddCause={handleAddCause}
          onSaveAll={handleSaveAll}
          onGenerateAI={handleGenerateAI}
        />
      );

      expect(screen.getByText('Solenoid coil burnout')).toBeDefined();
      expect(screen.getByText(/Machine \(Equipment\)/)).toBeDefined();

      // Click Add Cause for Method
      const addBtn = screen.getByRole('button', { name: /add method cause/i });
      fireEvent.click(addBtn);

      // Enter cause text
      const input = screen.getByPlaceholderText(/potential failure mode/i);
      fireEvent.change(input, { target: { value: 'Inadequate preventive maintenance schedule' } });

      const confirmBtn = screen.getByRole('button', { name: /^add$/i });
      fireEvent.click(confirmBtn);

      expect(handleAddCause).toHaveBeenCalledTimes(1);
    });
  });

  describe('EvidenceList Component', () => {
    it('renders evidence categories and allows adding a new artifact', () => {
      const mockEvidence = [
        {
          id: 'EVID-1',
          title: 'Chromatogram Purity Peak',
          category: 'Supporting Evidence',
          type: 'HPLC Data',
          reference: 'HPLC-2026-RUN-04',
          status: 'Verified by QA',
          notes: 'Exhibited 98.2% peak purity, confirming no chemical degradation.',
        },
      ];

      const handleAddEvidence = vi.fn();
      const handleUpdateStatus = vi.fn();

      render(
        <EvidenceList
          evidence={mockEvidence}
          onAddEvidence={handleAddEvidence}
          onUpdateEvidenceStatus={handleUpdateStatus}
        />
      );

      expect(screen.getByText('Chromatogram Purity Peak')).toBeDefined();
      expect(screen.getByText(/HPLC-2026-RUN-04/)).toBeDefined();

      // Open Add Evidence form
      const addBtn = screen.getByRole('button', { name: /add evidence item/i });
      fireEvent.click(addBtn);

      expect(screen.getByText('Link New Evidence or Inquiry')).toBeDefined();
      const titleInput = screen.getByPlaceholderText(/Chiller secondary flow transmitter/i);
      fireEvent.change(titleInput, { target: { value: 'Calibration Certificate #2026-09' } });

      const submitBtn = screen.getByRole('button', { name: /link evidence/i });
      fireEvent.click(submitBtn);

      expect(handleAddEvidence).toHaveBeenCalledTimes(1);
      expect(handleAddEvidence).toHaveBeenCalledWith(
        expect.objectContaining({
          title: 'Calibration Certificate #2026-09',
        })
      );
    });
  });

  describe('CAPAForm Component', () => {
    it('renders CAPA actions, supports AI recommendation, proposal, and QA approval/rejection', () => {
      const mockCapa = [
        {
          id: 'CAPA-01',
          action_id: 'CAPA-01',
          action_type: 'Corrective Action',
          description: 'Replace worn PTFE seal on reactor R-101 agitation shaft.',
          action_owner: 'Maintenance Lead',
          target_date: '2026-11-20',
          effectiveness_verification_method: 'Pressure hold test across 3 commercial batches.',
          status: 'Pending Review',
        },
      ];

      const handleGenerateAI = vi.fn();
      const handleCreateCAPA = vi.fn();
      const handleUpdateStatus = vi.fn();

      render(
        <CAPAForm
          capa={mockCapa}
          onGenerateAI={handleGenerateAI}
          onCreateCAPA={handleCreateCAPA}
          onUpdateStatus={handleUpdateStatus}
        />
      );

      expect(screen.getByText(/Replace worn PTFE seal on reactor R-101 agitation shaft/i)).toBeDefined();
      expect(screen.getAllByText('Pending Review').length).toBeGreaterThan(0);

      // Trigger AI generation
      const aiBtn = screen.getByRole('button', { name: /generate ai capa/i });
      fireEvent.click(aiBtn);
      expect(handleGenerateAI).toHaveBeenCalledTimes(1);

      // Approve action
      const approveBtn = screen.getByRole('button', { name: /approve action/i });
      fireEvent.click(approveBtn);
      expect(handleUpdateStatus).toHaveBeenCalledWith('CAPA-01', 'Approved');

      // Reject action
      const rejectBtn = screen.getByRole('button', { name: /^reject$/i });
      fireEvent.click(rejectBtn);
      expect(handleUpdateStatus).toHaveBeenCalledWith('CAPA-01', 'Rejected');

      // Propose manual CAPA
      const proposeBtn = screen.getByRole('button', { name: /propose action/i });
      fireEvent.click(proposeBtn);
      expect(screen.getByText(/Propose New CAPA Remediation Action/i)).toBeDefined();
    });
  });

  describe('CAPAManagementPage Integration', () => {
    it('fetches and renders live CAPA portfolio and KPI statistics', async () => {
      const mockCapas = [
        {
          action_id: 'CAPA-2026-001',
          description: 'Automated nitrogen purge validation protocol',
          action_type: 'Preventive Action',
          investigation_id: 'INV-2026-001',
          action_owner: 'Validation Lead',
          target_date: '2026-12-10',
          status: 'In Progress',
          effectiveness_verification_method: '3 consecutive purge cycle alarms verified',
        },
      ];

      vi.spyOn(capaService, 'listAllCAPA').mockResolvedValue(mockCapas);

      render(
        <MemoryRouter>
          <CAPAManagementPage />
        </MemoryRouter>
      );

      await waitFor(() => {
        expect(screen.getByText('Automated nitrogen purge validation protocol')).toBeDefined();
        expect(screen.getByText('CAPA-2026-001')).toBeDefined();
        expect(screen.getByText('Validation Lead')).toBeDefined();
      });
    });

    it('renders valid linked investigation IDs as links and navigates from multiple records', async () => {
      const mockCapas = [
        {
          action_id: 'CAPA-001',
          description: 'Recalibrate temperature transmitter TT-401',
          action_type: 'Corrective Action',
          investigation_id: 'INV-2026-7277',
          action_owner: 'Lead Instrumentation Engineer',
          target_date: '2026-11-15',
          status: 'Approved',
          effectiveness_verification_method: 'Verify 3-batch calibration drift under 0.1C',
        },
        {
          action_id: 'CAPA-002',
          description: 'Update centrifuge CIP spray nozzle SOP',
          action_type: 'Preventive Action',
          investigation_id: 'INV-2026-9005',
          action_owner: 'Quality Assurance Specialist',
          target_date: '2026-12-01',
          status: 'In Progress',
          effectiveness_verification_method: 'Review riboflavin coverage test records',
        },
        {
          action_id: 'CAPA-003',
          description: 'Orphaned action item without linked investigation',
          action_type: 'Corrective Action',
          investigation_id: null,
          action_owner: 'Operations Lead',
          target_date: '2026-11-30',
          status: 'Draft',
          effectiveness_verification_method: 'Visual inspection',
        },
      ];

      vi.spyOn(capaService, 'listAllCAPA').mockResolvedValue(mockCapas);

      render(
        <MemoryRouter>
          <CAPAManagementPage />
        </MemoryRouter>
      );

      await waitFor(() => {
        expect(screen.getByText('INV-2026-7277')).toBeDefined();
        expect(screen.getByText('INV-2026-9005')).toBeDefined();
      });

      // 1. Verify first record link destination matches clicked ID
      const link1 = screen.getByText('INV-2026-7277').closest('a');
      expect(link1).not.toBeNull();
      expect(link1.getAttribute('href')).toBe('/investigations/INV-2026-7277');

      // 2. Verify second record link destination matches clicked ID
      const link2 = screen.getByText('INV-2026-9005').closest('a');
      expect(link2).not.toBeNull();
      expect(link2.getAttribute('href')).toBe('/investigations/INV-2026-9005');

      // 3. Verify orphaned record renders N/A gracefully without broken link
      const naElements = screen.getAllByText('N/A');
      expect(naElements.length).toBeGreaterThan(0);
      const naLink = naElements.find((el) => el.closest('a'));
      expect(naLink).toBeUndefined();
    });

    it('navigates to investigation workspace when linked ID is clicked', async () => {
      const mockCapas = [
        {
          action_id: 'CAPA-001',
          description: 'Recalibrate temperature transmitter TT-401',
          action_type: 'Corrective Action',
          investigation_id: 'INV-2026-7277',
          action_owner: 'Lead Instrumentation Engineer',
          target_date: '2026-11-15',
          status: 'Approved',
          effectiveness_verification_method: 'Verify 3-batch calibration drift under 0.1C',
        },
      ];

      const mockInvestigation = {
        investigation_id: 'INV-2026-7277',
        incident_title: 'Live Validation Excursion: Crystallizer CR-101 Temperature Drift',
        batch_number: 'BATCH-CR-9901',
        severity: 'Critical',
        investigation_status: 'Under Investigation',
        department: 'API Synthesis',
        product_name: 'Atorvastatin Calcium API',
        equipment: 'CR-101',
        incident_description: 'Temperature peaked at 22.4C',
        immediate_action_taken: 'Manual bypass valve',
        date: '2026-11-05',
      };

      vi.spyOn(capaService, 'listAllCAPA').mockResolvedValue(mockCapas);
      vi.spyOn(investigationService, 'getInvestigation').mockResolvedValue(mockInvestigation);
      vi.spyOn(investigationService, 'listDocuments').mockResolvedValue([]);
      vi.spyOn(rcaService, 'getRCA').mockResolvedValue({ five_whys: [], fishbone_causes: [] });
      vi.spyOn(evidenceService, 'listEvidence').mockResolvedValue([]);
      vi.spyOn(capaService, 'listCAPA').mockResolvedValue(mockCapas);

      const store = createMockStore();

      render(
        <Provider store={store}>
          <MemoryRouter initialEntries={['/capa']}>
            <Routes>
              <Route path="/capa" element={<CAPAManagementPage />} />
              <Route path="/investigations/:id" element={<InvestigationDetailPage />} />
            </Routes>
          </MemoryRouter>
        </Provider>
      );

      await waitFor(() => {
        expect(screen.getByText('INV-2026-7277')).toBeDefined();
      });

      const link = screen.getByText('INV-2026-7277').closest('a');
      expect(link).toBeDefined();

      fireEvent.click(link);

      await waitFor(() => {
        expect(
          screen.getByText('Live Validation Excursion: Crystallizer CR-101 Temperature Drift')
        ).toBeDefined();
      });
    });
  });

  describe('Sidebar Dynamic Badge Component', () => {
    it('displays dynamic open investigations count instead of hardcoded badge', () => {
      const store = createMockStore({
        dashboard: {
          summary: { open_investigations: 7 },
        },
      });

      render(
        <Provider store={store}>
          <MemoryRouter>
            <Sidebar />
          </MemoryRouter>
        </Provider>
      );

      expect(screen.getAllByText('7 Active').length).toBeGreaterThanOrEqual(1);
    });
  });
});
