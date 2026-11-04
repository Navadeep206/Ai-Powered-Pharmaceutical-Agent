import React from 'react';
import { Loader2 } from 'lucide-react';

/**
 * Reusable enterprise Button component adhering to RootIQ design system.
 */
export default function Button({
  children,
  variant = 'primary',
  size = 'md',
  isLoading = false,
  disabled = false,
  fullWidth = false,
  leftIcon: LeftIcon,
  rightIcon: RightIcon,
  className = '',
  type = 'button',
  ...props
}) {
  const baseStyles =
    'inline-flex items-center justify-center font-medium rounded-lg transition-all duration-150 focus:outline-none focus:ring-2 focus:ring-offset-1 disabled:opacity-60 disabled:cursor-not-allowed select-none';

  const variants = {
    primary:
      'bg-[#142B45] text-white hover:bg-[#1E3E63] active:bg-[#0D1C2E] focus:ring-[#142B45]/40 shadow-xs border border-transparent',
    secondary:
      'bg-white text-[#334155] border border-[#CBD5E1] hover:bg-[#F8FAFC] hover:border-[#94A3B8] active:bg-[#F1F5F9] focus:ring-[#64748B]/30 shadow-2xs',
    accent:
      'bg-[#0F9D91] text-white hover:bg-[#0B756C] active:bg-[#085E57] focus:ring-[#0F9D91]/40 shadow-xs border border-transparent',
    danger:
      'bg-[#DC2626] text-white hover:bg-[#B91C1C] active:bg-[#991B1B] focus:ring-[#DC2626]/40 shadow-xs border border-transparent',
    ghost:
      'bg-transparent text-[#475569] hover:bg-[#F1F5F9] hover:text-[#1E293B] active:bg-[#E2E8F0] focus:ring-[#64748B]/20',
    outline:
      'bg-transparent text-[#0F9D91] border border-[#0F9D91] hover:bg-[#E6F7F5] active:bg-[#C9F0EC] focus:ring-[#0F9D91]/30',
  };

  const sizes = {
    xs: 'text-xs px-2.5 py-1.5 gap-1.5',
    sm: 'text-xs px-3 py-1.5 gap-1.5 font-medium',
    md: 'text-sm px-4 py-2 gap-2 font-medium',
    lg: 'text-base px-5 py-2.5 gap-2.5 font-semibold',
  };

  const iconSizes = {
    xs: 'w-3.5 h-3.5',
    sm: 'w-4 h-4',
    md: 'w-4 h-4',
    lg: 'w-5 h-5',
  };

  return (
    <button
      type={type}
      disabled={disabled || isLoading}
      className={`${baseStyles} ${variants[variant] || variants.primary} ${sizes[size] || sizes.md} ${
        fullWidth ? 'w-full' : ''
      } ${className}`}
      {...props}
    >
      {isLoading ? (
        <Loader2 className={`${iconSizes[size]} animate-spin text-current`} />
      ) : (
        LeftIcon && <LeftIcon className={iconSizes[size]} />
      )}
      <span>{children}</span>
      {!isLoading && RightIcon && <RightIcon className={iconSizes[size]} />}
    </button>
  );
}

