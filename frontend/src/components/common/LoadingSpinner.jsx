import React from 'react';
import { Loader2 } from 'lucide-react';

export function LoadingSpinner({
  size = 'md',
  message = 'Loading...',
  className = '',
}) {
  const sizes = {
    sm: 'w-4 h-4',
    md: 'w-6 h-6',
    lg: 'w-8 h-8',
  };

  return (
    <div
      className={`flex flex-col items-center justify-center p-8 space-y-3 ${className}`}
    >
      <Loader2
        className={`${sizes[size] || sizes.md} animate-spin text-[#0F9D91]`}
      />
      {message && <p className="text-xs text-[#64748B] font-medium">{message}</p>}
    </div>
  );
}

export function Skeleton({ className = '', ...props }) {
  return (
    <div
      className={`animate-pulse bg-[#E2E8F0] rounded-md ${className}`}
      {...props}
    />
  );
}

export default LoadingSpinner;

