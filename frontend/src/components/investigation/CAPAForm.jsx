import React, { useState } from 'react';
import { Card, CardHeader, CardTitle, CardDescription, CardContent, CardFooter } from '../common/Card';
import Input from '../common/Input';
import Select from '../common/Select';
import StatusBadge from '../common/StatusBadge';
import Button from '../common/Button';
import {
  ShieldCheck,
  Save,
  AlertTriangle,
  CheckCircle2,
  Calendar,
  Sparkles,
  PlusCircle,
  X,
  Check,
  Ban,
  Clock,
  Play,
  CheckCheck,
  User,
  FileCheck,
  Tag,
  Loader2,
} from 'lucide-react';

const STATUS_VARIANTS = {
  Proposed: 'neutral',
  'Pending Review': 'warning',
  Approved: 'teal',
  'In Progress': 'info',
  Completed: 'success',
  Closed: 'success',
  Rejected: 'danger',
  Draft: 'neutral',
};

/**
 * Enterprise GxP CAPA Workspace.
 * Supports generating AI recommendations, proposing manual actions,
 * human review decisions (approve, reject, edit), and lifecycle state transitions.
 */
export default function CAPAForm({
  capa = [],
  onGenerateAI,
  onCreateCAPA,
  onUpdateStatus,
  onSaveCAPA,
  isGenerating = false,
  isSaving = false,
}) {
  // Normalize actions array
  const actionList = Array.isArray(capa)
    ? capa
    : Array.isArray(capa.actions)
    ? capa.actions
    : [];

  const [showProposeModal, setShowProposeModal] = useState(false);
  const [editingActionId, setEditingActionId] = useState(null);
  const [editForm, setEditForm] = useState({});

  // Proposal form state
  const [proposeType, setProposeType] = useState('Corrective Action');
  const [proposeDescription, setProposeDescription] = useState('');
  const [proposeOwner, setProposeOwner] = useState('');
  const [proposeTargetDate, setProposeTargetDate] = useState(
    new Date(Date.now() + 30 * 86400000).toISOString().split('T')[0]
  );
  const [proposeVerification, setProposeVerification] = useState('');
  const [proposeRootCauseRef, setProposeRootCauseRef] = useState('');
  const [proposeError, setProposeError] = useState(null);

  const handleStartEdit = (action) => {
    setEditingActionId(action.id || action.action_id);
    setEditForm({
      description: action.description || '',
      action_owner: action.action_owner || action.actionOwner || '',
      target_date: action.target_date || action.targetDate || '',
      effectiveness_verification_method:
        action.effectiveness_verification_method || action.effectivenessVerification || '',
    });
  };

  const handleSaveEdit = async (actionId) => {
    if (onUpdateStatus) {
      await onUpdateStatus(actionId, null, editForm);
    }
    setEditingActionId(null);
  };

  const handleProposeSubmit = async (e) => {
    e.preventDefault();
    setProposeError(null);

    if (proposeDescription.trim().length < 10) {
      setProposeError('Description must contain at least 10 characters.');
      return;
    }
    if (proposeOwner.trim().length < 2) {
      setProposeError('Action owner must specify a responsible role or individual.');
      return;
    }
    if (proposeVerification.trim().length < 10) {
      setProposeError('Effectiveness verification protocol must contain at least 10 characters.');
      return;
    }

    const payload = {
      action_type: proposeType,
      description: proposeDescription.trim(),
      action_owner: proposeOwner.trim(),
      target_date: proposeTargetDate,
      effectiveness_verification_method: proposeVerification.trim(),
      status: 'Proposed',
      related_root_cause_reference: proposeRootCauseRef.trim() || null,
    };

    if (onCreateCAPA) {
      await onCreateCAPA(payload);
    } else if (onSaveCAPA) {
      onSaveCAPA(payload);
    }

    // Reset modal
    setProposeDescription('');
    setProposeOwner('');
    setProposeVerification('');
    setProposeRootCauseRef('');
    setShowProposeModal(false);
  };

  return (
    <div className="space-y-6">
      {/* 1. GxP Compliance Notice */}
      <div className="p-4 rounded-xl bg-[#FFFBEB] border border-[#FDE68A] text-xs text-[#92400E] flex items-start space-x-3">
        <AlertTriangle className="w-5 h-5 text-[#D97706] shrink-0 mt-0.5" />
        <div>
          <span className="font-bold">CAPA Plan Formulation & Human QA Review (ICH Q10 / 21 CFR Part 11):</span>
          <p className="mt-0.5 leading-relaxed text-[#92400E]">
            AI recommendations are machine suggestions designed to address confirmed root causes. Under GxP standards, AI systems must never automatically approve or close remediation plans. Formal implementation requires qualified Quality Assurance authorization.
          </p>
        </div>
      </div>

      {/* 2. Top Header Controls Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 p-4 bg-white rounded-xl border border-[#E2E8F0] shadow-2xs">
        <div>
          <h3 className="text-sm font-bold text-[#142B45]">
            Corrective & Preventive Actions (CAPA) Workspace
          </h3>
          <p className="text-xs text-[#64748B]">
            Remediate immediate excursions and implement engineering controls to eliminate recurrence.
          </p>
        </div>

        <div className="flex items-center space-x-2">
          {onGenerateAI && (
            <Button
              variant="accent"
              size="sm"
              leftIcon={isGenerating ? Loader2 : Sparkles}
              onClick={onGenerateAI}
              disabled={isGenerating}
            >
              {isGenerating ? 'Running AI CAPA Nodes...' : 'Generate AI CAPA'}
            </Button>
          )}

          <Button
            variant="primary"
            size="sm"
            leftIcon={PlusCircle}
            onClick={() => setShowProposeModal(true)}
            disabled={isGenerating}
          >
            Propose Action
          </Button>
        </div>
      </div>

      {/* 3. Propose New Action Modal / Card */}
      {showProposeModal && (
        <Card className="border-[#0F9D91]/40 shadow-md">
          <CardHeader className="bg-[#E6F7F5]/50 py-3">
            <div className="flex items-center justify-between w-full">
              <CardTitle className="text-sm font-bold text-[#142B45]">
                Propose New CAPA Remediation Action
              </CardTitle>
              <button
                type="button"
                onClick={() => setShowProposeModal(false)}
                className="text-[#64748B] hover:text-[#142B45] p-1 rounded-md cursor-pointer"
              >
                <X className="w-4 h-4" />
              </button>
            </div>
          </CardHeader>

          <form onSubmit={handleProposeSubmit}>
            <CardContent className="p-4 sm:p-5 space-y-4">
              {proposeError && (
                <div className="p-3 bg-[#FEF2F2] border border-[#FECACA] rounded-lg text-xs text-[#991B1B]">
                  {proposeError}
                </div>
              )}

              <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                <Select
                  label="Action Classification"
                  value={proposeType}
                  onChange={(e) => setProposeType(e.target.value)}
                  options={[
                    { value: 'Corrective Action', label: 'Corrective Action (Immediate Remediation)' },
                    { value: 'Preventive Action', label: 'Preventive Action (Systemic Elimination)' },
                  ]}
                  required
                />

                <Input
                  label="Action Owner / RACI Role"
                  placeholder="e.g. Lead Validation Engineer / QA Officer"
                  value={proposeOwner}
                  onChange={(e) => setProposeOwner(e.target.value)}
                  required
                />

                <Input
                  label="Target Implementation Date"
                  type="date"
                  value={proposeTargetDate}
                  onChange={(e) => setProposeTargetDate(e.target.value)}
                  required
                  leftIcon={Calendar}
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-[#142B45] mb-1.5 uppercase tracking-wider">
                  Action Description & Technical Specification <span className="text-[#DC2626]">*</span>
                </label>
                <textarea
                  rows={3}
                  value={proposeDescription}
                  onChange={(e) => setProposeDescription(e.target.value)}
                  placeholder="Detail explicit physical, software, or procedural steps to remediate or prevent recurrence..."
                  className="block w-full rounded-lg border border-[#CBD5E1] text-sm p-3 bg-white focus:border-[#0F9D91] focus:ring-2 focus:ring-[#0F9D91]/20 leading-relaxed"
                  required
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-[#142B45] mb-1.5 uppercase tracking-wider">
                  Effectiveness Verification Protocol (ICH Q10) <span className="text-[#DC2626]">*</span>
                </label>
                <textarea
                  rows={2}
                  value={proposeVerification}
                  onChange={(e) => setProposeVerification(e.target.value)}
                  placeholder="e.g. Inspect next 3 commercial batches for zero thermal excursions and complete calibration re-qualification audit."
                  className="block w-full rounded-lg border border-[#CBD5E1] text-sm p-3 bg-white focus:border-[#0F9D91] focus:ring-2 focus:ring-[#0F9D91]/20 leading-relaxed"
                  required
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-[#64748B] mb-1">
                  Associated Root Cause Reference (Optional)
                </label>
                <Input
                  placeholder="e.g. CAUSE-MAC-01 or 5-Whys Level 4"
                  value={proposeRootCauseRef}
                  onChange={(e) => setProposeRootCauseRef(e.target.value)}
                />
              </div>
            </CardContent>

            <CardFooter className="py-3 bg-[#F8FAFC] flex justify-end space-x-2">
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setShowProposeModal(false)}
              >
                Cancel
              </Button>
              <Button
                variant="accent"
                size="sm"
                type="submit"
                disabled={isSaving}
              >
                {isSaving ? 'Submitting to DB...' : 'Submit Proposed Action'}
              </Button>
            </CardFooter>
          </form>
        </Card>
      )}

      {/* 4. Action Cards List */}
      {actionList.length === 0 ? (
        <Card className="py-12 text-center border-dashed border-[#CBD5E1]">
          <CardContent className="space-y-3 max-w-sm mx-auto">
            <div className="w-12 h-12 rounded-full bg-[#E6F7F5] text-[#0F9D91] flex items-center justify-center mx-auto">
              <ShieldCheck className="w-6 h-6" />
            </div>
            <h4 className="text-sm font-semibold text-[#142B45]">
              No CAPA Actions Currently Recorded
            </h4>
            <p className="text-xs text-[#64748B]">
              Generate AI-assisted recommendations based on confirmed root causes or propose custom actions.
            </p>
            <div className="pt-2 flex items-center justify-center gap-2">
              {onGenerateAI && (
                <Button
                  variant="accent"
                  size="sm"
                  leftIcon={Sparkles}
                  onClick={onGenerateAI}
                  disabled={isGenerating}
                >
                  Generate AI Recommendations
                </Button>
              )}
              <Button
                variant="secondary"
                size="sm"
                leftIcon={PlusCircle}
                onClick={() => setShowProposeModal(true)}
              >
                Propose Action
              </Button>
            </div>
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-4">
          {actionList.map((action, idx) => {
            const actionId = action.id || action.action_id || `action-${idx}`;
            const isEditing = editingActionId === actionId;
            const currentStatus = action.status || action.action_status || 'Proposed';
            const statusVariant = STATUS_VARIANTS[currentStatus] || 'neutral';
            const isCorrective =
              (action.action_type || action.actionType || '').toLowerCase().includes('corrective');

            return (
              <Card
                key={actionId}
                className={`transition-all duration-150 border ${
                  currentStatus === 'Approved'
                    ? 'border-[#0F9D91]/60'
                    : currentStatus === 'Rejected'
                    ? 'border-[#FECACA] bg-[#FEF2F2]/20'
                    : 'border-[#E2E8F0]'
                }`}
              >
                <CardHeader className="py-3.5 bg-[#F8FAFC]">
                  <div className="flex items-center space-x-3">
                    <div
                      className={`w-7 h-7 rounded-lg flex items-center justify-center text-xs font-bold ${
                        isCorrective
                          ? 'bg-[#E6F7F5] text-[#0F9D91]'
                          : 'bg-[#EFF6FF] text-[#2563EB]'
                      }`}
                    >
                      {idx + 1}
                    </div>
                    <div>
                      <div className="flex items-center space-x-2">
                        <span className="text-xs font-bold text-[#142B45] font-mono">
                          {action.action_id || action.capa_id || `CAPA-REC-${idx + 1}`}
                        </span>
                        <span
                          className={`text-[10px] font-semibold px-2 py-0.5 rounded-full ${
                            isCorrective
                              ? 'bg-[#E6F7F5] text-[#0F9D91]'
                              : 'bg-[#EFF6FF] text-[#2563EB]'
                          }`}
                        >
                          {isCorrective ? 'Corrective Action' : 'Preventive Action'}
                        </span>
                      </div>
                    </div>
                  </div>

                  <div className="flex items-center space-x-2">
                    <StatusBadge variant={statusVariant} size="sm">
                      {currentStatus}
                    </StatusBadge>
                  </div>
                </CardHeader>

                <CardContent className="p-4 sm:p-5 space-y-3">
                  {/* Action Description */}
                  {isEditing ? (
                    <div className="space-y-3">
                      <div>
                        <label className="block text-xs font-semibold text-[#142B45] mb-1">
                          Edit Action Description:
                        </label>
                        <textarea
                          rows={2}
                          value={editForm.description}
                          onChange={(e) =>
                            setEditForm((prev) => ({ ...prev, description: e.target.value }))
                          }
                          className="block w-full text-xs p-2.5 rounded border border-[#CBD5E1]"
                        />
                      </div>
                      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                        <Input
                          label="Action Owner"
                          value={editForm.action_owner}
                          onChange={(e) =>
                            setEditForm((prev) => ({ ...prev, action_owner: e.target.value }))
                          }
                        />
                        <Input
                          label="Target Date"
                          type="date"
                          value={editForm.target_date}
                          onChange={(e) =>
                            setEditForm((prev) => ({ ...prev, target_date: e.target.value }))
                          }
                        />
                      </div>
                    </div>
                  ) : (
                    <>
                      <p className="text-xs text-[#1E293B] font-medium leading-relaxed">
                        {action.description}
                      </p>

                      {action.rationale && (
                        <div className="p-2.5 rounded-lg bg-[#F8FAFC] border border-[#E2E8F0] text-xs space-y-0.5">
                          <span className="font-semibold text-[#0F9D91] text-[11px] block">
                            Regulatory / Causal Rationale:
                          </span>
                          <p className="text-[11px] text-[#64748B] leading-relaxed">
                            {action.rationale}
                          </p>
                        </div>
                      )}

                      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs text-[#475569] pt-1">
                        <div className="flex items-center space-x-2">
                          <User className="w-3.5 h-3.5 text-[#64748B]" />
                          <span>
                            <strong>Owner:</strong>{' '}
                            {action.action_owner || action.actionOwner || 'QA Engineering Lead'}
                          </span>
                        </div>
                        <div className="flex items-center space-x-2">
                          <Calendar className="w-3.5 h-3.5 text-[#64748B]" />
                          <span>
                            <strong>Target Date:</strong>{' '}
                            {action.target_date || action.targetDate || 'Within 30 Days'}
                          </span>
                        </div>
                      </div>

                      {/* Effectiveness verification */}
                      <div className="text-xs text-[#64748B] bg-[#FAFAFA] p-2.5 rounded border border-[#F1F5F9] space-y-1">
                        <div className="flex items-center text-[11px] font-semibold text-[#142B45]">
                          <FileCheck className="w-3.5 h-3.5 mr-1 text-[#059669]" />
                          Effectiveness Verification Protocol:
                        </div>
                        <p className="text-[11px] leading-relaxed text-[#475569]">
                          {action.effectiveness_verification_method ||
                            action.effectivenessVerification ||
                            (typeof action.effectiveness_verification === 'string'
                              ? action.effectiveness_verification
                              : 'Measurable verification protocol required before closure.')}
                        </p>
                      </div>
                    </>
                  )}
                </CardContent>

                {/* Human QA Review Action Footer */}
                <CardFooter className="py-2.5 bg-[#F8FAFC] flex flex-wrap items-center justify-between gap-2">
                  <div className="text-[11px] text-[#64748B]">
                    Status: <span className="font-semibold">{currentStatus}</span>
                  </div>

                  <div className="flex items-center space-x-1.5 flex-wrap gap-y-1">
                    {isEditing ? (
                      <>
                        <Button
                          variant="ghost"
                          size="xs"
                          onClick={() => setEditingActionId(null)}
                        >
                          Cancel
                        </Button>
                        <Button
                          variant="accent"
                          size="xs"
                          onClick={() => handleSaveEdit(actionId)}
                        >
                          Save Edits
                        </Button>
                      </>
                    ) : (
                      <>
                        {/* Status Actions based on GxP state */}
                        {(currentStatus === 'Proposed' || currentStatus === 'Pending Review' || currentStatus === 'Draft') && (
                          <>
                            <Button
                              variant="secondary"
                              size="xs"
                              leftIcon={Check}
                              onClick={() =>
                                onUpdateStatus && onUpdateStatus(actionId, 'Approved')
                              }
                            >
                              Approve Action
                            </Button>
                            <Button
                              variant="ghost"
                              size="xs"
                              leftIcon={Ban}
                              onClick={() =>
                                onUpdateStatus && onUpdateStatus(actionId, 'Rejected')
                              }
                            >
                              Reject
                            </Button>
                          </>
                        )}

                        {currentStatus === 'Approved' && (
                          <Button
                            variant="primary"
                            size="xs"
                            leftIcon={Play}
                            onClick={() =>
                              onUpdateStatus && onUpdateStatus(actionId, 'In Progress')
                            }
                          >
                            Start Implementation
                          </Button>
                        )}

                        {currentStatus === 'In Progress' && (
                          <Button
                            variant="accent"
                            size="xs"
                            leftIcon={CheckCheck}
                            onClick={() =>
                              onUpdateStatus && onUpdateStatus(actionId, 'Completed')
                            }
                          >
                            Mark Completed
                          </Button>
                        )}

                        <Button
                          variant="ghost"
                          size="xs"
                          onClick={() => handleStartEdit(action)}
                        >
                          Edit
                        </Button>
                      </>
                    )}
                  </div>
                </CardFooter>
              </Card>
            );
          })}
        </div>
      )}
    </div>
  );
}
