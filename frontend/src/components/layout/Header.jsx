import { Menu } from 'lucide-react';
import { Badge } from '../ui/Badge';

export function Header({ title, subtitle, status, onMenuClick, action }) {
  const statusVariant =
    status === 'running' ? 'brand' : status === 'completed' ? 'success' : status === 'failed' ? 'danger' : 'default';

  const statusLabel =
    status === 'running'
      ? 'Processing'
      : status === 'completed'
        ? 'Idle'
        : status === 'failed'
          ? 'Error'
          : 'Ready';

  return (
    <header className="sticky top-0 z-30 border-b border-slate-200 bg-white/90 backdrop-blur-md">
      <div className="flex h-16 items-center justify-between gap-4 px-4 sm:px-6 lg:px-8">
        <div className="flex items-center gap-3">
          <button
            type="button"
            onClick={onMenuClick}
            className="rounded-lg p-2 text-slate-600 hover:bg-slate-100 lg:hidden"
          >
            <Menu className="h-5 w-5" />
          </button>
          <div>
            <h1 className="text-lg font-bold text-slate-900 sm:text-xl">{title}</h1>
            {subtitle && <p className="text-sm text-slate-500">{subtitle}</p>}
          </div>
        </div>
        <div className="flex items-center gap-3">
          {status && (
            <Badge variant={statusVariant} dot className={status === 'running' ? 'animate-pulse-soft' : ''}>
              {statusLabel}
            </Badge>
          )}
          {action}
        </div>
      </div>
    </header>
  );
}
