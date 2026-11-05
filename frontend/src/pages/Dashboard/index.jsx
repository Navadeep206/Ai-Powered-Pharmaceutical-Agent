import React, { useEffect, useCallback } from 'react';
import { Link } from 'react-router-dom';
import { useSelector, useDispatch } from 'react-redux';
import PageHeader from '../../components/common/PageHeader';
import Button from '../../components/common/Button';
import StatusBadge from '../../components/common/StatusBadge';
import KpiCard from '../../components/dashboard/KpiCard';
import StatusDistribution from '../../components/dashboard/StatusDistribution';
import RecentInvestigations from '../../components/dashboard/RecentInvestigations';
import RecentActivity from '../../components/dashboard/RecentActivity';
import PendingCapaSummary from '../../components/dashboard/PendingCapaSummary';
import QuickActions from '../../components/dashboard/QuickActions';
import {
  fetchDashboardSummary,
  fetchDashboardActivities,
} from '../../redux/slices/dashboardSlice';
import { fetchInvestigations } from '../../redux/slices/investigationSlice';
import { PlusCircle, ListFilter, AlertCircle, RotateCcw } from 'lucide-react';

/**
 * RootIQ Executive & Operational Quality Investigation Dashboard.
 * Connected directly to the FastAPI backend and PostgreSQL database.
 */
export default function DashboardPage() {
  const dispatch = useDispatch();

  const {
    summary,
    summaryLoading,
    summaryError,
    activities,
    activitiesLoading,
    activitiesError,
  } = useSelector((state) => state.dashboard);

  const {
    investigations,
    listLoading,
    listError,
  } = useSelector((state) => state.investigations);

  const loadDashboardData = useCallback(() => {
    dispatch(fetchDashboardSummary());
    dispatch(fetchDashboardActivities(10));
    dispatch(fetchInvestigations({ limit: 6 }));
  }, [dispatch]);

  useEffect(() => {
    loadDashboardData();
  }, [loadDashboardData]);

  const activeError = summaryError || listError || activitiesError;

  return (
    <div className="space-y-8">
      {/* 1. Dashboard Header */}
      <PageHeader
        title="Quality Investigation Overview"
        description="Monitor manufacturing deviations, investigate systemic root causes, and govern corrective actions under ICH Q9/Q10."
        badge={
          <StatusBadge variant={activeError ? 'danger' : 'teal'} size="sm">
            {activeError ? 'Connection Issue' : 'Database Active'}
          </StatusBadge>
        }
        actions={
          <div className="flex items-center gap-2.5">
            <Link to="/investigations">
              <Button variant="secondary" size="sm" leftIcon={ListFilter}>
                Deviation Registry
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

      {/* Error Banner with Retry */}
      {activeError && (
        <div className="p-4 rounded-xl border border-[#FECACA] bg-[#FEF2F2] flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 text-sm text-[#991B1B]">
          <div className="flex items-center space-x-2.5">
            <AlertCircle className="w-5 h-5 shrink-0 text-[#DC2626]" />
            <div>
              <p className="font-semibold">Backend Connection Issue</p>
              <p className="text-xs text-[#B91C1C] mt-0.5">{activeError}</p>
            </div>
          </div>
          <Button
            variant="secondary"
            size="sm"
            leftIcon={RotateCcw}
            onClick={loadDashboardData}
            className="shrink-0 bg-white border-[#FCA5A5] hover:bg-[#FEE2E2]"
          >
            Retry Connection
          </Button>
        </div>
      )}

      {/* 2. Five KPI Cards */}
      <section aria-labelledby="kpi-heading">
        <h2 id="kpi-heading" className="sr-only">Key Quality Indicators</h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
          <KpiCard
            title="Total Investigations"
            value={summaryLoading ? '—' : (summary?.total_investigations ?? 0)}
            label="Quality registry log"
            indicator="Scope"
            indicatorType="neutral"
            iconName="FolderKanban"
          />
          <KpiCard
            title="Open Investigations"
            value={summaryLoading ? '—' : (summary?.open_investigations ?? 0)}
            label="Initial triage needed"
            indicator="Action"
            indicatorType="warning"
            iconName="AlertCircle"
          />
          <KpiCard
            title="Under Investigation"
            value={summaryLoading ? '—' : (summary?.investigations_under_investigation ?? 0)}
            label="RCA causal tree"
            indicator="In Progress"
            indicatorType="teal"
            iconName="Activity"
          />
          <KpiCard
            title="Pending CAPA"
            value={summaryLoading ? '—' : (summary?.investigations_pending_capa ?? 0)}
            label="Action formulation"
            indicator="Required"
            indicatorType="danger"
            iconName="ShieldAlert"
          />
          <KpiCard
            title="Completed Investigations"
            value={summaryLoading ? '—' : (summary?.completed_investigations ?? 0)}
            label="Verified & closed"
            indicator="SLA Compliant"
            indicatorType="success"
            iconName="CheckCircle2"
          />
        </div>
      </section>

      {/* 3. Distribution & Pending CAPA Review Queue */}
      <section className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div>
          <StatusDistribution summary={summary} />
        </div>
        <div>
          <PendingCapaSummary />
        </div>
      </section>

      {/* 4. Recent Investigations & Activity Stream */}
      <section className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2">
          <RecentInvestigations
            investigations={investigations}
            loading={listLoading}
            totalCount={summary?.total_investigations}
          />
        </div>
        <div className="lg:col-span-1">
          <RecentActivity activities={activities} loading={activitiesLoading} />
        </div>
      </section>

      {/* 5. Quick Actions */}
      <section className="space-y-3">
        <div className="flex items-center justify-between">
          <h3 className="text-sm font-bold text-[#142B45] uppercase tracking-wider">
            Quality Team Shortcuts
          </h3>
          <span className="text-xs text-[#64748B]">Immediate investigation workflows</span>
        </div>
        <QuickActions />
      </section>
    </div>
  );
}
