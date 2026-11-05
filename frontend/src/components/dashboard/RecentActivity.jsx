import React from 'react';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '../common/Card';
import StatusBadge from '../common/StatusBadge';
import LoadingSpinner from '../common/LoadingSpinner';
import EmptyState from '../common/EmptyState';
import {
  PlusCircle,
  GitBranch,
  CheckSquare,
  FileCheck,
  FileText,
  Clock,
  History,
} from 'lucide-react';

const ICON_MAP = {
  PlusCircle,
  GitBranch,
  CheckSquare,
  FileCheck,
  FileText,
  History,
};

/**
 * Recent Activity stream displaying real GxP audit & investigation updates
 * fetched from the PostgreSQL investigation_activities table.
 */
export default function RecentActivity({ activities = [], loading = false }) {
  return (
    <Card className="h-full flex flex-col">
      <CardHeader>
        <div className="flex items-center space-x-2">
          <History className="w-4 h-4 text-[#0F9D91]" />
          <div>
            <CardTitle>Recent Activity Stream</CardTitle>
            <CardDescription>21 CFR Part 11 contemporaneous audit trail</CardDescription>
          </div>
        </div>
        <StatusBadge variant="teal" size="sm">
          Audit Trail
        </StatusBadge>
      </CardHeader>

      <CardContent className="flex-1 overflow-y-auto">
        {loading ? (
          <div className="py-12 flex flex-col items-center justify-center">
            <LoadingSpinner size="md" />
            <p className="text-xs text-[#64748B] mt-2 font-medium">Loading audit events...</p>
          </div>
        ) : activities.length === 0 ? (
          <div className="py-6">
            <EmptyState
              title="No recent activities"
              description="No audit events have been logged in the system yet."
            />
          </div>
        ) : (
          <ol className="relative border-l border-[#E2E8F0] ml-3.5 space-y-4 my-1">
            {activities.map((act) => {
              const Icon = ICON_MAP[act.iconName] || History;

              return (
                <li key={act.id} className="ml-5">
                  <span
                    className={`absolute -left-3 flex items-center justify-center w-6 h-6 rounded-full border border-white ring-2 ring-[#E2E8F0] ${act.iconBg || 'bg-[#142B45]/10'}`}
                  >
                    <Icon className={`w-3.5 h-3.5 ${act.iconColor || 'text-[#142B45]'}`} />
                  </span>

                  <div className="flex flex-col">
                    <p className="text-xs font-semibold text-[#142B45] leading-snug">
                      {act.description}
                    </p>
                    <span className="text-[11px] text-[#64748B] mt-0.5">
                      {act.detail}
                    </span>
                    <div className="flex items-center space-x-1 text-[10px] text-[#94A3B8] mt-1 font-mono">
                      <Clock className="w-3 h-3 text-[#CBD5E1]" />
                      <span>{act.time}</span>
                    </div>
                  </div>
                </li>
              );
            })}
          </ol>
        )}
      </CardContent>
    </Card>
  );
}
