import React from 'react';
import { Link } from 'react-router-dom';
import StatusBadge from '../common/StatusBadge';
import { ArrowLeft, Clock, Building2, Tag, ShieldAlert, CheckCircle2, Cpu, Box } from 'lucide-react';

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
 * Executive header for the Investigation Workspace showing metadata, severity, status, and batch citations.
 */
export default function InvestigationHeader({ investigation }) {
  if (!investigation) return null;

  return (
    <div className="bg-white rounded-xl border border-[#E2E8F0] p-5 sm:p-6 shadow-2xs space-y-4">
      {/* Top row: Back link + badges + timestamps */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
        <div className="flex items-center space-x-3">
          <Link
            to="/investigations"
            className="p-1.5 text-[#64748B] hover:text-[#142B45] hover:bg-[#F1F5F9] rounded-lg transition"
            title="Back to Deviation Registry"
            aria-label="Back to Deviation Registry"
          >
            <ArrowLeft className="w-5 h-5" />
          </Link>

          <div className="flex items-center space-x-2 flex-wrap gap-y-1">
            <span className="font-mono text-xs font-bold text-[#142B45] bg-[#F1F5F9] px-2.5 py-1 rounded border border-[#E2E8F0] whitespace-nowrap">
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

        <div className="flex items-center space-x-3 text-xs text-[#64748B] flex-wrap">
          <span className="flex items-center">
            <Clock className="w-3.5 h-3.5 mr-1 text-[#94A3B8]" />
            Logged: {investigation.date || 'Contemporaneous'}
          </span>
          <span>&bull;</span>
          <span className="font-medium text-[#142B45]">
            Batch: <strong className="font-mono font-bold text-[#142B45]">{investigation.batch || 'N/A'}</strong>
          </span>
        </div>
      </div>

      {/* Title & Department */}
      <div>
        <h1 className="text-xl sm:text-2xl font-bold text-[#142B45] tracking-tight leading-snug">
          {investigation.title}
        </h1>
        <div className="flex flex-wrap items-center gap-3 text-xs text-[#64748B] mt-2">
          <span className="flex items-center text-[#475569] font-medium bg-[#F8FAFC] px-2.5 py-1 rounded-md border border-[#F1F5F9]">
            <Building2 className="w-3.5 h-3.5 mr-1.5 text-[#0F9D91]" />
            Dept: <strong className="ml-1 text-[#142B45]">{investigation.department || 'General QA'}</strong>
          </span>
          {investigation.productName && (
            <span className="flex items-center text-[#475569] font-medium bg-[#F8FAFC] px-2.5 py-1 rounded-md border border-[#F1F5F9]">
              <Box className="w-3.5 h-3.5 mr-1.5 text-[#2563EB]" />
              API: <strong className="ml-1 text-[#142B45]">{investigation.productName}</strong>
            </span>
          )}
          {investigation.equipment && investigation.equipment !== 'N/A' && (
            <span className="flex items-center text-[#475569] font-medium bg-[#F8FAFC] px-2.5 py-1 rounded-md border border-[#F1F5F9]">
              <Cpu className="w-3.5 h-3.5 mr-1.5 text-[#D97706]" />
              Unit: <strong className="ml-1 text-[#142B45]">{investigation.equipment}</strong>
            </span>
          )}
        </div>
      </div>
    </div>
  );
}
