import { Check, X } from 'lucide-react';
import React, { useCallback, useEffect, useState } from 'react';
import { InlineError, LoadingBlock } from '../components/StatusBlocks';
import { adminRecipesApi, ApiError } from '../lib/api';
import type { AdminRecipeListItemOut } from '../lib/types';
import { PageHeader } from './OverviewPage';

function errMsg(err: unknown, fallback: string) {
  return err instanceof ApiError ? err.message : fallback;
}

export default function ModerationPage() {
  const [recipes, setRecipes] = useState<AdminRecipeListItemOut[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [actioningId, setActioningId] = useState<string | null>(null);
  const [rejectReasonFor, setRejectReasonFor] = useState<string | null>(null);
  const [reasonDraft, setReasonDraft] = useState('');

  const load = useCallback(() => {
    setLoading(true);
    setError(null);
    adminRecipesApi
      .pending()
      .then(setRecipes)
      .catch((err) => setError(errMsg(err, 'Could not load the moderation queue.')))
      .finally(() => setLoading(false));
  }, []);

  useEffect(load, [load]);

  async function approve(recipeId: string) {
    setActioningId(recipeId);
    try {
      await adminRecipesApi.moderate(recipeId, 'approve');
      setRecipes((prev) => prev.filter((r) => r.id !== recipeId));
    } catch (err) {
      setError(errMsg(err, 'Could not approve this recipe.'));
    } finally {
      setActioningId(null);
    }
  }

  async function reject(recipeId: string) {
    setActioningId(recipeId);
    try {
      await adminRecipesApi.moderate(recipeId, 'reject', reasonDraft.trim() || undefined);
      setRecipes((prev) => prev.filter((r) => r.id !== recipeId));
      setRejectReasonFor(null);
      setReasonDraft('');
    } catch (err) {
      setError(errMsg(err, 'Could not reject this recipe.'));
    } finally {
      setActioningId(null);
    }
  }

  return (
    <div>
      <PageHeader title="Moderation" subtitle={`${recipes.length} recipe${recipes.length === 1 ? '' : 's'} waiting on the pass.`} />

      {loading && <LoadingBlock label="Firing the queue…" />}
      {!loading && error && (
        <div className="mb-4">
          <InlineError message={error} />
        </div>
      )}

      {!loading && recipes.length === 0 && !error && (
        <div className="chit p-10 text-center">
          <p className="font-body text-sm text-ticket-dim">Nothing pending review right now.</p>
        </div>
      )}

      {!loading && recipes.length > 0 && (
        <div className="space-y-3">
          {recipes.map((recipe) => (
            <div key={recipe.id} className="chit p-5">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <p className="font-mono-ticket text-[10px] text-ticket-faint mb-1">#{recipe.id}</p>
                  <p className="font-display text-base font-semibold text-ticket">{recipe.name_en}</p>
                  <p className="font-body text-xs text-ticket-dim mt-1">
                    {recipe.cuisine} · {recipe.source_type} · trust {recipe.trust_score.toFixed(2)}
                    {recipe.average_rating !== null && (
                      <> · {recipe.average_rating.toFixed(1)}★ ({recipe.review_count})</>
                    )}
                  </p>
                </div>
                <div className="flex items-center gap-2 shrink-0">
                  <button
                    onClick={() => approve(recipe.id)}
                    disabled={actioningId === recipe.id}
                    className="stamp text-mint disabled:opacity-50 hover:bg-mint-container transition-colors"
                  >
                    <Check size={13} /> Approve
                  </button>
                  <button
                    onClick={() => setRejectReasonFor(rejectReasonFor === recipe.id ? null : recipe.id)}
                    disabled={actioningId === recipe.id}
                    className="stamp text-rust disabled:opacity-50 hover:bg-rust-container transition-colors"
                  >
                    <X size={13} /> Reject
                  </button>
                </div>
              </div>

              {rejectReasonFor === recipe.id && (
                <div className="mt-4 flex flex-col sm:flex-row gap-2">
                  <input
                    type="text"
                    placeholder="Reason (optional)"
                    value={reasonDraft}
                    onChange={(e) => setReasonDraft(e.target.value)}
                    className="flex-1 h-10 px-4 rounded-lg bg-backstage border border-line text-ticket font-body text-sm focus:outline-none focus:ring-2 focus:ring-ember/40"
                  />
                  <button
                    onClick={() => reject(recipe.id)}
                    disabled={actioningId === recipe.id}
                    className="h-10 px-5 rounded-lg bg-rust text-backstage font-body text-xs font-semibold shrink-0 disabled:opacity-50"
                  >
                    Confirm reject
                  </button>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
