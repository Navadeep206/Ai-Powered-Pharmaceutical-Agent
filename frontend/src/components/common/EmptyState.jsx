import React from 'react';
import { FolderSearch } from 'lucide-react';

/**
 * Reusable EmptyState component for zero-data views.
 */
export default function EmptyState({
  icon: Icon = FolderSearch,
  title = 'No records found',
  description = 'There are no active items to display under the selected criteria.',
  action,
  className = '',
}) {
  return (
    <div
      className={`p-10 text-center flex flex-col items-center justify-center bg-white rounded-xl border border-dashed border-[#CBD5E1] ${className}`}
    >
      <div className="w-12 h-12 rounded-full bg-[#F1F5F9] text-[#64748B] flex items-center justify-center mb-3.5 shadow-2xs">
        <Icon className="w-6 h-6 text-[#142B45]" />
      </div>
      <h3 className="text-base font-semibold text-[#142B45]">{title}</h3>
      <p className="text-sm text-[#64748B] max-w-sm mt-1 mb-5 leading-normal">
        {description}
      </p>
      {action && <div>{action}</div>}
    </div>
  );
}

