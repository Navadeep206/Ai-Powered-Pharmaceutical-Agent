import React from 'react';
import { Link } from 'react-router-dom';
import StatusBadge from '../common/StatusBadge';
import Button from '../common/Button';
import { ArrowLeft, Clock, Building2, Tag, ShieldAlert, CheckCircle2 } from 'lucide-react';

const SEVERITY_BADGE_MAP = {
  Critical: 'danger',
  High: 'warning',
  Medium: 'info',
  Low: 'neutral',
};

const STATUS_BADGE_MAP = {
  Open: 'warning',
  'Under Investigation': 'teal',
  'Pending Review': 'info',
  Closed: 'success',
};

/**
 * Header for the Investigation Workspace showing metadata, severity, status, and progress steps.
 */
export default function InvestigationHeader({ investigation, activeTab, onTabChange }) {
  if (!investigation) return null;

  const steps = [
    { id: 'overview', label: '1. Overview', step: 1 },
    { id: 'rca', label: '2. RCA Analysis', step: 2 },
    { id: 'evidence', label: '3. Evidence & Gaps', step: 3 },
    { id: 'capa', label: '4. CAPA Plan', step: 4 },
  ];

  return (
    <div className="bg-white rounded-xl border border-[#E2E8F0] p-6 shadow-2xs space-y-5">
      {/* Top row: Back link + badges */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
        <div className="flex items-center space-x-3">
          <Link
            to="/investigations"
            className="p-1.5 text-[#64748B] hover:text-[#142B45] hover:bg-[#F1F5F9] rounded-lg transition"
            title="Back to Investigations"
          >
            <ArrowLeft className="w-5 h-5" />
          </Link>

          <div className="flex items-center space-x-2">
            <span className="font-mono text-xs font-bold text-[#142B45] bg-[#F1F5F9] px-2.5 py-1 rounded border border-[#E2E8F0]">
              {investigation.id}
            </span>
            <StatusBadge
              variant={SEVERITY_BADGE_MAP[investigation.severity] || 'warning'}
              size="sm"
            >
              {investigation.severity} Severity
            </StatusBadge>
            <StatusBadge
              variant={STATUS_BADGE_MAP[investigation.status] || 'teal'}
              size="sm"
            >
              {investigation.status}
            </StatusBadge>
          </div>
        </div>

        <div className="flex items-center space-x-3 text-xs text-[#64748B]">
          <span className="flex items-center">
            <Clock className="w-3.5 h-3.5 mr-1 text-[#94A3B8]" />
            Created: {investigation.date}
          </span>
          <span>&bull;</span>
          <span className="font-medium text-[#142B45]">
            Batch: {investigation.batch}
          </span>
        </div>
      </div>

      {/* Title & Department */}
      <div>
        <h1 className="text-xl sm:text-2xl font-bold text-[#142B45] tracking-tight">
          {investigation.title}
        </h1>
        <div className="flex flex-wrap items-center gap-3 text-xs text-[#64748B] mt-1.5">
          <span className="flex items-center text-[#475569] font-medium">
            <Building2 className="w-3.5 h-3.5 mr-1 text-[#0F9D91]" />
            {investigation.department}
          </span>
          {investigation.productName && (
            <>
              <span>&bull;</span>
              <span>API: <strong className="text-[#334155]">{investigation.productName}</strong></span>
            </>
          )}
          {investigation.equipment && (
            <>
              <span>&bull;</span>
              <span>Unit: <strong className="text-[#334155]">{investigation.equipment}</strong></span>
            </>
          )}
        </div>
      </div>

      {/* Linear GxP Investigation Lifecycle Stepper */}
      <div className="pt-2 border-t border-[#F1F5F9]">
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
          {steps.map((s) => {
            const isActive = activeTab === s.id;
            return (
              <button
                key={s.id}
                type="button"
                onClick={() => onTabChange(s.id)}
                className={`flex items-center px-3 py-2 rounded-lg text-xs font-semibold transition-all ${
                  isActive
                    ? 'bg-[#142B45] text-white shadow-xs'
                    : 'bg-[#F8FAFC] text-[#64748B] hover:bg-[#F1F5F9] hover:text-[#142B45]'
                }`}
              >
                <span
                  className={`w-5 h-5 rounded-full flex items-center justify-center mr-2 text-[10px] font-bold ${
                    isActive ? 'bg-[#0F9D91] text-white' : 'bg-[#E2E8F0] text-[#64748B]'
                  }`}
                >
                  {s.step}
                </span>
                <span className="truncate">{s.label.replace(/^\d+\.\s*/, '')}</span>
              </button>
            );
          })}
        </div>
      </div>
    </div>
  );
}

