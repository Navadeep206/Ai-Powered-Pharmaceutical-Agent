import React, { useState } from 'react';
import { Card, CardHeader, CardTitle, CardDescription, CardContent, CardFooter } from '../common/Card';
import Input from '../common/Input';
import Select from '../common/Select';
import StatusBadge from '../common/StatusBadge';
import Button from '../common/Button';
import {
  FileText,
  Sliders,
  AlertTriangle,
  Save,
  ArrowRight,
  Edit3,
  CheckCircle2,
  Info,
} from 'lucide-react';

/**
 * Structured review interface displaying extracted deviation metadata with editable fields.
 */
export default function ExtractionReviewForm({
  extractedData,
  onUpdateField,
  onSaveDraft,
  onContinueToRCA,
  isDraftSaved,
}) {
  const [isEditing, setIsEditing] = useState(true);

  if (!extractedData) return null;

  const { incidentInfo = {}, context = {} } = extractedData;

  const handleFieldChange = (section, field, value) => {
    onUpdateField(section, field, value);
  };

  return (
    <div className="space-y-6">
      {/* Extraction State & Verification Disclaimer Banner */}
      <div className="p-4 rounded-xl bg-[#FFFBEB] border border-[#FDE68A] text-xs text-[#92400E] shadow-2xs space-y-2">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-2 font-bold text-sm text-[#B45309]">
            <AlertTriangle className="w-4 h-4 text-[#D97706]" />
            <span>Demonstration Extraction State &bull; Unverified AI Draft</span>
          </div>
          <StatusBadge variant="warning" size="sm">
            Pending Human Review
          </StatusBadge>
        </div>
        <p className="leading-relaxed text-[#92400E]">
          <strong>Notice:</strong> The values below simulate information extracted from the provided incident intake. All extracted fields must be carefully reviewed and verified by a qualified quality investigator prior to initiating formal 6M causal trees.
        </p>
      </div>

      {/* Action Controls Bar */}
      <div className="flex items-center justify-between bg-white p-4 rounded-xl border border-[#E2E8F0] shadow-2xs">
        <div className="flex items-center space-x-3">
          <div className="w-8 h-8 rounded-lg bg-[#E6F7F5] text-[#0F9D91] flex items-center justify-center font-bold text-xs">
            1
          </div>
          <div>
            <h3 className="text-sm font-bold text-[#142B45]">
              Verify Extracted Deviation Record
            </h3>
            <p className="text-xs text-[#64748B]">
              Edit fields as needed before progressing to Root Cause Analysis
            </p>
          </div>
        </div>

        <div className="flex items-center space-x-2.5">
          <Button
            variant={isEditing ? 'secondary' : 'outline'}
            size="sm"
            leftIcon={Edit3}
            onClick={() => setIsEditing(!isEditing)}
          >
            {isEditing ? 'Lock for Preview' : 'Enable Editing'}
          </Button>

          <Button
            variant="secondary"
            size="sm"
            leftIcon={Save}
            onClick={onSaveDraft}
          >
            {isDraftSaved ? 'Draft Saved Locally' : 'Save Draft'}
          </Button>

          <Button
            variant="accent"
            size="sm"
            rightIcon={ArrowRight}
            onClick={onContinueToRCA}
          >
            Continue to RCA
          </Button>
        </div>
      </div>

      {/* Section 1: Incident Information */}
      <Card>
        <CardHeader>
          <div className="flex items-center space-x-2.5">
            <div className="w-8 h-8 rounded-lg bg-[#142B45] text-white flex items-center justify-center">
              <FileText className="w-4 h-4 text-[#0F9D91]" />
            </div>
            <div>
              <CardTitle>Section 1: Incident Information</CardTitle>
              <CardDescription>
                Core event identifiers, manufacturing equipment, and timestamps
              </CardDescription>
            </div>
          </div>
          <StatusBadge variant="neutral" size="sm">
            Editable Draft
          </StatusBadge>
        </CardHeader>

        <CardContent className="space-y-4">
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <Input
              label="Deviation ID"
              value={incidentInfo.deviationId || ''}
              onChange={(e) => handleFieldChange('incidentInfo', 'deviationId', e.target.value)}
              disabled={!isEditing}
              required
            />
            <Input
              label="Batch Number"
              value={incidentInfo.batchNumber || ''}
              onChange={(e) => handleFieldChange('incidentInfo', 'batchNumber', e.target.value)}
              disabled={!isEditing}
              required
            />
            <Select
              label="Deviation Severity"
              value={incidentInfo.severity || 'Critical'}
              onChange={(e) => handleFieldChange('incidentInfo', 'severity', e.target.value)}
              disabled={!isEditing}
              options={[
                { value: 'Critical', label: 'Critical (Disposition Impact)' },
                { value: 'High', label: 'High (Process Excursion)' },
                { value: 'Medium', label: 'Medium (Minor OOS / Yield)' },
                { value: 'Low', label: 'Low (Documentation / Non-critical)' },
              ]}
              required
            />
          </div>

          <Input
            label="Incident Title"
            value={incidentInfo.incidentTitle || ''}
            onChange={(e) => handleFieldChange('incidentInfo', 'incidentTitle', e.target.value)}
            disabled={!isEditing}
            required
          />

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <Input
              label="Product / API Name"
              value={incidentInfo.productName || ''}
              onChange={(e) => handleFieldChange('incidentInfo', 'productName', e.target.value)}
              disabled={!isEditing}
              required
            />
            <Input
              label="Department / Area"
              value={incidentInfo.department || ''}
              onChange={(e) => handleFieldChange('incidentInfo', 'department', e.target.value)}
              disabled={!isEditing}
              required
            />
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <Input
              label="Equipment / Machine Tag"
              value={incidentInfo.equipment || ''}
              onChange={(e) => handleFieldChange('incidentInfo', 'equipment', e.target.value)}
              disabled={!isEditing}
              required
            />
            <Input
              label="Incident Date"
              type="text"
              value={incidentInfo.incidentDate || ''}
              onChange={(e) => handleFieldChange('incidentInfo', 'incidentDate', e.target.value)}
              disabled={!isEditing}
              helperText="UTC ISO timestamp"
              required
            />
            <Input
              label="Detection Date"
              type="text"
              value={incidentInfo.detectionDate || ''}
              onChange={(e) => handleFieldChange('incidentInfo', 'detectionDate', e.target.value)}
              disabled={!isEditing}
              helperText="Date deviation detected"
              required
            />
          </div>

          <div>
            <label className="block text-xs font-semibold text-[#142B45] mb-1.5 uppercase tracking-wider">
              Incident Description <span className="text-[#DC2626]">*</span>
            </label>
            <textarea
              rows={3}
              value={incidentInfo.incidentDescription || ''}
              onChange={(e) => handleFieldChange('incidentInfo', 'incidentDescription', e.target.value)}
              disabled={!isEditing}
              className={`block w-full rounded-lg border text-sm p-3 bg-white leading-relaxed ${
                isEditing
                  ? 'border-[#CBD5E1] focus:border-[#0F9D91] focus:ring-2 focus:ring-[#0F9D91]/20'
                  : 'bg-[#F8FAFC] text-[#64748B] border-[#E2E8F0]'
              }`}
            />
          </div>

          <div>
            <label className="block text-xs font-semibold text-[#142B45] mb-1.5 uppercase tracking-wider">
              Immediate Action Taken <span className="text-[#64748B]">(Containment)</span>
            </label>
            <textarea
              rows={2}
              value={incidentInfo.immediateActionTaken || ''}
              onChange={(e) => handleFieldChange('incidentInfo', 'immediateActionTaken', e.target.value)}
              disabled={!isEditing}
              className={`block w-full rounded-lg border text-sm p-3 bg-white leading-relaxed ${
                isEditing
                  ? 'border-[#CBD5E1] focus:border-[#0F9D91] focus:ring-2 focus:ring-[#0F9D91]/20'
                  : 'bg-[#F8FAFC] text-[#64748B] border-[#E2E8F0]'
              }`}
            />
          </div>
        </CardContent>
      </Card>

      {/* Section 2: Investigation Context */}
      <Card>
        <CardHeader>
          <div className="flex items-center space-x-2.5">
            <div className="w-8 h-8 rounded-lg bg-[#0F9D91]/10 text-[#0F9D91] flex items-center justify-center">
              <Sliders className="w-4 h-4 text-[#0F9D91]" />
            </div>
            <div>
              <CardTitle>Section 2: Investigation Context & Observations</CardTitle>
              <CardDescription>
                Process conditions, observed impact, and baseline operational specs
              </CardDescription>
            </div>
          </div>
          <StatusBadge variant="teal" size="sm">
            Contextual Signals
          </StatusBadge>
        </CardHeader>

        <CardContent className="space-y-4">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <Input
              label="Expected Condition (SOP Limit)"
              value={context.expectedCondition || ''}
              onChange={(e) => handleFieldChange('context', 'expectedCondition', e.target.value)}
              disabled={!isEditing}
              required
            />
            <Input
              label="Actual Condition (Observed Excursion)"
              value={context.actualCondition || ''}
              onChange={(e) => handleFieldChange('context', 'actualCondition', e.target.value)}
              disabled={!isEditing}
              required
            />
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <Input
              label="Observed Impact on Batch / Quality"
              value={context.observedImpact || ''}
              onChange={(e) => handleFieldChange('context', 'observedImpact', e.target.value)}
              disabled={!isEditing}
              required
            />
            <Input
              label="Affected Process Stage"
              value={context.affectedProcess || ''}
              onChange={(e) => handleFieldChange('context', 'affectedProcess', e.target.value)}
              disabled={!isEditing}
              required
            />
          </div>

          <div>
            <label className="block text-xs font-semibold text-[#142B45] mb-1.5 uppercase tracking-wider">
              Initial Observations & Telemetry Signals
            </label>
            <textarea
              rows={2}
              value={context.initialObservations || ''}
              onChange={(e) => handleFieldChange('context', 'initialObservations', e.target.value)}
              disabled={!isEditing}
              className={`block w-full rounded-lg border text-sm p-3 bg-white leading-relaxed ${
                isEditing
                  ? 'border-[#CBD5E1] focus:border-[#0F9D91] focus:ring-2 focus:ring-[#0F9D91]/20'
                  : 'bg-[#F8FAFC] text-[#64748B] border-[#E2E8F0]'
              }`}
            />
          </div>
        </CardContent>

        <CardFooter>
          <div className="flex items-center text-xs text-[#64748B]">
            <Info className="w-3.5 h-3.5 mr-1 text-[#0F9D91]" />
            Confirming fields will create the active root cause analysis tree in the next stage.
          </div>

          <div className="flex items-center space-x-2">
            <Button
              variant="secondary"
              size="sm"
              leftIcon={Save}
              onClick={onSaveDraft}
            >
              Save Draft
            </Button>
            <Button
              variant="accent"
              size="sm"
              rightIcon={ArrowRight}
              onClick={onContinueToRCA}
            >
              Continue to RCA
            </Button>
          </div>
        </CardFooter>
      </Card>
    </div>
  );
}

