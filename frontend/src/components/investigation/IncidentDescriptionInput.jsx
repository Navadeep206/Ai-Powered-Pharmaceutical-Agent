import React from 'react';
import { AlertCircle, HelpCircle } from 'lucide-react';

/**
 * Incident Description narrative input with character counter and context guidance.
 */
export default function IncidentDescriptionInput({
  value,
  onChange,
  error,
  placeholder,
}) {
  const defaultPlaceholder =
    'Provide detailed incident observations:\n' +
    '- Batch Number & API Product Name (e.g. Batch API-705, Atorvastatin)\n' +
    '- Stage of synthesis or unit operation (e.g. Condensation, Drying)\n' +
    '- Observed process excursion (e.g. Temperature spiked to 68.4°C vs limit of 56.0°C)\n' +
    '- Duration of excursion and equipment involved (e.g. Reactor R-102 for 27 mins)\n' +
    '- Immediate corrective or containment actions taken by operator...';

  const charCount = value ? value.length : 0;
  const minRecommended = 50;

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between">
        <label className="block text-xs font-semibold text-[#142B45] uppercase tracking-wider">
          Incident Narrative Description <span className="text-[#DC2626]">*</span>
        </label>
        <span
          className={`text-xs font-mono ${
            charCount < minRecommended ? 'text-[#D97706]' : 'text-[#64748B]'
          }`}
        >
          {charCount} characters {charCount < minRecommended && `(min ~${minRecommended})`}
        </span>
      </div>

      <div className="relative rounded-lg shadow-2xs">
        <textarea
          rows={7}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          placeholder={placeholder || defaultPlaceholder}
          className={`block w-full rounded-lg border text-sm transition-all duration-150 p-3.5 bg-white leading-relaxed ${
            error
              ? 'border-[#DC2626] text-[#991B1B] focus:ring-2 focus:ring-[#DC2626]/20 focus:border-[#DC2626]'
              : 'border-[#CBD5E1] text-[#1E293B] hover:border-[#94A3B8] focus:border-[#0F9D91] focus:ring-2 focus:ring-[#0F9D91]/20'
          }`}
        />
      </div>

      <div className="flex items-center justify-between text-xs text-[#64748B] pt-1">
        <span className="flex items-center">
          <HelpCircle className="w-3.5 h-3.5 mr-1 text-[#0F9D91]" />
          Include specific equipment IDs, temperatures, pressures, or analytical readings.
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

