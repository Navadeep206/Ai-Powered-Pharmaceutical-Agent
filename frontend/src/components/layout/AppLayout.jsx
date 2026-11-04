import React from 'react';
import { Outlet } from 'react-router-dom';
import Sidebar from './Sidebar';
import Topbar from './Topbar';

/**
 * Main application shell establishing the enterprise layout hierarchy:
 * Persistent/collapsible sidebar + sticky topbar + responsive content viewport.
 */
export default function AppLayout() {
  return (
    <div className="min-h-screen bg-[#F5F7FA] flex overflow-x-hidden">
      {/* Sidebar Navigation */}
      <Sidebar />

      {/* Main Content Column */}
      <div className="flex-1 flex flex-col min-w-0">
        <Topbar />

        <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-6 sm:py-8 overflow-x-hidden">
          <Outlet />
        </main>

        {/* Enterprise Compliance Footer */}
        <footer className="bg-white border-t border-[#E2E8F0] px-4 sm:px-6 lg:px-8 py-3 text-center text-[11px] text-[#64748B] flex flex-col sm:flex-row items-center justify-between gap-2">
          <div className="flex items-center space-x-2">
            <span className="font-semibold text-[#142B45]">RootIQ Enterprise</span>
            <span>&bull;</span>
            <span>Pharmaceutical Quality Intelligence</span>
          </div>
          <div>
            FDA 21 CFR Part 11 &bull; EU Annex 11 &bull; ICH Q9/Q10 Validated Framework &bull; ALCOA+ Audit Enforced
          </div>
        </footer>
      </div>
    </div>
  );
}
