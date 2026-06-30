import clsx from 'clsx';

export function ProgressBar({ value = 0, className, showLabel = true }) {
  const clamped = Math.min(100, Math.max(0, value));
  return (
    <div className={clsx('w-full', className)}>
      {showLabel && (
        <div className="mb-2 flex items-center justify-between text-xs font-medium text-slate-600">
          <span>Progress</span>
          <span>{clamped.toFixed(0)}%</span>
        </div>
      )}
      <div className="h-2.5 overflow-hidden rounded-full bg-slate-100">
        <div
          className="h-full rounded-full bg-gradient-to-r from-brand-500 to-brand-600 transition-all duration-500 ease-out"
          style={{ width: `${clamped}%` }}
        />
      </div>
    </div>
  );
}
