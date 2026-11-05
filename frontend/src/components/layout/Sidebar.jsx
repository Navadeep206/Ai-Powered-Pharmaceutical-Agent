import React from 'react';
import { NavLink, useLocation } from 'react-router-dom';
import { useSelector, useDispatch } from 'react-redux';
import { setMobileNavOpen } from '../../redux/slices/appSlice';
import {
  LayoutDashboard,
  Activity,
  PlusCircle,
  CheckSquare,
  Settings,
  ShieldCheck,
  Building2,
  X,
  FileText,
  HelpCircle,
  Network,
} from 'lucide-react';

/**
 * Enterprise Left Sidebar component for RootIQ.
 * Supports persistent desktop layout and collapsible mobile drawer.
 */
export default function Sidebar() {
  const dispatch = useDispatch();
  const location = useLocation();
  const { appName, tagline, currentFacility, systemStatus, mobileNavOpen } = useSelector(
    (state) => state.app
  );
  const { summary } = useSelector((state) => state.dashboard);

  const activeCount = summary?.open_investigations;
  const activeBadge = typeof activeCount === 'number' && activeCount > 0 ? `${activeCount} Active` : null;

  const navItems = [
    {
      name: 'Dashboard',
      to: '/',
      icon: LayoutDashboard,
      end: true,
      badge: null,
    },
    {
      name: 'Investigations',
      to: '/investigations',
      icon: Activity,
      end: true,
      badge: activeBadge,
    },
    {
      name: 'New Investigation',
      to: '/investigations/new',
      icon: PlusCircle,
      end: false,
      badge: null,
    },
    {
      name: 'CAPA Management',
      to: '/capa',
      icon: CheckSquare,
      end: false,
      badge: null,
    },
    {
      name: 'Settings',
      to: '/settings',
      icon: Settings,
      end: false,
      badge: null,
    },
  ];

  const handleLinkClick = () => {
    if (mobileNavOpen) {
      dispatch(setMobileNavOpen(false));
    }
  };

  const navContent = (
    <div className="flex flex-col h-full bg-white border-r border-[#E2E8F0]">
      {/* Brand Header & Logo */}
      <div className="p-5 border-b border-[#F1F5F9]">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <div className="w-10 h-10 rounded-xl bg-[#142B45] text-white flex items-center justify-center shadow-sm">
              <Network className="w-5 h-5 text-[#0F9D91]" />
            </div>
            <div>
              <div className="flex items-baseline space-x-1">
                <span className="text-xl font-bold tracking-tight text-[#142B45]">
                  Root<span className="text-[#0F9D91]">IQ</span>
                </span>
                <span className="text-[10px] font-mono px-1.5 py-0.5 bg-[#E6F7F5] text-[#0A736A] font-semibold rounded">
                  GxP
                </span>
              </div>
            </div>
          </div>

          {/* Mobile close button */}
          <button
            onClick={() => dispatch(setMobileNavOpen(false))}
            className="md:hidden p-1.5 text-[#64748B] hover:text-[#142B45] hover:bg-[#F1F5F9] rounded-lg transition"
            aria-label="Close menu"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        <p className="text-[11px] font-medium text-[#64748B] mt-2.5 leading-snug">
          {tagline}
        </p>
      </div>

      {/* Facility & GxP Compliance Banner */}
      <div className="px-5 py-3 bg-[#F8FAFC] border-b border-[#F1F5F9] text-xs">
        <div className="flex items-center text-[#475569] font-medium truncate">
          <Building2 className="w-3.5 h-3.5 text-[#0F9D91] mr-1.5 shrink-0" />
          <span className="truncate">{currentFacility}</span>
        </div>
        <div className="flex items-center justify-between mt-1.5 text-[11px] text-[#64748B]">
          <span className="inline-flex items-center">
            <span className="w-2 h-2 rounded-full bg-[#059669] inline-block mr-1.5 animate-pulse" />
            21 CFR Part 11
          </span>
          <span className="uppercase text-[10px] font-semibold tracking-wider text-[#059669]">
            {systemStatus}
          </span>
        </div>
      </div>

      {/* Main Navigation Links */}
      <nav className="flex-1 px-3 py-4 space-y-1 overflow-y-auto">
        <div className="px-3 pb-2 text-[10px] font-bold uppercase tracking-wider text-[#94A3B8]">
          Investigation Operations
        </div>

        {navItems.map((item) => {
          const Icon = item.icon;
          const isActive = item.end
            ? location.pathname === item.to
            : location.pathname.startsWith(item.to);

          return (
            <NavLink
              key={item.to}
              to={item.to}
              onClick={handleLinkClick}
              end={item.end}
              className={({ isActive: navActive }) => {
                const active = item.end ? navActive : location.pathname.startsWith(item.to);
                return `group flex items-center justify-between px-3 py-2.5 rounded-lg text-sm font-medium transition-all duration-150 ${
                  active
                    ? 'bg-[#E6F7F5] text-[#142B45] font-semibold shadow-2xs'
                    : 'text-[#475569] hover:bg-[#F8FAFC] hover:text-[#142B45]'
                }`;
              }}
            >
              <div className="flex items-center space-x-3">
                <Icon
                  className={`w-4 h-4 transition-colors ${
                    isActive
                      ? 'text-[#0F9D91]'
                      : 'text-[#64748B] group-hover:text-[#142B45]'
                  }`}
                />
                <span>{item.name}</span>
              </div>
              {item.badge && (
                <span
                  className={`text-[10px] px-2 py-0.5 rounded-full font-semibold ${
                    isActive
                      ? 'bg-[#0F9D91] text-white'
                      : 'bg-[#F1F5F9] text-[#64748B] group-hover:bg-[#E2E8F0]'
                  }`}
                >
                  {item.badge}
                </span>
              )}
            </NavLink>
          );
        })}
      </nav>

      {/* Footer / Knowledge Base & Help */}
      <div className="p-4 border-t border-[#F1F5F9] bg-[#FAFAFA]">
        <div className="bg-white p-3 rounded-lg border border-[#E2E8F0] shadow-2xs">
          <div className="flex items-center space-x-2 text-xs font-semibold text-[#142B45]">
            <HelpCircle className="w-4 h-4 text-[#0F9D91]" />
            <span>Regulatory Guide</span>
          </div>
          <p className="text-[11px] text-[#64748B] mt-1">
            ICH Q9 Risk Management & Ishikawa 6M standard protocols.
          </p>
        </div>

        <div className="mt-3 flex items-center justify-between text-[11px] text-[#94A3B8] px-1 font-mono">
          <span>v1.0.0-rc1</span>
          <span>Pharma API</span>
        </div>
      </div>
    </div>
  );

  return (
    <>
      {/* Desktop Persistent Sidebar */}
      <aside className="hidden md:flex flex-col w-64 shrink-0 h-screen sticky top-0 z-30">
        {navContent}
      </aside>

      {/* Mobile Off-canvas Drawer Backdrop */}
      {mobileNavOpen && (
        <div
          className="fixed inset-0 bg-slate-900/40 backdrop-blur-xs z-40 md:hidden transition-opacity"
          onClick={() => dispatch(setMobileNavOpen(false))}
          aria-hidden="true"
        />
      )}

      {/* Mobile Off-canvas Drawer */}
      <div
        className={`fixed inset-y-0 left-0 w-72 max-w-[85vw] bg-white z-50 md:hidden transform transition-transform duration-250 ease-in-out shadow-xl ${
          mobileNavOpen ? 'translate-x-0' : '-translate-x-full'
        }`}
      >
        {navContent}
      </div>
    </>
  );
}

