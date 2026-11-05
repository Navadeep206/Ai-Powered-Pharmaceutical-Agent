import { createSlice, createAsyncThunk } from '@reduxjs/toolkit';
import investigationService from '../../services/investigationService';
import rcaService from '../../services/rcaService';
import evidenceService from '../../services/evidenceService';
import capaService from '../../services/capaService';
import { normalizeInvestigation } from '../../utils/normalizers';

export const fetchInvestigations = createAsyncThunk(
  'investigations/fetchList',
  async (params = {}, { rejectWithValue }) => {
    try {
      const response = await investigationService.listInvestigations(params);
      return {
        items: (response.items || []).map(normalizeInvestigation),
        pagination: response.pagination || {
          page: 1,
          limit: params.limit || 20,
          total: response.items ? response.items.length : 0,
          total_pages: 1,
          has_next: false,
          has_prev: false,
        },
      };
    } catch (err) {
      return rejectWithValue({
        message: err.message || 'Failed to retrieve quality investigations.',
        statusCode: err.statusCode || null,
        isNetworkError: Boolean(err.isNetworkError),
      });
    }
  }
);

export const fetchInvestigationById = createAsyncThunk(
  'investigations/fetchById',
  async (id, { rejectWithValue }) => {
    try {
      const data = await investigationService.getInvestigation(id);
      return normalizeInvestigation(data);
    } catch (err) {
      return rejectWithValue({
        message: err.message || `Failed to retrieve investigation ${id}.`,
        statusCode: err.statusCode || null,
        isNetworkError: Boolean(err.isNetworkError),
      });
    }
  }
);

export const createInvestigationAsync = createAsyncThunk(
  'investigations/create',
  async (payload, { rejectWithValue }) => {
    try {
      const data = await investigationService.createInvestigation(payload);
      return normalizeInvestigation(data);
    } catch (err) {
      return rejectWithValue({
        message: err.message || 'Failed to create quality investigation.',
        statusCode: err.statusCode || null,
        details: err.details || null,
      });
    }
  }
);

export const fetchInvestigationRCA = createAsyncThunk(
  'investigations/fetchRCA',
  async (id, { rejectWithValue }) => {
    try {
      const data = await rcaService.getRCA(id);
      return data;
    } catch (err) {
      return rejectWithValue({
        message: err.message || 'Failed to retrieve RCA analysis.',
        statusCode: err.statusCode || null,
      });
    }
  }
);

export const fetchInvestigationEvidence = createAsyncThunk(
  'investigations/fetchEvidence',
  async (id, { rejectWithValue }) => {
    try {
      const data = await evidenceService.listEvidence(id);
      return data;
    } catch (err) {
      return rejectWithValue({
        message: err.message || 'Failed to retrieve evidence records.',
        statusCode: err.statusCode || null,
      });
    }
  }
);

export const fetchInvestigationCAPA = createAsyncThunk(
  'investigations/fetchCAPA',
  async (id, { rejectWithValue }) => {
    try {
      const data = await capaService.listCAPA(id);
      return data;
    } catch (err) {
      return rejectWithValue({
        message: err.message || 'Failed to retrieve CAPA records.',
        statusCode: err.statusCode || null,
      });
    }
  }
);

const initialState = {
  // Master listing
  investigations: [],
  pagination: null,
  listLoading: false,
  listError: null,

  // Investigation Detail
  currentInvestigation: null,
  detailLoading: false,
  detailError: null,
  detailStatusCode: null,

  // Associated Tabs
  rca: null,
  rcaLoading: false,
  rcaError: null,

  evidence: [],
  evidenceLoading: false,
  evidenceError: null,

  capa: [],
  capaLoading: false,
  capaError: null,

  // Intake State
  draftIntake: {
    method: 'upload',
    fileInfo: null,
    rawText: '',
    emailSubject: '',
    emailBody: '',
    extractionState: 'idle',
    extractedData: null,
    isEdited: false,
  },
};

export const investigationSlice = createSlice({
  name: 'investigations',
  initialState,
  reducers: {
    clearInvestigationErrors: (state) => {
      state.listError = null;
      state.detailError = null;
      state.detailStatusCode = null;
    },
    setIntakeMethod: (state, action) => {
      state.draftIntake.method = action.payload;
    },
    setIntakeFile: (state, action) => {
      state.draftIntake.fileInfo = action.payload;
    },
    clearIntakeFile: (state) => {
      state.draftIntake.fileInfo = null;
    },
    setIntakeText: (state, action) => {
      state.draftIntake.rawText = action.payload;
    },
    setIntakeEmail: (state, action) => {
      state.draftIntake.emailSubject = action.payload.subject;
      state.draftIntake.emailBody = action.payload.body;
    },
    setExtractionState: (state, action) => {
      state.draftIntake.extractionState = action.payload;
    },
    setExtractedData: (state, action) => {
      state.draftIntake.extractedData = action.payload;
      state.draftIntake.extractionState = 'extracted';
      state.draftIntake.isEdited = false;
    },
    updateExtractedField: (state, action) => {
      const { section, field, value } = action.payload;
      if (state.draftIntake.extractedData && state.draftIntake.extractedData[section]) {
        state.draftIntake.extractedData[section][field] = value;
        state.draftIntake.isEdited = true;
      }
    },
    resetDraftIntake: (state) => {
      state.draftIntake = {
        method: 'upload',
        fileInfo: null,
        rawText: '',
        emailSubject: '',
        emailBody: '',
        extractionState: 'idle',
        extractedData: null,
        isEdited: false,
      };
    },
    updateInvestigationDetails: (state, action) => {
      const { id, incidentInfo, context } = action.payload;
      const inv = state.investigations.find((item) => item.id === id);
      if (inv) {
        if (incidentInfo) inv.incidentInfo = { ...inv.incidentInfo, ...incidentInfo };
        if (context) inv.context = { ...inv.context, ...context };
      }
      if (state.currentInvestigation && state.currentInvestigation.id === id) {
        if (incidentInfo) state.currentInvestigation.incidentInfo = { ...state.currentInvestigation.incidentInfo, ...incidentInfo };
        if (context) state.currentInvestigation.context = { ...state.currentInvestigation.context, ...context };
      }
    },
    updateFiveWhysLevel: (state, action) => {
      const { id, levelIndex, answer, evidence, status } = action.payload;
      const target = state.currentInvestigation?.id === id ? state.currentInvestigation : state.investigations.find((i) => i.id === id);
      if (target && target.fiveWhys && target.fiveWhys[levelIndex]) {
        if (answer !== undefined) target.fiveWhys[levelIndex].answer = answer;
        if (evidence !== undefined) target.fiveWhys[levelIndex].evidence = evidence;
        if (status !== undefined) target.fiveWhys[levelIndex].status = status;
      }
    },
    addFishboneCause: (state, action) => {
      const { id, category, cause, status } = action.payload;
      const target = state.currentInvestigation?.id === id ? state.currentInvestigation : state.investigations.find((i) => i.id === id);
      if (target && target.fishbone && target.fishbone[category]) {
        target.fishbone[category].push({
          id: `cause-${Date.now()}`,
          cause,
          category,
          status: status || 'Pending Human Review',
        });
      }
    },
    updateFishboneCauseStatus: (state, action) => {
      const { id, category, causeId, status } = action.payload;
      const target = state.currentInvestigation?.id === id ? state.currentInvestigation : state.investigations.find((i) => i.id === id);
      if (target && target.fishbone && target.fishbone[category]) {
        const item = target.fishbone[category].find((c) => c.id === causeId);
        if (item) item.status = status;
      }
    },
    removeFishboneCause: (state, action) => {
      const { id, category, causeId } = action.payload;
      const target = state.currentInvestigation?.id === id ? state.currentInvestigation : state.investigations.find((i) => i.id === id);
      if (target && target.fishbone && target.fishbone[category]) {
        target.fishbone[category] = target.fishbone[category].filter((c) => c.id !== causeId);
      }
    },
    addEvidenceItem: (state, action) => {
      const { id, item } = action.payload;
      const target = state.currentInvestigation?.id === id ? state.currentInvestigation : state.investigations.find((i) => i.id === id);
      if (target) {
        if (!target.evidence) target.evidence = [];
        target.evidence.push({
          id: `EVD-${Date.now()}`,
          ...item,
        });
      }
    },
    updateEvidenceStatus: (state, action) => {
      const { id, evidenceId, status } = action.payload;
      const target = state.currentInvestigation?.id === id ? state.currentInvestigation : state.investigations.find((i) => i.id === id);
      if (target && target.evidence) {
        const item = target.evidence.find((e) => e.id === evidenceId);
        if (item) item.status = status;
      }
    },
    updateCAPA: (state, action) => {
      const { id, capa } = action.payload;
      const target = state.currentInvestigation?.id === id ? state.currentInvestigation : state.investigations.find((i) => i.id === id);
      if (target) {
        target.capa = { ...target.capa, ...capa };
      }
    },
    createNewInvestigationFromIntake: (state, action) => {
      const { extractedData } = action.payload;
      const newId = `INV-${new Date().getFullYear()}-${Math.floor(1000 + Math.random() * 9000)}`;
      const newInv = normalizeInvestigation({
        investigation_id: newId,
        incident_title: extractedData.incidentInfo.incidentTitle || 'New Investigated Event',
        department: extractedData.incidentInfo.department || 'Chemical Synthesis',
        batch_number: extractedData.incidentInfo.batchNumber || 'API-NEW',
        product_name: extractedData.incidentInfo.productName || 'Active Pharmaceutical Ingredient',
        equipment: extractedData.incidentInfo.equipment || 'Reactor / Process Unit',
        severity: extractedData.incidentInfo.severity || 'Major',
        investigation_status: 'Under Investigation',
        incident_date: new Date().toISOString().split('T')[0],
        detection_date: extractedData.incidentInfo.detectionDate || new Date().toISOString().split('T')[0],
        reported_by: 'Quality Assurance Unit',
        incident_description: extractedData.incidentInfo.incidentDescription || '',
        immediate_action_taken: extractedData.incidentInfo.immediateActionTaken || '',
        expected_condition: extractedData.context?.expectedCondition || '',
        actual_condition: extractedData.context?.actualCondition || '',
        observed_impact: extractedData.context?.observedImpact || '',
        affected_process: extractedData.context?.affectedProcess || '',
        initial_observations: extractedData.context?.initialObservations || '',
      });

      state.investigations.unshift(newInv);
      state.currentInvestigation = newInv;
      return newId;
    },
  },
  extraReducers: (builder) => {
    builder
      // Fetch List
      .addCase(fetchInvestigations.pending, (state) => {
        state.listLoading = true;
        state.listError = null;
      })
      .addCase(fetchInvestigations.fulfilled, (state, action) => {
        state.listLoading = false;
        state.investigations = action.payload.items;
        state.pagination = action.payload.pagination;
        state.listError = null;
      })
      .addCase(fetchInvestigations.rejected, (state, action) => {
        state.listLoading = false;
        state.listError = action.payload?.message || 'Failed to retrieve quality investigations.';
      })

      // Fetch by ID
      .addCase(fetchInvestigationById.pending, (state) => {
        state.detailLoading = true;
        state.detailError = null;
        state.detailStatusCode = null;
      })
      .addCase(fetchInvestigationById.fulfilled, (state, action) => {
        state.detailLoading = false;
        state.currentInvestigation = action.payload;
        state.detailError = null;
        state.detailStatusCode = null;
      })
      .addCase(fetchInvestigationById.rejected, (state, action) => {
        state.detailLoading = false;
        state.currentInvestigation = null;
        state.detailError = action.payload?.message || 'Failed to retrieve investigation.';
        state.detailStatusCode = action.payload?.statusCode || null;
      })

      // Create
      .addCase(createInvestigationAsync.fulfilled, (state, action) => {
        state.investigations.unshift(action.payload);
        state.currentInvestigation = action.payload;
      })

      // RCA
      .addCase(fetchInvestigationRCA.pending, (state) => {
        state.rcaLoading = true;
        state.rcaError = null;
      })
      .addCase(fetchInvestigationRCA.fulfilled, (state, action) => {
        state.rcaLoading = false;
        state.rca = action.payload;
        if (state.currentInvestigation) {
          if (action.payload.five_whys?.length > 0) {
            state.currentInvestigation.fiveWhys = action.payload.five_whys;
          }
          if (action.payload.fishbone_causes?.length > 0) {
            // Group fishbone by category
            const grouped = {
              Manpower: [],
              Machine: [],
              Method: [],
              Material: [],
              Measurement: [],
              Environment: [],
            };
            action.payload.fishbone_causes.forEach((c) => {
              const cat = c.category;
              if (grouped[cat]) grouped[cat].push(c);
            });
            state.currentInvestigation.fishbone = grouped;
          }
        }
      })
      .addCase(fetchInvestigationRCA.rejected, (state, action) => {
        state.rcaLoading = false;
        state.rcaError = action.payload?.message || 'Failed to retrieve RCA analysis.';
      })

      // Evidence
      .addCase(fetchInvestigationEvidence.pending, (state) => {
        state.evidenceLoading = true;
        state.evidenceError = null;
      })
      .addCase(fetchInvestigationEvidence.fulfilled, (state, action) => {
        state.evidenceLoading = false;
        state.evidence = action.payload;
        if (state.currentInvestigation && Array.isArray(action.payload)) {
          state.currentInvestigation.evidence = action.payload;
        }
      })
      .addCase(fetchInvestigationEvidence.rejected, (state, action) => {
        state.evidenceLoading = false;
        state.evidenceError = action.payload?.message || 'Failed to retrieve evidence.';
      })

      // CAPA
      .addCase(fetchInvestigationCAPA.pending, (state) => {
        state.capaLoading = true;
        state.capaError = null;
      })
      .addCase(fetchInvestigationCAPA.fulfilled, (state, action) => {
        state.capaLoading = false;
        state.capa = action.payload;
        if (state.currentInvestigation && Array.isArray(action.payload)) {
          state.currentInvestigation.capa = action.payload;
        }
      })
      .addCase(fetchInvestigationCAPA.rejected, (state, action) => {
        state.capaLoading = false;
        state.capaError = action.payload?.message || 'Failed to retrieve CAPA records.';
      });
  },
});

export const {
  clearInvestigationErrors,
  setIntakeMethod,
  setIntakeFile,
  clearIntakeFile,
  setIntakeText,
  setIntakeEmail,
  setExtractionState,
  setExtractedData,
  updateExtractedField,
  resetDraftIntake,
  updateInvestigationDetails,
  updateFiveWhysLevel,
  addFishboneCause,
  updateFishboneCauseStatus,
  removeFishboneCause,
  addEvidenceItem,
  updateEvidenceStatus,
  updateCAPA,
  createNewInvestigationFromIntake,
} = investigationSlice.actions;

export default investigationSlice.reducer;
