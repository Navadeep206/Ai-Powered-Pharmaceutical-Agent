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
