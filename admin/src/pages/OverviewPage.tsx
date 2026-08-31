import React, { useCallback, useEffect, useState } from 'react';
import { ErrorBlock, LoadingBlock } from '../components/StatusBlocks';
import { adminDashboardApi, ApiError } from '../lib/api';
import type { DashboardSummaryOut } from '../lib/types';

function errMsg(err: unknown, fallback: string) {
  return err instanceof ApiError ? err.message : fallback;
}

export default function OverviewPage() {
  const [summary, setSummary] = useState<DashboardSummaryOut | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(() => {
    setLoading(true);
    setError(null);
    adminDashboardApi
      .summary()
      .then(setSummary)
      .catch((err) => setError(errMsg(err, 'Could not load the dashboard summary.')))
      .finally(() => setLoading(false));
  }, []);

  useEffect(load, [load]);

  return (
    <div>
      <PageHeader
        title="Overview"
        subtitle="A snapshot of what's on the pass right now."
      />

      {loading && <LoadingBlock label="Pulling the numbers…" />}
      {!loading && error && <ErrorBlock message={error} onRetry={load} />}

      {!loading && !error && summary && (
        <>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-6">
            <Stat label="Total recipes" value={summary.total_recipes} />
            <Stat label="Pending moderation" value={summary.pending_recipe_moderation} tone={summary.pending_recipe_moderation > 0 ? 'ember' : undefined} />
            <Stat label="Pending tag proposals" value={summary.pending_occasion_tag_proposals} tone={summary.pending_occasion_tag_proposals > 0 ? 'ember' : undefined} />
            <Stat label="Below trust threshold" value={summary.recipes_below_trust_threshold} tone={summary.recipes_below_trust_threshold > 0 ? 'rust' : undefined} />
            <Stat label="Unmatched ingredient lines" value={summary.unmatched_ingredient_lines} tone={summary.unmatched_ingredient_lines > 0 ? 'rust' : undefined} />
            <Stat label="Total users" value={summary.total_users} />
            <Stat label="Total reviews" value={summary.total_reviews} />
          </div>

          <div className="chit p-6">
            <h2 className="font-display text-sm font-semibold text-ticket mb-4">Recipes by source type</h2>
            <div className="flex flex-wrap gap-2.5">
              {Object.entries(summary.recipes_by_source_type).map(([source, count]) => (
                <div
                  key={source}
                  className="flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-backstage-high border border-line"
                >
                  <span className="font-mono-ticket text-[11px] uppercase tracking-wide text-ticket-dim">{source}</span>
                  <span className="font-display text-sm text-ticket">{count}</span>
                </div>
              ))}
            </div>
          </div>
        </>
      )}
    </div>
  );
}

export function PageHeader({ title, subtitle }: { title: string; subtitle: string }) {
  return (
    <div className="mb-7">
      <h1 className="font-display text-2xl font-semibold text-ticket">{title}</h1>
      <p className="font-body text-sm text-ticket-dim mt-1">{subtitle}</p>
    </div>
  );
}

function Stat({ label, value, tone }: { label: string; value: number; tone?: 'ember' | 'rust' }) {
  const valueColor = tone === 'ember' ? 'text-ember' : tone === 'rust' ? 'text-rust' : 'text-ticket';
  return (
    <div className="chit p-4">
      <p className={`font-display text-2xl font-semibold ${valueColor}`}>{value}</p>
      <p className="font-mono-ticket text-[10px] uppercase tracking-wide text-ticket-faint mt-1">{label}</p>
    </div>
  );
}
