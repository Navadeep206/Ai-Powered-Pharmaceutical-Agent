import React from 'react';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '../common/Card';
import StatusBadge from '../common/StatusBadge';
import { Info } from 'lucide-react';

/**
 * CSS-based Investigation Status Distribution Chart with proportional segments,
 * metrics breakdown, and legend derived from PostgreSQL database summary.
 */
export default function StatusDistribution({ summary }) {
  const openCount = summary?.open_investigations || 0;
  const underInvCount = summary?.investigations_under_investigation || 0;
  const pendingCapaCount = summary?.investigations_pending_capa || 0;
  const completedCount = summary?.completed_investigations || 0;
  const totalCount = summary?.total_investigations || (openCount + underInvCount + pendingCapaCount + completedCount);

  const calculatePct = (count) => {
    if (!totalCount || totalCount <= 0) return 0;
    return Math.round((count / totalCount) * 100);
  };

  const distribution = [
    {
      status: 'Under Investigation',
      count: underInvCount,
      percentage: calculatePct(underInvCount),
      color: '#0F9D91',
      bgColor: 'bg-[#0F9D91]',
    },
    {
      status: 'Open',
      count: openCount,
      percentage: calculatePct(openCount),
      color: '#D97706',
      bgColor: 'bg-[#D97706]',
    },
    {
      status: 'Pending Review',
      count: pendingCapaCount,
      percentage: calculatePct(pendingCapaCount),
      color: '#2563EB',
      bgColor: 'bg-[#2563EB]',
    },
    {
      status: 'Closed',
      count: completedCount,
      percentage: calculatePct(completedCount),
      color: '#059669',
      bgColor: 'bg-[#059669]',
    },
  ];

  return (
    <Card className="h-full flex flex-col">
      <CardHeader>
        <div>
          <CardTitle>Investigation Status Distribution</CardTitle>
          <CardDescription>
            Live allocation of manufacturing deviations ({totalCount} Total Recorded)
          </CardDescription>
        </div>
        <StatusBadge variant="teal" size="sm">
          Live Database Metrics
        </StatusBadge>
      </CardHeader>

      <CardContent className="space-y-6 flex-1 flex flex-col justify-between">
        {/* Multi-Segment Proportional Progress Bar */}
        <div>
          <div className="flex items-center justify-between text-xs text-[#64748B] mb-2 font-medium">
            <span>Portfolio Breakdown</span>
            <span>{totalCount > 0 ? '100% Accounted' : '0 Records'}</span>
          </div>

          <div className="h-4 w-full bg-[#F1F5F9] rounded-full overflow-hidden flex shadow-inner p-0.5 gap-0.5">
            {totalCount > 0 ? (
              distribution.map((item) => (
                <div
                  key={item.status}
                  style={{ width: `${item.percentage}%` }}
                  className={`h-full rounded-sm transition-all duration-300 hover:opacity-90 relative group ${item.bgColor}`}
                  title={`${item.status}: ${item.count} (${item.percentage}%)`}
                />
              ))
            ) : (
              <div className="h-full w-full bg-[#E2E8F0] rounded-sm text-center text-[10px] text-[#94A3B8] flex items-center justify-center">
                No active records
              </div>
            )}
          </div>
        </div>

        {/* Legend & Metrics Grid */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          {distribution.map((item) => (
            <div
              key={item.status}
              className="p-3 rounded-lg border border-[#E2E8F0] bg-[#F8FAFC] flex flex-col justify-between"
            >
              <div className="flex items-center space-x-1.5 mb-1.5">
                <span
                  className="w-2.5 h-2.5 rounded-full shrink-0"
                  style={{ backgroundColor: item.color }}
                />
                <span className="text-xs font-semibold text-[#142B45] truncate">
                  {item.status}
                </span>
              </div>
              <div className="flex items-baseline justify-between mt-1">
                <span className="text-xl font-bold text-[#142B45]">{item.count}</span>
                <span className="text-xs font-medium text-[#64748B]">
                  {item.percentage}%
                </span>
              </div>
            </div>
          ))}
        </div>

        {/* Informational Guidance */}
        <div className="p-3 bg-[#EFF6FF] border border-[#BFDBFE] rounded-lg flex items-start space-x-2 text-xs text-[#1E40AF]">
          <Info className="w-4 h-4 text-[#2563EB] mt-0.5 shrink-0" />
          <p className="leading-relaxed">
            <span className="font-semibold">Workflow Target:</span> Active investigations must progress from Open to RCA within 5 business days per GxP deviation SLA.
          </p>
        </div>
      </CardContent>
    </Card>
  );
}
