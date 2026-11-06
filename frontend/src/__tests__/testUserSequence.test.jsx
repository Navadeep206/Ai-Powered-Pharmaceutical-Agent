import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import { Provider } from 'react-redux';
import { MemoryRouter, Routes, Route } from 'react-router-dom';
import store from '../redux/store';
import AppLayout from '../components/layout/AppLayout';
import DashboardPage from '../pages/Dashboard';
import InvestigationsPage from '../pages/Investigations';
import InvestigationDetailPage from '../pages/Investigations/InvestigationDetail';
import CAPAManagementPage from '../pages/CAPAManagement';
import investigationService from '../services/investigationService';
import rcaService from '../services/rcaService';
import evidenceService from '../services/evidenceService';
import capaService from '../services/capaService';
import api from '../services/api';

describe('User Acceptance Test Navigation Sequence', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it('reproduces open investigation -> CAPA Management -> Investigations -> reopen same investigation', async () => {
    const invId = 'INV-2026-1487';
    const mockInvestigation = {
      investigation_id: invId,
      incident_title: 'Reactor Temperature Excursion',
      batch_number: 'BATCH-100',
      department: 'Formulation',
      severity: 'Critical',
      investigation_status: 'Under Investigation',
      created_at: '2026-11-06T10:00:00Z',
    };

    const getInvSpy = vi.spyOn(investigationService, 'getInvestigation').mockResolvedValue(mockInvestigation);
    const getRcaSpy = vi.spyOn(rcaService, 'getRCA').mockResolvedValue({ five_whys: [], fishbone_causes: [] });
    const getEvdSpy = vi.spyOn(evidenceService, 'listEvidence').mockResolvedValue([]);
    const getCapaSpy = vi.spyOn(capaService, 'listCAPA').mockResolvedValue([]);
    const getDocsSpy = vi.spyOn(investigationService, 'listDocuments').mockResolvedValue([]);
    const listInvSpy = vi.spyOn(investigationService, 'listInvestigations').mockResolvedValue({
      items: [mockInvestigation],
      pagination: { page: 1, limit: 15, total: 1, total_pages: 1 },
    });
    const listAllCapaSpy = vi.spyOn(capaService, 'listAllCAPA').mockResolvedValue([]);

    const { unmount } = render(
      <Provider store={store}>
        <MemoryRouter initialEntries={[`/investigations/${invId}`]}>
          <Routes>
            <Route path="/" element={<AppLayout />}>
              <Route path="investigations" element={<InvestigationsPage />} />
              <Route path="investigations/:id" element={<InvestigationDetailPage />} />
              <Route path="capa" element={<CAPAManagementPage />} />
            </Route>
          </Routes>
        </MemoryRouter>
      </Provider>
    );

    // 1. Initial Load of investigation
    await waitFor(() => {
      expect(screen.getByText('Reactor Temperature Excursion')).toBeDefined();
    });

    expect(getInvSpy).toHaveBeenCalledTimes(1);
    expect(getRcaSpy).toHaveBeenCalledTimes(1);
    expect(getEvdSpy).toHaveBeenCalledTimes(1);
    expect(getCapaSpy).toHaveBeenCalledTimes(1);
    expect(getDocsSpy).toHaveBeenCalledTimes(1);

    // 2. Navigate to CAPA Management
    const capaNavLink = screen.getAllByText('CAPA Management')[0];
    fireEvent.click(capaNavLink);

    await waitFor(() => {
      expect(screen.getByText('CAPA Management Portfolio')).toBeDefined();
    });

    // 3. Clear mock call counts (mimicking user clearing Network log)
    getInvSpy.mockClear();
    getRcaSpy.mockClear();
    getEvdSpy.mockClear();
    getCapaSpy.mockClear();
    getDocsSpy.mockClear();
    listInvSpy.mockClear();
    listAllCapaSpy.mockClear();

    // 4. Return to Investigations
    const invNavLink = screen.getAllByText('Investigations')[0];
    fireEvent.click(invNavLink);

    await waitFor(() => {
      expect(screen.getByText('Investigations Registry')).toBeDefined();
    });

    // 5. Reopen the same investigation (click "Open Workspace")
    const openWorkspaceBtn = screen.getByText('Open Workspace');
    fireEvent.click(openWorkspaceBtn);

    await waitFor(() => {
      expect(screen.getByText('Reactor Temperature Excursion')).toBeDefined();
    });

    console.log('CALL COUNTS AFTER REOPEN:');
    console.log('getInvSpy:', getInvSpy.mock.calls.length);
    console.log('getRcaSpy:', getRcaSpy.mock.calls.length);
    console.log('getEvdSpy:', getEvdSpy.mock.calls.length);
    console.log('getCapaSpy:', getCapaSpy.mock.calls.length);
    console.log('getDocsSpy:', getDocsSpy.mock.calls.length);
    console.log('listInvSpy:', listInvSpy.mock.calls.length);
    console.log('listAllCapaSpy:', listAllCapaSpy.mock.calls.length);

    expect(getInvSpy).toHaveBeenCalledTimes(0);
    expect(getRcaSpy).toHaveBeenCalledTimes(0);
    expect(getEvdSpy).toHaveBeenCalledTimes(0);
    expect(getCapaSpy).toHaveBeenCalledTimes(0);
    expect(getDocsSpy).toHaveBeenCalledTimes(0);
  });

  it('guarantees 0 raw API network calls when reopening cached investigation via Axios', async () => {
    investigationService.clearCache?.();
    rcaService.clearCache?.();
    evidenceService.clearCache?.();
    capaService.clearCache?.();

    const invId = 'INV-2026-SERVICE-CACHE';
    const mockInvestigation = {
      investigation_id: invId,
      incident_title: 'API Layer Excursion Test',
    };

    const apiGetSpy = vi.spyOn(api, 'get').mockImplementation(async (url) => {
      if (url.includes('/rca')) return { data: { five_whys: [], fishbone_causes: [] } };
      if (url.includes('/evidence')) return { data: [] };
      if (url.includes('/capa')) return { data: [] };
      if (url.includes('/documents')) return { data: [] };
      if (url.includes('/investigations')) return { data: mockInvestigation };
      return { data: {} };
    });

    // 1. First fetch through services
    await Promise.all([
      investigationService.getInvestigation(invId),
      rcaService.getRCA(invId),
      evidenceService.listEvidence(invId),
      capaService.listCAPA(invId),
      investigationService.listDocuments(invId),
    ]);

    expect(apiGetSpy).toHaveBeenCalledTimes(5);

    // 2. Clear API call counts (simulating Network log clear)
    apiGetSpy.mockClear();

    // 3. Second fetch through services (must be served 100% from service cache)
    const [inv, rca, evd, capa, docs] = await Promise.all([
      investigationService.getInvestigation(invId),
      rcaService.getRCA(invId),
      evidenceService.listEvidence(invId),
      capaService.listCAPA(invId),
      investigationService.listDocuments(invId),
    ]);

    expect(apiGetSpy).toHaveBeenCalledTimes(0);
    expect(inv).toEqual(mockInvestigation);
    expect(rca).toEqual({ five_whys: [], fishbone_causes: [] });
    expect(evd).toEqual([]);
    expect(capa).toEqual([]);
    expect(docs).toEqual([]);
  });
});
