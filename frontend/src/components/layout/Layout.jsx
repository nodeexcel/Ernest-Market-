import { useState } from 'react';
import { Outlet, useLocation } from 'react-router-dom';
import { Sidebar } from './Sidebar';
import { Header } from './Header';
import { useScanStatus } from '../../hooks/useScanStatus';
import clsx from 'clsx';
import {
  Activity,
  History,
  LayoutDashboard,
  PackageSearch,
  Settings,
  Table2,
  X,
} from 'lucide-react';
import { NavLink } from 'react-router-dom';

const PAGE_META = {
  '/': { title: 'Overview', subtitle: 'Monitor marketplace scans and deal pipeline health' },
  '/processing': { title: 'Live Processing', subtitle: 'Real-time scan progress and activity feed' },
  '/results': { title: 'Results', subtitle: 'Qualified deals logged from eBay' },
  '/config': { title: 'Configuration', subtitle: 'Manage buy rules and runtime settings' },
  '/history': { title: 'History', subtitle: 'Previous scan runs and downloadable exports' },
};

const MOBILE_NAV = [
  { to: '/', label: 'Overview', icon: LayoutDashboard },
  { to: '/processing', label: 'Processing', icon: Activity },
  { to: '/results', label: 'Results', icon: Table2 },
  { to: '/config', label: 'Config', icon: Settings },
  { to: '/history', label: 'History', icon: History },
];

export function Layout() {
  const location = useLocation();
  const { data: scanStatus } = useScanStatus();
  const [mobileOpen, setMobileOpen] = useState(false);
  const meta = PAGE_META[location.pathname] || PAGE_META['/'];

  return (
    <div className="flex min-h-screen bg-slate-50">
      <Sidebar />

      {mobileOpen && (
        <div className="fixed inset-0 z-40 lg:hidden">
          <button
            type="button"
            className="absolute inset-0 bg-slate-900/40"
            onClick={() => setMobileOpen(false)}
          />
          <div className="absolute left-0 top-0 flex h-full w-72 flex-col bg-white shadow-xl">
            <div className="flex h-16 items-center justify-between border-b border-slate-200 px-4">
              <div className="flex items-center gap-2">
                <PackageSearch className="h-5 w-5 text-brand-600" />
                <span className="font-bold text-slate-900">Ernest Market</span>
              </div>
              <button type="button" onClick={() => setMobileOpen(false)} className="rounded-lg p-2 hover:bg-slate-100">
                <X className="h-5 w-5" />
              </button>
            </div>
            <nav className="space-y-1 p-3">
              {MOBILE_NAV.map(({ to, label, icon: Icon }) => (
                <NavLink
                  key={to}
                  to={to}
                  end={to === '/'}
                  onClick={() => setMobileOpen(false)}
                  className={({ isActive }) =>
                    clsx(
                      'flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium',
                      isActive ? 'bg-brand-50 text-brand-700' : 'text-slate-600 hover:bg-slate-50',
                    )
                  }
                >
                  <Icon className="h-4 w-4" />
                  {label}
                </NavLink>
              ))}
            </nav>
          </div>
        </div>
      )}

      <div className="flex min-w-0 flex-1 flex-col">
        <Header
          title={meta.title}
          subtitle={meta.subtitle}
          status={scanStatus?.status}
          onMenuClick={() => setMobileOpen(true)}
        />
        <main className="flex-1 p-4 sm:p-6 lg:p-8">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
