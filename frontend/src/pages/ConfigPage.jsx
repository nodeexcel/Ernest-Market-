import { useCallback, useEffect, useState } from 'react';
import { Plus, Save, Settings, Trash2 } from 'lucide-react';
import { Card, CardHeader } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import { Spinner } from '../components/ui/Spinner';
import { Badge } from '../components/ui/Badge';
import { useToast } from '../context/ToastContext';
import { configApi } from '../services/api';

const EMPTY_RULE = {
  keyword: '',
  max_price: 10,
  min_price: 1,
  match_in: 'title',
  exclude_words: [],
};

export default function ConfigPage() {
  const { toast } = useToast();
  const [rules, setRules] = useState([]);
  const [settings, setSettings] = useState(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [errors, setErrors] = useState({});

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [rulesData, settingsData] = await Promise.all([
        configApi.getRules(),
        configApi.getSettings(),
      ]);
      setRules(rulesData.rules);
      setSettings(settingsData);
    } catch (err) {
      toast(err.message, 'error');
    } finally {
      setLoading(false);
    }
  }, [toast]);

  useEffect(() => {
    load();
  }, [load]);

  const validate = () => {
    const next = {};
    rules.forEach((rule, index) => {
      if (!rule.keyword.trim()) next[`keyword-${index}`] = 'Keyword is required';
      if (rule.max_price <= 0) next[`max-${index}`] = 'Max price must be > 0';
      if (rule.min_price < 0) next[`min-${index}`] = 'Min price must be >= 0';
      if (rule.min_price > rule.max_price) next[`min-${index}`] = 'Min cannot exceed max';
    });
    setErrors(next);
    return Object.keys(next).length === 0;
  };

  const handleSave = async () => {
    if (!validate()) {
      toast('Please fix validation errors before saving.', 'error');
      return;
    }
    setSaving(true);
    try {
      const result = await configApi.saveRules({ rules, rule_count: rules.length });
      toast(result.message, 'success');
    } catch (err) {
      toast(err.message, 'error');
    } finally {
      setSaving(false);
    }
  };

  const updateRule = (index, field, value) => {
    setRules((prev) =>
      prev.map((rule, i) => (i === index ? { ...rule, [field]: value } : rule)),
    );
  };

  const addRule = () => setRules((prev) => [...prev, { ...EMPTY_RULE }]);

  const removeRule = (index) => setRules((prev) => prev.filter((_, i) => i !== index));

  if (loading) return <Spinner label="Loading configuration…" />;

  return (
    <div className="space-y-6 animate-fade-in">
      {settings && (
        <Card>
          <CardHeader title="Runtime Settings" subtitle="Read from .env (edit file to change secrets)" />
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            <Setting label="eBay Backend" value={settings.ebay_backend} />
            <Setting label="Marketplace" value={settings.ebay_marketplace_id} />
            <Setting label="Rules / Run" value={settings.rules_per_run} />
            <Setting label="Alert Cap" value={settings.max_alerts_per_run} />
            <Setting label="Price Buffer" value={`${settings.max_price_tolerance_percent}%`} />
            <Setting label="Poll Interval" value={`${settings.poll_interval_minutes} min`} />
            <Setting label="Telegram" value={settings.telegram_configured ? 'Connected' : 'Missing'} />
            <Setting label="Google Sheets" value={settings.google_sheets_configured ? 'Connected' : 'Missing'} />
          </div>
        </Card>
      )}

      <Card>
        <CardHeader
          title="Buy Rules"
          subtitle={`${rules.length} keyword rules in config.yaml`}
          action={
            <div className="flex gap-2">
              <Button variant="secondary" size="sm" onClick={addRule}>
                <Plus className="h-4 w-4" />
                Add Rule
              </Button>
              <Button size="sm" loading={saving} onClick={handleSave}>
                <Save className="h-4 w-4" />
                Save Rules
              </Button>
            </div>
          }
        />

        <div className="space-y-4">
          {rules.map((rule, index) => (
            <div
              key={index}
              className="rounded-xl border border-slate-200 bg-slate-50/50 p-4 transition hover:border-slate-300"
            >
              <div className="mb-3 flex items-center justify-between">
                <Badge variant="brand">Rule {index + 1}</Badge>
                <button
                  type="button"
                  onClick={() => removeRule(index)}
                  className="rounded-lg p-1.5 text-slate-400 transition hover:bg-rose-50 hover:text-rose-600"
                >
                  <Trash2 className="h-4 w-4" />
                </button>
              </div>

              <div className="grid gap-3 md:grid-cols-2 lg:grid-cols-3">
                <Field label="Keyword" error={errors[`keyword-${index}`]}>
                  <input
                    value={rule.keyword}
                    onChange={(e) => updateRule(index, 'keyword', e.target.value)}
                    className="field-input"
                    placeholder="e.g. Dexcom G7 sensor"
                  />
                </Field>
                <Field label="Min Price ($)" error={errors[`min-${index}`]}>
                  <input
                    type="number"
                    value={rule.min_price}
                    onChange={(e) => updateRule(index, 'min_price', parseFloat(e.target.value) || 0)}
                    className="field-input"
                  />
                </Field>
                <Field label="Max Price ($)" error={errors[`max-${index}`]}>
                  <input
                    type="number"
                    value={rule.max_price}
                    onChange={(e) => updateRule(index, 'max_price', parseFloat(e.target.value) || 0)}
                    className="field-input"
                  />
                </Field>
                <Field label="Match In">
                  <select
                    value={rule.match_in}
                    onChange={(e) => updateRule(index, 'match_in', e.target.value)}
                    className="field-input"
                  >
                    <option value="title">Title</option>
                    <option value="title_and_description">Title & Description</option>
                  </select>
                </Field>
                <Field label="Exclude Words (comma-separated)">
                  <input
                    value={(rule.exclude_words || []).join(', ')}
                    onChange={(e) =>
                      updateRule(
                        index,
                        'exclude_words',
                        e.target.value.split(',').map((w) => w.trim()).filter(Boolean),
                      )
                    }
                    className="field-input"
                    placeholder="expired, opened, for parts"
                  />
                </Field>
              </div>
            </div>
          ))}
        </div>

        {rules.length === 0 && (
          <div className="flex flex-col items-center py-12 text-center">
            <Settings className="mb-3 h-10 w-10 text-slate-300" />
            <p className="text-sm text-slate-500">No buy rules configured. Add your first rule above.</p>
          </div>
        )}
      </Card>

      <style>{`
        .field-input {
          width: 100%;
          border-radius: 0.75rem;
          border: 1px solid #e2e8f0;
          background: white;
          padding: 0.625rem 0.875rem;
          font-size: 0.875rem;
          outline: none;
        }
        .field-input:focus {
          box-shadow: 0 0 0 2px #6366f1;
        }
      `}</style>
    </div>
  );
}

function Field({ label, error, children }) {
  return (
    <label className="block">
      <span className="mb-1 block text-xs font-medium text-slate-600">{label}</span>
      {children}
      {error && <span className="mt-1 block text-xs text-rose-600">{error}</span>}
    </label>
  );
}

function Setting({ label, value }) {
  return (
    <div className="rounded-xl border border-slate-200 bg-white px-3 py-2.5">
      <p className="text-xs text-slate-500">{label}</p>
      <p className="mt-0.5 text-sm font-semibold capitalize text-slate-900">{value}</p>
    </div>
  );
}
