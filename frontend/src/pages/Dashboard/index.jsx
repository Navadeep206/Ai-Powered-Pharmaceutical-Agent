import React from 'react';
import { Link } from 'react-router-dom';
import PageHeader from '../../components/common/PageHeader';
import Button from '../../components/common/Button';
import StatusBadge from '../../components/common/StatusBadge';
import KpiCard from '../../components/dashboard/KpiCard';
import StatusDistribution from '../../components/dashboard/StatusDistribution';
import RecentInvestigations from '../../components/dashboard/RecentInvestigations';
import RecentActivity from '../../components/dashboard/RecentActivity';
import QuickActions from '../../components/dashboard/QuickActions';
import { PlusCircle, ListFilter, ShieldCheck } from 'lucide-react';
import { KPI_METRICS } from '../../utils/demoData';

/**
 * RootIQ Executive & Operational Quality Investigation Dashboard.
 */
export default function DashboardPage() {
  return (
    <div className="space-y-8">
      {/* 1. Dashboard Header */}
      <PageHeader
        title="Quality Investigation Overview"
        description="Monitor deviations, investigate root causes and manage corrective actions."
        badge={
          <StatusBadge variant="teal" size="sm">
            Plant Operational
          </StatusBadge>
        }
        actions={
          <div className="flex items-center gap-2.5">
            <Link to="/investigations">
              <Button variant="secondary" size="sm" leftIcon={ListFilter}>
                View All Investigations
              </Button>
            </Link>
            <Link to="/investigations/new">
              <Button variant="accent" size="sm" leftIcon={PlusCircle}>
                New Investigation
              </Button>
            </Link>
          </div>
        }
      />

      {/* 2. Five KPI Cards */}
      <section aria-labelledby="kpi-heading">
        <h2 id="kpi-heading" className="sr-only">Key Quality Indicators</h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
          {KPI_METRICS.map((kpi) => (
            <KpiCard
              key={kpi.id}
              title={kpi.title}
              value={kpi.value}
              label={kpi.label}
              indicator={kpi.indicator}
              indicatorType={kpi.indicatorType}
              iconName={kpi.iconName}
            />
          ))}
        </div>
      </section>

      {/* 3 & 5. Status Distribution & Recent Activity Stream */}
      <section className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2">
          <StatusDistribution />
        </div>
        <div className="lg:col-span-1">
          <RecentActivity />
        </div>
      </section>

      {/* 4. Recent Investigations Table */}
      <section>
        <RecentInvestigations />
      </section>

      {/* 6. Quick Actions */}
      <section className="space-y-3">
        <div className="flex items-center justify-between">
          <h3 className="text-sm font-semibold text-[#142B45] uppercase tracking-wider">
            Quality Team Shortcuts
          </h3>
          <span className="text-xs text-[#64748B]">Immediate workflows</span>
        </div>
        <QuickActions />
      </section>
    </div>
  );
}
