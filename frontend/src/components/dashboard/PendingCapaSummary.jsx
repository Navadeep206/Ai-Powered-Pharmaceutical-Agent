import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '../common/Card';
import StatusBadge from '../common/StatusBadge';
import Button from '../common/Button';
import capaService from '../../services/capaService';
import {
  ShieldAlert,
  CheckSquare,
  ArrowRight,
  Clock,
  User,
  ExternalLink,
  CheckCircle2,
} from 'lucide-react';

/**
 * Dashboard widget highlighting pending CAPA actions awaiting formal QA approval.
 */
export default function PendingCapaSummary() {
  const [pendingCapas, setPendingCapas] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let isMounted = true;
    async function loadPending() {
      try {
        const data = await capaService.listAllCAPA({ status: 'Pending Review', limit: 4 });
        if (isMounted) {
          setPendingCapas(data || []);
        }
      } catch (err) {
        // Non-blocking for dashboard
      } finally {
        if (isMounted) setLoading(false);
      }
    }
    loadPending();
    return () => {
      isMounted = false;
    };
  }, []);

  return (
    <Card className="h-full flex flex-col justify-between">
      <CardHeader className="py-4 bg-[#F8FAFC]">
        <div className="flex items-center space-x-2.5">
          <div className="w-8 h-8 rounded-lg bg-[#FFFBEB] border border-[#FDE68A] flex items-center justify-center text-[#D97706]">
            <ShieldAlert className="w-4 h-4" />
          </div>
          <div>
            <CardTitle className="text-sm">Pending CAPA Review Queue</CardTitle>
            <CardDescription className="text-[11px]">
              ICH Q10 corrective & preventive actions requiring human QA approval
            </CardDescription>
          </div>
        </div>

        <Link to="/capa">
          <span className="text-xs font-semibold text-[#0F9D91] hover:underline flex items-center gap-1">
            View All ({pendingCapas.length}) <ArrowRight className="w-3.5 h-3.5" />
          </span>
        </Link>
      </CardHeader>

      <CardContent className="p-4 sm:p-5 flex-1 flex flex-col justify-between">
        {loading ? (
          <div className="space-y-3 py-2">
            {[1, 2, 3].map((i) => (
              <div key={i} className="animate-pulse flex items-center justify-between p-3 rounded-lg bg-[#F8FAFC]">
                <div className="space-y-1.5 flex-1">
                  <div className="h-3 bg-[#E2E8F0] rounded w-3/4" />
                  <div className="h-2.5 bg-[#E2E8F0] rounded w-1/2" />
                </div>
                <div className="h-5 bg-[#E2E8F0] rounded-full w-20 ml-3" />
              </div>
            ))}
          </div>
        ) : pendingCapas.length > 0 ? (
          <div className="space-y-2.5">
            {pendingCapas.map((capa) => {
              const isCorrective = (capa.action_type || '').includes('Corrective');
              return (
                <div
                  key={capa.action_id}
                  className="p-3 rounded-lg border border-[#E2E8F0] bg-white hover:border-[#CBD5E1] transition flex flex-col sm:flex-row sm:items-center justify-between gap-2.5 shadow-2xs"
                >
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center space-x-2">
                      <span
                        className={`text-[10px] font-semibold px-2 py-0.5 rounded-full ${
                          isCorrective
                            ? 'bg-[#E6F7F5] text-[#0A736A]'
                            : 'bg-[#EFF6FF] text-[#1E40AF]'
                        }`}
                      >
                        {isCorrective ? 'Corrective' : 'Preventive'}
                      </span>
                      {capa.investigation_number && (
                        <span className="text-[10px] font-mono text-[#64748B] bg-[#F1F5F9] px-1.5 py-0.5 rounded">
                          {capa.investigation_number}
                        </span>
                      )}
                    </div>
                    <p className="text-xs font-semibold text-[#142B45] mt-1 line-clamp-1">
                      {capa.title || capa.description}
                    </p>
                    <div className="flex items-center space-x-3 text-[11px] text-[#64748B] mt-1">
                      <span className="flex items-center gap-1">
                        <User className="w-3 h-3 text-[#94A3B8]" />
                        {capa.action_owner || 'QA Engineering'}
                      </span>
                      {capa.target_date && (
                        <span className="flex items-center gap-1">
                          <Clock className="w-3 h-3 text-[#94A3B8]" />
                          Due: {capa.target_date}
                        </span>
                      )}
                    </div>
                  </div>

                  <div className="shrink-0 flex items-center space-x-2">
                    <StatusBadge variant="warning" size="sm">
                      Pending Review
                    </StatusBadge>
                    <Link
                      to={`/investigations/${capa.investigation_number || capa.investigation_id}?tab=capa`}
                      className="p-1.5 text-[#64748B] hover:text-[#0F9D91] hover:bg-[#E6F7F5] rounded-md transition"
                      title="Review CAPA in Investigation Workspace"
                    >
                      <ExternalLink className="w-4 h-4" />
                    </Link>
                  </div>
                </div>
              );
            })}
          </div>
        ) : (
          <div className="py-6 text-center text-xs text-[#64748B] my-auto">
            <CheckCircle2 className="w-8 h-8 text-[#059669] mx-auto mb-2" />
            <p className="font-bold text-[#142B45]">No Actions Awaiting Review</p>
            <p className="text-[11px] mt-0.5">All corrective & preventive actions are verified or in implementation.</p>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
