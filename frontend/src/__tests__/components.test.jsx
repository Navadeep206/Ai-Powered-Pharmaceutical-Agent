import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { Provider } from 'react-redux';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { configureStore } from '@reduxjs/toolkit';
import appReducer from '../redux/slices/appSlice';
import investigationReducer from '../redux/slices/investigationSlice';
import dashboardReducer from '../redux/slices/dashboardSlice';

import dashboardService from '../services/dashboardService';
import investigationService from '../services/investigationService';
import rcaService from '../services/rcaService';
import evidenceService from '../services/evidenceService';
import capaService from '../services/capaService';

import DashboardPage from '../pages/Dashboard/index';
import InvestigationsPage from '../pages/Investigations/index';
import InvestigationDetailPage from '../pages/Investigations/InvestigationDetail';
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
    it('renders empty state when no activities exist', () => {
      render(<RecentActivity activities={[]} loading={false} />);
      expect(screen.getByText('No recent activities')).toBeDefined();
    });

    it('renders activity items with audit details', () => {
      const activities = [
        {
          id: 'act-1',
          description: 'Investigation INV-2026-001 created',
          detail: 'Logged by System',
          time: '2h ago',
          iconName: 'PlusCircle',
        },
      ];

      render(<RecentActivity activities={activities} loading={false} />);
      expect(screen.getByText('Investigation INV-2026-001 created')).toBeDefined();
      expect(screen.getByText('Logged by System')).toBeDefined();
      expect(screen.getByText('2h ago')).toBeDefined();
    });
  });

  describe('DashboardPage Integration', () => {
    it('displays connection error banner with retry button when backend fails', async () => {
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
        expect(screen.getByText('Backend Connection Issue')).toBeDefined();
        expect(screen.getByText(/Cannot connect to the RootIQ backend API/i)).toBeDefined();
        expect(screen.getByRole('button', { name: /retry connection/i })).toBeDefined();
      });
    });

    it('renders real KPI values when backend summary succeeds', async () => {
      vi.spyOn(dashboardService, 'getSummary').mockResolvedValue({
        total_investigations: 42,
        open_investigations: 12,
        investigations_under_investigation: 20,
        investigations_pending_capa: 6,
        completed_investigations: 4,
        total_capa_actions: 18,
        capa_actions_pending_review: 5,
      });
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
        expect(screen.getByText('42')).toBeDefined();
        expect(screen.getAllByText('12').length).toBeGreaterThan(0);
        expect(screen.getAllByText('20').length).toBeGreaterThan(0);
      });
    });
  });

  describe('InvestigationsPage Integration', () => {
    it('renders empty state when no investigations match search', async () => {
      vi.spyOn(investigationService, 'listInvestigations').mockResolvedValue({
        items: [],
        pagination: { total: 0, total_pages: 0, page: 1, limit: 15 },
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
        expect(screen.getByText('No investigations found')).toBeDefined();
      });
    });

    it('renders list of investigations when data returns', async () => {
      vi.spyOn(investigationService, 'listInvestigations').mockResolvedValue({
        items: [
          {
            investigation_id: 'INV-2026-7777',
            incident_title: 'Centrifuge seal rupture',
            department: 'Centrifugation',
            batch_number: 'BATCH-C1',
            severity: 'High',
            investigation_status: 'Open',
            incident_date: '2026-11-02',
          },
        ],
        pagination: { total: 1, total_pages: 1, page: 1, limit: 15 },
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
        expect(screen.getByText('INV-2026-7777')).toBeDefined();
        expect(screen.getByText('Centrifuge seal rupture')).toBeDefined();
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
});
