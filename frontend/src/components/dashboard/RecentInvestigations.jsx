import React from 'react';
import { Link } from 'react-router-dom';
import { Card, CardHeader, CardTitle, CardDescription, CardContent, CardFooter } from '../common/Card';
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell } from '../common/Table';
import StatusBadge from '../common/StatusBadge';
import Button from '../common/Button';
import EmptyState from '../common/EmptyState';
import { ArrowRight, ExternalLink, AlertTriangle } from 'lucide-react';
import { DEMO_INVESTIGATIONS } from '../../utils/demoData';

const SEVERITY_BADGE_MAP = {
  Critical: 'danger',
  High: 'warning',
  Medium: 'info',
  Low: 'neutral',
};

const STATUS_BADGE_MAP = {
  Open: 'warning',
  'Under Investigation': 'teal',
  'Pending Review': 'info',
  Closed: 'success',
};

/**
 * Recent Investigations Table component displaying the latest 5 deviation records.
 */
export default function RecentInvestigations() {
  const recentRecords = DEMO_INVESTIGATIONS.slice(0, 5);

  return (
    <Card>
      <CardHeader>
        <div>
          <CardTitle>Recent Manufacturing Deviations</CardTitle>
          <CardDescription>
            Contemporaneous investigation log across production suites & analytical testing
          </CardDescription>
        </div>
        <Link to="/investigations">
          <Button variant="secondary" size="xs" rightIcon={ArrowRight}>
            View All ({DEMO_INVESTIGATIONS.length})
          </Button>
        </Link>
      </CardHeader>

      <CardContent noPadding>
        {recentRecords.length === 0 ? (
          <EmptyState
            title="No recent investigations"
            description="All manufacturing deviations have been resolved or archived."
            action={
              <Link to="/investigations/new">
                <Button variant="primary" size="sm">
                  Create New Investigation
                </Button>
              </Link>
            }
          />
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm text-[#334155]">
              <thead className="bg-[#F8FAFC] border-b border-[#E2E8F0] text-xs font-semibold text-[#64748B] uppercase tracking-wider">
                <tr>
                  <th className="px-5 py-3">Investigation ID</th>
                  <th className="px-5 py-3">Incident Title</th>
                  <th className="px-5 py-3">Department</th>
                  <th className="px-5 py-3">Severity</th>
                  <th className="px-5 py-3">Status</th>
                  <th className="px-5 py-3">Date</th>
                  <th className="px-5 py-3 text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#F1F5F9] bg-white">
                {recentRecords.map((inv) => (
                  <tr
                    key={inv.id}
                    className="hover:bg-[#F8FAFC] transition-colors duration-150"
                  >
                    <td className="px-5 py-3.5 font-mono text-xs font-bold text-[#142B45]">
                      <span className="bg-[#F1F5F9] px-2 py-0.5 rounded border border-[#E2E8F0]">
                        {inv.id}
                      </span>
                    </td>
                    <td className="px-5 py-3.5 max-w-xs">
                      <div className="font-medium text-[#142B45] truncate" title={inv.title}>
                        {inv.title}
                      </div>
                      <div className="text-xs text-[#64748B]">Batch: {inv.batch}</div>
                    </td>
                    <td className="px-5 py-3.5 text-xs text-[#475569]">
                      {inv.department}
                    </td>
                    <td className="px-5 py-3.5">
                      <StatusBadge
                        variant={SEVERITY_BADGE_MAP[inv.severity] || 'neutral'}
                        size="sm"
                      >
                        {inv.severity}
                      </StatusBadge>
                    </td>
                    <td className="px-5 py-3.5">
                      <StatusBadge
                        variant={STATUS_BADGE_MAP[inv.status] || 'neutral'}
                        size="sm"
                      >
                        {inv.status}
                      </StatusBadge>
                    </td>
                    <td className="px-5 py-3.5 text-xs text-[#64748B] font-mono whitespace-nowrap">
                      {inv.date}
                    </td>
                    <td className="px-5 py-3.5 text-right whitespace-nowrap">
                      <Link to={`/investigations/${inv.id}`}>
                        <Button variant="ghost" size="xs" rightIcon={ExternalLink}>
                          View Details
                        </Button>
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </CardContent>

      <CardFooter>
        <span className="text-xs text-[#64748B]">
          Showing 5 most recent records &bull; Demonstration Dataset
        </span>
        <Link
          to="/investigations"
          className="text-xs font-semibold text-[#0F9D91] hover:text-[#0A736A] inline-flex items-center"
        >
          Explore Full Registry <ArrowRight className="w-3.5 h-3.5 ml-1" />
        </Link>
      </CardFooter>
    </Card>
  );
}

