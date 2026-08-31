import { ArrowLeft, Check, Plus, Trash2 } from 'lucide-react';
import React, { useEffect, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { MainHeader } from '../components/MainHeader';
import { MobileBottomNav } from '../components/MobileBottomNav';
import { ErrorBlock, LoadingBlock } from '../components/StatusBlocks';
import { ApiError, bookmarksApi } from '../lib/api';
import type { ShoppingListOut } from '../lib/types';

export default function ShoppingListPage() {
  const { listId } = useParams<{ listId: string }>();
  const navigate = useNavigate();
  const id = Number(listId);

  const [list, setList] = useState<ShoppingListOut | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [newItem, setNewItem] = useState('');

  function load() {
    setError(null);
    bookmarksApi
      .shoppingListDetail(id)
      .then(setList)
      .catch((err) => setError(err instanceof ApiError ? err.message : 'Failed to load this shopping list.'));
  }

  useEffect(load, [id]);

  async function toggleItem(itemId: number) {
    if (!list) return;
    // optimistic toggle -- this is a checklist the user is actively working through in a store aisle
    setList({
      ...list,
      items: list.items.map((it) => (it.id === itemId ? { ...it, is_checked: !it.is_checked } : it)),
    });
    try {
      await bookmarksApi.toggleShoppingListItem(id, itemId);
    } catch {
      load();
    }
  }

  async function removeItem(itemId: number) {
    if (!list) return;
    setList({ ...list, items: list.items.filter((it) => it.id !== itemId) });
    try {
      await bookmarksApi.removeShoppingListItem(id, itemId);
    } catch {
      load();
    }
  }

  async function addItem() {
    const name = newItem.trim();
    if (!name) return;
    setNewItem('');
    try {
      await bookmarksApi.addShoppingListItem(id, { name });
      load();
    } catch {
      load();
    }
  }

  const checkedCount = list?.items.filter((i) => i.is_checked).length ?? 0;

  return (
    <div className="bg-surface min-h-screen">
      <MainHeader />
      <main className="pt-32 pb-24 max-w-2xl mx-auto px-5">
        <button
          onClick={() => navigate(-1)}
          className="flex items-center gap-2 text-on-surface-variant hover:text-on-surface font-ui text-sm mb-6"
        >
          <ArrowLeft size={16} /> Back
        </button>

        {error ? (
          <ErrorBlock message={error} onRetry={load} />
        ) : list === null ? (
          <LoadingBlock label="Loading shopping list…" />
        ) : (
          <>
            <h1 className="font-display text-3xl md:text-4xl text-on-surface mb-1">{list.name}</h1>
            <p className="font-ui text-sm text-on-surface-variant mb-6">
              {checkedCount} of {list.items.length} checked off
            </p>
            {/* Real, honest limitation from the backend: ingredients named differently across
                recipes (e.g. "Tomato" vs "Tomatoes") may appear as separate lines rather than
                being merged into one. */}
            <p className="text-xs text-on-surface-variant/70 mb-6">
              Items may not be fully merged if recipes named the same ingredient differently.
            </p>

            <div className="flex gap-3 mb-6">
              <input
                value={newItem}
                onChange={(e) => setNewItem(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && addItem()}
                placeholder="Add an item…"
                className="flex-1 h-12 px-5 bg-surface-container rounded-full focus:outline-none focus:ring-2 focus:ring-primary-container"
              />
              <button
                onClick={addItem}
                aria-label="Add item"
                className="w-12 h-12 shrink-0 rounded-full bg-primary text-on-primary flex items-center justify-center"
              >
                <Plus size={18} />
              </button>
            </div>

            <ul className="space-y-2">
              {list.items.map((item) => (
                <li
                  key={item.id}
                  className={`flex items-center gap-3 rounded-2xl px-4 py-3.5 ${
                    item.is_checked ? 'bg-tertiary-container/20' : 'bg-surface-container'
                  }`}
                >
                  <button
                    onClick={() => toggleItem(item.id)}
                    aria-label={item.is_checked ? 'Mark unchecked' : 'Mark checked'}
                    className={`w-6 h-6 rounded-full border-2 flex items-center justify-center shrink-0 ${
                      item.is_checked ? 'bg-tertiary border-tertiary text-on-tertiary' : 'border-outline-variant'
                    }`}
                  >
                    {item.is_checked && <Check size={14} />}
                  </button>
                  <span
                    className={`flex-1 font-body-md text-sm ${
                      item.is_checked ? 'text-on-surface-variant line-through' : 'text-on-surface'
                    }`}
                  >
                    {item.quantity !== null ? `${item.quantity} ${item.unit || ''} ` : ''}
                    {item.name}
                    {item.is_manual && (
                      <span className="ml-2 text-[10px] uppercase tracking-wide text-on-surface-variant/60">added</span>
                    )}
                  </span>
                  <button
                    onClick={() => removeItem(item.id)}
                    aria-label={`Remove ${item.name}`}
                    className="text-on-surface-variant hover:text-error shrink-0"
                  >
                    <Trash2 size={15} />
                  </button>
                </li>
              ))}
            </ul>
          </>
        )}
      </main>
      <MobileBottomNav />
    </div>
  );
}
