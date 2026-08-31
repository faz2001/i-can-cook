import { ArrowLeft, ShoppingCart, Trash2 } from 'lucide-react';
import React, { useEffect, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { MainHeader } from '../components/MainHeader';
import { MobileBottomNav } from '../components/MobileBottomNav';
import { EmptyBlock, ErrorBlock, LoadingBlock } from '../components/StatusBlocks';
import { ApiError, bookmarksApi } from '../lib/api';
import type { CollectionDetailOut } from '../lib/types';

export default function CollectionDetailPage() {
  const { collectionId } = useParams<{ collectionId: string }>();
  const navigate = useNavigate();
  const id = Number(collectionId);

  const [collection, setCollection] = useState<CollectionDetailOut | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [generating, setGenerating] = useState(false);
  const [generateError, setGenerateError] = useState<string | null>(null);

  function load() {
    setError(null);
    bookmarksApi
      .collectionDetail(id)
      .then(setCollection)
      .catch((err) => setError(err instanceof ApiError ? err.message : 'Failed to load this collection.'));
  }

  useEffect(load, [id]);

  async function removeRecipe(recipeId: string) {
    if (!collection) return;
    // optimistic -- the list is what the user is looking at, no need to wait on a spinner for a delete
    setCollection({ ...collection, recipes: collection.recipes.filter((r) => r.recipe_id !== recipeId) });
    try {
      await bookmarksApi.removeBookmark(id, recipeId);
    } catch {
      load(); // reconcile with the server if the delete actually failed
    }
  }

  async function generateShoppingList() {
    setGenerateError(null);
    setGenerating(true);
    try {
      const list = await bookmarksApi.generateShoppingList(id);
      navigate(`/bookmarks/shopping-lists/${list.id}`);
    } catch (err) {
      setGenerateError(err instanceof ApiError ? err.message : 'Could not generate a shopping list.');
      setGenerating(false);
    }
  }

  return (
    <div className="bg-surface min-h-screen">
      <MainHeader />
      <main className="pt-32 pb-24 max-w-[1440px] mx-auto px-5 md:px-20">
        <button
          onClick={() => navigate('/bookmarks')}
          className="flex items-center gap-2 text-on-surface-variant hover:text-on-surface font-ui text-sm mb-6"
        >
          <ArrowLeft size={16} /> All collections
        </button>

        {error ? (
          <ErrorBlock message={error} onRetry={load} />
        ) : collection === null ? (
          <LoadingBlock label="Loading collection…" />
        ) : (
          <>
            <div className="flex flex-wrap items-center justify-between gap-4 mb-8">
              <h1 className="font-display text-3xl md:text-5xl text-on-surface">{collection.name}</h1>
              {collection.recipes.length > 0 && (
                <button
                  onClick={generateShoppingList}
                  disabled={generating}
                  className="flex items-center gap-2 bg-primary text-on-primary px-5 py-2.5 rounded-full font-ui text-sm font-semibold shadow-lg disabled:opacity-70"
                >
                  <ShoppingCart size={16} /> {generating ? 'Generating…' : 'Generate Shopping List'}
                </button>
              )}
            </div>
            {generateError && <p className="text-xs text-error mb-6">{generateError}</p>}

            {collection.recipes.length === 0 ? (
              <EmptyBlock
                icon={<ShoppingCart className="text-outline" size={40} />}
                title="Nothing bookmarked here yet"
                description="Save a recipe to this collection from its detail page."
              />
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {collection.recipes.map((r) => (
                  <div
                    key={r.recipe_id}
                    className="flex items-center justify-between bg-surface-container rounded-2xl px-5 py-4"
                  >
                    <button
                      onClick={() => navigate(`/recipe/${r.recipe_id}`)}
                      className="text-left flex-1 min-w-0"
                    >
                      <h3 className="font-heading text-base text-on-surface truncate">{r.name_en}</h3>
                      <p className="font-ui text-xs text-on-surface-variant mt-0.5">
                        {[r.cuisine, r.course].filter(Boolean).join(' • ')}
                      </p>
                    </button>
                    <button
                      onClick={() => removeRecipe(r.recipe_id)}
                      aria-label={`Remove ${r.name_en}`}
                      className="text-on-surface-variant hover:text-error shrink-0 ml-3"
                    >
                      <Trash2 size={16} />
                    </button>
                  </div>
                ))}
              </div>
            )}
          </>
        )}
      </main>
      <MobileBottomNav />
    </div>
  );
}
