import { Card } from '../ui/Card';
import clsx from 'clsx';

const ACCENTS = {
  brand: 'from-brand-500 to-brand-600',
  emerald: 'from-emerald-500 to-emerald-600',
  sky: 'from-sky-500 to-sky-600',
  amber: 'from-amber-500 to-amber-600',
  rose: 'from-rose-500 to-rose-600',
};

export function StatCard({ label, value, hint, icon: Icon, accent = 'brand', trend }) {
  return (
    <Card className="animate-fade-in overflow-hidden">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-sm font-medium text-slate-500">{label}</p>
          <p className="mt-2 text-2xl font-bold tracking-tight text-slate-900">{value}</p>
          {hint && <p className="mt-1 text-xs text-slate-500">{hint}</p>}
          {trend && <p className="mt-2 text-xs font-medium text-emerald-600">{trend}</p>}
        </div>
        {Icon && (
          <div
            className={clsx(
              'flex h-11 w-11 items-center justify-center rounded-xl bg-gradient-to-br text-white shadow-lg',
              ACCENTS[accent],
            )}
          >
            <Icon className="h-5 w-5" />
          </div>
        )}
      </div>
    </Card>
  );
}
