import { useState } from 'react';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts';
import {
  AlertTriangle,
  CheckCircle2,
  Download,
  Package,
  Play,
  Search,
  Target,
} from 'lucide-react';
import { StatCard } from '../components/dashboard/StatCard';
import { ProcessingStatus } from '../components/dashboard/ProcessingStatus';
import { ActivityFeed } from '../components/dashboard/ActivityFeed';
import { Card, CardHeader } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import { Spinner } from '../components/ui/Spinner';
import { usePolling } from '../hooks/usePolling';
import { useScanStatus } from '../hooks/useScanStatus';
import { useToast } from '../context/ToastContext';
import { dashboardApi, dealsApi, scanApi } from '../services/api';

function formatDate(value) {
  if (!value) return 'Never';
  try {
    return new Date(value).toLocaleString();
  } catch {
    return value;
  }
}

export default function DashboardPage() {
  const { toast } = useToast();
  const [starting, setStarting] = useState(false);
  const { data: overview, loading, error, refresh } = usePolling(dashboardApi.getOverview, 8000);
  const { data: scanStatus } = useScanStatus();
  const { data: logs } = usePolling(() => scanApi.getLogs(40), 4000);
  const { data: exportStatus } = usePolling(dealsApi.exportStatus, 15000);

  const handleStartScan = async (mode) => {
    setStarting(true);
    try {
      const result = await scanApi.start(mode);
      toast(result.message, 'success');
      refresh();
    } catch (err) {
      toast(err.message, 'error');
    } finally {
      setStarting(false);
    }
  };

  if (loading && !overview) return <Spinner label="Loading dashboard…" />;

  if (error && !overview) {
    return (
      <Card className="border-rose-200 bg-rose-50">
        <div className="flex items-start gap-3 text-rose-800">
          <AlertTriangle className="mt-0.5 h-5 w-5" />
          <div>
            <p className="font-semibold">Unable to load dashboard</p>
            <p className="mt-1 text-sm">{error.message}</p>
            <p className="mt-2 text-sm">
              Check that the API server is running and reachable.
            </p>
          </div>
        </div>
      </Card>
    );
  }

  const stats = overview?.last_stats;
  const chartData = [
    { name: 'Fetched', value: stats?.listings_fetched || 0 },
    { name: 'Qualified', value: stats?.listings_qualified || 0 },
    { name: 'Alerts', value: stats?.alerts_sent || 0 },
    { name: 'Skipped', value: stats?.listings_skipped_seen || 0 },
  ];

  return (
    <div className="space-y-6 animate-fade-in">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <p className="text-sm text-slate-500">Last scan: {formatDate(overview?.last_scan_at)}</p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Button variant="secondary" loading={starting} onClick={() => handleStartScan('dry_run')}>
            <Search className="h-4 w-4" />
            Dry Run
          </Button>
          <Button loading={starting} onClick={() => handleStartScan('full')}>
            <Play className="h-4 w-4" />
            Start Full Scan
          </Button>
          {exportStatus?.ready && (
            <a href={dealsApi.exportUrl('xlsx')} download>
              <Button variant="secondary">
                <Download className="h-4 w-4" />
                Export Excel
              </Button>
            </a>
          )}
        </div>
      </div>

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <StatCard
          label="Products Processed"
          value={stats?.listings_fetched?.toLocaleString() ?? '0'}
          hint="Listings fetched last run"
          icon={Package}
          accent="brand"
        />
        <StatCard
          label="Matching Products"
          value={stats?.listings_qualified?.toLocaleString() ?? '0'}
          hint="Passed keyword & price filters"
          icon={Target}
          accent="emerald"
        />
        <StatCard
          label="Deals Logged"
          value={overview?.total_deals_logged?.toLocaleString() ?? '0'}
          hint="Total rows in Google Sheet"
          icon={CheckCircle2}
          accent="sky"
        />
        <StatCard
          label="Active Rules"
          value={overview?.total_rules ?? 0}
          hint={`${overview?.rules_per_run} rules per scheduled run`}
          icon={Search}
          accent="amber"
        />
      </div>

      <ProcessingStatus status={scanStatus} />

      <div className="grid gap-6 xl:grid-cols-3">
        <Card className="xl:col-span-2">
          <CardHeader title="Pipeline Breakdown" subtitle="Last completed scan metrics" />
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={chartData} barSize={48}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e2e8f0" />
                <XAxis dataKey="name" tick={{ fontSize: 12 }} axisLine={false} tickLine={false} />
                <YAxis tick={{ fontSize: 12 }} axisLine={false} tickLine={false} />
                <Tooltip
                  contentStyle={{
                    borderRadius: '12px',
                    border: '1px solid #e2e8f0',
                    boxShadow: '0 4px 12px rgba(0,0,0,0.08)',
                  }}
                />
                <Bar dataKey="value" fill="#6366f1" radius={[8, 8, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </Card>

        <Card>
          <CardHeader title="System Status" subtitle="Runtime configuration" />
          <dl className="space-y-3 text-sm">
            <Row label="Processing" value={overview?.processing_status} />
            <Row label="eBay Backend" value={overview?.ebay_backend} />
            <Row label="Seen Listings" value={`${overview?.seen_listings} / ${overview?.seen_capacity}`} />
            <Row label="Poll Interval" value={`${overview?.poll_interval_minutes} min`} />
            <Row label="Alert Cap" value={overview?.max_alerts_per_run} />
          </dl>
        </Card>
      </div>

      <ActivityFeed logs={logs || []} loading={!logs} />
    </div>
  );
}

function Row({ label, value }) {
  return (
    <div className="flex items-center justify-between rounded-lg bg-slate-50 px-3 py-2">
      <dt className="text-slate-500">{label}</dt>
      <dd className="font-medium capitalize text-slate-900">{value}</dd>
    </div>
  );
}
