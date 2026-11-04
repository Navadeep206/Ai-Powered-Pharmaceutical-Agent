import React from 'react';
import PageHeader from '../../components/common/PageHeader';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '../../components/common/Card';
import StatusBadge from '../../components/common/StatusBadge';
import Button from '../../components/common/Button';
import Input from '../../components/common/Input';
import { Sliders, Shield, Save } from 'lucide-react';

export default function SettingsPage() {
  return (
    <div className="space-y-6">
      <PageHeader
        title="System Settings"
        description="Facility configurations, GxP electronic signature policies, and ALCOA+ audit settings."
        breadcrumbs={[
          { label: 'RootIQ', to: '/' },
          { label: 'Settings' },
        ]}
        badge={<StatusBadge variant="teal">Compliance Active</StatusBadge>}
      />

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <Card>
          <CardHeader>
            <div>
              <CardTitle>Plant Facility Information</CardTitle>
              <CardDescription>Active manufacturing site configuration</CardDescription>
            </div>
            <Sliders className="w-5 h-5 text-[#64748B]" />
          </CardHeader>
          <CardContent className="space-y-4">
            <Input
              label="Facility Name"
              value="API Plant Alpha - Hyderabad"
              disabled
              helperText="Managed by Enterprise Site Administrator"
            />
            <Input
              label="GxP Timezone"
              value="UTC (Coordinated Universal Time)"
              disabled
              helperText="Mandatory UTC timestamping per 21 CFR Part 11"
            />
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <div>
              <CardTitle>Electronic Signature Policy</CardTitle>
              <CardDescription>Authentication requirements for investigation closure</CardDescription>
            </div>
            <Shield className="w-5 h-5 text-[#0F9D91]" />
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="p-4 rounded-lg bg-[#F8FAFC] border border-[#E2E8F0] space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-xs font-semibold text-[#142B45]">Session Inactivity Timeout</span>
                <StatusBadge variant="neutral" size="sm">15 Minutes</StatusBadge>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-xs font-semibold text-[#142B45]">Dual-Factor Approval</span>
                <StatusBadge variant="success" size="sm">Enforced</StatusBadge>
              </div>
            </div>

            <Button variant="secondary" size="sm" fullWidth leftIcon={Save} disabled>
              Settings Managed by GxP QA Admin
            </Button>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

