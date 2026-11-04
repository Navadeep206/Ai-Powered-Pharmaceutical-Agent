import React from 'react';
import { useLocation } from 'react-router-dom';
import { useDispatch, useSelector } from 'react-redux';
import { toggleMobileNav } from '../../redux/slices/appSlice';
import {
  Menu,
  Search,
  Bell,
  ShieldCheck,
  User,
  ChevronDown,
  Sparkles,
  Command,
} from 'lucide-react';

/**
 * Top navigation bar featuring search, notifications, user avatar, and mobile toggle.
 */
export default function Topbar() {
  const dispatch = useDispatch();
  const location = useLocation();
  const { currentFacility } = useSelector((state) => state.app);

  // Derive contextual page title based on current route
  const getPageContext = () => {
    const path = location.pathname;
    if (path === '/') return { title: 'Executive Overview', section: 'Dashboard' };
    if (path === '/investigations') return { title: 'Deviation Registry', section: 'Investigations' };
    if (path === '/investigations/new') return { title: 'Initiate Investigation', section: 'Investigations' };
    if (path.startsWith('/investigations/')) return { title: 'Root Cause Workspace', section: 'Investigations' };
    if (path === '/capa') return { title: 'Corrective & Preventive Actions', section: 'CAPA' };
    if (path === '/settings') return { title: 'System Configuration', section: 'Settings' };
    return { title: 'Quality Management', section: 'RootIQ' };
  };

  const context = getPageContext();

  return (
    <header className="sticky top-0 z-20 h-16 bg-white border-b border-[#E2E8F0] px-4 sm:px-6 lg:px-8 flex items-center justify-between shadow-2xs">
      {/* Left: Mobile Toggle & Page Context */}
      <div className="flex items-center space-x-3 sm:space-x-4">
        <button
          onClick={() => dispatch(toggleMobileNav())}
          className="md:hidden p-2 text-[#475569] hover:text-[#142B45] hover:bg-[#F1F5F9] rounded-lg transition"
          aria-label="Open sidebar navigation"
        >
          <Menu className="w-5 h-5" />
        </button>

        <div className="flex flex-col">
          <div className="flex items-center space-x-2 text-xs font-medium text-[#64748B]">
            <span>RootIQ</span>
            <span>/</span>
            <span className="text-[#142B45] font-semibold">{context.section}</span>
          </div>
          <h2 className="text-base font-bold text-[#142B45] leading-none mt-0.5 hidden sm:block">
            {context.title}
          </h2>
        </div>
      </div>

      {/* Center: Search Interface Placeholder (Visual only) */}
      <div className="hidden lg:flex items-center flex-1 max-w-md mx-8">
        <div className="relative w-full">
          <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-[#94A3B8]">
            <Search className="w-4 h-4" />
          </div>
          <input
            type="text"
            readOnly
            placeholder="Search batches, deviations, OOS, or SOPs..."
            className="w-full bg-[#F8FAFC] border border-[#E2E8F0] rounded-lg pl-9 pr-16 py-1.5 text-xs text-[#334155] placeholder-[#94A3B8] focus:outline-none hover:border-[#CBD5E1] cursor-pointer transition shadow-2xs"
          />
          <div className="absolute inset-y-0 right-0 pr-2.5 flex items-center pointer-events-none">
            <span className="text-[10px] font-mono text-[#64748B] bg-white border border-[#E2E8F0] rounded px-1.5 py-0.5 shadow-2xs flex items-center gap-0.5">
              <Command className="w-2.5 h-2.5" /> K
            </span>
          </div>
        </div>
      </div>

      {/* Right: Actions, Notifications, & User Avatar */}
      <div className="flex items-center space-x-2.5 sm:space-x-4">
        {/* Search icon trigger for small screens */}
        <button
          className="lg:hidden p-2 text-[#64748B] hover:text-[#142B45] hover:bg-[#F1F5F9] rounded-lg transition"
          aria-label="Search"
        >
          <Search className="w-4 h-4" />
        </button>

        {/* Notifications Icon (Visual placeholder) */}
        <div className="relative">
          <button
            className="p-2 text-[#64748B] hover:text-[#142B45] hover:bg-[#F1F5F9] rounded-lg transition relative"
            aria-label="View notifications"
          >
            <Bell className="w-4 h-4" />
            <span className="absolute top-1.5 right-1.5 w-2 h-2 rounded-full bg-[#DC2626] ring-2 ring-white" />
          </button>
        </div>

        {/* Divider */}
        <div className="h-6 w-px bg-[#E2E8F0]" />

        {/* User Profile / Avatar Placeholder */}
        <div className="flex items-center space-x-3 pl-1">
          <div className="relative">
            <div className="w-8 h-8 rounded-full bg-[#142B45] text-white flex items-center justify-center font-semibold text-xs shadow-2xs border border-[#CBD5E1]">
              EV
            </div>
            <span className="absolute bottom-0 right-0 w-2.5 h-2.5 rounded-full bg-[#059669] ring-2 ring-white" />
          </div>

          <div className="hidden sm:flex flex-col text-left">
            <div className="flex items-center space-x-1">
              <span className="text-xs font-semibold text-[#142B45]">
                Dr. Elena Vance
              </span>
              <ChevronDown className="w-3 h-3 text-[#94A3B8]" />
            </div>
            <span className="text-[11px] text-[#64748B] font-medium leading-tight">
              QA Director &bull; GxP Signer
            </span>
          </div>
        </div>
      </div>
    </header>
  );
}

