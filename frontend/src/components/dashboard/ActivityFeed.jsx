import { Card, CardHeader } from '../ui/Card';
import { Badge } from '../ui/Badge';
import clsx from 'clsx';

const LEVEL_STYLES = {
  INFO: 'text-slate-600',
  WARNING: 'text-amber-600',
  ERROR: 'text-rose-600',
  DEBUG: 'text-slate-400',
};

export function ActivityFeed({ logs = [], loading }) {
  return (
    <Card className="flex h-full flex-col">
      <CardHeader title="Recent Activity" subtitle="Live pipeline log feed" />
      <div className="scrollbar-thin max-h-80 flex-1 space-y-2 overflow-y-auto pr-1">
        {loading && logs.length === 0 && (
          <p className="py-8 text-center text-sm text-slate-500">Loading activity…</p>
        )}
        {!loading && logs.length === 0 && (
          <p className="py-8 text-center text-sm text-slate-500">No recent activity yet.</p>
        )}
        {logs
          .slice()
          .reverse()
          .map((log, index) => (
            <div
              key={`${log.timestamp}-${index}`}
              className="animate-fade-in rounded-xl border border-slate-100 bg-slate-50/80 px-3 py-2.5"
            >
              <div className="flex items-center justify-between gap-2">
                <span className="text-[11px] font-medium text-slate-400">
                  {log.timestamp || '—'}
                </span>
                {log.level && (
                  <Badge variant={log.level === 'ERROR' ? 'danger' : log.level === 'WARNING' ? 'warning' : 'default'}>
                    {log.level}
                  </Badge>
                )}
              </div>
              <p className={clsx('mt-1 text-sm leading-relaxed', LEVEL_STYLES[log.level] || 'text-slate-700')}>
                {log.message}
              </p>
            </div>
          ))}
      </div>
    </Card>
  );
}
