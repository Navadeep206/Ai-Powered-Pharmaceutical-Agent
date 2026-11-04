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
} from 'lucide-react';

const CATEGORY_SECTIONS = [
  {
    key: 'Supporting Evidence',
    title: 'Supporting Evidence',
    description: 'Empirical data corroborating causal hypotheses',
    icon: FileCheck,
    color: 'text-[#059669]',
    bgColor: 'bg-[#ECFDF5]',
    borderColor: 'border-[#A7F3D0]',
  },
  {
    key: 'Contradictory Evidence',
    title: 'Contradictory Evidence',
    description: 'Data refuting or disproving suspected failure modes',
    icon: AlertOctagon,
    color: 'text-[#DC2626]',
    bgColor: 'bg-[#FEF2F2]',
    borderColor: 'border-[#FECACA]',
  },
  {
    key: 'Missing Evidence',
    title: 'Missing Evidence & Data Gaps',
    description: 'Uncollected reports, pending calibration logs, or unmeasured parameters',
    icon: HelpCircle,
    color: 'text-[#D97706]',
    bgColor: 'bg-[#FFFBEB]',
    borderColor: 'border-[#FDE68A]',
  },
  {
    key: 'Investigator Questions',
    title: 'Investigator Inquiry Questions',
    description: 'Engineering inquiries and procedural clarifications assigned to SME leads',
    icon: FileQuestion,
    color: 'text-[#2563EB]',
    bgColor: 'bg-[#EFF6FF]',
    borderColor: 'border-[#BFDBFE]',
  },
];

const STATUS_VARIANTS = {
  'Verified by QA': 'success',
  'Under Review': 'info',
  'Pending Collection': 'warning',
  Contradictory: 'danger',
};

/**
 * Evidence & Gap Analysis viewer partitioned into Supporting, Contradictory, Missing, and Questions.
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
            Corroborate failure modes with chromatographic, sensor, and batch records.
          </p>
        </div>

        <div className="flex items-center space-x-2">
          <StatusBadge variant="neutral" size="sm">
            {evidence.length} Artifacts Linked
          </StatusBadge>
          {!showAddForm && (
            <Button
              variant="accent"
              size="sm"
              leftIcon={PlusCircle}
              onClick={() => setShowAddForm(true)}
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
      <div className="space-y-5">
        {CATEGORY_SECTIONS.map((section) => {
          const Icon = section.icon;
          const sectionItems = evidence.filter(
            (e) => e.category === section.key
          );

          return (
            <Card key={section.key}>
              <CardHeader className="py-3 bg-[#F8FAFC]">
                <div className="flex items-center space-x-2.5">
                  <div
                    className={`w-7 h-7 rounded-lg flex items-center justify-center ${section.bgColor}`}
                  >
                    <Icon className={`w-4 h-4 ${section.color}`} />
                  </div>
                  <div>
                    <CardTitle className="text-sm">{section.title}</CardTitle>
                    <CardDescription className="text-[11px]">
                      {section.description}
                    </CardDescription>
                  </div>
                </div>

                <span className="text-xs font-mono font-bold bg-white px-2 py-0.5 rounded border border-[#E2E8F0] text-[#142B45]">
                  {sectionItems.length}
                </span>
              </CardHeader>

              <CardContent className="p-4 space-y-3">
                {sectionItems.length === 0 ? (
                  <p className="text-xs text-[#94A3B8] italic py-2">
                    No items recorded under {section.title.toLowerCase()}.
                  </p>
                ) : (
                  <div className="divide-y divide-[#F1F5F9]">
                    {sectionItems.map((item) => (
                      <div
                        key={item.id}
                        className="py-3 first:pt-0 last:pb-0 flex flex-col sm:flex-row sm:items-start justify-between gap-3"
                      >
                        <div className="space-y-1 max-w-xl">
                          <div className="flex items-center space-x-2">
                            <span className="text-xs font-bold text-[#142B45]">
                              {item.title}
                            </span>
                          </div>

                          <div className="flex items-center space-x-2 text-xs text-[#64748B]">
                            <span className="font-semibold text-[#0F9D91]">
                              Type: {item.type}
                            </span>
                            <span>&bull;</span>
                            <span className="font-mono text-[#334155] bg-[#F1F5F9] px-1.5 py-0.2 rounded">
                              Ref: {item.reference}
                            </span>
                          </div>

                          {item.notes && (
                            <p className="text-xs text-[#475569] leading-relaxed pt-0.5">
                              {item.notes}
                            </p>
                          )}
                        </div>

                        {/* Review Status Switcher */}
                        <div className="flex items-center space-x-2 shrink-0">
                          <StatusBadge
                            variant={STATUS_VARIANTS[item.status] || 'neutral'}
                            size="sm"
                          >
                            {item.status}
                          </StatusBadge>

                          <select
                            value={item.status}
                            onChange={(e) =>
                              onUpdateEvidenceStatus(item.id, e.target.value)
                            }
                            className="text-[11px] bg-white border border-[#CBD5E1] rounded px-2 py-1 text-[#142B45] focus:outline-none focus:border-[#0F9D91]"
                          >
                            <option value="Under Review">Under Review</option>
                            <option value="Verified by QA">Verified by QA</option>
                            <option value="Pending Collection">Pending Collection</option>
                            <option value="Contradictory">Contradictory</option>
                          </select>
                        </div>
                      </div>
                    ))}
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

