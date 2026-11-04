import React from 'react';
import PageHeader from '../../components/common/PageHeader';
import Button from '../../components/common/Button';
import StatusBadge from '../../components/common/StatusBadge';
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell } from '../../components/common/Table';
import { CheckSquare, Clock, PlusCircle, ArrowRight } from 'lucide-react';

export default function CAPAManagementPage() {
  const sampleCapas = [
    {
      id: 'CAPA-2026-014',
      type: 'Preventive Action',
      target: 'Implement Dual Temperature Sensor Interlock on Reactor R-102',
      investigationId: 'INV-2026-001',
      dueDate: '2026-12-15',
      status: 'warning',
      statusText: 'In Progress',
    },
    {
      id: 'CAPA-2026-012',
      type: 'Corrective Action',
      target: 'Quarantine and Recalibrate HPLC Column Packing Station',
      investigationId: 'INV-2026-002',
      dueDate: '2026-11-20',
      status: 'info',
      statusText: 'Verification Pending',
    },
  ];

  return (
    <div className="space-y-6">
      <PageHeader
        title="CAPA Management"
        description="Corrective and Preventive Action lifecycle tracking, assignees, verification milestones, and effectiveness reviews (ICH Q10)."
        breadcrumbs={[
          { label: 'RootIQ', to: '/' },
          { label: 'CAPA Management' },
        ]}
        badge={<StatusBadge variant="teal">ICH Q10 Validated</StatusBadge>}
        actions={
          <Button variant="accent" size="sm" leftIcon={PlusCircle} disabled>
            Draft Action Item
          </Button>
        }
      />

      <Table>
        <TableHeader>
          <TableRow hover={false}>
            <TableHead>CAPA ID</TableHead>
            <TableHead>Remediation Target</TableHead>
            <TableHead>Type</TableHead>
            <TableHead>Linked Investigation</TableHead>
            <TableHead>Target Due Date</TableHead>
            <TableHead>Lifecycle Status</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {sampleCapas.map((capa) => (
            <TableRow key={capa.id}>
              <TableCell>
                <span className="font-mono text-xs font-bold text-[#142B45] bg-[#F1F5F9] px-2 py-1 rounded">
                  {capa.id}
                </span>
              </TableCell>
              <TableCell>
                <div className="font-medium text-[#142B45]">{capa.target}</div>
                <div className="text-xs text-[#64748B]">S.M.A.R.T. criteria enforced</div>
              </TableCell>
              <TableCell>
                <StatusBadge variant="neutral" size="sm" dot={false}>
                  {capa.type}
                </StatusBadge>
              </TableCell>
              <TableCell>
                <span className="font-mono text-xs text-[#0F9D91] font-semibold">
                  {capa.investigationId}
                </span>
              </TableCell>
              <TableCell>
                <div className="flex items-center text-xs text-[#475569]">
                  <Clock className="w-3.5 h-3.5 mr-1.5 text-[#94A3B8]" />
                  <span>{capa.dueDate}</span>
                </div>
              </TableCell>
              <TableCell>
                <StatusBadge variant={capa.status} size="sm">
                  {capa.statusText}
                </StatusBadge>
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
}
