import React, { useState } from 'react';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '../common/Card';
import StatusBadge from '../common/StatusBadge';
import Button from '../common/Button';
import EvidenceForm from './EvidenceForm';
import {
  FileCheck,
  AlertOctagon,
  HelpCircle,
  FileQuestion,
  PlusCircle,
  FileText,
  CheckCircle,
  Clock,
  ExternalLink,
  AlertTriangle,
  FileWarning,
  CheckCircle2,
  XCircle,
} from 'lucide-react';

const CATEGORY_SECTIONS = [
  {
    key: 'Supporting Evidence',
    title: 'Supporting Evidence',
    description: 'Empirical data corroborating causal hypotheses & parameter compliance',
    icon: FileCheck,
    color: 'text-[#059669]',
    bgColor: 'bg-[#ECFDF5]',
    borderColor: 'border-[#A7F3D0]',
    cardBorder: 'border-[#E2E8F0]',
    isGap: false,
  },
  {
    key: 'Contradictory Evidence',
    title: 'Contradictory Evidence',
    description: 'Data refuting, disproving, or challenging suspected failure modes',
    icon: AlertOctagon,
    color: 'text-[#DC2626]',
    bgColor: 'bg-[#FEF2F2]',
    borderColor: 'border-[#FECACA]',
    cardBorder: 'border-[#FECACA]/60',
    isGap: false,
  },
  {
    key: 'Missing Evidence',
    title: 'Missing Evidence & Investigation Data Gaps',
    description: 'Uncollected records, pending calibration certificates, or unmeasured parameters (Must be collected before closure)',
    icon: FileWarning,
    color: 'text-[#D97706]',
    bgColor: 'bg-[#FFFBEB]',
    borderColor: 'border-[#FDE68A]',
    cardBorder: 'border-dashed border-[#F59E0B] bg-[#FFFBEB]/20',
    isGap: true,
  },
  {
    key: 'Investigator Questions',
    title: 'Investigator Inquiries & Clarifications',
    description: 'Formal technical queries assigned to subject matter experts and process owners',
    icon: FileQuestion,
    color: 'text-[#2563EB]',
    bgColor: 'bg-[#EFF6FF]',
    borderColor: 'border-[#BFDBFE]',
    cardBorder: 'border-[#E2E8F0]',
    isGap: false,
  },
];

const STATUS_VARIANTS = {
  Verified: 'success',
  'Verified by QA': 'success',
  'Under Review': 'info',
  'Pending Review': 'warning',
  'Pending Collection': 'warning',
  Contradictory: 'danger',
  Rejected: 'danger',
};

/**
 * Enterprise Evidence & Gap Analysis workspace partitioned into Supporting, Contradictory,
 * Missing Evidence (strictly visually distinguished as data gaps), and Investigator Inquiries.
 */
export default function EvidenceList({
  evidence = [],
  onAddEvidence,
  onUpdateEvidenceStatus,
}) {
  const [showAddForm, setShowAddForm] = useState(false);

  return (
    <div className="space-y-6">
      {/* Header controls & Add button */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 p-4 bg-white rounded-xl border border-[#E2E8F0] shadow-2xs">
        <div>
          <h3 className="text-sm font-bold text-[#142B45]">
            Evidence Repository & Gap Analysis
          </h3>
          <p className="text-xs text-[#64748B]">
            Corroborate causal mechanisms with chromatographic, SCADA telemetry, calibration, and batch records.
          </p>
        </div>

        <div className="flex items-center space-x-2">
          <StatusBadge variant="neutral" size="sm">
            {evidence.length} Total Artifacts & Gaps
          </StatusBadge>
          {!showAddForm && (
            <Button
              variant="accent"
              size="sm"
              leftIcon={PlusCircle}
              onClick={() => setShowAddForm(true)}
              aria-label="Add Evidence Item"
            >
              Add Evidence Item
            </Button>
          )}
        </div>
      </div>

      {/* Add Evidence Form Drawer/Card */}
      {showAddForm && (
        <EvidenceForm
          onAddEvidence={(item) => {
            onAddEvidence(item);
            setShowAddForm(false);
          }}
          onCancel={() => setShowAddForm(false)}
        />
      )}

      {/* 4 Categorized Sections */}
      <div className="space-y-6">
        {CATEGORY_SECTIONS.map((section) => {
          const Icon = section.icon;
          const sectionItems = evidence.filter(
            (e) => e.category === section.key
          );

          return (
            <Card key={section.key} className={section.cardBorder}>
              <CardHeader className={`py-3.5 ${section.isGap ? 'bg-[#FFFBEB]/60' : 'bg-[#F8FAFC]'}`}>
                <div className="flex items-center space-x-2.5">
                  <div
                    className={`w-8 h-8 rounded-lg flex items-center justify-center ${section.bgColor} border ${section.borderColor}`}
                  >
                    <Icon className={`w-4 h-4 ${section.color}`} />
                  </div>
                  <div>
                    <div className="flex items-center space-x-2">
                      <CardTitle className="text-sm">{section.title}</CardTitle>
                      {section.isGap && (
                        <span className="text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded bg-[#FEF3C7] text-[#92400E] border border-[#FDE68A]">
                          Action Required
                        </span>
                      )}
                    </div>
                    <CardDescription className="text-[11px]">
                      {section.description}
                    </CardDescription>
                  </div>
                </div>

                <span
                  className={`text-xs font-mono font-bold px-2 py-0.5 rounded border ${
                    section.isGap
                      ? 'bg-[#FEF3C7] text-[#92400E] border-[#FDE68A]'
                      : 'bg-white text-[#142B45] border-[#E2E8F0]'
                  }`}
                >
                  {sectionItems.length}
                </span>
              </CardHeader>

              <CardContent className="p-4 sm:p-5 space-y-3">
                {sectionItems.length === 0 ? (
                  <div
                    className={`p-4 text-center rounded-lg border ${
                      section.isGap
                        ? 'border-dashed border-[#FDE68A] bg-[#FFFBEB]/30'
                        : 'border-dashed border-[#CBD5E1] bg-[#FAFAFA]'
                    }`}
                  >
                    <p className="text-xs text-[#94A3B8] italic">
                      {section.isGap
                        ? 'Zero uncollected evidence gaps recorded. All required parameters are currently accounted for.'
                        : `No records logged under ${section.title.toLowerCase()}.`}
                    </p>
                  </div>
                ) : (
                  <div className="space-y-3">
                    {sectionItems.map((item) => {
                      const isGapItem = section.isGap;

                      return (
                        <div
                          key={item.id}
                          className={`p-3.5 rounded-lg border transition-all ${
                            isGapItem
                              ? 'border-dashed border-[#F59E0B] bg-[#FFFBEB]/40 hover:bg-[#FFFBEB]/60'
                              : 'border-[#E2E8F0] bg-white hover:border-[#CBD5E1]'
                          } flex flex-col sm:flex-row sm:items-start justify-between gap-3 shadow-2xs`}
                        >
                          <div className="space-y-1.5 flex-1 min-w-0">
                            <div className="flex items-center space-x-2 flex-wrap">
                              {isGapItem && (
                                <span className="inline-flex items-center text-[10px] font-bold text-[#D97706] bg-[#FEF3C7] px-1.5 py-0.5 rounded">
                                  <AlertTriangle className="w-3 h-3 mr-1" />
                                  MISSING DATA GAP
                                </span>
                              )}
                              <h4 className="text-xs font-bold text-[#142B45]">
                                {item.title || item.description}
                              </h4>
                            </div>

                            <div className="flex flex-wrap items-center gap-2 text-xs text-[#64748B]">
                              <span className="font-semibold text-[#0F9D91]">
                                Format: {item.type || 'Investigation Artifact'}
                              </span>
                              <span>&bull;</span>
                              <span className="font-mono text-[#334155] bg-[#F1F5F9] px-1.5 py-0.5 rounded text-[11px]">
                                Citation: {item.reference || item.source_reference || 'Attached Document'}
                              </span>
                            </div>

                            {item.notes && (
                              <p className="text-xs text-[#475569] leading-relaxed pt-1 bg-[#FAFAFA] p-2 rounded border border-[#F1F5F9]">
                                {item.notes}
                              </p>
                            )}
                          </div>

                          {/* Review Status & Actions */}
                          <div className="flex sm:flex-col items-end justify-between sm:justify-start gap-2 shrink-0">
                            <StatusBadge
                              variant={STATUS_VARIANTS[item.status] || (isGapItem ? 'warning' : 'neutral')}
                              size="sm"
                            >
                              {item.status || 'Pending Review'}
                            </StatusBadge>

                            {onUpdateEvidenceStatus && (
                              <div className="flex items-center space-x-1">
                                <label className="text-[10px] text-[#64748B] sr-only">
                                  Review Status
                                </label>
                                <select
                                  value={item.status}
                                  onChange={(e) =>
                                    onUpdateEvidenceStatus(item.id, e.target.value)
                                  }
                                  className="text-[11px] bg-white border border-[#CBD5E1] rounded px-2 py-1 text-[#142B45] focus:outline-none focus:border-[#0F9D91] cursor-pointer"
                                >
                                  <option value="Pending Review">Pending Review</option>
                                  <option value="Verified">Verified by QA</option>
                                  <option value="Rejected">Rejected / Disproven</option>
                                </select>
                              </div>
                            )}
                          </div>
                        </div>
                      );
                    })}
                  </div>
                )}
              </CardContent>
            </Card>
          );
        })}
      </div>
    </div>
  );
}
