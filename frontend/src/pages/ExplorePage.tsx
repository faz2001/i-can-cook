import { Search, SlidersHorizontal, X } from 'lucide-react';
import React, { useEffect, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { EmptyBlock, ErrorBlock } from '../components/StatusBlocks';
import { FilterSortPanel } from '../components/FilterSortPanel';
import { MainHeader } from '../components/MainHeader';
import { MobileBottomNav } from '../components/MobileBottomNav';
import { RecipeCard } from '../components/RecipeCard';
import { ApiError, recipesApi } from '../lib/api';
import type { RecipeListItemOut } from '../lib/types';

const PAGE_SIZE = 60;

export default function ExplorePage() {
  const [params, setParams] = useSearchParams();
  const q = params.get('q') || '';
  const course = params.get('course') || '';
  const sortBy = params.get('sortBy') || '';
  const cuisine = params.get('cuisine') || '';
  const maxTimeMin = params.get('maxTimeMin') || '';

  const [filterPanelOpen, setFilterPanelOpen] = useState(false);
  const hasActiveFilters = (sortBy !== '' && sortBy !== 'relevance') || cuisine !== '' || maxTimeMin !== '';

  const [items, setItems] = useState<RecipeListItemOut[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Live course chips / cuisine dropdown options -- was a static list read
  // off the 99-recipe SL-Cook100 CATALOG snapshot, which never knew about
  // values introduced by later imports (e.g. every "International" row
  // sharing one cuisine string and a NULL course) and, worse, offered
  // course chips that could only ever match Sri Lankan rows.
  const [courses, setCourses] = useState<string[]>([]);
  const [cuisines, setCuisines] = useState<string[]>([]);
  useEffect(() => {
    let cancelled = false;
    recipesApi
      .facets()
      .then((res) => {
        if (cancelled) return;
        setCourses(res.courses);
        setCuisines(res.cuisines);
      })
      .catch(() => {
        // Non-critical: search/browsing still works with no chips/options shown.
      });
    return () => {
      cancelled = true;
    };
  }, []);

  // Debounced: fetches live from GET /api/recipes rather than filtering a
  // static snapshot, so this covers every imported recipe, not just the 99
  // SL-Cook100 ones a pre-generated catalog file would have known about.
  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    const timer = setTimeout(() => {
      recipesApi
        .browse({
          q: q || undefined,
          course: course || undefined,
          cuisine: cuisine || undefined,
          sort_by: (sortBy || undefined) as 'relevance' | 'rating' | 'newest' | 'quickest' | undefined,
          max_time_min: maxTimeMin ? Number(maxTimeMin) : undefined,
          limit: PAGE_SIZE,
        })
        .then((res) => {
          if (cancelled) return;
          setItems(res.items);
          setTotal(res.total);
          setLoading(false);
        })
        .catch((err) => {
          if (cancelled) return;
          setError(err instanceof ApiError ? err.message : 'Failed to load recipes.');
          setLoading(false);
        });
    }, 300);
    return () => {
      cancelled = true;
      clearTimeout(timer);
    };
  }, [q, course, cuisine, sortBy, maxTimeMin]);

  function setQuery(value: string) {
    const next = new URLSearchParams(params);
    if (value) next.set('q', value);
    else next.delete('q');
    setParams(next, { replace: true });
  }

  function toggleCourse(c: string) {
    const next = new URLSearchParams(params);
    if (course === c) next.delete('course');
    else next.set('course', c);
    setParams(next, { replace: true });
  }

  function handleFilterChange(next: { sortBy?: string; cuisine?: string; maxTimeMin?: string }) {
    const nextParams = new URLSearchParams(params);
    if (next.sortBy !== undefined) {
      if (next.sortBy && next.sortBy !== 'relevance') nextParams.set('sortBy', next.sortBy);
      else nextParams.delete('sortBy');
    }
    if (next.cuisine !== undefined) {
      if (next.cuisine) nextParams.set('cuisine', next.cuisine);
      else nextParams.delete('cuisine');
    }
    if (next.maxTimeMin !== undefined) {
      if (next.maxTimeMin) nextParams.set('maxTimeMin', next.maxTimeMin);
      else nextParams.delete('maxTimeMin');
    }
    setParams(nextParams, { replace: true });
  }

  return (
    <div className="bg-surface min-h-screen">
      <MainHeader />
      <main className="pt-32 pb-24 max-w-[1440px] mx-auto px-5 md:px-20">
        <div className="mb-8">
          <h1 className="font-display text-3xl md:text-5xl text-on-surface">
            {loading ? 'Searching…' : `${total} ${total === 1 ? 'Recipe' : 'Recipes'} Found`}
          </h1>
          <p className="font-body-md text-on-surface-variant mt-1">
            {q ? `Showing results for "${q}"` : 'Browse the full recipe collection'}
            {course ? ` in ${course}` : ''}
            {!loading && total > PAGE_SIZE ? ` — showing first ${PAGE_SIZE}` : ''}
          </p>
        </div>

        <div className="flex items-start gap-3 mb-6">
          <div className="relative max-w-xl flex-1">
            <Search className="absolute left-5 top-1/2 -translate-y-1/2 text-on-surface-variant" size={18} />
            <input
              value={q}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Search by dish, ingredient, or tag…"
              className="w-full h-[52px] pl-[52px] pr-10 bg-surface-container rounded-full focus:outline-none focus:ring-2 focus:ring-primary-container"
            />
            {q && (
              <button
                aria-label="Clear search"
                onClick={() => setQuery('')}
                className="absolute right-4 top-1/2 -translate-y-1/2 text-on-surface-variant hover:text-on-surface"
              >
                <X size={16} />
              </button>
            )}
          </div>

          <div className="relative">
            <button
                aria-label="Sort and filter"
                onClick={() => setFilterPanelOpen((open) => !open)}
                onMouseDown={(e) => e.stopPropagation()}   // add this line
                className="relative h-[52px] w-[52px] flex items-center justify-center bg-surface-container rounded-full text-on-surface-variant hover:text-on-surface"
              >
              <SlidersHorizontal size={18} />
              {hasActiveFilters && (
                <span className="absolute top-2 right-2 h-2 w-2 rounded-full bg-primary" />
              )}
            </button>
            {filterPanelOpen && (
              <FilterSortPanel
                sortBy={sortBy}
                cuisine={cuisine}
                cuisines={cuisines}
                maxTimeMin={maxTimeMin}
                onChange={handleFilterChange}
                onClose={() => setFilterPanelOpen(false)}
              />
            )}
          </div>
        </div>

        <div className="flex flex-wrap gap-2 mb-10">
          {courses.map((c) => (
            <button
              key={c}
              onClick={() => toggleCourse(c)}
              className={`px-4 py-1.5 rounded-full text-xs font-ui font-medium border transition-colors ${
                course === c
                  ? 'bg-primary text-on-primary border-primary'
                  : 'bg-transparent text-on-surface-variant border-outline-variant hover:border-primary'
              }`}
            >
              {c}
            </button>
          ))}
        </div>

        {loading ? (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {[0, 1, 2, 3, 4, 5].map((i) => (
              <div key={i} className="h-64 rounded-lg bg-surface-container animate-pulse" />
            ))}
          </div>
        ) : error ? (
          <ErrorBlock message={error} onRetry={() => setParams(new URLSearchParams(params))} />
        ) : items.length === 0 ? (
          <EmptyBlock
            icon={<Search className="text-outline" size={40} />}
            title="No recipes match"
            description="Try a different search term, or clear the course, cuisine, or time filters."
          />
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {items.map((recipe) => (
              <RecipeCard key={recipe.id} recipe={recipe} />
            ))}
          </div>
        )}
      </main>
      <MobileBottomNav />
    </div>
  );
}