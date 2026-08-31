import { AlertTriangle } from 'lucide-react';
import React, { useCallback, useEffect, useState } from 'react';
import { InlineError, LoadingBlock } from '../components/StatusBlocks';
import { adminDatasetApi, ApiError } from '../lib/api';
import type { UnmatchedIngredientGroupOut, ValidationIssueOut } from '../lib/types';
import { PageHeader } from './OverviewPage';

function errMsg(err: unknown, fallback: string) {
  return err instanceof ApiError ? err.message : fallback;
}

export default function DatasetPage() {
  const [issues, setIssues] = useState<ValidationIssueOut[]>([]);
  const [unmatched, setUnmatched] = useState<UnmatchedIngredientGroupOut[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [resolvingFor, setResolvingFor] = useState<string | null>(null);
  const [ingredientIdDraft, setIngredientIdDraft] = useState('');
  const [saving, setSaving] = useState(false);

  const load = useCallback(() => {
    setLoading(true);
    setError(null);
    Promise.all([adminDatasetApi.validate(), adminDatasetApi.unmatchedIngredients()])
      .then(([v, u]) => {
        setIssues(v);
        setUnmatched(u);
      })
      .catch((err) => setError(errMsg(err, 'Could not load the dataset overview.')))
      .finally(() => setLoading(false));
  }, []);

  useEffect(load, [load]);

  async function resolve(rawName: string) {
    if (!ingredientIdDraft.trim()) return;
    setSaving(true);
    setError(null);
    try {
      await adminDatasetApi.resolveUnmatchedIngredient(rawName, ingredientIdDraft.trim());
      setUnmatched((prev) => prev.filter((u) => u.raw_name !== rawName));
      setResolvingFor(null);
      setIngredientIdDraft('');
    } catch (err) {
      setError(errMsg(err, 'Could not resolve that ingredient. Check the canonical id.'));
    } finally {
      setSaving(false);
    }
  }

  const errors = issues.filter((i) => i.severity === 'error');
  const warnings = issues.filter((i) => i.severity === 'warning');

  return (
    <div>
      <PageHeader title="Dataset" subtitle="Validation issues and ingredient lines that didn't match the taxonomy." />

      {loading && <LoadingBlock label="Validating the dataset…" />}
      {!loading && error && (
        <div className="mb-4">
          <InlineError message={error} />
        </div>
      )}

      {!loading && (
        <>
          <Section title={`Validation issues (${errors.length} errors, ${warnings.length} warnings)`}>
            {issues.length === 0 ? (
              <p className="font-body text-sm text-ticket-dim text-center py-6">
                The curated dataset passed validation cleanly.
              </p>
            ) : (
              <div className="space-y-2 max-h-[420px] overflow-y-auto pr-1">
                {issues.map((issue, idx) => (
                  <div
                    key={`${issue.recipe_id}-${idx}`}
                    className={`flex items-start gap-3 rounded-lg px-4 py-3 border ${
                      issue.severity === 'error' ? 'bg-rust-container border-rust/30' : 'bg-backstage-high border-line'
                    }`}
                  >
                    <AlertTriangle
                      size={14}
                      className={`mt-0.5 shrink-0 ${issue.severity === 'error' ? 'text-rust' : 'text-ember'}`}
                    />
                    <div>
                      <p className="font-body text-sm text-ticket">{issue.recipe_name}</p>
                      <p className="font-mono-ticket text-[10px] text-ticket-faint mt-0.5">{issue.issue}</p>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </Section>

          <Section title={`Unmatched ingredient lines (${unmatched.length})`}>
            {unmatched.length === 0 ? (
              <p className="font-body text-sm text-ticket-dim text-center py-6">
                Every ingredient line matches the canonical taxonomy.
              </p>
            ) : (
              <div className="space-y-2.5">
                {unmatched.map((group) => (
                  <div key={group.raw_name} className="rounded-lg border border-line p-4">
                    <div className="flex flex-wrap items-center justify-between gap-3">
                      <div>
                        <p className="font-body text-sm text-ticket">"{group.raw_name}"</p>
                        <p className="font-mono-ticket text-[10px] text-ticket-faint mt-0.5">
                          {group.occurrence_count} occurrence{group.occurrence_count === 1 ? '' : 's'} · e.g.{' '}
                          {group.sample_recipe_ids.slice(0, 3).join(', ')}
                        </p>
                      </div>
                      <button
                        onClick={() => setResolvingFor(resolvingFor === group.raw_name ? null : group.raw_name)}
                        className="bg-ember text-backstage px-4 py-2 rounded-lg font-body text-xs font-semibold shrink-0 hover:bg-ember-dim transition-colors"
                      >
                        Resolve
                      </button>
                    </div>

                    {resolvingFor === group.raw_name && (
                      <div className="mt-3 flex flex-col sm:flex-row gap-2">
                        <input
                          type="text"
                          placeholder="Canonical ingredient id, e.g. ing_coconut_milk"
                          value={ingredientIdDraft}
                          onChange={(e) => setIngredientIdDraft(e.target.value)}
                          className="flex-1 h-10 px-4 rounded-lg bg-backstage border border-line text-ticket font-mono-ticket text-xs focus:outline-none focus:ring-2 focus:ring-ember/40"
                        />
                        <button
                          onClick={() => resolve(group.raw_name)}
                          disabled={saving || !ingredientIdDraft.trim()}
                          className="h-10 px-5 rounded-lg bg-ember text-backstage font-body text-xs font-semibold shrink-0 disabled:opacity-50 hover:bg-ember-dim transition-colors"
                        >
                          {saving ? 'Saving…' : 'Assign'}
                        </button>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </Section>
        </>
      )}
    </div>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="chit p-6 mb-5">
      <h2 className="font-display text-sm font-semibold text-ticket mb-4">{title}</h2>
      {children}
    </section>
  );
}
