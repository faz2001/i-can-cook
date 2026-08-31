import { CheckCircle2, FolderPlus, Loader2, X } from 'lucide-react';
import { useEffect, useState } from 'react';
import { EmptyBlock, ErrorBlock, LoadingBlock } from './StatusBlocks';
import { ApiError, bookmarksApi } from '../lib/api';
import type { CollectionOut } from '../lib/types';

interface AddToCollectionModalProps {
  recipeId: string;
  onClose: () => void;
  /** Fired once the recipe has actually been saved into a collection (either
   * an existing one, or a freshly-created one) -- lets the caller flip its
   * own "saved" UI (e.g. RecipeDetailPage's bookmark button) without this
   * modal needing to know anything about that button. */
  onSaved?: () => void;
}

/** Same overlay convention as KitchenModePage's pendingTimerStart card:
 * fixed inset-0 z-20 flex items-center justify-center bg-black/40 px-5,
 * wrapping a w-full max-w-sm rounded-3xl bg-surface-container-high p-6
 * shadow-xl panel. */
export function AddToCollectionModal({ recipeId, onClose, onSaved }: AddToCollectionModalProps) {
  const [collections, setCollections] = useState<CollectionOut[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  const [savingId, setSavingId] = useState<number | null>(null);
  const [savedId, setSavedId] = useState<number | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);

  const [creating, setCreating] = useState(false);
  const [newName, setNewName] = useState('');
  const [createBusy, setCreateBusy] = useState(false);
  const [createError, setCreateError] = useState<string | null>(null);

  function load() {
    setError(null);
    bookmarksApi
      .listCollections()
      .then(setCollections)
      .catch((err) => setError(err instanceof ApiError ? err.message : 'Failed to load your collections.'));
  }

  useEffect(load, []);

  async function handleSelect(collection: CollectionOut) {
    if (savingId !== null || savedId !== null) return;
    setActionError(null);
    setSavingId(collection.id);
    try {
      await bookmarksApi.addBookmark(recipeId, collection.id);
      setSavingId(null);
      setSavedId(collection.id);
      onSaved?.();
      setTimeout(onClose, 700);
    } catch (err) {
      setSavingId(null);
      setActionError(err instanceof ApiError ? err.message : 'Could not save to this collection.');
    }
  }

  async function createCollection() {
    const name = newName.trim();
    if (!name || createBusy) return;
    setCreateError(null);
    setCreateBusy(true);
    try {
      const collection = await bookmarksApi.createCollection(name);
      await bookmarksApi.addBookmark(recipeId, collection.id);
      setNewName('');
      setCreating(false);
      setSavedId(collection.id);
      onSaved?.();
      load();
      setTimeout(onClose, 700);
    } catch (err) {
      // 409 -- "A collection with this name already exists" comes through verbatim from the backend
      setCreateError(err instanceof ApiError ? err.message : 'Could not create collection.');
    } finally {
      setCreateBusy(false);
    }
  }

  return (
    <div
      className="fixed inset-0 z-20 flex items-center justify-center bg-black/40 px-5"
      onClick={(e) => e.stopPropagation()}
    >
      <div className="w-full max-w-sm rounded-3xl bg-surface-container-high p-6 shadow-xl">
        <div className="flex items-center justify-between mb-6">
          <h2 className="font-heading text-lg text-on-surface">Save to Collection</h2>
          <button
            onClick={onClose}
            aria-label="Close"
            className="text-on-surface-variant hover:text-on-surface"
          >
            <X size={18} />
          </button>
        </div>

        {error ? (
          <ErrorBlock message={error} onRetry={load} />
        ) : collections === null ? (
          <LoadingBlock label="Loading your collections…" />
        ) : collections.length === 0 && !creating ? (
          <EmptyBlock
            icon={<FolderPlus className="text-outline" size={40} />}
            title="No collections yet — create one below"
          />
        ) : (
          <div className="flex flex-col gap-3 max-h-72 overflow-y-auto mb-2">
            {collections.map((c) => (
              <button
                key={c.id}
                onClick={() => handleSelect(c)}
                disabled={savingId !== null || savedId !== null}
                className="w-full flex items-center justify-between bg-surface-container rounded-2xl px-6 py-5 text-left hover:bg-surface-container-high transition-colors disabled:opacity-60"
              >
                <div>
                  <h3 className="font-heading text-base text-on-surface">{c.name}</h3>
                  <p className="font-ui text-xs text-on-surface-variant mt-0.5">
                    {c.recipe_count} {c.recipe_count === 1 ? 'recipe' : 'recipes'}
                  </p>
                </div>
                {savedId === c.id ? (
                  <CheckCircle2 className="text-tertiary shrink-0" size={20} />
                ) : savingId === c.id ? (
                  <Loader2 className="animate-spin text-on-surface-variant shrink-0" size={18} />
                ) : null}
              </button>
            ))}
          </div>
        )}

        {actionError && <p className="text-xs text-error mt-2 mb-2">{actionError}</p>}

        <div className="mt-4 pt-4 border-t border-outline-variant/20">
          {creating ? (
            <div className="flex gap-2">
              <input
                autoFocus
                value={newName}
                onChange={(e) => setNewName(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && createCollection()}
                placeholder="Collection name"
                className="flex-1 h-11 px-4 bg-surface-container rounded-full focus:outline-none focus:ring-2 focus:ring-primary-container"
              />
              <button
                onClick={createCollection}
                disabled={createBusy}
                className="h-11 px-5 rounded-full bg-primary text-on-primary font-ui text-sm font-semibold disabled:opacity-60 flex items-center gap-2"
              >
                {createBusy && <Loader2 size={14} className="animate-spin" />}
                Create
              </button>
            </div>
          ) : (
            <button
              onClick={() => setCreating(true)}
              className="w-full flex items-center justify-center gap-2 h-11 rounded-full bg-surface-container text-on-surface font-ui text-sm font-semibold hover:bg-surface-container-high transition-colors"
            >
              <FolderPlus size={16} /> New collection
            </button>
          )}
          {createError && <p className="text-xs text-error mt-2">{createError}</p>}
        </div>
      </div>
    </div>
  );
}