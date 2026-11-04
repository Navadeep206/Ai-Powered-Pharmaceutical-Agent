import React from 'react';
import { LayoutDashboard, GitBranch, FolderOpen, CheckSquare } from 'lucide-react';

/**
 * Secondary tab bar navigation for Investigation Workspace.
 */
export default function InvestigationTabs({ activeTab, onTabChange }) {
  const tabs = [
    { id: 'overview', label: 'Incident Overview', icon: LayoutDashboard },
    { id: 'rca', label: 'RCA Analysis (5-Whys & 6M)', icon: GitBranch },
    { id: 'evidence', label: 'Evidence & Gaps', icon: FolderOpen },
    { id: 'capa', label: 'CAPA Management Plan', icon: CheckSquare },
  ];

  return (
    <div className="border-b border-[#E2E8F0] bg-white rounded-t-xl px-4 sm:px-6 shadow-2xs">
      <nav className="flex space-x-6 overflow-x-auto scrollbar-none" aria-label="Investigation tabs">
        {tabs.map((tab) => {
          const Icon = tab.icon;
          const isActive = activeTab === tab.id;

          return (
            <button
              key={tab.id}
              type="button"
              onClick={() => onTabChange(tab.id)}
              className={`py-3.5 px-1 border-b-2 font-medium text-xs sm:text-sm flex items-center space-x-2 whitespace-nowrap transition-colors duration-150 ${
                isActive
                  ? 'border-[#0F9D91] text-[#142B45] font-bold'
                  : 'border-transparent text-[#64748B] hover:text-[#142B45] hover:border-[#CBD5E1]'
              }`}
            >
              <Icon
                className={`w-4 h-4 ${
                  isActive ? 'text-[#0F9D91]' : 'text-[#94A3B8]'
                }`}
              />
              <span>{tab.label}</span>
            </button>
          );
        })}
      </nav>
    </div>
  );
}

