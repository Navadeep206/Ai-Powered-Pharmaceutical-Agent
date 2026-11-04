import React from 'react';
import { Link } from 'react-router-dom';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '../common/Card';
import { PlusCircle, Search, CheckSquare, ArrowRight, Zap } from 'lucide-react';

/**
 * Quick Action shortcuts for common Quality Team tasks.
 */
export default function QuickActions() {
  const actions = [
    {
      title: 'Create New Investigation',
      description: 'Record an unexpected deviation, OOS excursion, or equipment anomaly.',
      to: '/investigations/new',
      icon: PlusCircle,
      accentColor: 'text-[#0F9D91]',
      hoverBg: 'hover:border-[#0F9D91]/40',
      badge: 'New Event',
    },
    {
      title: 'Browse Investigations',
      description: 'Filter, review, and analyze ongoing 6M causal trees and batch logs.',
      to: '/investigations',
      icon: Search,
      accentColor: 'text-[#142B45]',
      hoverBg: 'hover:border-[#142B45]/40',
      badge: 'Master Log',
    },
    {
      title: 'Manage CAPA Tasks',
      description: 'Track corrective actions, assignees, milestones, and effectiveness reviews.',
      to: '/capa',
      icon: CheckSquare,
      accentColor: 'text-[#059669]',
      hoverBg: 'hover:border-[#059669]/40',
      badge: 'ICH Q10',
    },
  ];

  return (
    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
      {actions.map((act) => {
        const Icon = act.icon;
        return (
          <Link
            key={act.title}
            to={act.to}
            className={`block group bg-white p-5 rounded-xl border border-[#E2E8F0] shadow-2xs ${act.hoverBg} hover:shadow-md transition-all duration-200`}
          >
            <div className="flex items-start justify-between">
              <div className="w-10 h-10 rounded-xl bg-[#F8FAFC] border border-[#E2E8F0] flex items-center justify-center group-hover:scale-105 transition-transform">
                <Icon className={`w-5 h-5 ${act.accentColor}`} />
              </div>
              <span className="text-[10px] font-semibold font-mono uppercase px-2 py-0.5 rounded bg-[#F1F5F9] text-[#64748B]">
                {act.badge}
              </span>
            </div>

            <h4 className="text-sm font-semibold text-[#142B45] group-hover:text-[#0F9D91] transition-colors mt-3">
              {act.title}
            </h4>
            <p className="text-xs text-[#64748B] mt-1 leading-relaxed">
              {act.description}
            </p>

            <div className="mt-4 flex items-center text-xs font-semibold text-[#0F9D91] group-hover:translate-x-0.5 transition-transform">
              <span>Execute Action</span>
              <ArrowRight className="w-3.5 h-3.5 ml-1" />
            </div>
          </Link>
        );
      })}
    </div>
  );
}

