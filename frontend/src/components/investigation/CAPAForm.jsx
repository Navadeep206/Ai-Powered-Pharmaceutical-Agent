import React, { useState, useEffect } from 'react';
import { Card, CardHeader, CardTitle, CardDescription, CardContent, CardFooter } from '../common/Card';
import Input from '../common/Input';
import Select from '../common/Select';
import StatusBadge from '../common/StatusBadge';
import Button from '../common/Button';
import { ShieldCheck, Save, AlertTriangle, CheckCircle2, Clock, Calendar } from 'lucide-react';

/**
 * CAPA Form component establishing S.M.A.R.T. Corrective and Preventive Actions preview.
 */
export default function CAPAForm({ capa = {}, onSaveCAPA }) {
  const [formData, setFormData] = useState({
    correctiveAction: capa.correctiveAction || '',
    preventiveAction: capa.preventiveAction || '',
    actionOwner: capa.actionOwner || '',
    targetDate: capa.targetDate || '',
    effectivenessVerification: capa.effectivenessVerification || '',
    status: capa.status || 'Draft',
  });

  const [savedNotification, setSavedNotification] = useState(false);

  useEffect(() => {
    setFormData({
      correctiveAction: capa.correctiveAction || '',
      preventiveAction: capa.preventiveAction || '',
      actionOwner: capa.actionOwner || '',
      targetDate: capa.targetDate || '',
      effectivenessVerification: capa.effectivenessVerification || '',
      status: capa.status || 'Draft',
    });
  }, [capa]);

  const handleChange = (field, value) => {
    setFormData((prev) => ({ ...prev, [field]: value }));
  };

  const handleSave = (e) => {
    e?.preventDefault();
    if (onSaveCAPA) {
      onSaveCAPA(formData);
    }
    setSavedNotification(true);
    setTimeout(() => setSavedNotification(false), 3000);
  };

  return (
    <div className="space-y-6">
      {/* GxP Preview Notice */}
      <div className="p-4 rounded-xl bg-[#FFFBEB] border border-[#FDE68A] text-xs text-[#92400E] flex items-start space-x-3">
        <AlertTriangle className="w-5 h-5 text-[#D97706] shrink-0 mt-0.5" />
        <div>
          <span className="font-bold">CAPA Plan Formulation Preview (ICH Q10):</span>
          <p className="mt-0.5 leading-relaxed text-[#92400E]">
            This section represents the candidate Corrective and Preventive Action plan derived from the confirmed root causes. Formal issuance and execution requires Quality Unit review and dual-factor electronic sign-off per 21 CFR Part 11.
          </p>
        </div>
      </div>

      <Card>
        <CardHeader>
          <div className="flex items-center space-x-2.5">
            <div className="w-8 h-8 rounded-lg bg-[#059669]/10 text-[#059669] flex items-center justify-center">
              <ShieldCheck className="w-4 h-4 text-[#059669]" />
            </div>
            <div>
              <CardTitle>Corrective & Preventive Action Specification</CardTitle>
              <CardDescription>
                Define remediation actions, accountability, and post-implementation effectiveness criteria
              </CardDescription>
            </div>
          </div>

          <StatusBadge variant="teal" size="sm">
            {formData.status || 'Draft'}
          </StatusBadge>
        </CardHeader>

        <CardContent className="space-y-5">
          {/* Corrective Action (Immediate) */}
          <div>
            <label className="block text-xs font-semibold text-[#142B45] mb-1.5 uppercase tracking-wider">
              1. Corrective Action (Immediate Containment & Remediation) <span className="text-[#DC2626]">*</span>
            </label>
            <textarea
              rows={3}
              value={formData.correctiveAction}
              onChange={(e) => handleChange('correctiveAction', e.target.value)}
              placeholder="Detail immediate actions to contain the non-conforming batch, quarantine affected lots, and remediate the immediate symptom..."
              className="block w-full rounded-lg border border-[#CBD5E1] text-sm p-3 bg-white focus:border-[#0F9D91] focus:ring-2 focus:ring-[#0F9D91]/20 leading-relaxed"
            />
            <p className="text-[11px] text-[#64748B] mt-1">
              Focuses on containing existing defective intermediate or API materials.
            </p>
          </div>

          {/* Preventive Action (Systemic) */}
          <div>
            <label className="block text-xs font-semibold text-[#142B45] mb-1.5 uppercase tracking-wider">
              2. Preventive Action (Systemic Recurrence Elimination) <span className="text-[#DC2626]">*</span>
            </label>
            <textarea
              rows={3}
              value={formData.preventiveAction}
              onChange={(e) => handleChange('preventiveAction', e.target.value)}
              placeholder="Detail engineering controls, SOP procedural revisions, automation interlocks, or equipment modifications to prevent recurrence..."
              className="block w-full rounded-lg border border-[#CBD5E1] text-sm p-3 bg-white focus:border-[#0F9D91] focus:ring-2 focus:ring-[#0F9D91]/20 leading-relaxed"
            />
            <p className="text-[11px] text-[#64748B] mt-1">
              Addresses the root mechanism confirmed through 5-Whys and Ishikawa analysis.
            </p>
          </div>

          {/* Owner & Target Date */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <Input
              label="Action Owner / RACI Assignee"
              placeholder="e.g. Lead Process Engineer / QA Manager"
              value={formData.actionOwner}
              onChange={(e) => handleChange('actionOwner', e.target.value)}
              required
            />

            <Input
              label="Target Implementation Date"
              type="date"
              value={formData.targetDate}
              onChange={(e) => handleChange('targetDate', e.target.value)}
              required
              leftIcon={Calendar}
            />

            <Select
              label="CAPA Lifecycle Status"
              value={formData.status}
              onChange={(e) => handleChange('status', e.target.value)}
              options={[
                { value: 'Draft', label: 'Draft Proposal' },
                { value: 'Assigned', label: 'Assigned to Engineering' },
                { value: 'Pending Verification', label: 'Pending Effectiveness Verification' },
                { value: 'Completed', label: 'Completed & Closed' },
              ]}
              required
            />
          </div>

          {/* Effectiveness Verification Criteria */}
          <div>
            <label className="block text-xs font-semibold text-[#142B45] mb-1.5 uppercase tracking-wider">
              3. Effectiveness Verification Protocol (ICH Q10) <span className="text-[#DC2626]">*</span>
            </label>
            <textarea
              rows={2}
              value={formData.effectivenessVerification}
              onChange={(e) => handleChange('effectivenessVerification', e.target.value)}
              placeholder="e.g. Verification across 3 consecutive batches with 100% CQA compliance and zero temperature excursions..."
              className="block w-full rounded-lg border border-[#CBD5E1] text-sm p-3 bg-white focus:border-[#0F9D91] focus:ring-2 focus:ring-[#0F9D91]/20 leading-relaxed"
            />
            <p className="text-[11px] text-[#64748B] mt-1">
              Pre-defined measurable criteria to confirm that the CAPA has solved the issue without introducing new risks.
            </p>
          </div>
        </CardContent>

        <CardFooter className="py-3 bg-[#F8FAFC]">
          <div className="text-xs text-[#64748B]">
            {savedNotification ? (
              <span className="text-[#059669] font-semibold flex items-center">
                <CheckCircle2 className="w-4 h-4 mr-1" /> CAPA Plan Saved in Local State
              </span>
            ) : (
              <span>Demonstration CAPA plan saved in frontend session.</span>
            )}
          </div>

          <Button
            variant="primary"
            size="sm"
            leftIcon={Save}
            onClick={handleSave}
          >
            Save CAPA Plan
          </Button>
        </CardFooter>
      </Card>
    </div>
  );
}

