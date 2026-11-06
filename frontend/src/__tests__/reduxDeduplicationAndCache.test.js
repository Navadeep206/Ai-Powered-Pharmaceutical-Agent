import { describe, it, expect, vi, beforeEach } from 'vitest';
import { configureStore } from '@reduxjs/toolkit';
import investigationReducer, {
  fetchInvestigations,
  fetchInvestigationById,
  fetchInvestigationRCA,
  fetchInvestigationEvidence,
  fetchInvestigationCAPA,
  fetchInvestigationDocuments,
  saveInvestigationRCA,
  createEvidenceRecord,
  createCAPAAction,
  updateInvestigationDetails,
  setActiveInvestigationId,
  invalidateInvestigation,
} from '../redux/slices/investigationSlice';
import api from '../services/api';
import investigationService from '../services/investigationService';
import rcaService from '../services/rcaService';
import evidenceService from '../services/evidenceService';
import capaService from '../services/capaService';
import { reviewCAPAActions } from '../redux/slices/investigationSlice';

function createTestStore() {
  return configureStore({
    reducer: {
      investigations: investigationReducer,
    },
  });
}

describe('Redux Toolkit Request Deduplication & Per-Investigation Caching', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    investigationService.clearCache?.();
    capaService.clearCache?.();
  });

  it('1. Two identical simultaneous requests produce only one HTTP request', async () => {
    const store = createTestStore();
    const mockInvestigation = {
      investigation_id: 'INV-2026-SIMULTANEOUS',
      incident_title: 'Reactor Temperature Excursion',
      department: 'Formulation',
      severity: 'High',
    };

    const spy = vi
      .spyOn(investigationService, 'getInvestigation')
      .mockImplementation(
        () => new Promise((resolve) => setTimeout(() => resolve(mockInvestigation), 20))
      );

    // Dispatch two identical requests concurrently
    const [res1, res2] = await Promise.all([
      store.dispatch(fetchInvestigationById('INV-2026-SIMULTANEOUS')),
      store.dispatch(fetchInvestigationById('INV-2026-SIMULTANEOUS')),
    ]);

    // Condition guard blocks the second dispatch while the first is pending
    expect(spy).toHaveBeenCalledTimes(1);
    expect(res1.type).toBe('investigations/fetchById/fulfilled');
    expect(res2.meta.condition).toBe(true);

    const state = store.getState().investigations;
    expect(state.currentInvestigation?.id).toBe('INV-2026-SIMULTANEOUS');
  });

  it('2. Reopening an already-loaded investigation reuses its cached data', async () => {
    const store = createTestStore();
    const mockInvestigation = {
      investigation_id: 'INV-2026-REOPEN',
      incident_title: 'pH Calibration Drift',
      department: 'Quality Control',
      severity: 'Medium',
    };

    const spy = vi
      .spyOn(investigationService, 'getInvestigation')
      .mockResolvedValue(mockInvestigation);

    // Initial load
    await store.dispatch(fetchInvestigationById('INV-2026-REOPEN'));
    expect(spy).toHaveBeenCalledTimes(1);

    // Second load should be skipped by condition guard
    const repeatResult = await store.dispatch(fetchInvestigationById('INV-2026-REOPEN'));
    expect(repeatResult.meta.condition).toBe(true);
    expect(spy).toHaveBeenCalledTimes(1);

    // Data remains resident in store
    const state = store.getState().investigations;
    expect(state.currentInvestigation?.id).toBe('INV-2026-REOPEN');
    expect(state.cacheById['INV-2026-REOPEN']?.details?.status).toBe('fulfilled');
  });

  it('3. Opening a different investigation fetches the correct data and isolates state', async () => {
    const store = createTestStore();
    const invA = {
      investigation_id: 'INV-AAA',
      incident_title: 'Batch A Contamination',
      department: 'Packaging',
      severity: 'Critical',
    };
    const invB = {
      investigation_id: 'INV-BBB',
      incident_title: 'Batch B Pressure Drop',
      department: 'Synthesis',
      severity: 'Low',
    };

    const spy = vi
      .spyOn(investigationService, 'getInvestigation')
      .mockImplementation((id) => Promise.resolve(id === 'INV-AAA' ? invA : invB));

    // Load Investigation A
    await store.dispatch(fetchInvestigationById('INV-AAA'));
    expect(store.getState().investigations.currentInvestigation?.id).toBe('INV-AAA');

    // Switch to Investigation B
    store.dispatch(setActiveInvestigationId('INV-BBB'));
    // While loading B, currentInvestigation should NOT show A's data
    expect(store.getState().investigations.currentInvestigation).toBeNull();

    await store.dispatch(fetchInvestigationById('INV-BBB'));
    expect(store.getState().investigations.currentInvestigation?.id).toBe('INV-BBB');
    expect(spy).toHaveBeenCalledTimes(2);

    // Both remain preserved in the cache dictionary
    const cache = store.getState().investigations.cacheById;
    expect(cache['INV-AAA']?.details?.data?.id).toBe('INV-AAA');
    expect(cache['INV-BBB']?.details?.data?.id).toBe('INV-BBB');

    // Switching back to A restores A instantly from cache without an extra API call
    store.dispatch(setActiveInvestigationId('INV-AAA'));
    expect(store.getState().investigations.currentInvestigation?.id).toBe('INV-AAA');
    const cachedRefetch = await store.dispatch(fetchInvestigationById('INV-AAA'));
    expect(cachedRefetch.meta.condition).toBe(true);
    expect(spy).toHaveBeenCalledTimes(2);
  });

  it('4. Failed background refresh preserves previously loaded data', async () => {
    const store = createTestStore();
    const initialInv = {
      investigation_id: 'INV-BG-FAIL',
      incident_title: 'HVAC Humidity Spike',
      department: 'Cleanroom',
      severity: 'Medium',
    };

    vi.spyOn(investigationService, 'getInvestigation')
      .mockResolvedValueOnce(initialInv)
      .mockRejectedValueOnce({
        message: 'Network connection lost.',
        statusCode: null,
        isNetworkError: true,
      });

    // Initial successful load
    await store.dispatch(fetchInvestigationById('INV-BG-FAIL'));
    expect(store.getState().investigations.currentInvestigation?.id).toBe('INV-BG-FAIL');

    // Force refresh that fails with network error
    const failedResult = await store.dispatch(
      fetchInvestigationById({ id: 'INV-BG-FAIL', force: true })
    );
    expect(failedResult.type).toBe('investigations/fetchById/rejected');

    // Previously loaded data MUST be preserved in currentInvestigation and cache
    const state = store.getState().investigations;
    expect(state.currentInvestigation?.id).toBe('INV-BG-FAIL');
    expect(state.cacheById['INV-BG-FAIL']?.details?.data?.id).toBe('INV-BG-FAIL');
    expect(state.detailError).toBe('Network connection lost.');
  });

  it('5. A successful mutation updates and invalidates the relevant cache', async () => {
    const store = createTestStore();
    const initialInv = {
      investigation_id: 'INV-MUTATION',
      incident_title: 'Seal Degradation',
      department: 'Synthesis',
    };

    vi.spyOn(investigationService, 'getInvestigation').mockResolvedValue(initialInv);
    await store.dispatch(fetchInvestigationById('INV-MUTATION'));

    // 1. RCA Mutation updates RCA cache
    const mockRcaPayload = {
      five_whys: [
        { level: 1, question: 'Why leak?', answer: 'Gasket worn', status: 'Evidence-Supported' },
      ],
      fishbone_causes: [],
    };
    vi.spyOn(rcaService, 'saveRCA').mockResolvedValue(mockRcaPayload);

    await store.dispatch(
      saveInvestigationRCA({
        investigationId: 'INV-MUTATION',
        fiveWhys: mockRcaPayload.five_whys,
      })
    );

    const rcaState = store.getState().investigations.cacheById['INV-MUTATION']?.rca;
    expect(rcaState?.status).toBe('fulfilled');
    expect(rcaState?.data).toEqual(mockRcaPayload);
    expect(store.getState().investigations.rca).toEqual(mockRcaPayload);

    // 2. Invalidate investigation triggers refetch on next query
    store.dispatch(invalidateInvestigation('INV-MUTATION'));
    expect(store.getState().investigations.cacheById['INV-MUTATION'].isInvalidated).toBe(true);

    const updateSpy = vi.spyOn(investigationService, 'getInvestigation').mockResolvedValue({
      ...initialInv,
      incident_title: 'Seal Degradation (Updated Title)',
    });
    updateSpy.mockClear();

    await store.dispatch(fetchInvestigationById('INV-MUTATION'));
    expect(updateSpy).toHaveBeenCalledTimes(1);
    expect(store.getState().investigations.currentInvestigation?.title).toBe(
      'Seal Degradation (Updated Title)'
    );
  });

  it('6. Different investigation IDs can load independently without cross-blocking', async () => {
    const store = createTestStore();

    vi.spyOn(rcaService, 'getRCA').mockImplementation((id) =>
      Promise.resolve({
        investigation_id: id,
        five_whys: [{ level: 1, answer: `Cause for ${id}` }],
      })
    );

    const [rcaA, rcaB] = await Promise.all([
      store.dispatch(fetchInvestigationRCA('INV-ID-1')),
      store.dispatch(fetchInvestigationRCA('INV-ID-2')),
    ]);

    expect(rcaA.type).toBe('investigations/fetchRCA/fulfilled');
    expect(rcaB.type).toBe('investigations/fetchRCA/fulfilled');

    const cache = store.getState().investigations.cacheById;
    expect(cache['INV-ID-1']?.rca?.data?.investigation_id).toBe('INV-ID-1');
    expect(cache['INV-ID-2']?.rca?.data?.investigation_id).toBe('INV-ID-2');
  });

  it('7. Existing selectors and legacy state properties continue working seamlessly', async () => {
    const store = createTestStore();
    const mockInv = {
      investigation_id: 'INV-LEGACY-TEST',
      incident_title: 'Legacy Compatibility Check',
      severity: 'Low',
    };

    vi.spyOn(investigationService, 'getInvestigation').mockResolvedValue(mockInv);
    vi.spyOn(evidenceService, 'listEvidence').mockResolvedValue([
      { id: 'E-1', title: 'Calibration Log', category: 'Supporting Evidence', status: 'Pending Review' },
    ]);
    vi.spyOn(capaService, 'listCAPA').mockResolvedValue([
      { id: 'C-1', description: 'Replace O-ring', status: 'Proposed' },
    ]);

    await store.dispatch(fetchInvestigationById('INV-LEGACY-TEST'));
    await store.dispatch(fetchInvestigationEvidence('INV-LEGACY-TEST'));
    await store.dispatch(fetchInvestigationCAPA('INV-LEGACY-TEST'));

    const state = store.getState().investigations;

    // Direct legacy singleton property assertions used by existing components
    expect(state.currentInvestigation?.id).toBe('INV-LEGACY-TEST');
    expect(state.detailLoading).toBe(false);
    expect(state.detailError).toBeNull();
    expect(state.evidence).toHaveLength(1);
    expect(state.evidence[0].title).toBe('Calibration Log');
    expect(state.capa).toHaveLength(1);
    expect(state.capa[0].id).toBe('C-1');
    expect(state.currentInvestigation.evidence).toHaveLength(1);
    expect(state.currentInvestigation.capa).toHaveLength(1);
  });

  it('8. fetchInvestigations deduplicates in-flight calls and reuses fresh cached list', async () => {
    const store = createTestStore();
    const mockList = {
      items: [{ id: 'INV-LIST-1', title: 'Batch Deviation' }],
      pagination: { page: 1, limit: 6, total: 1, total_pages: 1 },
    };

    const spy = vi
      .spyOn(investigationService, 'listInvestigations')
      .mockImplementation(
        () => new Promise((resolve) => setTimeout(() => resolve(mockList), 20))
      );

    // Simultaneous dispatches with identical parameters produce only one service call
    const [res1, res2] = await Promise.all([
      store.dispatch(fetchInvestigations({ limit: 6 })),
      store.dispatch(fetchInvestigations({ limit: 6 })),
    ]);

    expect(spy).toHaveBeenCalledTimes(1);
    expect(res1.type).toBe('investigations/fetchList/fulfilled');
    expect(res2.meta.condition).toBe(true);

    const state = store.getState().investigations;
    expect(state.investigations).toHaveLength(1);
    expect(state.listLastFetched).not.toBeNull();

    // Re-dispatching with identical parameters reuses cache and skips fetch
    const repeated = await store.dispatch(fetchInvestigations({ limit: 6 }));
    expect(repeated.meta.condition).toBe(true);
    expect(spy).toHaveBeenCalledTimes(1);

    // Dispatching with different parameters triggers a new fetch
    await store.dispatch(fetchInvestigations({ page: 2, limit: 15 }));
    expect(spy).toHaveBeenCalledTimes(2);
  });

  it('9. capaService.listAllCAPA deduplicates concurrent requests and caches fresh results', async () => {
    const mockCapas = [{ action_id: 'C-ALL-1', status: 'Pending Review' }];
    const spy = vi
      .spyOn(api, 'get')
      .mockImplementation(
        () => new Promise((resolve) => setTimeout(() => resolve({ data: mockCapas }), 20))
      );

    // Two simultaneous calls share the same in-flight promise
    const [res1, res2] = await Promise.all([
      capaService.listAllCAPA({ status: 'Pending Review', limit: 4 }),
      capaService.listAllCAPA({ status: 'Pending Review', limit: 4 }),
    ]);

    expect(spy).toHaveBeenCalledTimes(1);
    expect(res1).toEqual(mockCapas);
    expect(res2).toEqual(mockCapas);

    // Subsequent call within TTL returns cached data without calling API again
    const cachedRes = await capaService.listAllCAPA({ status: 'Pending Review', limit: 4 });
    expect(spy).toHaveBeenCalledTimes(1);
    expect(cachedRes).toEqual(mockCapas);

    // Mutation clears the cache
    vi.spyOn(api, 'patch').mockResolvedValue({ data: { action_id: 'C-ALL-1', status: 'Approved' } });
    await capaService.updateCAPAStatus('INV-1', 'C-ALL-1', { status: 'Approved' });

    // Next call refetches from API
    await capaService.listAllCAPA({ status: 'Pending Review', limit: 4 });
    expect(spy).toHaveBeenCalledTimes(2);
  });

  it('10. investigationService.listInvestigations deduplicates concurrent in-flight requests', async () => {
    const mockData = { items: [{ id: 'INV-1' }], pagination: { total: 1 } };
    const spy = vi
      .spyOn(api, 'get')
      .mockImplementation(
        () => new Promise((resolve) => setTimeout(() => resolve({ data: mockData }), 20))
      );

    const [res1, res2] = await Promise.all([
      investigationService.listInvestigations({ search: 'Temperature', status: 'Open' }),
      investigationService.listInvestigations({ search: 'Temperature', status: 'Open' }),
    ]);

    expect(spy).toHaveBeenCalledTimes(1);
    expect(res1).toEqual(mockData);
    expect(res2).toEqual(mockData);
  });

  it('11. CAPA review mutation updates Redux cache and avoids redundant GET requests', async () => {
    const store = createTestStore();
    const invId = 'INV-CAPA-REVIEW';

    // 1. Initial investigation and CAPA load
    vi.spyOn(investigationService, 'getInvestigation').mockResolvedValue({
      investigation_id: invId,
      incident_title: 'Excursion Test',
    });
    const listSpy = vi.spyOn(capaService, 'listCAPA').mockResolvedValue([
      { id: 'C-1', description: 'Original Description', status: 'Proposed' },
    ]);

    await store.dispatch(fetchInvestigationById(invId));
    await store.dispatch(fetchInvestigationCAPA(invId));
    expect(listSpy).toHaveBeenCalledTimes(1);

    // 2. Perform QA Review mutation
    const updatedCapas = [
      { id: 'C-1', description: 'Reviewed Description', status: 'Approved', action_owner: 'QA Lead' },
    ];
    vi.spyOn(capaService, 'reviewCAPA').mockResolvedValue({
      capa_review_status: 'REVIEWED',
      capa_recommendations: updatedCapas,
    });

    await store.dispatch(
      reviewCAPAActions({
        investigationId: invId,
        decisions: [{ capa_id: 'C-1', decision: 'Approved' }],
      })
    );

    // 3. Store and cache are updated directly
    const state = store.getState().investigations;
    expect(state.capa[0].status).toBe('Approved');
    expect(state.cacheById[invId]?.capa?.data[0].status).toBe('Approved');

    // 4. Subsequent fetchInvestigationCAPA is caught by condition guard (0 HTTP GET calls)
    const refetch = await store.dispatch(fetchInvestigationCAPA(invId));
    expect(refetch.meta.condition).toBe(true);
    expect(listSpy).toHaveBeenCalledTimes(1);
  });
});
