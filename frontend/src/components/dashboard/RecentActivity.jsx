import React from 'react';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '../common/Card';
import StatusBadge from '../common/StatusBadge';
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
      <CardHeader className="py-4 bg-[#F8FAFC]">
        <div className="flex items-center space-x-2.5">
          <div className="w-8 h-8 rounded-lg bg-[#E6F7F5] border border-[#A7F3D0] flex items-center justify-center text-[#0F9D91]">
            <History className="w-4 h-4" />
          </div>
          <div>
            <CardTitle className="text-sm">Recent Audit Activities</CardTitle>
            <CardDescription className="text-[11px]">21 CFR Part 11 contemporaneous audit trail</CardDescription>
          </div>
        </div>
        <StatusBadge variant="teal" size="sm">
          ALCOA+
        </StatusBadge>
      </CardHeader>

      <CardContent className="flex-1 overflow-y-auto p-4 sm:p-5">
        {loading ? (
          <div className="space-y-4 py-2">
            {[1, 2, 3, 4].map((i) => (
              <div key={i} className="animate-pulse flex items-start space-x-3">
                <div className="w-6 h-6 rounded-full bg-[#E2E8F0] shrink-0" />
                <div className="flex-1 space-y-1.5">
                  <div className="h-3 bg-[#E2E8F0] rounded w-3/4" />
                  <div className="h-2.5 bg-[#E2E8F0] rounded w-1/2" />
                </div>
              </div>
            ))}
          </div>
        ) : activities.length === 0 ? (
          <div className="py-8 text-center text-xs text-[#64748B]">
            <History className="w-8 h-8 text-[#94A3B8] mx-auto mb-2 opacity-50" />
            <p className="font-semibold text-[#142B45]">No Recent Audit Events</p>
            <p className="text-[11px] mt-0.5">Audit activities will populate as deviations are logged and investigated.</p>
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
