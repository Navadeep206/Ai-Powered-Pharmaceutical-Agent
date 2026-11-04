import { createSlice } from '@reduxjs/toolkit';
import { DEMO_INVESTIGATIONS, SAMPLE_EXTRACTED_PAYLOAD } from '../../utils/demoData';

const initialState = {
  investigations: DEMO_INVESTIGATIONS,
  currentInvestigation: DEMO_INVESTIGATIONS[0],
  draftIntake: {
    method: 'upload', // 'upload' | 'text' | 'email'
    fileInfo: null, // { name, size, type }
    rawText: '',
    emailSubject: '',
    emailBody: '',
    extractionState: 'idle', // 'idle' | 'analyzing' | 'extracted'
    extractedData: null,
    isEdited: false,
  },
};

export const investigationSlice = createSlice({
  name: 'investigations',
  initialState,
  reducers: {
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
    loadInvestigation: (state, action) => {
      const id = action.payload;
      const found = state.investigations.find((inv) => inv.id === id);
      if (found) {
        state.currentInvestigation = found;
      } else {
        // Fallback demo scaffold for any arbitrary ID
        state.currentInvestigation = {
          id,
          title: `Investigation Workspace for ${id}`,
          department: 'Chemical Synthesis Suite A',
          batch: 'API-DEMO',
          severity: 'High',
          status: 'Under Investigation',
          date: new Date().toISOString().split('T')[0],
          detectionDate: new Date().toISOString().split('T')[0],
          reportedBy: 'Quality Assurance Unit',
          slaDaysRemaining: 25,
          progressStep: 2,
          incidentInfo: {
            ...SAMPLE_EXTRACTED_PAYLOAD.incidentInfo,
            deviationId: `DEV-${id}`,
          },
          context: { ...SAMPLE_EXTRACTED_PAYLOAD.context },
          fiveWhys: [
            {
              level: 1,
              question: 'Why did the incident occur?',
              answer: 'Process parameter excursion detected during production run.',
              evidence: 'SCADA telemetry record.',
              status: 'Requires Evidence',
            },
            {
              level: 2,
              question: 'Why did that condition happen?',
              answer: '',
              evidence: '',
              status: 'Pending Human Review',
            },
            {
              level: 3,
              question: 'What caused the previous condition?',
              answer: '',
              evidence: '',
              status: 'Pending Human Review',
            },
            {
              level: 4,
              question: 'Why was that cause present?',
              answer: '',
              evidence: '',
              status: 'Pending Human Review',
            },
            {
              level: 5,
              question: 'What underlying system or process weakness contributed?',
              answer: '',
              evidence: '',
              status: 'Pending Human Review',
            },
          ],
          fishbone: {
            Manpower: [],
            Machine: [],
            Method: [],
            Material: [],
            Measurement: [],
            Environment: [],
          },
          evidence: [],
          capa: {
            correctiveAction: '',
            preventiveAction: '',
            actionOwner: '',
            targetDate: '',
            effectivenessVerification: '',
            status: 'Draft',
          },
        };
      }
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
      const newId = `INV-2026-00${state.investigations.length + 1}`;
      const newInv = {
        id: newId,
        title: extractedData.incidentInfo.incidentTitle || 'New Investigated Event',
        department: extractedData.incidentInfo.department || 'Chemical Synthesis',
        batch: extractedData.incidentInfo.batchNumber || 'API-NEW',
        productName: extractedData.incidentInfo.productName || 'Active Pharmaceutical Ingredient',
        equipment: extractedData.incidentInfo.equipment || 'Reactor / Process Unit',
        severity: extractedData.incidentInfo.severity || 'Major',
        status: 'Under Investigation',
        date: new Date().toISOString().split('T')[0],
        detectionDate: extractedData.incidentInfo.detectionDate || new Date().toISOString().split('T')[0],
        reportedBy: 'Quality Assurance Unit',
        slaDaysRemaining: 30,
        progressStep: 2,
        incidentInfo: { ...extractedData.incidentInfo },
        context: { ...extractedData.context },
        fiveWhys: [
          {
            level: 1,
            question: 'Why did the incident occur?',
            answer: extractedData.context?.actualCondition || '',
            evidence: 'Initial incident intake report.',
            status: 'Requires Evidence',
          },
          {
            level: 2,
            question: 'Why did that condition happen?',
            answer: '',
            evidence: '',
            status: 'Pending Human Review',
          },
          {
            level: 3,
            question: 'What caused the previous condition?',
            answer: '',
            evidence: '',
            status: 'Pending Human Review',
          },
          {
            level: 4,
            question: 'Why was that cause present?',
            answer: '',
            evidence: '',
            status: 'Pending Human Review',
          },
          {
            level: 5,
            question: 'What underlying system or process weakness contributed?',
            answer: '',
            evidence: '',
            status: 'Pending Human Review',
          },
        ],
        fishbone: {
          Manpower: [],
          Machine: [],
          Method: [],
          Material: [],
          Measurement: [],
          Environment: [],
        },
        evidence: [],
        capa: {
          correctiveAction: extractedData.incidentInfo.immediateActionTaken || '',
          preventiveAction: '',
          actionOwner: '',
          targetDate: '',
          effectivenessVerification: '',
          status: 'Draft',
        },
      };

      state.investigations.unshift(newInv);
      state.currentInvestigation = newInv;
      return newId;
    },
  },
});

export const {
  setIntakeMethod,
  setIntakeFile,
  clearIntakeFile,
  setIntakeText,
  setIntakeEmail,
  setExtractionState,
  setExtractedData,
  updateExtractedField,
  resetDraftIntake,
  loadInvestigation,
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

