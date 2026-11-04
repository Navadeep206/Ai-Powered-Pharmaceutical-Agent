import React from 'react';

/**
 * Reusable Form Input with label, error message, helper text, and icons.
 */
export default function Input({
  label,
  id,
  name,
  type = 'text',
  placeholder,
  value,
  onChange,
  disabled = false,
  required = false,
  error,
  helperText,
  leftIcon: LeftIcon,
  rightIcon: RightIcon,
  className = '',
  ...props
}) {
  const inputId = id || name;

  return (
    <div className={`w-full ${className}`}>
      {label && (
        <label
          htmlFor={inputId}
          className="block text-xs font-semibold text-[#142B45] mb-1.5 uppercase tracking-wider"
        >
          {label} {required && <span className="text-[#DC2626]">*</span>}
        </label>
      )}

      <div className="relative rounded-lg shadow-2xs">
        {LeftIcon && (
          <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-[#64748B]">
            <LeftIcon className="w-4 h-4" />
          </div>
        )}

        <input
          id={inputId}
          name={name}
          type={type}
          value={value}
          onChange={onChange}
          disabled={disabled}
          placeholder={placeholder}
          className={`block w-full rounded-lg border text-sm transition-all duration-150 py-2 ${
            LeftIcon ? 'pl-9' : 'pl-3.5'
          } ${RightIcon ? 'pr-9' : 'pr-3.5'} ${
            error
              ? 'border-[#DC2626] text-[#991B1B] focus:ring-2 focus:ring-[#DC2626]/20 focus:border-[#DC2626]'
              : 'border-[#CBD5E1] text-[#1E293B] bg-white hover:border-[#94A3B8] focus:border-[#0F9D91] focus:ring-2 focus:ring-[#0F9D91]/20'
          } ${disabled ? 'bg-[#F1F5F9] text-[#94A3B8] cursor-not-allowed border-[#E2E8F0]' : ''}`}
          {...props}
        />

        {RightIcon && (
          <div className="absolute inset-y-0 right-0 pr-3 flex items-center pointer-events-none text-[#64748B]">
            <RightIcon className="w-4 h-4" />
          </div>
        )}
      </div>

      {error ? (
        <p className="mt-1.5 text-xs text-[#DC2626] font-medium">{error}</p>
      ) : helperText ? (
        <p className="mt-1.5 text-xs text-[#64748B]">{helperText}</p>
      ) : null}
    </div>
  );
}

