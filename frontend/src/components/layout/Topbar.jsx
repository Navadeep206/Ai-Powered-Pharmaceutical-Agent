import React, { useState } from 'react';
import { useLocation, useNavigate, Link } from 'react-router-dom';
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
  CheckCircle2,
  Activity,
  X,
} from 'lucide-react';

/**
 * Top navigation bar featuring search, notifications, active GxP session, and mobile navigation toggle.
 */
export default function Topbar() {
  const dispatch = useDispatch();
  const navigate = useNavigate();
  const location = useLocation();
  const { currentFacility } = useSelector((state) => state.app);
  const { activities } = useSelector((state) => state.dashboard);

  const [topSearch, setTopSearch] = useState('');
  const [showNotifications, setShowNotifications] = useState(false);

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

  const handleSearchSubmit = (e) => {
    e.preventDefault();
    if (topSearch.trim()) {
      navigate(`/investigations?search=${encodeURIComponent(topSearch.trim())}`);
    }
  };

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

      {/* Center: Search Interface */}
      <form onSubmit={handleSearchSubmit} className="hidden lg:flex items-center flex-1 max-w-md mx-8">
        <div className="relative w-full">
          <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-[#94A3B8]">
            <Search className="w-4 h-4" />
          </div>
          <input
            type="text"
            value={topSearch}
            onChange={(e) => setTopSearch(e.target.value)}
            placeholder="Search batches, deviations, OOS, or SOPs..."
            className="w-full bg-[#F8FAFC] border border-[#E2E8F0] rounded-lg pl-9 pr-16 py-1.5 text-xs text-[#334155] placeholder-[#94A3B8] focus:outline-none focus:border-[#0F9D91] focus:ring-1 focus:ring-[#0F9D91] hover:border-[#CBD5E1] transition shadow-2xs"
          />
          <div className="absolute inset-y-0 right-0 pr-2.5 flex items-center pointer-events-none">
            <span className="text-[10px] font-mono text-[#64748B] bg-white border border-[#E2E8F0] rounded px-1.5 py-0.5 shadow-2xs flex items-center gap-0.5">
              <Command className="w-2.5 h-2.5" /> K
            </span>
          </div>
        </div>
      </form>

      {/* Right: Actions, Notifications, & Active Role Session */}
      <div className="flex items-center space-x-2.5 sm:space-x-4">
        {/* Search icon trigger for small screens */}
        <button
          onClick={() => navigate('/investigations')}
          className="lg:hidden p-2 text-[#64748B] hover:text-[#142B45] hover:bg-[#F1F5F9] rounded-lg transition"
          aria-label="Search investigations"
        >
          <Search className="w-4 h-4" />
        </button>

        {/* Notifications Popover */}
        <div className="relative">
          <button
            onClick={() => setShowNotifications(!showNotifications)}
            className="p-2 text-[#64748B] hover:text-[#142B45] hover:bg-[#F1F5F9] rounded-lg transition relative"
            aria-label="View system notifications"
          >
            <Bell className="w-4 h-4" />
          </button>

          {showNotifications && (
            <div className="absolute right-0 mt-2 w-80 sm:w-96 bg-white rounded-xl shadow-xl border border-[#E2E8F0] z-50 p-4">
              <div className="flex items-center justify-between pb-3 border-b border-[#F1F5F9]">
                <div className="flex items-center space-x-2">
                  <ShieldCheck className="w-4 h-4 text-[#0F9D91]" />
                  <span className="text-xs font-bold text-[#142B45]">Audit Trail & Alerts</span>
                </div>
                <button
                  onClick={() => setShowNotifications(false)}
                  className="text-[#94A3B8] hover:text-[#142B45] text-xs p-1"
                >
                  <X className="w-3.5 h-3.5" />
                </button>
              </div>

              <div className="py-3 space-y-2.5 max-h-64 overflow-y-auto">
                {activities && activities.length > 0 ? (
                  activities.slice(0, 4).map((act, i) => (
                    <div key={i} className="text-xs p-2 rounded-lg bg-[#F8FAFC] border border-[#F1F5F9]">
                      <div className="flex items-center justify-between text-[11px] font-semibold text-[#142B45]">
                        <span className="truncate">{act.activity_type || act.action || 'Quality Audit Event'}</span>
                        <span className="text-[10px] text-[#94A3B8] font-normal shrink-0">
                          {act.timestamp ? new Date(act.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : 'Logged'}
                        </span>
                      </div>
                      <p className="text-[11px] text-[#64748B] mt-0.5 line-clamp-2">
                        {act.description || act.details || 'Contemporaneous audit trail event recorded.'}
                      </p>
                    </div>
                  ))
                ) : (
                  <div className="text-center py-4 text-xs text-[#64748B]">
                    <CheckCircle2 className="w-6 h-6 text-[#059669] mx-auto mb-1.5" />
                    <p className="font-semibold text-[#142B45]">All Systems Nominal</p>
                    <p className="text-[11px] mt-0.5">21 CFR Part 11 audit logging active across all modules.</p>
                  </div>
                )}
              </div>

              <div className="pt-2.5 border-t border-[#F1F5F9] text-center">
                <Link
                  to="/"
                  onClick={() => setShowNotifications(false)}
                  className="text-[11px] font-semibold text-[#0F9D91] hover:underline"
                >
                  View Full Audit Log on Dashboard &rarr;
                </Link>
              </div>
            </div>
          )}
        </div>

        {/* Divider */}
        <div className="h-6 w-px bg-[#E2E8F0]" />

        {/* User Role & Session Identifier */}
        <div className="flex items-center space-x-3 pl-1">
          <div className="relative">
            <div className="w-8 h-8 rounded-full bg-[#142B45] text-white flex items-center justify-center font-bold text-xs shadow-2xs border border-[#CBD5E1]">
              QA
            </div>
            <span className="absolute bottom-0 right-0 w-2.5 h-2.5 rounded-full bg-[#059669] ring-2 ring-white" />
          </div>

          <div className="hidden sm:flex flex-col text-left">
            <div className="flex items-center space-x-1">
              <span className="text-xs font-bold text-[#142B45]">
                QA Lead / Investigator
              </span>
            </div>
            <span className="text-[11px] text-[#64748B] font-medium leading-tight">
              GxP Authorized &bull; {currentFacility || 'Hyderabad Site'}
            </span>
          </div>
        </div>
      </div>
    </header>
  );
}
