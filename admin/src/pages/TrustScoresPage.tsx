import React, { useCallback, useEffect, useState } from 'react';
import { InlineError, LoadingBlock } from '../components/StatusBlocks';
import { adminTrustScoresApi, ApiError } from '../lib/api';
import type { TrustScoreFlaggedRecipeOut } from '../lib/types';
import { PageHeader } from './OverviewPage';

function errMsg(err: unknown, fallback: string) {
  return err instanceof ApiError ? err.message : fallback;
}

export default function TrustScoresPage() {
  const [flagged, setFlagged] = useState<TrustScoreFlaggedRecipeOut[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [valueDraft, setValueDraft] = useState('');
  const [reasonDraft, setReasonDraft] = useState('');
  const [saving, setSaving] = useState(false);

  const load = useCallback(() => {
    setLoading(true);
    setError(null);
    adminTrustScoresApi
      .flagged()
      .then(setFlagged)
      .catch((err) => setError(errMsg(err, 'Could not load flagged recipes.')))
      .finally(() => setLoading(false));
  }, []);

  useEffect(load, [load]);

  function startEdit(recipe: TrustScoreFlaggedRecipeOut) {
    setEditingId(recipe.id);
    setValueDraft(recipe.trust_score.toFixed(2));
    setReasonDraft('');
  }

  async function submitOverride(recipeId: string) {
    const parsed = Number(valueDraft);
    if (Number.isNaN(parsed) || parsed < 0 || parsed > 1) {
      setError('Trust score must be a number between 0 and 1.');
      return;
    }
    setSaving(true);
    setError(null);
    try {
      await adminTrustScoresApi.override(recipeId, parsed, reasonDraft.trim() || undefined);
      setFlagged((prev) => prev.filter((r) => r.id !== recipeId));
      setEditingId(null);
    } catch (err) {
      setError(errMsg(err, 'Could not save that override.'));
    } finally {
      setSaving(false);
    }
  }

  return (
    <div>
      <PageHeader title="Trust scores" subtitle={`${flagged.length} recipe${flagged.length === 1 ? '' : 's'} flagged for review.`} />

      {loading && <LoadingBlock label="Checking the numbers…" />}
      {!loading && error && (
        <div className="mb-4">
          <InlineError message={error} />
        </div>
      )}

      {!loading && flagged.length === 0 && !error && (
        <div className="chit p-10 text-center">
          <p className="font-body text-sm text-ticket-dim">No recipes currently flagged.</p>
        </div>
      )}

      {!loading && flagged.length > 0 && (
        <div className="space-y-3">
          {flagged.map((recipe) => (
            <div key={recipe.id} className="chit p-5">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <p className="font-mono-ticket text-[10px] text-ticket-faint mb-1">#{recipe.id}</p>
                  <p className="font-display text-base font-semibold text-ticket">{recipe.name_en}</p>
                  <p className="font-body text-xs text-ticket-dim mt-1">
                    {recipe.source_type} · trust {recipe.trust_score.toFixed(2)}
                    {recipe.average_rating !== null && (
                      <> · {recipe.average_rating.toFixed(1)}★ ({recipe.review_count} reviews)</>
                    )}
                  </p>
                  <p className="flex items-start gap-1.5 font-body text-xs text-ember mt-2">{recipe.flag_reason}</p>
                </div>
                {editingId !== recipe.id && (
                  <button
                    onClick={() => startEdit(recipe)}
                    className="bg-ember text-backstage px-4 py-2 rounded-lg font-body text-xs font-semibold shrink-0 hover:bg-ember-dim transition-colors"
                  >
                    Override score
                  </button>
                )}
              </div>

              {editingId === recipe.id && (
                <div className="mt-4 flex flex-col sm:flex-row gap-2">
                  <input
                    type="number"
                    min={0}
                    max={1}
                    step={0.01}
                    value={valueDraft}
                    onChange={(e) => setValueDraft(e.target.value)}
                    className="sm:w-28 h-10 px-4 rounded-lg bg-backstage border border-line text-ticket font-mono-ticket text-sm focus:outline-none focus:ring-2 focus:ring-ember/40"
                  />
                  <input
                    type="text"
                    placeholder="Reason (optional)"
                    value={reasonDraft}
                    onChange={(e) => setReasonDraft(e.target.value)}
                    className="flex-1 h-10 px-4 rounded-lg bg-backstage border border-line text-ticket font-body text-sm focus:outline-none focus:ring-2 focus:ring-ember/40"
                  />
                  <div className="flex gap-2 shrink-0">
                    <button
                      onClick={() => submitOverride(recipe.id)}
                      disabled={saving}
                      className="h-10 px-5 rounded-lg bg-ember text-backstage font-body text-xs font-semibold disabled:opacity-50 hover:bg-ember-dim transition-colors"
                    >
                      {saving ? 'Saving…' : 'Save'}
                    </button>
                    <button
                      onClick={() => setEditingId(null)}
                      disabled={saving}
                      className="h-10 px-4 rounded-lg bg-backstage-high text-ticket-dim font-body text-xs font-semibold disabled:opacity-50"
                    >
                      Cancel
                    </button>
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
