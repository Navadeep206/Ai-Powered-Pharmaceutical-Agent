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
  const date = rawDate ? (typeof rawDate === 'string' ? rawDate.split('T')[0] : String(rawDate)) : (raw.created_at ? raw.created_at.split('T')[0] : '');

  const rawDetect = raw.detection_date || raw.detectionDate;
  const detectionDate = rawDetect ? (typeof rawDetect === 'string' ? rawDetect.split('T')[0] : String(rawDetect)) : date;

  const deviationId = raw.deviation_id || raw.deviationId || `DEV-${id}`;
  const description = raw.incident_description || raw.description || '';
  const immediateAction = raw.immediate_action_taken || raw.immediateAction || '';

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
    fiveWhys: raw.fiveWhys || raw.five_whys || [],
    fishbone: raw.fishbone || raw.fishbone_causes || {
      Manpower: [],
      Machine: [],
      Method: [],
      Material: [],
      Measurement: [],
      Environment: [],
    },
    evidence: raw.evidence || raw.evidence_records || [],
    capa: raw.capa || raw.capa_actions || [],
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
    detail: `Logged by ${act.actor_identifier || 'System'} • Investigation ${act.investigation_id ? act.investigation_id.slice(0, 8) : 'General'}`,
    time: timeStr,
    createdAt: act.created_at,
    iconName,
    iconColor,
    iconBg,
  };
}

/**
 * Normalizes an individual ExtractedField from the backend into a consistent structure.
 *
 * @param {Object|any} rawField - Backend ExtractedField or primitive value
 * @param {string} canonicalName - The canonical target field name
 * @returns {Object} Normalized ExtractedField with full metadata
 */
export function normalizeExtractedField(rawField, canonicalName) {
  if (rawField && typeof rawField === 'object' && ('value' in rawField || 'ai_extracted_value' in rawField)) {
    const effectiveValue = rawField.value !== undefined && rawField.value !== null
      ? rawField.value
      : (rawField.ai_extracted_value ?? null);

    return {
      fieldName: rawField.field_name || canonicalName,
      field_name: rawField.field_name || canonicalName,
      value: effectiveValue,
      ai_extracted_value: rawField.ai_extracted_value ?? effectiveValue,
      human_edited_value: rawField.human_edited_value ?? null,
      is_human_modified: Boolean(rawField.is_human_modified),
      confidence_score: typeof rawField.confidence_score === 'number' ? rawField.confidence_score : null,
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
      extraction_status: rawField.extraction_status || (effectiveValue ? 'EXTRACTED' : 'MISSING'),
      review_status: rawField.review_status || 'AI_SUGGESTED',
      requires_human_review: rawField.requires_human_review ?? true,
      is_verified: Boolean(rawField.is_verified),
      validation_warnings: Array.isArray(rawField.validation_warnings) ? rawField.validation_warnings : [],
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
    confidence_score: primitiveValue ? 0.85 : null,
    source_reference: null,
    extraction_status: primitiveValue ? 'EXTRACTED' : 'MISSING',
    review_status: 'AI_SUGGESTED',
    requires_human_review: true,
    is_verified: false,
    validation_warnings: [],
  };
}

/**
 * Normalizes backend ExtractionAnalysisResponse into a structured object for UI rendering.
 *
 * @param {Object} response - Backend ExtractionAnalysisResponse
 * @returns {Object} Standardized extraction review state
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
    'personnel_roles_involved',
    'relevant_measurements',
    'relevant_operating_parameters',
  ];

  canonicalFields.forEach((key) => {
    fieldMeta[key] = normalizeExtractedField(rawData[key], key);
  });

  // Backward compatibility aliases
  fieldMeta['equipment'] = fieldMeta['equipment_id'];
  fieldMeta['affected_process'] = fieldMeta['process_stage'];
  fieldMeta['observed_impact'] = fieldMeta['potential_impact'];
  fieldMeta['initial_observations'] = fieldMeta['observations'];

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
    severity: 'Medium', // Default severity since extraction does not predict risk category
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
    completenessScore: typeof response.completeness_score === 'number' ? response.completeness_score : 0,
    overallConfidence: typeof response.overall_confidence === 'number' ? response.overall_confidence : 0,
    disclaimer: response.disclaimer || 'AI-extracted fields require qualified human confirmation prior to RCA.',
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
 *
 * @param {Object} extractedData - The draftIntake.extractedData containing incidentInfo, context, etc.
 * @returns {Object} Validated InvestigationCreate payload
 */
export function buildInvestigationPayloadFromReviewedData(extractedData) {
  if (!extractedData) throw new Error('Cannot build investigation payload: extractedData is missing.');

  const info = extractedData.incidentInfo || {};
  const ctx = extractedData.context || {};

  const cleanString = (val) => (val && typeof val === 'string' && val.trim() ? val.trim() : null);

  const cleanDate = (val) => {
    if (!val || typeof val !== 'string') return null;
    const trimmed = val.trim();
    // Validate simple YYYY-MM-DD
    if (/^\d{4}-\d{2}-\d{2}$/.test(trimmed)) {
      return trimmed;
    }
    // Attempt parse
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
