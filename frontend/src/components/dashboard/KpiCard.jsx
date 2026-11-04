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
    <Card hover className="relative overflow-hidden">
      <CardContent className="p-5">
        <div className="flex items-start justify-between">
          <div>
            <p className="text-xs font-semibold text-[#64748B] uppercase tracking-wider">
              {title}
            </p>
            <h3 className="text-3xl font-bold text-[#142B45] tracking-tight mt-1.5">
              {value}
            </h3>
          </div>
          <div className="w-10 h-10 rounded-xl bg-[#F8FAFC] border border-[#E2E8F0] flex items-center justify-center text-[#142B45] shadow-2xs">
            <IconComponent className="w-5 h-5 text-[#0F9D91]" />
          </div>
        </div>

        <div className="mt-3.5 flex items-center justify-between text-xs">
          <span className="text-[#64748B] font-normal truncate mr-2">{label}</span>
          {indicator && (
            <span
              className={`text-[10px] font-semibold px-2 py-0.5 rounded-full border shrink-0 ${
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

