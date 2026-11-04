import React from 'react';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '../common/Card';
import StatusBadge from '../common/StatusBadge';
import { PieChart, Info } from 'lucide-react';
import { STATUS_DISTRIBUTION } from '../../utils/demoData';

/**
 * CSS-based Investigation Status Distribution Chart with proportional segments,
 * metrics breakdown, and legend.
 */
export default function StatusDistribution() {
  const totalCount = STATUS_DISTRIBUTION.reduce((acc, curr) => acc + curr.count, 0);

  return (
    <Card className="h-full flex flex-col">
      <CardHeader>
        <div>
          <CardTitle>Investigation Status Distribution</CardTitle>
          <CardDescription>
            Live allocation of active manufacturing deviations (Demonstration Pool: {totalCount})
          </CardDescription>
        </div>
        <StatusBadge variant="neutral" size="sm">
          Demonstration Data
        </StatusBadge>
      </CardHeader>

      <CardContent className="space-y-6 flex-1 flex flex-col justify-between">
        {/* Multi-Segment Proportional Progress Bar */}
        <div>
          <div className="flex items-center justify-between text-xs text-[#64748B] mb-2 font-medium">
            <span>Portfolio Breakdown</span>
            <span>100% Accounted</span>
          </div>

          <div className="h-4 w-full bg-[#F1F5F9] rounded-full overflow-hidden flex shadow-inner p-0.5 gap-0.5">
            {STATUS_DISTRIBUTION.map((item) => (
              <div
                key={item.status}
                style={{ width: `${item.percentage}%` }}
                className={`h-full rounded-sm transition-all duration-300 hover:opacity-90 relative group ${item.bgColor}`}
                title={`${item.status}: ${item.count} (${item.percentage}%)`}
              />
            ))}
          </div>
        </div>

        {/* Legend & Metrics Grid */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          {STATUS_DISTRIBUTION.map((item) => (
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

