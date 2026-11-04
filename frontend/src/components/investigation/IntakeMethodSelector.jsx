import React from 'react';
import { FileUp, AlignLeft, Mail } from 'lucide-react';

/**
 * Switcher component for incident intake options.
 */
export default function IntakeMethodSelector({ selectedMethod, onSelectMethod }) {
  const methods = [
    {
      id: 'upload',
      label: 'Upload Document',
      description: 'PDF batch record or deviation log',
      icon: FileUp,
    },
    {
      id: 'text',
      label: 'Paste Description',
      description: 'Raw narrative or operator statement',
      icon: AlignLeft,
    },
    {
      id: 'email',
      label: 'Email Input',
      description: 'Supervisor alert or shift email',
      icon: Mail,
    },
  ];

  return (
    <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
      {methods.map((method) => {
        const Icon = method.icon;
        const isSelected = selectedMethod === method.id;

        return (
          <button
            key={method.id}
            type="button"
            onClick={() => onSelectMethod(method.id)}
            className={`flex items-start p-4 rounded-xl border text-left transition-all duration-150 select-none ${
              isSelected
                ? 'bg-[#E6F7F5] border-[#0F9D91] shadow-xs ring-1 ring-[#0F9D91]'
                : 'bg-white border-[#E2E8F0] hover:border-[#CBD5E1] hover:bg-[#F8FAFC]'
            }`}
          >
            <div
              className={`w-9 h-9 rounded-lg flex items-center justify-center mr-3 shrink-0 ${
                isSelected
                  ? 'bg-[#0F9D91] text-white shadow-2xs'
                  : 'bg-[#F1F5F9] text-[#64748B]'
              }`}
            >
              <Icon className="w-5 h-5" />
            </div>

            <div>
              <div
                className={`text-sm font-semibold ${
                  isSelected ? 'text-[#142B45]' : 'text-[#334155]'
                }`}
              >
                {method.label}
              </div>
              <div className="text-xs text-[#64748B] mt-0.5 leading-snug">
                {method.description}
              </div>
            </div>
          </button>
        );
      })}
    </div>
  );
}

