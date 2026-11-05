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
import StatusDistribution from '../components/dashboard/StatusDistribution';
import RecentInvestigations from '../components/dashboard/RecentInvestigations';
import RecentActivity from '../components/dashboard/RecentActivity';

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
  });
});
