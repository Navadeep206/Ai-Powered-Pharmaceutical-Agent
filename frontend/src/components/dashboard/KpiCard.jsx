import React from 'react';
import {
  FolderKanban,
  AlertCircle,
  Activity,
  ShieldAlert,
  CheckCircle2,
  TrendingUp,
} from 'lucide-react';
import { Card, CardContent } from '../common/Card';

const ICON_MAP = {
  FolderKanban,
  AlertCircle,
  Activity,
  ShieldAlert,
  CheckCircle2,
};

const INDICATOR_STYLES = {
  neutral: 'bg-[#F1F5F9] text-[#475569] border-[#E2E8F0]',
  warning: 'bg-[#FFFBEB] text-[#92400E] border-[#FDE68A]',
  teal: 'bg-[#E6F7F5] text-[#0A736A] border-[#A2E6DF]',
  danger: 'bg-[#FEF2F2] text-[#991B1B] border-[#FECACA]',
  success: 'bg-[#ECFDF5] text-[#065F46] border-[#A7F3D0]',
};

/**
 * Enterprise KPI Card displaying metric, icon, supporting label, and subtle status badge.
 */
export default function KpiCard({
  title,
  value,
  label,
  indicator,
  indicatorType = 'neutral',
  iconName = 'FolderKanban',
}) {
  const IconComponent = ICON_MAP[iconName] || FolderKanban;

  return (
    <Card hover className="relative overflow-hidden flex flex-col justify-between">
      <CardContent className="p-4 sm:p-5 flex-1 flex flex-col justify-between">
        <div className="flex items-start justify-between gap-2">
          <div className="min-w-0">
            <p className="text-[11px] font-bold text-[#64748B] uppercase tracking-wider truncate">
              {title}
            </p>
            <h3 className="text-2xl sm:text-3xl font-extrabold text-[#142B45] tracking-tight mt-1">
              {value}
            </h3>
          </div>
          <div className="w-9 h-9 sm:w-10 sm:h-10 rounded-xl bg-[#F8FAFC] border border-[#E2E8F0] flex items-center justify-center text-[#142B45] shadow-2xs shrink-0">
            <IconComponent className="w-4 h-4 sm:w-5 sm:h-5 text-[#0F9D91]" />
          </div>
        </div>

        <div className="mt-3 pt-2.5 border-t border-[#F8FAFC] flex flex-wrap items-center justify-between gap-1 text-[11px]">
          <span className="text-[#64748B] font-medium leading-tight">
            {label}
          </span>
          {indicator && (
            <span
              className={`text-[9px] font-semibold px-1.5 py-0.5 rounded-full border shrink-0 ${
                INDICATOR_STYLES[indicatorType] || INDICATOR_STYLES.neutral
              }`}
            >
              {indicator}
            </span>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
