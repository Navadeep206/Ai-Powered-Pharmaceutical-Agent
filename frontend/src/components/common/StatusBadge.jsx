import React from 'react';

/**
 * Accessible enterprise StatusBadge component for GxP & RCA statuses.
 */
export default function StatusBadge({
  children,
  variant = 'neutral',
  size = 'md',
  dot = true,
  icon: Icon,
  className = '',
}) {
  const variants = {
    success: 'bg-[#ECFDF5] text-[#065F46] border-[#A7F3D0]',
    warning: 'bg-[#FFFBEB] text-[#92400E] border-[#FDE68A]',
    danger: 'bg-[#FEF2F2] text-[#991B1B] border-[#FECACA]',
    critical: 'bg-[#FEF2F2] text-[#991B1B] border-[#FECACA]',
    info: 'bg-[#EFF6FF] text-[#1E40AF] border-[#BFDBFE]',
    teal: 'bg-[#E6F7F5] text-[#0A736A] border-[#A2E6DF]',
    neutral: 'bg-[#F1F5F9] text-[#475569] border-[#E2E8F0]',
    navy: 'bg-[#142B45]/10 text-[#142B45] border-[#142B45]/20',
  };

  const dotColors = {
    success: 'bg-[#059669]',
    warning: 'bg-[#D97706]',
    danger: 'bg-[#DC2626]',
    critical: 'bg-[#DC2626]',
    info: 'bg-[#2563EB]',
    teal: 'bg-[#0F9D91]',
    neutral: 'bg-[#64748B]',
    navy: 'bg-[#142B45]',
  };

  const sizes = {
    sm: 'text-[11px] px-2 py-0.5 gap-1',
    md: 'text-xs px-2.5 py-1 gap-1.5',
    lg: 'text-sm px-3 py-1.5 gap-2',
  };

  const dotSizes = {
    sm: 'w-1.5 h-1.5',
    md: 'w-2 h-2',
    lg: 'w-2.5 h-2.5',
  };

  return (
    <span
      className={`inline-flex items-center font-medium rounded-full border border-solid select-none tracking-normal ${
        variants[variant] || variants.neutral
      } ${sizes[size] || sizes.md} ${className}`}
    >
      {dot && (
        <span
          className={`rounded-full shrink-0 ${dotColors[variant] || dotColors.neutral} ${
            dotSizes[size] || dotSizes.md
          }`}
        />
      )}
      {Icon && <Icon className="w-3.5 h-3.5 shrink-0" />}
      <span>{children}</span>
    </span>
  );
}

