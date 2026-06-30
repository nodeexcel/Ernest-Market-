import { useEffect, useState } from 'react';
import { Calendar, Download, History } from 'lucide-react';
import { Card, CardHeader } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import { Badge } from '../components/ui/Badge';
import { Spinner } from '../components/ui/Spinner';
import { EmptyState } from '../components/ui/EmptyState';
import { useToast } from '../context/ToastContext';
import { historyApi } from '../services/api';

function formatDate(value) {
  if (!value) return '—';
  try {
    return new Date(value).toLocaleString();
  } catch {
    return value;
  }
}

export default function HistoryPage() {
  const { toast } = useToast();
  const [entries, setEntries] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    historyApi
      .list()
      .then(setEntries)
      .catch(setError)
      .finally(() => setLoading(false));
  }, []);

  const handleExport = (id, format) => {
    window.open(historyApi.exportUrl(id, format), '_blank');
    toast(`Downloading ${format.toUpperCase()} snapshot…`, 'success');
  };

  if (loading) return <Spinner label="Loading scan history…" />;

  if (error) {
    return (
      <Card className="border-rose-200 bg-rose-50 text-sm text-rose-700">
        {error.message}
      </Card>
    );
  }

  return (
    <div className="space-y-6 animate-fade-in">
      <Card>
        <CardHeader
          title="Scan History"
          subtitle="Previous runs triggered from the dashboard"
        />
      </Card>

      {entries.length === 0 ? (
        <EmptyState
          icon={History}
          title="No scan history yet"
          description="Start a scan from the Overview or Live Processing page to see run history here."
        />
      ) : (
        <div className="space-y-4">
          {entries.map((entry) => (
            <Card key={entry.id} className="animate-slide-up">
              <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
                <div className="space-y-2">
                  <div className="flex flex-wrap items-center gap-2">
                    <Badge variant={entry.status === 'completed' ? 'success' : 'danger'} dot>
                      {entry.status}
                    </Badge>
                    <Badge variant="default">{entry.mode === 'dry_run' ? 'Dry Run' : 'Full Scan'}</Badge>
                  </div>
                  <div className="flex flex-wrap gap-4 text-sm text-slate-600">
                    <span className="inline-flex items-center gap-1.5">
                      <Calendar className="h-4 w-4 text-slate-400" />
                      Started: {formatDate(entry.started_at)}
                    </span>
                    <span>Completed: {formatDate(entry.completed_at)}</span>
                  </div>
                  {entry.stats && (
                    <div className="flex flex-wrap gap-3 text-sm">
                      <StatPill label="Fetched" value={entry.stats.listings_fetched} />
                      <StatPill label="Qualified" value={entry.stats.listings_qualified} />
                      <StatPill label="Alerts" value={entry.stats.alerts_sent} />
                      <StatPill label="Errors" value={entry.stats.errors} />
                    </div>
                  )}
                  {entry.error && (
                    <p className="text-sm text-rose-600">{entry.error}</p>
                  )}
                </div>
                <div className="flex shrink-0 gap-2">
                  <Button variant="secondary" size="sm" onClick={() => handleExport(entry.id, 'csv')}>
                    <Download className="h-4 w-4" />
                    CSV
                  </Button>
                  <Button size="sm" onClick={() => handleExport(entry.id, 'xlsx')}>
                    <Download className="h-4 w-4" />
                    Excel
                  </Button>
                </div>
              </div>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}

function StatPill({ label, value }) {
  return (
    <span className="rounded-lg bg-slate-100 px-2.5 py-1 font-medium text-slate-700">
      {label}: <strong>{value ?? 0}</strong>
    </span>
  );
}
