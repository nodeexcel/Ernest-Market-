import { useState } from 'react';
import { Play, RefreshCw, Search } from 'lucide-react';
import { ProcessingStatus } from '../components/dashboard/ProcessingStatus';
import { ActivityFeed } from '../components/dashboard/ActivityFeed';
import { Card, CardHeader } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import { Badge } from '../components/ui/Badge';
import { useScanStatus } from '../hooks/useScanStatus';
import { usePolling } from '../hooks/usePolling';
import { useToast } from '../context/ToastContext';
import { scanApi } from '../services/api';

const STEPS = [
  { key: 'init', label: 'Initialize pipeline' },
  { key: 'search', label: 'Search marketplaces' },
  { key: 'filter', label: 'Filter & qualify listings' },
  { key: 'dedupe', label: 'Deduplicate seen items' },
  { key: 'alert', label: 'Send Telegram & Sheets alerts' },
];

export default function ProcessingPage() {
  const { toast } = useToast();
  const [starting, setStarting] = useState(false);
  const { data: status, refresh } = useScanStatus(true);
  const { data: logs, refresh: refreshLogs } = usePolling(() => scanApi.getLogs(100), 3000);

  const isRunning = status?.status === 'running';
  const progress = status?.progress?.percent || 0;
  const activeStepIndex = Math.min(
    STEPS.length - 1,
    Math.floor((progress / 100) * STEPS.length),
  );

  const handleStart = async (mode) => {
    setStarting(true);
    try {
      const result = await scanApi.start(mode);
      toast(result.message, 'success');
      refresh();
      refreshLogs();
    } catch (err) {
      toast(err.message, 'error');
    } finally {
      setStarting(false);
    }
  };

  return (
    <div className="space-y-6 animate-fade-in">
      <Card>
        <CardHeader
          title="Scan Controls"
          subtitle="Trigger a new marketplace scan without changing the backend pipeline"
          action={
            <div className="flex flex-wrap gap-2">
              <Button variant="secondary" size="sm" onClick={() => { refresh(); refreshLogs(); }}>
                <RefreshCw className="h-4 w-4" />
                Refresh
              </Button>
              <Button
                variant="secondary"
                size="sm"
                loading={starting}
                disabled={isRunning}
                onClick={() => handleStart('dry_run')}
              >
                <Search className="h-4 w-4" />
                Dry Run
              </Button>
              <Button size="sm" loading={starting} disabled={isRunning} onClick={() => handleStart('full')}>
                <Play className="h-4 w-4" />
                Full Scan
              </Button>
            </div>
          }
        />

        <div className="grid gap-3 sm:grid-cols-5">
          {STEPS.map((step, index) => {
            const done = !isRunning && status?.status === 'completed' && index <= activeStepIndex;
            const active = isRunning && index === activeStepIndex;
            return (
              <div
                key={step.key}
                className={`rounded-xl border px-3 py-3 text-center transition-all ${
                  active
                    ? 'border-brand-300 bg-brand-50 shadow-sm'
                    : done
                      ? 'border-emerald-200 bg-emerald-50'
                      : 'border-slate-200 bg-slate-50'
                }`}
              >
                <p className="text-xs font-semibold text-slate-500">Step {index + 1}</p>
                <p className="mt-1 text-sm font-medium text-slate-800">{step.label}</p>
                {active && (
                  <Badge variant="brand" dot className="mt-2 animate-pulse-soft">
                    Running
                  </Badge>
                )}
                {done && !active && (
                  <Badge variant="success" className="mt-2">
                    Done
                  </Badge>
                )}
              </div>
            );
          })}
        </div>
      </Card>

      <ProcessingStatus status={status} />

      {status?.error && (
        <Card className="border-rose-200 bg-rose-50">
          <p className="text-sm font-semibold text-rose-800">Scan failed</p>
          <p className="mt-1 text-sm text-rose-700">{status.error}</p>
        </Card>
      )}

      <ActivityFeed logs={logs || []} loading={!logs} />
    </div>
  );
}
