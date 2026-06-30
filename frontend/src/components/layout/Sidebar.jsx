import { NavLink } from 'react-router-dom';
import {
  Activity,
  History,
  LayoutDashboard,
  PackageSearch,
  Settings,
  Table2,
} from 'lucide-react';
import clsx from 'clsx';

const NAV = [
  { to: '/', label: 'Overview', icon: LayoutDashboard },
  { to: '/processing', label: 'Live Processing', icon: Activity },
  { to: '/results', label: 'Results', icon: Table2 },
  { to: '/config', label: 'Configuration', icon: Settings },
  { to: '/history', label: 'History', icon: History },
];

export function Sidebar() {
  return (
    <aside className="hidden w-64 shrink-0 border-r border-slate-200 bg-white lg:flex lg:flex-col">
      <div className="flex h-16 items-center gap-3 border-b border-slate-200 px-6">
        <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-brand-600 text-white shadow-lg shadow-brand-600/30">
          <PackageSearch className="h-5 w-5" />
        </div>
        <div>
          <p className="text-sm font-bold text-slate-900">Ernest Market</p>
          <p className="text-xs text-slate-500">Deal Monitor</p>
        </div>
      </div>

      <nav className="flex-1 space-y-1 p-4">
        {NAV.map(({ to, label, icon: Icon }) => (
          <NavLink
            key={to}
            to={to}
            end={to === '/'}
            className={({ isActive }) =>
              clsx(
                'flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium transition-all',
                isActive
                  ? 'bg-brand-50 text-brand-700 shadow-sm'
                  : 'text-slate-600 hover:bg-slate-50 hover:text-slate-900',
              )
            }
          >
            <Icon className="h-4 w-4" />
            {label}
          </NavLink>
        ))}
      </nav>

      <div className="border-t border-slate-200 p-4">
        <div className="rounded-xl bg-slate-50 p-3">
          <p className="text-xs font-medium text-slate-500">Pipeline</p>
          <p className="mt-1 text-sm font-semibold text-slate-800">eBay Monitor</p>
          <p className="mt-0.5 text-xs text-slate-500">Telegram & Sheets alerts</p>
        </div>
      </div>
    </aside>
  );
}
