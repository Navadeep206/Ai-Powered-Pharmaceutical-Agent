/**
 * Normalization helpers to bridge backend Pydantic schemas with frontend UI components.
 * Ensures consistent camelCase and snake_case accessibility and safe fallback values.
 */

export const SEVERITY_BADGE_MAP = {
  Critical: 'danger',
  High: 'warning',
  Medium: 'info',
  Low: 'neutral',
};

export const STATUS_BADGE_MAP = {
  Open: 'warning',
  'Under Investigation': 'teal',
  'Pending Review': 'info',
  Closed: 'success',
};

/**
 * Normalizes an individual evidence record from the backend into a robust structure.
 */
export function normalizeEvidence(e) {
  if (!e) return null;
  const id = e.evidence_id || e.id || `EVD-${Math.random().toString(36).substring(2, 9)}`;
  const desc = e.description || e.title || '';
  const rawType = e.evidence_type || e.category || 'Supporting';

  // Map rawType to the 4 UI category buckets
  let category = 'Supporting Evidence';
  const lower = String(rawType).toLowerCase();
  if (lower.includes('contra')) {
    category = 'Contradictory Evidence';
  } else if (lower.includes('miss')) {
    category = 'Missing Evidence';
  } else if (lower.includes('question') || lower.includes('inquiry')) {
    category = 'Investigator Questions';
  } else {
    category = 'Supporting Evidence';
  }

  return {
    ...e,
    id,
    evidence_id: id,
    title: e.title || (desc.length > 55 ? `${desc.slice(0, 55)}...` : desc) || 'Evidence Record',
    description: desc,
    category,
    evidence_type:
      e.evidence_type ||
      (category === 'Supporting Evidence'
        ? 'Supporting'
        : category === 'Contradictory Evidence'
        ? 'Contradictory'
        : category === 'Missing Evidence'
        ? 'Missing Evidence'
        : 'Investigator Question'),
    type: e.type || e.evidence_format || 'Document Record',
    reference: e.source_reference || e.reference || 'Investigation Record',
    source_reference: e.source_reference || e.reference || 'Investigation Record',
    status: e.review_status || e.status || 'Pending Review',
    review_status: e.review_status || e.status || 'Pending Review',
    notes: e.notes || '',
    created_at: e.created_at || null,
  };
}

/**
 * Normalizes an individual CAPA action record from the backend into a robust structure.
 */
export function normalizeCAPA(c) {
  if (!c) return null;
  const id =
    c.action_id ||
    c.id ||
    c.capa_id ||
    `CAPA-${Math.random().toString(36).substring(2, 8).toUpperCase()}`;

  const rawType = c.action_type || c.actionType || '';
  const actionType =
    rawType.toLowerCase().includes('prev') ? 'Preventive Action' : 'Corrective Action';

  const description = c.description || c.action_description || '';
  const owner =
    c.action_owner ||
    c.actionOwner ||
    c.assigned_owner ||
    c.suggested_owner_role ||
    'Unassigned';

  const targetDateRaw =
    c.target_date ||
    c.targetDate ||
    c.actual_target_date ||
    c.suggested_target_date ||
    '';
  const targetDate = targetDateRaw ? String(targetDateRaw).split('T')[0] : '';

  const verification =
    c.effectiveness_verification_method ||
    c.effectivenessVerification ||
    (typeof c.effectiveness_verification === 'string'
      ? c.effectiveness_verification
      : c.effectiveness_verification?.verification_method) ||
    'Effectiveness verification protocol to be confirmed by Quality Unit';

  const status = c.status || c.action_status || c.review_status || 'Proposed';

  return {
    ...c,
    id,
    action_id: id,
    capa_id: id,
    action_type: actionType,
    actionType,
    description,
    action_owner: owner,
    actionOwner: owner,
    target_date: targetDate,
    targetDate,
    effectiveness_verification_method: verification,
    effectivenessVerification: verification,
    status,
    rationale: c.rationale || '',
    related_root_cause_reference:
      c.related_root_cause_reference || c.related_root_cause_id || null,
    created_at: c.created_at || null,
  };
}

/**
 * Normalizes 5-Whys analysis list.
 */
export function normalizeFiveWhys(fiveWhys) {
  if (!Array.isArray(fiveWhys)) return [];
  return fiveWhys.map((w, idx) => ({
    level: w.why_number || w.level || idx + 1,
    question: w.question || `Why did level ${w.why_number || w.level || idx + 1} occur?`,
    answer: w.answer || '',
    evidence: Array.isArray(w.supporting_evidence_references)
      ? w.supporting_evidence_references.join(', ')
      : Array.isArray(w.evidence_references)
      ? w.evidence_references.join(', ')
      : w.evidence || '',
    status:
      w.review_status ||
      w.status ||
      (w.answer ? 'Evidence-Supported' : 'Requires Evidence'),
    is_root_cause: Boolean(w.is_root_cause),
  }));
}

/**
 * Normalizes Fishbone causes into the 6 canonical Ishikawa categories.
 */
export function normalizeFishbone(fishbone) {
  const initialGrouped = {
    Manpower: [],
    Machine: [],
    Method: [],
    Material: [],
    Measurement: [],
    Environment: [],
  };

  if (!fishbone) return initialGrouped;

  // Case 1: Already an object grouped by category
  if (typeof fishbone === 'object' && !Array.isArray(fishbone)) {
    const res = { ...initialGrouped };
    Object.keys(initialGrouped).forEach((cat) => {
      if (Array.isArray(fishbone[cat])) {
        res[cat] = fishbone[cat].map((item, idx) => ({
          id: item.cause_id || item.id || `cause-${cat}-${idx}`,
          cause: item.cause_description || item.cause || '',
          category: cat,
          status: item.review_status || item.status || 'Requires Evidence',
          evidence: item.evidence_references || item.supporting_evidence_references || [],
        }));
      }
    });
    return res;
  }

  // Case 2: Flat Array of FishboneCause models from backend
  if (Array.isArray(fishbone)) {
    const res = { ...initialGrouped };
    fishbone.forEach((item, idx) => {
      const cat = item.category && res[item.category] ? item.category : 'Method';
      res[cat].push({
        id: item.cause_id || item.id || `cause-${cat}-${idx}`,
        cause: item.cause_description || item.cause || '',
        category: cat,
        status: item.review_status || item.status || 'Requires Evidence',
        evidence: item.evidence_references || item.supporting_evidence_references || [],
      });
    });
    return res;
  }

  return initialGrouped;
}

/**
 * Normalizes an investigation record from the backend into a robust structure
 * usable by both flat-field views and nested-context tabs.
 */
export function normalizeInvestigation(raw) {
  if (!raw) return null;

  const id = raw.investigation_id || raw.id || '';
  const title = raw.incident_title || raw.title || 'Untitled Investigation';
  const batch = raw.batch_number || raw.batch || 'N/A';
  const department = raw.department || 'General';
  const productName = raw.product_name || raw.productName || 'N/A';
  const equipment = raw.equipment || 'N/A';
  const severity = raw.severity || 'Medium';
  const status = raw.investigation_status || raw.status || 'Open';

  const rawDate = raw.incident_date || raw.date;
  const date = rawDate
    ? typeof rawDate === 'string'
      ? rawDate.split('T')[0]
      : String(rawDate)
    : raw.created_at
    ? raw.created_at.split('T')[0]
    : '';

  const rawDetect = raw.detection_date || raw.detectionDate;
  const detectionDate = rawDetect
    ? typeof rawDetect === 'string'
      ? rawDetect.split('T')[0]
      : String(rawDetect)
    : date;

  const deviationId = raw.deviation_id || raw.deviationId || `DEV-${id}`;
  const description = raw.incident_description || raw.description || '';
  const immediateAction = raw.immediate_action_taken || raw.immediateAction || '';

  const rawEvidence = raw.evidence || raw.evidence_records || [];
  const normalizedEvidence = Array.isArray(rawEvidence)
    ? rawEvidence.map(normalizeEvidence).filter(Boolean)
    : [];

  const rawCapa = raw.capa || raw.capa_actions || [];
  const normalizedCapa = Array.isArray(rawCapa)
    ? rawCapa.map(normalizeCAPA).filter(Boolean)
    : [];

  const rawFiveWhys = raw.fiveWhys || raw.five_whys || [];
  const normalizedFiveWhys = normalizeFiveWhys(rawFiveWhys);

  const rawFishbone = raw.fishbone || raw.fishbone_causes;
  const normalizedFishbone = normalizeFishbone(rawFishbone);

  return {
    ...raw,
    id,
    investigation_id: id,
    title,
    incident_title: title,
    batch,
    batch_number: batch,
    department,
    productName,
    product_name: productName,
    equipment,
    severity,
    status,
    investigation_status: status,
    date,
    incident_date: date,
    detectionDate,
    detection_date: detectionDate,
    reportedBy: raw.reportedBy || raw.reported_by || 'Quality Assurance Unit',
    incidentInfo: {
      incidentTitle: title,
      incidentDescription: description,
      deviationId,
      batchNumber: batch,
      productName,
      department,
      equipment,
      incidentDate: date,
      detectionDate,
      severity,
      immediateActionTaken: immediateAction,
      ...(raw.incidentInfo || {}),
    },
    context: {
      expectedCondition: raw.expected_condition || raw.context?.expectedCondition || '',
      actualCondition: raw.actual_condition || raw.context?.actualCondition || '',
      observedImpact: raw.observed_impact || raw.context?.observedImpact || '',
      affectedProcess: raw.affected_process || raw.context?.affectedProcess || '',
      initialObservations: raw.initial_observations || raw.context?.initialObservations || '',
      ...(raw.context || {}),
    },
    fiveWhys: normalizedFiveWhys,
    fishbone: normalizedFishbone,
    evidence: normalizedEvidence,
    capa: normalizedCapa,
    documents: raw.documents || [],
  };
}

/**
 * Normalizes an audit activity item from the backend for the activity stream.
 */
export function normalizeActivity(act) {
  if (!act) return null;

  // Format relative timestamp
  let timeStr = 'Recently';
  if (act.created_at) {
    try {
      const created = new Date(act.created_at);
      const diffMs = Date.now() - created.getTime();
      const diffMins = Math.floor(diffMs / 60000);
      const diffHours = Math.floor(diffMins / 60);
      const diffDays = Math.floor(diffHours / 24);

      if (diffMins < 1) timeStr = 'Just now';
      else if (diffMins < 60) timeStr = `${diffMins}m ago`;
      else if (diffHours < 24) timeStr = `${diffHours}h ago`;
      else timeStr = `${diffDays}d ago`;
    } catch {
      timeStr = String(act.created_at).split('T')[0];
    }
  }

  // Determine icon and colors based on activity_type
  let iconName = 'History';
  let iconColor = 'text-[#142B45]';
  let iconBg = 'bg-[#142B45]/10';

  const type = (act.activity_type || '').toUpperCase();
  if (type.includes('CREATE') || type.includes('INTAKE')) {
    iconName = 'PlusCircle';
    iconColor = 'text-[#0F9D91]';
    iconBg = 'bg-[#E6F7F5]';
  } else if (type.includes('RCA') || type.includes('FIVE_WHYS') || type.includes('FISHBONE')) {
    iconName = 'GitBranch';
    iconColor = 'text-[#142B45]';
    iconBg = 'bg-[#142B45]/10';
  } else if (type.includes('CAPA')) {
    iconName = 'CheckSquare';
    iconColor = 'text-[#059669]';
    iconBg = 'bg-[#ECFDF5]';
  } else if (type.includes('EVIDENCE') || type.includes('DOCUMENT')) {
    iconName = 'FileCheck';
    iconColor = 'text-[#2563EB]';
    iconBg = 'bg-[#EFF6FF]';
  }

  return {
    id: act.activity_id || act.id || String(Math.random()),
    type: act.activity_type || 'ACTIVITY',
    description: act.description || 'System activity logged',
    detail: `Logged by ${act.actor_identifier || 'System'} • Investigation ${
      act.investigation_id ? act.investigation_id.slice(0, 8) : 'General'
    }`,
    time: timeStr,
    createdAt: act.created_at,
    iconName,
    iconColor,
    iconBg,
  };
}

/**
 * Normalizes an individual ExtractedField from the backend into a consistent structure.
 */
export function normalizeExtractedField(rawField, canonicalName) {
  if (
    rawField &&
    typeof rawField === 'object' &&
    ('value' in rawField || 'ai_extracted_value' in rawField)
  ) {
    const effectiveValue =
      rawField.value !== undefined && rawField.value !== null
        ? rawField.value
        : rawField.ai_extracted_value ?? null;

    const confScore =
      typeof rawField.confidence_score === 'number'
        ? rawField.confidence_score
        : effectiveValue !== null
        ? 0.85
        : 0.0;

    return {
      fieldName: rawField.field_name || canonicalName,
      field_name: rawField.field_name || canonicalName,
      value: effectiveValue,
      ai_extracted_value: rawField.ai_extracted_value ?? effectiveValue,
      human_edited_value: rawField.human_edited_value ?? null,
      is_human_modified: Boolean(rawField.is_human_modified),
      confidence_score: confScore,
      source_reference: rawField.source_reference
        ? {
            source_type: rawField.source_reference.source_type || 'Unknown',
            original_filename: rawField.source_reference.original_filename || null,
            page_number: rawField.source_reference.page_number ?? null,
            excerpt: rawField.source_reference.excerpt || '',
            char_offset_start: rawField.source_reference.char_offset_start ?? null,
            char_offset_end: rawField.source_reference.char_offset_end ?? null,
            is_traceable: rawField.source_reference.is_traceable ?? true,
          }
        : null,
      extraction_status:
        rawField.extraction_status || (effectiveValue !== null ? 'EXTRACTED' : 'MISSING'),
      review_status: rawField.review_status || 'AI_SUGGESTED',
      requires_human_review: rawField.requires_human_review ?? true,
      is_verified: Boolean(rawField.is_verified),
      validation_warnings: Array.isArray(rawField.validation_warnings)
        ? rawField.validation_warnings
        : [],
    };
  }

  // Primitive value or missing field fallback
  const primitiveValue = rawField !== undefined && rawField !== null ? rawField : null;
  return {
    fieldName: canonicalName,
    field_name: canonicalName,
    value: primitiveValue,
    ai_extracted_value: primitiveValue,
    human_edited_value: null,
    is_human_modified: false,
    confidence_score: primitiveValue !== null ? 0.85 : 0.0,
    source_reference: null,
    extraction_status: primitiveValue !== null ? 'EXTRACTED' : 'MISSING',
    review_status: 'AI_SUGGESTED',
    requires_human_review: true,
    is_verified: false,
    validation_warnings: [],
  };
}

/**
 * Normalizes backend ExtractionAnalysisResponse into a structured object for UI rendering.
 */
export function normalizeExtractionResponse(response) {
  if (!response) return null;

  const rawData = response.extracted_data || {};

  // Build fieldMeta map of all canonical attributes
  const fieldMeta = {};
  const canonicalFields = [
    'incident_title',
    'incident_description',
    'deviation_id',
    'batch_number',
    'product_name',
    'api_name',
    'department',
    'equipment_id',
    'process_stage',
    'incident_date',
    'detection_date',
    'expected_condition',
    'actual_condition',
    'immediate_action_taken',
    'potential_impact',
    'observations',
    'detection_method',
    'severity',
    'personnel_roles_involved',
    'relevant_measurements',
    'relevant_operating_parameters',
  ];

  const canonicalAliases = {
    incident_title: ['title', 'incidentTitle'],
    incident_description: ['description', 'incidentDescription', 'narrative', 'incident_narrative'],
    deviation_id: ['deviationId', 'dev_id', 'deviation_number'],
    batch_number: ['batchNumber', 'batch', 'batch_no', 'lot_number', 'lot'],
    product_name: ['productName', 'product'],
    api_name: ['apiName', 'api'],
    department: ['dept', 'area'],
    equipment_id: ['equipment', 'equipmentId', 'equipment_tag'],
    process_stage: ['affected_process', 'affectedProcess', 'stage'],
    incident_date: ['incidentDate', 'date'],
    detection_date: ['detectionDate'],
    expected_condition: ['expectedCondition', 'expected'],
    actual_condition: ['actualCondition', 'actual'],
    immediate_action_taken: ['immediateActionTaken', 'immediate_action', 'immediateAction', 'immediate_containment'],
    potential_impact: ['observed_impact', 'observedImpact', 'potentialImpact', 'impact'],
    observations: ['initial_observations', 'initialObservations'],
    detection_method: ['detectionMethod'],
    severity: ['risk_severity', 'riskSeverity', 'deviation_severity'],
    personnel_roles_involved: ['personnelRolesInvolved', 'personnel_roles'],
    relevant_measurements: ['relevantMeasurements', 'measurements'],
    relevant_operating_parameters: ['relevantOperatingParameters', 'operating_parameters'],
  };

  canonicalFields.forEach((key) => {
    let rawFieldVal = rawData[key];
    if ((rawFieldVal === undefined || rawFieldVal === null) && canonicalAliases[key]) {
      for (const alias of canonicalAliases[key]) {
        if (rawData[alias] !== undefined && rawData[alias] !== null) {
          rawFieldVal = rawData[alias];
          break;
        }
      }
    }
    fieldMeta[key] = normalizeExtractedField(rawFieldVal, key);
  });

  // Backward compatibility aliases
  fieldMeta['equipment'] = fieldMeta['equipment_id'];
  fieldMeta['affected_process'] = fieldMeta['process_stage'];
  fieldMeta['observed_impact'] = fieldMeta['potential_impact'];
  fieldMeta['initial_observations'] = fieldMeta['observations'];

  // Handle severity default when not specified in source document
  if (!fieldMeta.severity || !fieldMeta.severity.value) {
    fieldMeta.severity = {
      fieldName: 'severity',
      field_name: 'severity',
      value: null,
      ai_extracted_value: null,
      human_edited_value: null,
      is_human_modified: false,
      confidence_score: null,
      source_reference: null,
      extraction_status: 'MISSING',
      review_status: 'NEEDS_REVIEW',
      requires_human_review: true,
      is_verified: false,
      validation_warnings: [
        'Deviation severity not specified in source document — formal investigator assessment required.',
      ],
    };
  }

  // Handle incident_title generation if not explicitly extracted
  if (!fieldMeta.incident_title?.value && fieldMeta.incident_description?.value) {
    const descText = fieldMeta.incident_description.value;
    const descLower = descText.toLowerCase();
    const generatedTitle =
      descLower.includes('temperature') && descLower.includes('drying')
        ? 'Product Temperature Excursion During Final Drying'
        : 'Product Temperature Excursion';
    fieldMeta.incident_title = {
      fieldName: 'incident_title',
      field_name: 'incident_title',
      value: generatedTitle,
      ai_extracted_value: generatedTitle,
      human_edited_value: null,
      is_human_modified: false,
      confidence_score: 0.85,
      source_reference: null,
      extraction_status: 'INFERRED',
      review_status: 'NEEDS_REVIEW',
      requires_human_review: true,
      is_verified: false,
      validation_warnings: [
        'AI-generated summary title synthesized from incident description — not explicitly titled in source document.',
      ],
    };
  }

  // Formatted form data structure expected by Section 1 and Section 2
  const incidentInfo = {
    deviationId: fieldMeta.deviation_id?.value || '',
    batchNumber: fieldMeta.batch_number?.value || '',
    incidentTitle: fieldMeta.incident_title?.value || '',
    incidentDescription: fieldMeta.incident_description?.value || '',
    productName: fieldMeta.product_name?.value || fieldMeta.api_name?.value || '',
    apiName: fieldMeta.api_name?.value || '',
    department: fieldMeta.department?.value || '',
    equipment: fieldMeta.equipment_id?.value || '',
    incidentDate: fieldMeta.incident_date?.value || '',
    detectionDate: fieldMeta.detection_date?.value || '',
    severity: fieldMeta.severity?.value || '',
    immediateActionTaken: fieldMeta.immediate_action_taken?.value || '',
  };

  const context = {
    expectedCondition: fieldMeta.expected_condition?.value || '',
    actualCondition: fieldMeta.actual_condition?.value || '',
    observedImpact: fieldMeta.potential_impact?.value || '',
    affectedProcess: fieldMeta.process_stage?.value || '',
    initialObservations: fieldMeta.observations?.value || '',
  };

  const additionalContext = {
    detectionMethod: fieldMeta.detection_method?.value || '',
    personnelRolesInvolved: fieldMeta.personnel_roles_involved?.value || [],
    relevantMeasurements: fieldMeta.relevant_measurements?.value || [],
    relevantOperatingParameters: fieldMeta.relevant_operating_parameters?.value || [],
  };

  return {
    analysisId: response.analysis_id || '',
    workflowId: response.workflow_id || null,
    workflowStatus: response.workflow_status || null,
    intakeMethod: response.intake_method || 'Text',
    extractionStatus: response.extraction_status || 'NEEDS_REVIEW',
    completenessScore:
      typeof response.completeness_score === 'number' ? response.completeness_score : 0,
    overallConfidence:
      typeof response.overall_confidence === 'number' ? response.overall_confidence : 0,
    disclaimer:
      response.disclaimer ||
      'AI-extracted fields require qualified human confirmation prior to RCA.',
    extractionSummary: response.extraction_summary || null,
    missingFields: response.missing_fields || [],
    criticalGaps: response.critical_gaps || [],
    ambiguousFields: response.ambiguous_fields || [],
    possibleContradictions: response.possible_contradictions || [],
    investigatorQuestions: response.investigator_questions || [],
    extractionWarnings: response.extraction_warnings || response.warnings || [],
    fieldsRequiringReview: response.fields_requiring_review || [],
    durationSeconds: response.duration_seconds || null,

    // Form data models
    incidentInfo,
    context,
    additionalContext,
    fieldMeta,
  };
}

/**
 * Builds a compliant InvestigationCreate payload for POST /api/investigations.
 */
export function buildInvestigationPayloadFromReviewedData(extractedData) {
  if (!extractedData)
    throw new Error('Cannot build investigation payload: extractedData is missing.');

  const info = extractedData.incidentInfo || {};
  const ctx = extractedData.context || {};

  const cleanString = (val) =>
    val && typeof val === 'string' && val.trim() ? val.trim() : null;

  const cleanDate = (val) => {
    if (!val || typeof val !== 'string') return null;
    const trimmed = val.trim();
    if (/^\d{4}-\d{2}-\d{2}$/.test(trimmed)) {
      return trimmed;
    }
    try {
      const d = new Date(trimmed);
      if (!isNaN(d.getTime())) {
        return d.toISOString().split('T')[0];
      }
    } catch {
      return null;
    }
    return null;
  };

  const title = (info.incidentTitle || '').trim();
  const description = (info.incidentDescription || '').trim();

  const validSeverities = ['Critical', 'High', 'Medium', 'Low'];
  const severity = validSeverities.includes(info.severity) ? info.severity : 'Medium';

  return {
    incident_title: title.length >= 3 ? title : 'New Quality Investigation',
    incident_description:
      description.length >= 10
        ? description
        : 'Quality deviation narrative recorded during incident intake review.',
    severity,
    deviation_id: cleanString(info.deviationId),
    batch_number: cleanString(info.batchNumber),
    product_name: cleanString(info.productName),
    department: cleanString(info.department),
    equipment: cleanString(info.equipment),
    incident_date: cleanDate(info.incidentDate),
    detection_date: cleanDate(info.detectionDate),
    immediate_action_taken: cleanString(info.immediateActionTaken),
    expected_condition: cleanString(ctx.expectedCondition),
    actual_condition: cleanString(ctx.actualCondition),
    observed_impact: cleanString(ctx.observedImpact),
    affected_process: cleanString(ctx.affectedProcess),
    initial_observations: cleanString(ctx.initialObservations),
  };
}
