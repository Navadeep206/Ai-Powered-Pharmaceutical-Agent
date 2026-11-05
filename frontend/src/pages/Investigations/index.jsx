import React, { useState, useEffect, useCallback } from 'react';
import { Link } from 'react-router-dom';
import { useSelector, useDispatch } from 'react-redux';
import PageHeader from '../../components/common/PageHeader';
import Button from '../../components/common/Button';
import StatusBadge from '../../components/common/StatusBadge';
import Input from '../../components/common/Input';
import Select from '../../components/common/Select';
import EmptyState from '../../components/common/EmptyState';
import LoadingSpinner from '../../components/common/LoadingSpinner';
import { Card, CardContent } from '../../components/common/Card';
import { fetchInvestigations } from '../../redux/slices/investigationSlice';
import { SEVERITY_BADGE_MAP, STATUS_BADGE_MAP } from '../../utils/normalizers';
import {
  PlusCircle,
  Search,
  ExternalLink,
  RotateCcw,
  SlidersHorizontal,
  AlertCircle,
  ChevronLeft,
  ChevronRight,
} from 'lucide-react';

/**
 * Investigations Master Listing connected directly to the FastAPI backend.
 * Supports backend search, status/severity filtering, pagination, and error handling.
 */
export default function InvestigationsPage() {
  const dispatch = useDispatch();

  const {
    investigations,
    pagination,
    listLoading,
    listError,
  } = useSelector((state) => state.investigations);

  const [searchTerm, setSearchTerm] = useState('');
  const [debouncedSearch, setDebouncedSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState('ALL');
  const [severityFilter, setSeverityFilter] = useState('ALL');
  const [currentPage, setCurrentPage] = useState(1);

  // Debounce search input to avoid redundant API queries and race conditions
  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedSearch(searchTerm);
    }, 300);
    return () => clearTimeout(timer);
  }, [searchTerm]);

  const loadData = useCallback(() => {
    dispatch(
      fetchInvestigations({
        page: currentPage,
        limit: 15,
        search: debouncedSearch,
        status: statusFilter,
        severity: severityFilter,
      })
    );
  }, [dispatch, currentPage, debouncedSearch, statusFilter, severityFilter]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const hasActiveFilters =
    searchTerm.trim() !== '' || statusFilter !== 'ALL' || severityFilter !== 'ALL';

  const resetFilters = () => {
    setSearchTerm('');
    setDebouncedSearch('');
    setStatusFilter('ALL');
    setSeverityFilter('ALL');
    setCurrentPage(1);
  };

  const handlePageChange = (newPage) => {
    if (newPage >= 1 && (!pagination || newPage <= pagination.total_pages)) {
      setCurrentPage(newPage);
    }
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
          <StatusBadge variant={listError ? 'danger' : 'teal'}>
            {pagination ? `${pagination.total} Total Records` : `${investigations.length} Records`}
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
                onChange={(e) => {
                  setSearchTerm(e.target.value);
                  setCurrentPage(1);
                }}
                leftIcon={Search}
              />
            </div>

            {/* Status Filter */}
            <div className="w-full sm:w-48">
              <Select
                value={statusFilter}
                onChange={(e) => {
                  setStatusFilter(e.target.value);
                  setCurrentPage(1);
                }}
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
                onChange={(e) => {
                  setSeverityFilter(e.target.value);
                  setCurrentPage(1);
                }}
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
                Showing <strong className="text-[#142B45]">{investigations.length}</strong> of{' '}
                {pagination?.total ?? investigations.length} records
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

      {/* Error Banner with Retry */}
      {listError && (
        <div className="p-4 rounded-xl border border-[#FECACA] bg-[#FEF2F2] flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 text-sm text-[#991B1B]">
          <div className="flex items-center space-x-2.5">
            <AlertCircle className="w-5 h-5 shrink-0 text-[#DC2626]" />
            <div>
              <p className="font-semibold">Failed to Load Quality Investigations</p>
              <p className="text-xs text-[#B91C1C] mt-0.5">{listError}</p>
            </div>
          </div>
          <Button
            variant="secondary"
            size="sm"
            leftIcon={RotateCcw}
            onClick={loadData}
            className="shrink-0 bg-white border-[#FCA5A5] hover:bg-[#FEE2E2]"
          >
            Retry Connection
          </Button>
        </div>
      )}

      {/* Investigations Table or Loading / Empty State */}
      <Card>
        <CardContent noPadding>
          {listLoading ? (
            <div className="py-16 flex flex-col items-center justify-center space-y-3">
              <LoadingSpinner size="lg" />
              <p className="text-sm font-medium text-[#64748B]">Querying PostgreSQL quality records...</p>
            </div>
          ) : investigations.length === 0 ? (
            <div className="p-8">
              <EmptyState
                title="No investigations found"
                description={
                  hasActiveFilters
                    ? "We couldn't find any deviation records matching your search query or selected filters. Try broadening your keywords or clearing filters."
                    : "No quality deviation investigations are currently stored in the database."
                }
                action={
                  hasActiveFilters ? (
                    <Button variant="secondary" size="sm" leftIcon={RotateCcw} onClick={resetFilters}>
                      Clear All Filters
                    </Button>
                  ) : (
                    <Link to="/investigations/new">
                      <Button variant="primary" size="sm" leftIcon={PlusCircle}>
                        Create Investigation
                      </Button>
                    </Link>
                  )
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
                  {investigations.map((inv) => (
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
                        <div className="font-semibold text-[#142B45] truncate" title={inv.title}>
                          {inv.title}
                        </div>
                        <div className="text-xs text-[#64748B] mt-0.5 flex items-center space-x-2">
                          <span>Batch: <strong className="text-[#334155]">{inv.batch || 'N/A'}</strong></span>
                          <span>&bull;</span>
                          <span>Reported by: {inv.reportedBy}</span>
                        </div>
                      </td>

                      <td className="px-5 py-4 text-xs text-[#475569] font-medium">
                        {inv.department || 'General'}
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
                        {inv.date || 'N/A'}
                      </td>

                      <td className="px-5 py-4 text-right whitespace-nowrap">
                        <Link to={`/investigations/${encodeURIComponent(inv.id)}`}>
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

          {/* Pagination Controls */}
          {pagination && pagination.total_pages > 1 && (
            <div className="p-4 border-t border-[#E2E8F0] bg-[#F8FAFC] flex items-center justify-between text-xs text-[#64748B]">
              <span>
                Page <strong className="text-[#142B45]">{pagination.page}</strong> of{' '}
                <strong className="text-[#142B45]">{pagination.total_pages}</strong> ({pagination.total} total)
              </span>

              <div className="flex items-center space-x-2">
                <Button
                  variant="secondary"
                  size="xs"
                  leftIcon={ChevronLeft}
                  disabled={!pagination.has_prev}
                  onClick={() => handlePageChange(currentPage - 1)}
                >
                  Previous
                </Button>
                <Button
                  variant="secondary"
                  size="xs"
                  rightIcon={ChevronRight}
                  disabled={!pagination.has_next}
                  onClick={() => handlePageChange(currentPage + 1)}
                >
                  Next
                </Button>
              </div>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
