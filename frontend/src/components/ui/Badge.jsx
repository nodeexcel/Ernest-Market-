import clsx from 'clsx';

const styles = {
  default: 'bg-slate-100 text-slate-700',
  success: 'bg-emerald-100 text-emerald-700',
  warning: 'bg-amber-100 text-amber-700',
  danger: 'bg-rose-100 text-rose-700',
  brand: 'bg-brand-100 text-brand-700',
  info: 'bg-sky-100 text-sky-700',
};

export function Badge({ children, variant = 'default', className, dot = false }) {
  return (
    <span
      className={clsx(
        'inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-medium',
        styles[variant],
        className,
      )}
    >
      {dot && (
        <span
          className={clsx('h-1.5 w-1.5 rounded-full', {
            'bg-emerald-500': variant === 'success',
            'bg-amber-500': variant === 'warning',
            'bg-rose-500': variant === 'danger',
            'bg-brand-500': variant === 'brand',
            'bg-sky-500': variant === 'info',
            'bg-slate-500': variant === 'default',
          })}
        />
      )}
      {children}
    </span>
  );
}
