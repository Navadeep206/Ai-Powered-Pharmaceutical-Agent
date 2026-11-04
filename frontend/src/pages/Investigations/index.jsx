import React, { useState, useMemo } from 'react';
import { Link } from 'react-router-dom';
import PageHeader from '../../components/common/PageHeader';
import Button from '../../components/common/Button';
import StatusBadge from '../../components/common/StatusBadge';
import Input from '../../components/common/Input';
import Select from '../../components/common/Select';
import EmptyState from '../../components/common/EmptyState';
import { Card, CardContent } from '../../components/common/Card';
import {
  PlusCircle,
  Search,
  Filter,
  ArrowRight,
  ExternalLink,
  RotateCcw,
  SlidersHorizontal,
} from 'lucide-react';
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
 * Investigations Master Listing with functional local search and multi-criteria filters.
 */
export default function InvestigationsPage() {
  const [searchTerm, setSearchTerm] = useState('');
  const [statusFilter, setStatusFilter] = useState('ALL');
  const [severityFilter, setSeverityFilter] = useState('ALL');

  // Multi-criteria filter executed locally against demonstration dataset
  const filteredInvestigations = useMemo(() => {
    return DEMO_INVESTIGATIONS.filter((inv) => {
      // 1. Keyword search (ID, Title, Department, Batch, Reporter)
      const term = searchTerm.trim().toLowerCase();
      const matchesSearch =
        !term ||
        inv.id.toLowerCase().includes(term) ||
        inv.title.toLowerCase().includes(term) ||
        inv.department.toLowerCase().includes(term) ||
        inv.batch.toLowerCase().includes(term) ||
        inv.reportedBy.toLowerCase().includes(term);

      // 2. Status filter
      const matchesStatus =
        statusFilter === 'ALL' || inv.status === statusFilter;

      // 3. Severity filter
      const matchesSeverity =
        severityFilter === 'ALL' || inv.severity === severityFilter;

      return matchesSearch && matchesStatus && matchesSeverity;
    });
  }, [searchTerm, statusFilter, severityFilter]);

  const hasActiveFilters =
    searchTerm.trim() !== '' || statusFilter !== 'ALL' || severityFilter !== 'ALL';

  const resetFilters = () => {
    setSearchTerm('');
    setStatusFilter('ALL');
    setSeverityFilter('ALL');
  };

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <PageHeader
        title="Investigations Registry"
        description="Comprehensive log of pharmaceutical deviations, out-of-specification events, and active root cause workspaces."
        breadcrumbs={[
          { label: 'RootIQ', to: '/' },
          { label: 'Investigations' },
        ]}
        badge={
          <StatusBadge variant="teal">
            {DEMO_INVESTIGATIONS.length} Total Records
          </StatusBadge>
        }
        actions={
          <Link to="/investigations/new">
            <Button variant="accent" size="sm" leftIcon={PlusCircle}>
              New Investigation
            </Button>
          </Link>
        }
      />

      {/* Search and Filters Bar */}
      <Card>
        <CardContent className="p-4">
          <div className="flex flex-col md:flex-row items-center gap-3">
            {/* Search Input */}
            <div className="w-full md:flex-1">
              <Input
                placeholder="Search by ID (INV-...), batch, title, or department..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                leftIcon={Search}
              />
            </div>

            {/* Status Filter */}
            <div className="w-full sm:w-48">
              <Select
                value={statusFilter}
                onChange={(e) => setStatusFilter(e.target.value)}
                options={[
                  { value: 'ALL', label: 'All Statuses' },
                  { value: 'Open', label: 'Open' },
                  { value: 'Under Investigation', label: 'Under Investigation' },
                  { value: 'Pending Review', label: 'Pending Review' },
                  { value: 'Closed', label: 'Closed' },
                ]}
              />
            </div>

            {/* Severity Filter */}
            <div className="w-full sm:w-44">
              <Select
                value={severityFilter}
                onChange={(e) => setSeverityFilter(e.target.value)}
                options={[
                  { value: 'ALL', label: 'All Severities' },
                  { value: 'Critical', label: 'Critical' },
                  { value: 'High', label: 'High' },
                  { value: 'Medium', label: 'Medium' },
                  { value: 'Low', label: 'Low' },
                ]}
              />
            </div>

            {/* Reset Filter Button */}
            {hasActiveFilters && (
              <Button
                variant="ghost"
                size="sm"
                leftIcon={RotateCcw}
                onClick={resetFilters}
                className="shrink-0"
              >
                Reset
              </Button>
            )}
          </div>

          {/* Active Filter Metrics */}
          <div className="mt-3 flex items-center justify-between text-xs text-[#64748B] pt-3 border-t border-[#F1F5F9]">
            <div className="flex items-center space-x-2">
              <SlidersHorizontal className="w-3.5 h-3.5 text-[#0F9D91]" />
              <span>
                Showing <strong className="text-[#142B45]">{filteredInvestigations.length}</strong> of{' '}
                {DEMO_INVESTIGATIONS.length} records
              </span>
            </div>

            {hasActiveFilters && (
              <span className="text-[#0F9D91] font-medium">
                Active filter applied
              </span>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Investigations Table or Empty State */}
      <Card>
        <CardContent noPadding>
          {filteredInvestigations.length === 0 ? (
            <div className="p-8">
              <EmptyState
                title="No investigations match criteria"
                description="We couldn't find any records matching your search query or selected filters. Try broadening your keywords or resetting filters."
                action={
                  <Button variant="secondary" size="sm" leftIcon={RotateCcw} onClick={resetFilters}>
                    Clear All Filters
                  </Button>
                }
              />
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm text-[#334155]">
                <thead className="bg-[#F8FAFC] border-b border-[#E2E8F0] text-xs font-semibold text-[#64748B] uppercase tracking-wider">
                  <tr>
                    <th className="px-5 py-3.5">Investigation ID</th>
                    <th className="px-5 py-3.5">Incident Title & Batch</th>
                    <th className="px-5 py-3.5">Department</th>
                    <th className="px-5 py-3.5">Severity</th>
                    <th className="px-5 py-3.5">Status</th>
                    <th className="px-5 py-3.5">Date Logged</th>
                    <th className="px-5 py-3.5 text-right">Action</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[#F1F5F9] bg-white">
                  {filteredInvestigations.map((inv) => (
                    <tr
                      key={inv.id}
                      className="hover:bg-[#F8FAFC] transition-colors duration-150"
                    >
                      <td className="px-5 py-4 font-mono text-xs font-bold text-[#142B45]">
                        <span className="bg-[#F1F5F9] px-2 py-0.5 rounded border border-[#E2E8F0]">
                          {inv.id}
                        </span>
                      </td>

                      <td className="px-5 py-4 max-w-sm">
                        <div className="font-semibold text-[#142B45]">{inv.title}</div>
                        <div className="text-xs text-[#64748B] mt-0.5 flex items-center space-x-2">
                          <span>Batch: <strong className="text-[#334155]">{inv.batch}</strong></span>
                          <span>&bull;</span>
                          <span>Reported by: {inv.reportedBy}</span>
                        </div>
                      </td>

                      <td className="px-5 py-4 text-xs text-[#475569] font-medium">
                        {inv.department}
                      </td>

                      <td className="px-5 py-4">
                        <StatusBadge
                          variant={SEVERITY_BADGE_MAP[inv.severity] || 'neutral'}
                          size="sm"
                        >
                          {inv.severity}
                        </StatusBadge>
                      </td>

                      <td className="px-5 py-4">
                        <StatusBadge
                          variant={STATUS_BADGE_MAP[inv.status] || 'neutral'}
                          size="sm"
                        >
                          {inv.status}
                        </StatusBadge>
                      </td>

                      <td className="px-5 py-4 text-xs text-[#64748B] font-mono whitespace-nowrap">
                        {inv.date}
                      </td>

                      <td className="px-5 py-4 text-right whitespace-nowrap">
                        <Link to={`/investigations/${inv.id}`}>
                          <Button variant="ghost" size="xs" rightIcon={ExternalLink}>
                            Open Workspace
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
      </Card>
    </div>
  );
}
