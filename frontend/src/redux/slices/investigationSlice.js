import { createSlice, createAsyncThunk } from '@reduxjs/toolkit';
import investigationService from '../../services/investigationService';
import documentService from '../../services/documentService';
import rcaService from '../../services/rcaService';
import evidenceService from '../../services/evidenceService';
import capaService from '../../services/capaService';
import {
  normalizeInvestigation,
  normalizeExtractionResponse,
  normalizeEvidence,
  normalizeCAPA,
  normalizeFiveWhys,
  normalizeFishbone,
} from '../../utils/normalizers';

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

/**
 * Async thunk orchestrating real multi-modal intake preprocessing and LangGraph AI extraction.
 */
export const analyzeIncidentIntake = createAsyncThunk(
  'investigations/analyzeIncidentIntake',
  async ({ method, file, rawText, emailSubject, emailBody }, { dispatch, rejectWithValue }) => {
    try {
      let analysisPayload = null;

      if (method === 'upload') {
        if (!file) {
          throw new Error('Please select or provide a valid PDF document to upload.');
        }

        dispatch(setAnalysisProgress('uploading'));
        const uploadResult = await documentService.uploadDocument(file);

        dispatch(setAnalysisProgress('extracting_text'));

        // Handle scanned document requiring OCR
        const statusUpper = (uploadResult.extraction_status || '').toUpperCase();
        if (statusUpper.includes('OCR')) {
          dispatch(setAnalysisProgress('ocr_required'));
        }

        analysisPayload = {
          intake_method: 'Document',
          document_id: uploadResult.document_id,
          document_text: uploadResult.extracted_text || '',
        };
      } else if (method === 'text') {
        if (!rawText || rawText.trim().length < 15) {
          throw new Error('Please provide a descriptive incident narrative (at least 15 characters).');
        }

        dispatch(setAnalysisProgress('analyzing'));
        analysisPayload = {
          intake_method: 'Text',
          text_input: {
            incident_text: rawText.trim(),
          },
        };
      } else if (method === 'email') {
        if (!emailSubject?.trim() && !emailBody?.trim()) {
          throw new Error('Please provide an email subject header or body content to analyze.');
        }

        dispatch(setAnalysisProgress('analyzing'));
        analysisPayload = {
          intake_method: 'Email',
          email_input: {
            subject: (emailSubject || 'Incident Notification Email').trim(),
            body: (emailBody || emailSubject || '').trim(),
          },
        };
      } else {
        throw new Error(`Unsupported intake method: ${method}`);
      }

      dispatch(setAnalysisProgress('validating'));
      const extractionResponse = await documentService.extractDocument(analysisPayload);
      const normalized = normalizeExtractionResponse(extractionResponse);

      return normalized;
    } catch (err) {
      return rejectWithValue({
        message: err.message || 'Incident extraction failed.',
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

/**
 * Persist 5-Whys and Ishikawa Fishbone findings into PostgreSQL.
 */
export const saveInvestigationRCA = createAsyncThunk(
  'investigations/saveRCA',
  async ({ investigationId, fiveWhys, fishboneCauses, summary }, { rejectWithValue }) => {
    try {
      const payload = {
        five_whys: (fiveWhys || []).map((w, idx) => ({
          level: w.level || idx + 1,
          question: w.question || `Why level ${w.level || idx + 1}`,
          answer: w.answer || '',
          evidence_references: Array.isArray(w.evidence)
            ? w.evidence
            : typeof w.evidence === 'string' && w.evidence.trim()
            ? [w.evidence.trim()]
            : [],
          is_root_cause: Boolean(w.is_root_cause),
          status: w.status || 'Requires Evidence',
        })),
        fishbone_causes: Object.entries(fishboneCauses || {}).flatMap(([cat, list]) =>
          (list || []).map((c, idx) => ({
            cause_id: c.id || `CAUSE-${cat.slice(0, 3).toUpperCase()}-${idx + 1}`,
            category: cat,
            cause_description: c.cause || c.cause_description || '',
            evidence_references: Array.isArray(c.evidence)
              ? c.evidence
              : typeof c.evidence === 'string' && c.evidence.trim()
              ? [c.evidence.trim()]
              : [],
            status: c.status || 'Requires Evidence',
            contributing_factors: [],
          }))
        ),
        investigator_notes: summary || null,
      };

      const data = await rcaService.saveRCA(investigationId, payload);
      return data;
    } catch (err) {
      return rejectWithValue({
        message: err.message || 'Failed to persist RCA findings in PostgreSQL.',
        statusCode: err.statusCode || null,
      });
    }
  }
);

/**
 * Trigger real LangGraph AI reasoning workflow for 5-Whys, 6M Fishbone, and Root Cause Candidates.
 */
export const generateInvestigationRCA = createAsyncThunk(
  'investigations/generateRCA',
  async ({ investigationId, problemStatement, incidentContext, facts }, { rejectWithValue }) => {
    try {
      const payload = {
        problem_statement: problemStatement || undefined,
        incident_context: incidentContext || {},
        investigation_facts: facts || [],
        persist: true,
      };
      const data = await rcaService.generateRCA(investigationId, payload);
      return data;
    } catch (err) {
      return rejectWithValue({
        message: err.message || 'AI RCA reasoning execution failed.',
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
      return (data || []).map(normalizeEvidence);
    } catch (err) {
      return rejectWithValue({
        message: err.message || 'Failed to retrieve evidence records.',
        statusCode: err.statusCode || null,
      });
    }
  }
);

/**
 * Attach and persist a new evidence finding to PostgreSQL.
 */
export const createEvidenceRecord = createAsyncThunk(
  'investigations/createEvidence',
  async ({ investigationId, item }, { rejectWithValue }) => {
    try {
      let evidenceType = 'Supporting';
      const cat = (item.category || '').toLowerCase();
      if (cat.includes('contra')) evidenceType = 'Contradictory';
      else if (cat.includes('miss')) evidenceType = 'Missing Evidence';
      else if (cat.includes('question') || cat.includes('inquiry')) evidenceType = 'Investigator Question';

      const payload = {
        description: item.title
          ? `${item.title}: ${item.notes || ''}`.trim()
          : item.description || item.notes || 'Evidence item',
        evidence_type: item.evidence_type || evidenceType,
        source_reference: item.reference || item.source_reference || 'Physical / System Record',
        review_status:
          item.review_status || (item.status === 'Verified by QA' ? 'Verified' : 'Pending Review'),
        notes: item.notes || null,
      };

      const data = await evidenceService.createEvidence(investigationId, payload);
      return normalizeEvidence(data);
    } catch (err) {
      return rejectWithValue({
        message: err.message || 'Failed to persist evidence record in PostgreSQL.',
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
      return (data || []).map(normalizeCAPA);
    } catch (err) {
      return rejectWithValue({
        message: err.message || 'Failed to retrieve CAPA records.',
        statusCode: err.statusCode || null,
      });
    }
  }
);

/**
 * Execute LangGraph AI-assisted CAPA recommendations workflow.
 */
export const generateCAPAActions = createAsyncThunk(
  'investigations/generateCAPA',
  async ({ investigationId, problemStatement }, { rejectWithValue }) => {
    try {
      const data = await capaService.generateCAPA(investigationId, {
        problem_statement: problemStatement || undefined,
        persist: true,
      });
      return data;
    } catch (err) {
      return rejectWithValue({
        message: err.message || 'AI CAPA recommendation generation failed.',
        statusCode: err.statusCode || null,
      });
    }
  }
);

/**
 * Propose and persist a new CAPA remediation action to PostgreSQL.
 */
export const createCAPAAction = createAsyncThunk(
  'investigations/createCAPA',
  async ({ investigationId, actionData }, { rejectWithValue }) => {
    try {
      const payload = {
        action_type: actionData.action_type || actionData.actionType || 'Corrective Action',
        description: actionData.description || 'Remediation action specification',
        action_owner: actionData.action_owner || actionData.actionOwner || 'QA Specialist',
        target_date:
          actionData.target_date ||
          actionData.targetDate ||
          new Date(Date.now() + 30 * 86400000).toISOString().split('T')[0],
        effectiveness_verification_method:
          actionData.effectiveness_verification_method ||
          actionData.effectivenessVerification ||
          'Verification protocol to be executed across subsequent commercial lots.',
        status: actionData.status || 'Draft',
        related_root_cause_reference: actionData.related_root_cause_reference || null,
      };

      const data = await capaService.createCAPA(investigationId, payload);
      return normalizeCAPA(data);
    } catch (err) {
      return rejectWithValue({
        message: err.message || 'Failed to record CAPA action in database.',
        statusCode: err.statusCode || null,
      });
    }
  }
);

/**
 * Submit human QA review decisions (approval, rejection, owner/date edits) for CAPA actions.
 */
export const reviewCAPAActions = createAsyncThunk(
  'investigations/reviewCAPA',
  async ({ investigationId, decisions, generalComments }, { rejectWithValue }) => {
    try {
      const payload = {
        decisions: decisions || [],
        general_comments: generalComments || null,
        reviewer_identifier: 'Quality Assurance Reviewer',
      };
      const data = await capaService.reviewCAPA(investigationId, payload);
      return data;
    } catch (err) {
      return rejectWithValue({
        message: err.message || 'Failed to apply CAPA review decisions.',
        statusCode: err.statusCode || null,
      });
    }
  }
);

/**
 * Transition individual CAPA status adhering to GxP lifecycle gates.
 */
export const updateCAPAStatusAsync = createAsyncThunk(
  'investigations/updateCAPAStatus',
  async ({ investigationId, capaId, status, notes }, { rejectWithValue }) => {
    try {
      const data = await capaService.updateCAPAStatus(investigationId, capaId, {
        status,
        notes: notes || null,
      });
      return normalizeCAPA(data);
    } catch (err) {
      return rejectWithValue({
        message: err.message || 'Failed to update CAPA status.',
        statusCode: err.statusCode || null,
      });
    }
  }
);

/**
 * Retrieve document metadata associated with an investigation.
 */
export const fetchInvestigationDocuments = createAsyncThunk(
  'investigations/fetchDocuments',
  async (investigationId, { rejectWithValue }) => {
    try {
      const data = await investigationService.listDocuments(investigationId);
      return data;
    } catch (err) {
      return rejectWithValue({
        message: err.message || 'Failed to retrieve investigation documents.',
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
    fileInfo: null, // Pure serializable metadata (name, size, type, lastModified)
    rawText: '',
    emailSubject: '',
    emailBody: '',
    extractionState: 'idle', // 'idle' | 'analyzing' | 'extracted' | 'failed'
    analysisProgress: 'idle', // 'idle' | 'uploading' | 'extracting_text' | 'analyzing' | 'validating' | 'completed' | 'failed' | 'ocr_required'
    extractionError: null,
    extractionResponse: null,
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
    setAnalysisProgress: (state, action) => {
      state.draftIntake.analysisProgress = action.payload;
    },
    setExtractedData: (state, action) => {
      state.draftIntake.extractedData = action.payload;
      state.draftIntake.extractionState = 'extracted';
      state.draftIntake.isEdited = false;
    },
    updateExtractedField: (state, action) => {
      const { section, field, value, canonicalKey } = action.payload;
      if (!state.draftIntake.extractedData) return;

      if (state.draftIntake.extractedData[section]) {
        state.draftIntake.extractedData[section][field] = value;
      }

      const metaKey = canonicalKey || field;
      if (state.draftIntake.extractedData.fieldMeta) {
        let targetMeta = state.draftIntake.extractedData.fieldMeta[metaKey];
        if (!targetMeta && section === 'context') {
          const aliasMap = {
            expectedCondition: 'expected_condition',
            actualCondition: 'actual_condition',
            observedImpact: 'potential_impact',
            affectedProcess: 'process_stage',
            initialObservations: 'observations',
          };
          if (aliasMap[field]) targetMeta = state.draftIntake.extractedData.fieldMeta[aliasMap[field]];
        } else if (!targetMeta && section === 'incidentInfo') {
          const aliasMap = {
            deviationId: 'deviation_id',
            batchNumber: 'batch_number',
            incidentTitle: 'incident_title',
            incidentDescription: 'incident_description',
            productName: 'product_name',
            apiName: 'api_name',
            department: 'department',
            equipment: 'equipment_id',
            incidentDate: 'incident_date',
            detectionDate: 'detection_date',
            immediateActionTaken: 'immediate_action_taken',
          };
          if (aliasMap[field]) targetMeta = state.draftIntake.extractedData.fieldMeta[aliasMap[field]];
        }

        if (targetMeta) {
          if (!targetMeta.is_human_modified && targetMeta.ai_extracted_value === null) {
            targetMeta.ai_extracted_value = targetMeta.value;
          }
          targetMeta.value = value;
          targetMeta.human_edited_value = value;
          targetMeta.is_human_modified = true;
          targetMeta.review_status = 'HUMAN_REVIEWED';
          targetMeta.requires_human_review = false;
        }
      }

      state.draftIntake.isEdited = true;
    },
    revertExtractedField: (state, action) => {
      const { section, field, canonicalKey } = action.payload;
      if (!state.draftIntake.extractedData) return;

      const metaKey = canonicalKey || field;
      let targetMeta = state.draftIntake.extractedData.fieldMeta?.[metaKey];

      if (!targetMeta && section === 'context') {
        const aliasMap = {
          expectedCondition: 'expected_condition',
          actualCondition: 'actual_condition',
          observedImpact: 'potential_impact',
          affectedProcess: 'process_stage',
          initialObservations: 'observations',
        };
        if (aliasMap[field]) targetMeta = state.draftIntake.extractedData.fieldMeta?.[aliasMap[field]];
      } else if (!targetMeta && section === 'incidentInfo') {
        const aliasMap = {
          deviationId: 'deviation_id',
          batchNumber: 'batch_number',
          incidentTitle: 'incident_title',
          incidentDescription: 'incident_description',
          productName: 'product_name',
          apiName: 'api_name',
          department: 'department',
          equipment: 'equipment_id',
          incidentDate: 'incident_date',
          detectionDate: 'detection_date',
          immediateActionTaken: 'immediate_action_taken',
        };
        if (aliasMap[field]) targetMeta = state.draftIntake.extractedData.fieldMeta?.[aliasMap[field]];
      }

      if (targetMeta) {
        const originalValue = targetMeta.ai_extracted_value ?? '';
        targetMeta.value = originalValue;
        targetMeta.human_edited_value = null;
        targetMeta.is_human_modified = false;
        targetMeta.review_status = 'AI_SUGGESTED';
        targetMeta.requires_human_review = true;

        if (state.draftIntake.extractedData[section]) {
          state.draftIntake.extractedData[section][field] = originalValue;
        }
      }
    },
    confirmExtractedField: (state, action) => {
      const { canonicalKey } = action.payload;
      const meta = state.draftIntake.extractedData?.fieldMeta?.[canonicalKey];
      if (meta) {
        meta.review_status = 'HUMAN_CONFIRMED';
        meta.is_verified = true;
        meta.requires_human_review = false;
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
        analysisProgress: 'idle',
        extractionError: null,
        extractionResponse: null,
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
          status: status || 'Requires Evidence',
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
        target.evidence.push(normalizeEvidence(item));
      }
    },
    updateEvidenceStatus: (state, action) => {
      const { id, evidenceId, status } = action.payload;
      const target = state.currentInvestigation?.id === id ? state.currentInvestigation : state.investigations.find((i) => i.id === id);
      if (target && target.evidence) {
        const item = target.evidence.find((e) => e.id === evidenceId || e.evidence_id === evidenceId);
        if (item) {
          item.status = status;
          item.review_status = status;
        }
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

      // AI Intake Extraction
      .addCase(analyzeIncidentIntake.pending, (state) => {
        state.draftIntake.extractionState = 'analyzing';
        state.draftIntake.extractionError = null;
      })
      .addCase(analyzeIncidentIntake.fulfilled, (state, action) => {
        state.draftIntake.extractionState = 'extracted';
        state.draftIntake.analysisProgress = 'completed';
        state.draftIntake.extractionResponse = action.payload;
        state.draftIntake.extractedData = action.payload;
        state.draftIntake.isEdited = false;
        state.draftIntake.extractionError = null;
      })
      .addCase(analyzeIncidentIntake.rejected, (state, action) => {
        state.draftIntake.extractionState = 'failed';
        state.draftIntake.analysisProgress = 'failed';
        state.draftIntake.extractionError = action.payload?.message || 'AI extraction failed.';
      })

      // RCA - Fetch
      .addCase(fetchInvestigationRCA.pending, (state) => {
        state.rcaLoading = true;
        state.rcaError = null;
      })
      .addCase(fetchInvestigationRCA.fulfilled, (state, action) => {
        state.rcaLoading = false;
        state.rca = action.payload;
        if (state.currentInvestigation) {
          if (action.payload.five_whys?.length > 0) {
            state.currentInvestigation.fiveWhys = normalizeFiveWhys(action.payload.five_whys);
          }
          if (action.payload.fishbone_causes?.length > 0) {
            state.currentInvestigation.fishbone = normalizeFishbone(action.payload.fishbone_causes);
          }
        }
      })
      .addCase(fetchInvestigationRCA.rejected, (state, action) => {
        state.rcaLoading = false;
        state.rcaError = action.payload?.message || 'Failed to retrieve RCA analysis.';
      })

      // RCA - Save
      .addCase(saveInvestigationRCA.pending, (state) => {
        state.rcaLoading = true;
        state.rcaError = null;
      })
      .addCase(saveInvestigationRCA.fulfilled, (state, action) => {
        state.rcaLoading = false;
        state.rca = action.payload;
        if (state.currentInvestigation) {
          if (action.payload.five_whys?.length > 0) {
            state.currentInvestigation.fiveWhys = normalizeFiveWhys(action.payload.five_whys);
          }
          if (action.payload.fishbone_causes?.length > 0) {
            state.currentInvestigation.fishbone = normalizeFishbone(action.payload.fishbone_causes);
          }
        }
      })
      .addCase(saveInvestigationRCA.rejected, (state, action) => {
        state.rcaLoading = false;
        state.rcaError = action.payload?.message || 'Failed to save RCA findings in database.';
      })

      // RCA - Generate
      .addCase(generateInvestigationRCA.pending, (state) => {
        state.rcaLoading = true;
        state.rcaError = null;
      })
      .addCase(generateInvestigationRCA.fulfilled, (state, action) => {
        state.rcaLoading = false;
        state.rca = action.payload;
        if (state.currentInvestigation) {
          if (action.payload.five_whys_analysis?.length > 0) {
            state.currentInvestigation.fiveWhys = normalizeFiveWhys(action.payload.five_whys_analysis);
          }
          if (action.payload.fishbone_analysis?.length > 0) {
            state.currentInvestigation.fishbone = normalizeFishbone(action.payload.fishbone_analysis);
          }
          if (action.payload.evidence_assessment?.length > 0) {
            const newEvidences = action.payload.evidence_assessment.map(normalizeEvidence);
            state.currentInvestigation.evidence = [
              ...newEvidences,
              ...(state.currentInvestigation.evidence || []),
            ];
          }
        }
      })
      .addCase(generateInvestigationRCA.rejected, (state, action) => {
        state.rcaLoading = false;
        state.rcaError = action.payload?.message || 'Failed to generate AI RCA findings.';
      })

      // Evidence - Fetch
      .addCase(fetchInvestigationEvidence.pending, (state) => {
        state.evidenceLoading = true;
        state.evidenceError = null;
      })
      .addCase(fetchInvestigationEvidence.fulfilled, (state, action) => {
        state.evidenceLoading = false;
        state.evidence = action.payload;
        if (state.currentInvestigation) {
          state.currentInvestigation.evidence = action.payload;
        }
      })
      .addCase(fetchInvestigationEvidence.rejected, (state, action) => {
        state.evidenceLoading = false;
        state.evidenceError = action.payload?.message || 'Failed to retrieve evidence.';
      })

      // Evidence - Create
      .addCase(createEvidenceRecord.fulfilled, (state, action) => {
        if (state.currentInvestigation) {
          if (!state.currentInvestigation.evidence) state.currentInvestigation.evidence = [];
          state.currentInvestigation.evidence.unshift(action.payload);
        }
        state.evidence.unshift(action.payload);
      })

      // CAPA - Fetch
      .addCase(fetchInvestigationCAPA.pending, (state) => {
        state.capaLoading = true;
        state.capaError = null;
      })
      .addCase(fetchInvestigationCAPA.fulfilled, (state, action) => {
        state.capaLoading = false;
        state.capa = action.payload;
        if (state.currentInvestigation) {
          state.currentInvestigation.capa = action.payload;
        }
      })
      .addCase(fetchInvestigationCAPA.rejected, (state, action) => {
        state.capaLoading = false;
        state.capaError = action.payload?.message || 'Failed to retrieve CAPA records.';
      })

      // CAPA - Generate
      .addCase(generateCAPAActions.pending, (state) => {
        state.capaLoading = true;
        state.capaError = null;
      })
      .addCase(generateCAPAActions.fulfilled, (state, action) => {
        state.capaLoading = false;
        const normalizedList = (action.payload.capa_recommendations || []).map(normalizeCAPA);
        if (state.currentInvestigation) {
          state.currentInvestigation.capa = normalizedList;
        }
        state.capa = normalizedList;
      })
      .addCase(generateCAPAActions.rejected, (state, action) => {
        state.capaLoading = false;
        state.capaError = action.payload?.message || 'Failed to generate AI CAPA actions.';
      })

      // CAPA - Create
      .addCase(createCAPAAction.fulfilled, (state, action) => {
        if (state.currentInvestigation) {
          if (!state.currentInvestigation.capa) state.currentInvestigation.capa = [];
          state.currentInvestigation.capa.unshift(action.payload);
        }
        state.capa.unshift(action.payload);
      })

      // CAPA - Review
      .addCase(reviewCAPAActions.pending, (state) => {
        state.capaLoading = true;
        state.capaError = null;
      })
      .addCase(reviewCAPAActions.fulfilled, (state, action) => {
        state.capaLoading = false;
        if (action.payload?.capa_recommendations?.length > 0) {
          const normalizedList = action.payload.capa_recommendations.map(normalizeCAPA);
          if (state.currentInvestigation) {
            state.currentInvestigation.capa = normalizedList;
          }
          state.capa = normalizedList;
        }
      })
      .addCase(reviewCAPAActions.rejected, (state, action) => {
        state.capaLoading = false;
        state.capaError = action.payload?.message || 'Failed to apply CAPA review decisions.';
      })

      // CAPA - Update Status
      .addCase(updateCAPAStatusAsync.fulfilled, (state, action) => {
        if (state.currentInvestigation && Array.isArray(state.currentInvestigation.capa)) {
          const idx = state.currentInvestigation.capa.findIndex(
            (c) => c.id === action.payload.id || c.action_id === action.payload.action_id
          );
          if (idx !== -1) {
            state.currentInvestigation.capa[idx] = action.payload;
          }
        }
        const stateIdx = state.capa.findIndex(
          (c) => c.id === action.payload.id || c.action_id === action.payload.action_id
        );
        if (stateIdx !== -1) {
          state.capa[stateIdx] = action.payload;
        }
      })

      // Documents - Fetch
      .addCase(fetchInvestigationDocuments.fulfilled, (state, action) => {
        if (state.currentInvestigation) {
          state.currentInvestigation.documents = action.payload;
        }
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
  setAnalysisProgress,
  setExtractedData,
  updateExtractedField,
  revertExtractedField,
  confirmExtractedField,
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
