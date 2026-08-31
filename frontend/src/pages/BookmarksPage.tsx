import { FolderPlus, ChevronRight } from 'lucide-react';
import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { MainHeader } from '../components/MainHeader';
import { MobileBottomNav } from '../components/MobileBottomNav';
import { EmptyBlock, ErrorBlock, LoadingBlock } from '../components/StatusBlocks';
import { ApiError, bookmarksApi } from '../lib/api';
import type { CollectionOut } from '../lib/types';

export default function BookmarksPage() {
  const navigate = useNavigate();
  const [collections, setCollections] = useState<CollectionOut[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [creating, setCreating] = useState(false);
  const [newName, setNewName] = useState('');
  const [createError, setCreateError] = useState<string | null>(null);

  function load() {
    setError(null);
    bookmarksApi
      .listCollections()
      .then(setCollections)
      .catch((err) => setError(err instanceof ApiError ? err.message : 'Failed to load your bookmarks.'));
  }

  useEffect(load, []);

  async function createCollection() {
    const name = newName.trim();
    if (!name) return;
    setCreateError(null);
    try {
      await bookmarksApi.createCollection(name);
      setNewName('');
      setCreating(false);
      load();
    } catch (err) {
      // 409 -- "A collection with this name already exists" comes through verbatim from the backend
      setCreateError(err instanceof ApiError ? err.message : 'Could not create collection.');
    }
  }

  return (
    <div className="bg-surface min-h-screen">
      <MainHeader />
      <main className="pt-32 pb-24 max-w-[1440px] mx-auto px-5 md:px-20">
        <div className="flex items-center justify-between mb-8">
          <h1 className="font-display text-3xl md:text-5xl text-on-surface">Your Bookmarks</h1>
          <button
            onClick={() => setCreating((c) => !c)}
            className="flex items-center gap-2 bg-primary text-on-primary px-5 py-2.5 rounded-full font-ui text-sm font-semibold shadow-lg"
          >
            <FolderPlus size={16} /> New Collection
          </button>
        </div>

        {creating && (
          <div className="mb-8 flex gap-3 max-w-md">
            <input
              autoFocus
              value={newName}
              onChange={(e) => setNewName(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && createCollection()}
              placeholder="Collection name"
              className="flex-1 h-12 px-5 bg-surface-container rounded-full focus:outline-none focus:ring-2 focus:ring-primary-container"
            />
            <button
              onClick={createCollection}
              className="h-12 px-6 rounded-full bg-primary text-on-primary font-ui text-sm font-semibold"
            >
              Create
            </button>
          </div>
        )}
        {createError && <p className="text-xs text-error mb-6">{createError}</p>}

        {error ? (
          <ErrorBlock message={error} onRetry={load} />
        ) : collections === null ? (
          <LoadingBlock label="Loading your collections…" />
        ) : collections.length === 0 ? (
          <EmptyBlock
            icon={<FolderPlus className="text-outline" size={40} />}
            title="No collections yet"
            description="Bookmark a recipe from its detail page to start your first collection."
          />
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {collections.map((c) => (
              <button
                key={c.id}
                onClick={() => navigate(`/bookmarks/${c.id}`)}
                className="flex items-center justify-between bg-surface-container rounded-2xl px-6 py-5 text-left hover:bg-surface-container-high transition-colors"
              >
                <div>
                  <h3 className="font-heading text-lg text-on-surface">{c.name}</h3>
                  <p className="font-ui text-xs text-on-surface-variant mt-0.5">
                    {c.recipe_count} {c.recipe_count === 1 ? 'recipe' : 'recipes'}
                  </p>
                </div>
                <ChevronRight size={18} className="text-on-surface-variant shrink-0" />
              </button>
            ))}
          </div>
        )}
      </main>
      <MobileBottomNav />
    </div>
  );
}
