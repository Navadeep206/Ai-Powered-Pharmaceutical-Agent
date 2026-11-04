import React from 'react';
import Input from '../common/Input';
import { Mail, AlertCircle, HelpCircle } from 'lucide-react';

/**
 * Intake form for raw email alerts or shift handover correspondence.
 */
export default function EmailIncidentInput({
  subject,
  body,
  onSubjectChange,
  onBodyChange,
  error,
}) {
  return (
    <div className="space-y-4">
      <div>
        <Input
          label="Email Subject Header"
          placeholder="e.g. URGENT: Temperature Excursion on Reactor R-102 (Batch API-705)"
          value={subject}
          onChange={(e) => onSubjectChange(e.target.value)}
          leftIcon={Mail}
          required
          helperText="Shift handover subject line or automated SCADA email alert header"
        />
      </div>

      <div>
        <div className="flex items-center justify-between mb-1.5">
          <label className="block text-xs font-semibold text-[#142B45] uppercase tracking-wider">
            Email Body Content <span className="text-[#DC2626]">*</span>
          </label>
          <span className="text-xs text-[#64748B] font-mono">
            {body ? body.length : 0} characters
          </span>
        </div>

        <textarea
          rows={6}
          value={body}
          onChange={(e) => onBodyChange(e.target.value)}
          placeholder="Paste full supervisor email thread or deviation alert communication..."
          className={`block w-full rounded-lg border text-sm transition-all duration-150 p-3.5 bg-white leading-relaxed ${
            error
              ? 'border-[#DC2626] text-[#991B1B] focus:ring-2 focus:ring-[#DC2626]/20 focus:border-[#DC2626]'
              : 'border-[#CBD5E1] text-[#1E293B] hover:border-[#94A3B8] focus:border-[#0F9D91] focus:ring-2 focus:ring-[#0F9D91]/20'
          }`}
        />
      </div>

      <div className="p-3 bg-[#F8FAFC] border border-[#E2E8F0] rounded-lg text-xs text-[#64748B] flex items-center space-x-2">
        <HelpCircle className="w-4 h-4 text-[#0F9D91] shrink-0" />
        <span>
          RootIQ will parse email sender metadata, timestamps, and unstructured narrative into structured deviation entities.
        </span>
      </div>

      {error && (
        <div className="p-2.5 bg-[#FEF2F2] border border-[#FECACA] rounded-lg text-xs text-[#991B1B] flex items-center space-x-2">
          <AlertCircle className="w-4 h-4 shrink-0 text-[#DC2626]" />
          <span>{error}</span>
        </div>
      )}
    </div>
  );
}

