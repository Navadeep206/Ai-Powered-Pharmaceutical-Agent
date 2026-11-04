import React from 'react';
import { ChevronDown } from 'lucide-react';

/**
 * Reusable Select field adhering to RootIQ design system.
 */
export default function Select({
  label,
  id,
  name,
  value,
  onChange,
  options = [],
  placeholder = 'Select an option',
  disabled = false,
  required = false,
  error,
  helperText,
  className = '',
  ...props
}) {
  const selectId = id || name;

  return (
    <div className={`w-full ${className}`}>
      {label && (
        <label
          htmlFor={selectId}
          className="block text-xs font-semibold text-[#142B45] mb-1.5 uppercase tracking-wider"
        >
          {label} {required && <span className="text-[#DC2626]">*</span>}
        </label>
      )}

      <div className="relative rounded-lg shadow-2xs">
        <select
          id={selectId}
          name={name}
          value={value}
          onChange={onChange}
          disabled={disabled}
          className={`block w-full appearance-none rounded-lg border text-sm transition-all duration-150 py-2 pl-3.5 pr-10 bg-white ${
            error
              ? 'border-[#DC2626] text-[#991B1B] focus:ring-2 focus:ring-[#DC2626]/20 focus:border-[#DC2626]'
              : 'border-[#CBD5E1] text-[#1E293B] hover:border-[#94A3B8] focus:border-[#0F9D91] focus:ring-2 focus:ring-[#0F9D91]/20'
          } ${disabled ? 'bg-[#F1F5F9] text-[#94A3B8] cursor-not-allowed border-[#E2E8F0]' : ''}`}
          {...props}
        >
          {placeholder && (
            <option value="" disabled>
              {placeholder}
            </option>
          )}
          {options.map((opt) => (
            <option key={opt.value} value={opt.value}>
              {opt.label}
            </option>
          ))}
        </select>

        <div className="absolute inset-y-0 right-0 pr-3 flex items-center pointer-events-none text-[#64748B]">
          <ChevronDown className="w-4 h-4" />
        </div>
      </div>

      {error ? (
        <p className="mt-1.5 text-xs text-[#DC2626] font-medium">{error}</p>
      ) : helperText ? (
        <p className="mt-1.5 text-xs text-[#64748B]">{helperText}</p>
      ) : null}
    </div>
  );
}

