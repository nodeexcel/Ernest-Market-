import { useCallback, useEffect, useState } from 'react';
import { Download, ExternalLink, Search, Table2 } from 'lucide-react';
import { Card, CardHeader } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import { Badge } from '../components/ui/Badge';
import { Spinner } from '../components/ui/Spinner';
import { EmptyState } from '../components/ui/EmptyState';
import { useToast } from '../context/ToastContext';
import { dealsApi } from '../services/api';

export default function ResultsPage() {
  const { toast } = useToast();
  const [data, setData] = useState(null);
  const [exportStatus, setExportStatus] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState('');
  const [marketplace, setMarketplace] = useState('all');
  const [debouncedSearch, setDebouncedSearch] = useState('');

  useEffect(() => {
    const id = setTimeout(() => setDebouncedSearch(search), 350);
    return () => clearTimeout(id);
  }, [search]);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [deals, status] = await Promise.all([
        dealsApi.list({ page, page_size: 15, search: debouncedSearch, marketplace }),
        dealsApi.exportStatus(),
      ]);
      setData(deals);
      setExportStatus(status);
      setError(null);
    } catch (err) {
      setError(err);
    } finally {
      setLoading(false);
    }
  }, [page, debouncedSearch, marketplace]);

  useEffect(() => {
    load();
  }, [load]);

  const handleExport = (format) => {
    if (!exportStatus?.ready) {
      toast('Spreadsheet is not ready for download yet.', 'info');
      return;
    }
    window.open(dealsApi.exportUrl(format), '_blank');
    toast(`Downloading ${format.toUpperCase()} file…`, 'success');
  };

  return (
    <div className="space-y-6 animate-fade-in">
      <Card>
        <CardHeader
          title="Spreadsheet Export"
          subtitle="Download qualified deals from Google Sheets"
          action={
            <div className="flex flex-wrap gap-2">
              <Button variant="secondary" size="sm" onClick={() => handleExport('csv')}>
                <Download className="h-4 w-4" />
                CSV
              </Button>
              <Button size="sm" onClick={() => handleExport('xlsx')} disabled={!exportStatus?.ready}>
                <Download className="h-4 w-4" />
                Excel (.xlsx)
              </Button>
            </div>
          }
        />
        <div className="flex flex-wrap items-center gap-4 text-sm">
          <Badge variant={exportStatus?.ready ? 'success' : 'warning'} dot>
            {exportStatus?.ready ? 'Ready for download' : 'Not available'}
          </Badge>
          <span className="text-slate-600">
            <strong>{exportStatus?.row_count ?? 0}</strong> deals logged
          </span>
          {exportStatus?.last_updated && (
            <span className="text-slate-500">Last updated: {exportStatus.last_updated}</span>
          )}
          {exportStatus?.google_sheet_url && (
            <a
              href={exportStatus.google_sheet_url}
              target="_blank"
              rel="noreferrer"
              className="inline-flex items-center gap-1 text-brand-600 hover:underline"
            >
              Open Google Sheet <ExternalLink className="h-3.5 w-3.5" />
            </a>
          )}
        </div>
      </Card>

      <Card>
        <CardHeader title="Results Table" subtitle="Sortable, searchable deal results" />
        <div className="mb-4 flex flex-col gap-3 sm:flex-row">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
            <input
              type="text"
              placeholder="Search title, keyword, or item ID…"
              value={search}
              onChange={(e) => {
                setSearch(e.target.value);
                setPage(1);
              }}
              className="w-full rounded-xl border border-slate-200 bg-white py-2.5 pl-10 pr-4 text-sm outline-none ring-brand-500 transition focus:ring-2"
            />
          </div>
          <select
            value={marketplace}
            onChange={(e) => {
              setMarketplace(e.target.value);
              setPage(1);
            }}
            className="rounded-xl border border-slate-200 bg-white px-4 py-2.5 text-sm outline-none ring-brand-500 focus:ring-2"
          >
            <option value="all">All listings</option>
            <option value="ebay">eBay</option>
          </select>
        </div>

        {loading && <Spinner label="Loading results…" />}

        {error && !loading && (
          <div className="rounded-xl border border-rose-200 bg-rose-50 p-4 text-sm text-rose-700">
            {error.message}
          </div>
        )}

        {!loading && !error && data?.items?.length === 0 && (
          <EmptyState
            icon={Table2}
            title="No deals found"
            description="Run a scan or adjust your filters to see qualified listings here."
          />
        )}

        {!loading && data?.items?.length > 0 && (
          <>
            <div className="overflow-x-auto rounded-xl border border-slate-200">
              <table className="min-w-full divide-y divide-slate-200 text-sm">
                <thead className="bg-slate-50">
                  <tr>
                    {['Time', 'Marketplace', 'Keyword', 'Title', 'Price', 'Condition', 'Link'].map((h) => (
                      <th key={h} className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-500">
                        {h}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 bg-white">
                  {data.items.map((deal) => (
                    <tr key={`${deal.item_id}-${deal.timestamp}`} className="transition hover:bg-slate-50/80">
                      <td className="whitespace-nowrap px-4 py-3 text-slate-500">{deal.timestamp}</td>
                      <td className="px-4 py-3">
                        <Badge variant="brand">
                          {deal.marketplace || 'ebay'}
                        </Badge>
                      </td>
                      <td className="px-4 py-3 font-medium text-slate-800">{deal.keyword}</td>
                      <td className="max-w-xs truncate px-4 py-3 text-slate-700" title={deal.title}>
                        {deal.title}
                      </td>
                      <td className="whitespace-nowrap px-4 py-3 font-semibold text-emerald-700">
                        ${Number(deal.price).toFixed(2)} {deal.currency}
                      </td>
                      <td className="px-4 py-3 text-slate-600">{deal.condition || '—'}</td>
                      <td className="px-4 py-3">
                        {deal.url ? (
                          <a
                            href={deal.url}
                            target="_blank"
                            rel="noreferrer"
                            className="inline-flex items-center gap-1 font-medium text-brand-600 hover:underline"
                          >
                            View <ExternalLink className="h-3.5 w-3.5" />
                          </a>
                        ) : (
                          '—'
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            <div className="mt-4 flex items-center justify-between">
              <p className="text-sm text-slate-500">
                Showing page {data.page} of {data.total_pages} ({data.total} total)
              </p>
              <div className="flex gap-2">
                <Button
                  variant="secondary"
                  size="sm"
                  disabled={page <= 1}
                  onClick={() => setPage((p) => p - 1)}
                >
                  Previous
                </Button>
                <Button
                  variant="secondary"
                  size="sm"
                  disabled={page >= data.total_pages}
                  onClick={() => setPage((p) => p + 1)}
                >
                  Next
                </Button>
              </div>
            </div>
          </>
        )}
      </Card>
    </div>
  );
}
