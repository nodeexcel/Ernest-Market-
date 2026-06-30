import { Card, CardHeader } from '../ui/Card';
import { ProgressBar } from '../ui/ProgressBar';
import { Badge } from '../ui/Badge';

export function ProcessingStatus({ status }) {
  if (!status) return null;

  const isRunning = status.status === 'running';
  const variant =
    status.status === 'running'
      ? 'brand'
      : status.status === 'completed'
        ? 'success'
        : status.status === 'failed'
          ? 'danger'
          : 'default';

  return (
    <Card>
      <CardHeader
        title="Live Processing Status"
        subtitle={status.current_step || 'Waiting for next scan'}
        action={
          <Badge variant={variant} dot>
            {status.status}
          </Badge>
        }
      />
      <ProgressBar
        value={status.progress?.percent || 0}
        className={isRunning ? 'mb-4' : 'mb-2'}
      />
      <div className="grid grid-cols-2 gap-3 text-sm sm:grid-cols-4">
        <Metric label="Rules" value={`${status.progress?.current || 0} / ${status.progress?.total || 0}`} />
        <Metric label="Fetched" value={status.stats?.listings_fetched ?? '—'} />
        <Metric label="Qualified" value={status.stats?.listings_qualified ?? '—'} />
        <Metric label="Alerts" value={status.stats?.alerts_sent ?? '—'} />
      </div>
    </Card>
  );
}

function Metric({ label, value }) {
  return (
    <div className="rounded-xl bg-slate-50 px-3 py-2">
      <p className="text-xs text-slate-500">{label}</p>
      <p className="mt-0.5 font-semibold text-slate-900">{value}</p>
    </div>
  );
}
