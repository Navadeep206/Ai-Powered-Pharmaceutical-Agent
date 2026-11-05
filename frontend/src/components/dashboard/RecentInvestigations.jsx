import React from 'react';
import { Link } from 'react-router-dom';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '../common/Card';
import StatusBadge from '../common/StatusBadge';
import Button from '../common/Button';
import EmptyState from '../common/EmptyState';
import LoadingSpinner from '../common/LoadingSpinner';
import { ArrowRight, ExternalLink } from 'lucide-react';
import { SEVERITY_BADGE_MAP, STATUS_BADGE_MAP } from '../../utils/normalizers';

/**
 * Recent Investigations Table component displaying the latest deviation records
 * fetched directly from the PostgreSQL backend API.
 */
export default function RecentInvestigations({ investigations = [], loading = false, totalCount = 0 }) {
  const recentRecords = (investigations || []).slice(0, 5);

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
            View All ({totalCount || investigations.length})
          </Button>
        </Link>
      </CardHeader>

      <CardContent noPadding>
        {loading ? (
          <div className="py-12 flex flex-col items-center justify-center">
            <LoadingSpinner size="md" />
            <p className="text-xs text-[#64748B] mt-2 font-medium">Loading recent investigations from database...</p>
          </div>
        ) : recentRecords.length === 0 ? (
          <div className="py-8">
            <EmptyState
              title="No recent investigations"
              description="No deviation investigations are currently recorded in the PostgreSQL database."
              action={
                <Link to="/investigations/new">
                  <Button variant="primary" size="sm">
                    Create New Investigation
                  </Button>
                </Link>
              }
            />
          </div>
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
                {recentRecords.map((inv, idx) => {
                  const invId = inv.id || inv.investigation_id || inv.investigation_number || `INV-${idx}`;
                  const invTitle = inv.title || inv.incident_title || 'Untitled Deviation';
                  const invBatch = inv.batch || inv.batch_number || 'N/A';
                  const invDept = inv.department || 'General';
                  const invSev = inv.severity || 'Medium';
                  const invStat = inv.status || inv.investigation_status || 'Open';
                  const invDate = inv.date || (inv.created_at ? String(inv.created_at).split('T')[0] : 'N/A');

                  return (
                    <tr
                      key={invId}
                      className="hover:bg-[#F8FAFC] transition-colors duration-150"
                    >
                      <td className="px-5 py-3.5 font-mono text-xs font-bold text-[#142B45]">
                        <span className="bg-[#F1F5F9] px-2 py-0.5 rounded border border-[#E2E8F0]">
                          {invId}
                        </span>
                      </td>
                      <td className="px-5 py-3.5 max-w-xs">
                        <div className="font-medium text-[#142B45] truncate" title={invTitle}>
                          {invTitle}
                        </div>
                        <div className="text-xs text-[#64748B]">Batch: {invBatch}</div>
                      </td>
                      <td className="px-5 py-3.5 text-xs text-[#475569]">
                        {invDept}
                      </td>
                      <td className="px-5 py-3.5">
                        <StatusBadge
                          variant={SEVERITY_BADGE_MAP[invSev] || 'neutral'}
                          size="sm"
                        >
                          {invSev}
                        </StatusBadge>
                      </td>
                      <td className="px-5 py-3.5">
                        <StatusBadge
                          variant={STATUS_BADGE_MAP[invStat] || 'neutral'}
                          size="sm"
                        >
                          {invStat}
                        </StatusBadge>
                      </td>
                      <td className="px-5 py-3.5 text-xs text-[#64748B] whitespace-nowrap">
                        {invDate}
                      </td>
                      <td className="px-5 py-3.5 text-right whitespace-nowrap">
                        <Link to={`/investigations/${encodeURIComponent(invId)}`}>
                          <Button variant="ghost" size="xs" rightIcon={ExternalLink}>
                            Open
                          </Button>
                        </Link>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
