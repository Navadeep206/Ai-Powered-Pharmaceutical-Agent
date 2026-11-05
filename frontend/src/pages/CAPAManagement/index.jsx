import React, { useState, useEffect, useCallback } from 'react';
import { Link } from 'react-router-dom';
import PageHeader from '../../components/common/PageHeader';
import Button from '../../components/common/Button';
import StatusBadge from '../../components/common/StatusBadge';
import Input from '../../components/common/Input';
import Select from '../../components/common/Select';
import EmptyState from '../../components/common/EmptyState';
import LoadingSpinner from '../../components/common/LoadingSpinner';
import { Card, CardContent } from '../../components/common/Card';
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell } from '../../components/common/Table';
import capaService from '../../services/capaService';
import {
  CheckSquare,
  Clock,
  ExternalLink,
  RotateCcw,
  Search,
  Filter,
  ShieldCheck,
  AlertCircle,
  User,
} from 'lucide-react';

const STATUS_VARIANTS = {
  Proposed: 'neutral',
  'Pending Review': 'warning',
  Approved: 'teal',
  'In Progress': 'info',
  Completed: 'success',
  Closed: 'success',
  Rejected: 'danger',
  Draft: 'neutral',
};

/**
 * Enterprise GxP CAPA Management Page.
 * Displays live, persistent corrective and preventive action items across manufacturing deviations.
 */
export default function CAPAManagementPage() {
  const [capas, setCapas] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [statusFilter, setStatusFilter] = useState('ALL');

  const loadCapas = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const params = {};
      if (statusFilter !== 'ALL') {
        params.status = statusFilter;
      }
      if (searchTerm.trim()) {
        params.search = searchTerm.trim();
      }
      const data = await capaService.listAllCAPA(params);
      setCapas(data || []);
    } catch (err) {
      setError(err.message || 'Failed to retrieve CAPA records from the quality database.');
    } finally {
      setLoading(false);
    }
  }, [statusFilter, searchTerm]);

  useEffect(() => {
    loadCapas();
  }, [loadCapas]);

  // Aggregate Metrics
  const totalCount = capas.length;
  const inProgressCount = capas.filter(
    (c) => (c.status || '').toLowerCase() === 'in progress'
  ).length;
  const pendingReviewCount = capas.filter((c) =>
    ['pending review', 'proposed'].includes((c.status || '').toLowerCase())
  ).length;
  const completedCount = capas.filter((c) =>
    ['completed', 'closed'].includes((c.status || '').toLowerCase())
  ).length;

  return (
    <div className="space-y-6">
      <PageHeader
        title="CAPA Management Portfolio"
        description="Enterprise tracking of corrective and preventive actions, assigned leads, verification protocols, and lifecycle progression (ICH Q10)."
        breadcrumbs={[
          { label: 'RootIQ', to: '/' },
          { label: 'CAPA Management' },
        ]}
        badge={
          <StatusBadge variant={error ? 'danger' : 'teal'}>
            {loading ? 'Querying...' : `${totalCount} Action Items`}
          </StatusBadge>
        }
        actions={
          <Link to="/investigations">
            <Button variant="secondary" size="sm" leftIcon={ExternalLink}>
              View Investigations
            </Button>
          </Link>
        }
      />

      {/* KPI Metric Strip */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        <Card className="p-4 border border-[#E2E8F0]">
          <span className="text-xs font-semibold text-[#64748B] uppercase tracking-wider block">
            Total CAPAs
          </span>
          <span className="text-2xl font-bold text-[#142B45] mt-1 block">
            {totalCount}
          </span>
        </Card>
        <Card className="p-4 border border-[#E2E8F0]">
          <span className="text-xs font-semibold text-[#D97706] uppercase tracking-wider block">
            Pending QA Review
          </span>
          <span className="text-2xl font-bold text-[#D97706] mt-1 block">
            {pendingReviewCount}
          </span>
        </Card>
        <Card className="p-4 border border-[#E2E8F0]">
          <span className="text-xs font-semibold text-[#2563EB] uppercase tracking-wider block">
            In Progress
          </span>
          <span className="text-2xl font-bold text-[#2563EB] mt-1 block">
            {inProgressCount}
          </span>
        </Card>
        <Card className="p-4 border border-[#E2E8F0]">
          <span className="text-xs font-semibold text-[#059669] uppercase tracking-wider block">
            Completed & Closed
          </span>
          <span className="text-2xl font-bold text-[#059669] mt-1 block">
            {completedCount}
          </span>
        </Card>
      </div>

      {/* Filter and Search Bar */}
      <Card>
        <CardContent className="p-4">
          <div className="flex flex-col sm:flex-row items-center gap-3">
            <div className="w-full sm:flex-1">
              <Input
                placeholder="Search by action description, owner, or protocol..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                leftIcon={Search}
              />
            </div>
            <div className="w-full sm:w-56">
              <Select
                value={statusFilter}
                onChange={(e) => setStatusFilter(e.target.value)}
                options={[
                  { value: 'ALL', label: 'All Lifecycle States' },
                  { value: 'Proposed', label: 'Proposed' },
                  { value: 'Pending Review', label: 'Pending Review' },
                  { value: 'Approved', label: 'Approved' },
                  { value: 'In Progress', label: 'In Progress' },
                  { value: 'Completed', label: 'Completed' },
                  { value: 'Closed', label: 'Closed' },
                  { value: 'Rejected', label: 'Rejected' },
                ]}
              />
            </div>
            {(searchTerm || statusFilter !== 'ALL') && (
              <Button
                variant="ghost"
                size="sm"
                leftIcon={RotateCcw}
                onClick={() => {
                  setSearchTerm('');
                  setStatusFilter('ALL');
                }}
              >
                Reset
              </Button>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Error Banner with Retry */}
      {error && (
        <div className="p-4 rounded-xl border border-[#FECACA] bg-[#FEF2F2] flex items-center justify-between text-sm text-[#991B1B]">
          <div className="flex items-center space-x-2">
            <AlertCircle className="w-5 h-5 text-[#DC2626] shrink-0" />
            <span>{error}</span>
          </div>
          <Button variant="secondary" size="xs" leftIcon={RotateCcw} onClick={loadCapas}>
            Retry
          </Button>
        </div>
      )}

      {/* Main Table or Empty State */}
      {loading ? (
        <div className="py-16 flex flex-col items-center justify-center space-y-2">
          <LoadingSpinner size="lg" />
          <p className="text-xs text-[#64748B]">Querying CAPA action records from PostgreSQL database...</p>
        </div>
      ) : capas.length === 0 ? (
        <EmptyState
          title="No CAPA Records Found"
          description={
            searchTerm || statusFilter !== 'ALL'
              ? 'No corrective actions match the selected filter criteria.'
              : 'No CAPA actions have been logged yet. Open an investigation to generate AI-assisted recommendations or propose actions.'
          }
          action={
            <Link to="/investigations">
              <Button variant="primary" size="sm" leftIcon={ExternalLink}>
                Go to Investigations Registry
              </Button>
            </Link>
          }
        />
      ) : (
        <Table>
          <TableHeader>
            <TableRow hover={false}>
              <TableHead>CAPA ID</TableHead>
              <TableHead>Remediation Target / Plan</TableHead>
              <TableHead>Classification</TableHead>
              <TableHead>Linked Investigation</TableHead>
              <TableHead>Owner</TableHead>
              <TableHead>Target Due Date</TableHead>
              <TableHead>Lifecycle Status</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {capas.map((capa) => {
              const statusVariant = STATUS_VARIANTS[capa.status] || 'neutral';
              const capaId = capa.action_id || capa.id || 'CAPA-N/A';
              const invRef = capa.investigation_id || capa.investigationId || 'N/A';

              return (
                <TableRow key={capaId}>
                  <TableCell>
                    <span className="font-mono text-xs font-bold text-[#142B45] bg-[#F1F5F9] px-2 py-1 rounded border border-[#E2E8F0]">
                      {capaId}
                    </span>
                  </TableCell>
                  <TableCell>
                    <div className="font-medium text-[#142B45] max-w-sm line-clamp-2">
                      {capa.description}
                    </div>
                    {capa.effectiveness_verification_method && (
                      <div className="text-[11px] text-[#64748B] mt-0.5 line-clamp-1">
                        Protocol: {capa.effectiveness_verification_method}
                      </div>
                    )}
                  </TableCell>
                  <TableCell>
                    <StatusBadge variant="neutral" size="sm" dot={false}>
                      {capa.action_type || 'Corrective Action'}
                    </StatusBadge>
                  </TableCell>
                  <TableCell>
                    <Link
                      to={`/investigations/${encodeURIComponent(invRef)}`}
                      className="font-mono text-xs text-[#0F9D91] hover:underline font-semibold flex items-center space-x-1"
                    >
                      <span>{invRef}</span>
                      <ExternalLink className="w-3 h-3 text-[#0F9D91]" />
                    </Link>
                  </TableCell>
                  <TableCell>
                    <div className="flex items-center text-xs text-[#475569]">
                      <User className="w-3 h-3 mr-1 text-[#94A3B8]" />
                      <span>{capa.action_owner || 'Unassigned'}</span>
                    </div>
                  </TableCell>
                  <TableCell>
                    <div className="flex items-center text-xs text-[#475569]">
                      <Clock className="w-3.5 h-3.5 mr-1 text-[#94A3B8]" />
                      <span>{capa.target_date || 'N/A'}</span>
                    </div>
                  </TableCell>
                  <TableCell>
                    <StatusBadge variant={statusVariant} size="sm">
                      {capa.status || 'Draft'}
                    </StatusBadge>
                  </TableCell>
                </TableRow>
              );
            })}
          </TableBody>
        </Table>
      )}
    </div>
  );
}
