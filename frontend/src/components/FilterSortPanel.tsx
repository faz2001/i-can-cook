import { useEffect, useRef, useState } from 'react';

const SORT_OPTIONS: { value: string; label: string }[] = [
  { value: 'relevance', label: 'Relevance' },
  { value: 'rating', label: 'Highest Rated' },
  { value: 'newest', label: 'Newest' },
  { value: 'quickest', label: 'Quickest to Make' },
];

interface FilterSortPanelProps {
  sortBy: string;
  cuisine: string;
  /** Live distinct cuisine values (from GET /api/recipes/facets) -- was
   * imported directly from the static 99-recipe CATALOG snapshot, which
   * could only ever offer "Sri Lankan" no matter how many other cuisines
   * existed in the live DB. Passed in by the caller (ExplorePage), which
   * already fetches facets for the course chips, rather than this panel
   * fetching its own duplicate copy. */
  cuisines: string[];
  maxTimeMin: string;
  onChange: (next: { sortBy?: string; cuisine?: string; maxTimeMin?: string }) => void;
  onClose: () => void;
}

/** Anchored dropdown panel (not a full-screen overlay) for the Explore page's
 * sort + cuisine + max-time filters. Styled with the same
 * bg-surface-container-high / rounded-3xl / shadow-xl convention as
 * KitchenModePage's pendingTimerStart confirmation card, positioned below its
 * trigger button rather than centered over a backdrop. */
export function FilterSortPanel({ sortBy, cuisine, cuisines, maxTimeMin, onChange, onClose }: FilterSortPanelProps) {
  const [localSortBy, setLocalSortBy] = useState(sortBy || 'relevance');
  const [localCuisine, setLocalCuisine] = useState(cuisine);
  const [localMaxTimeMin, setLocalMaxTimeMin] = useState(maxTimeMin);
  const panelRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (panelRef.current && !panelRef.current.contains(e.target as Node)) onClose();
    }
    function handleEscape(e: KeyboardEvent) {
      if (e.key === 'Escape') onClose();
    }
    document.addEventListener('mousedown', handleClickOutside);
    document.addEventListener('keydown', handleEscape);
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
      document.removeEventListener('keydown', handleEscape);
    };
  }, [onClose]);

  function apply() {
    onChange({ sortBy: localSortBy, cuisine: localCuisine, maxTimeMin: localMaxTimeMin });
    onClose();
  }

  function clearFilters() {
    setLocalSortBy('relevance');
    setLocalCuisine('');
    setLocalMaxTimeMin('');
    onChange({ sortBy: 'relevance', cuisine: '', maxTimeMin: '' });
    onClose();
  }

  return (
    <div
      ref={panelRef}
      className="absolute right-0 top-full mt-2 z-30 w-80 rounded-3xl bg-surface-container-high p-6 shadow-xl"
    >
      <fieldset className="mb-6">
        <legend className="font-ui text-xs font-semibold text-on-surface-variant uppercase tracking-wide mb-3">
          Sort by
        </legend>
        <div role="radiogroup" className="flex flex-col gap-2">
          {SORT_OPTIONS.map((opt) => (
            <label key={opt.value} className="flex items-center gap-3 cursor-pointer">
              <input
                type="radio"
                name="sort-by"
                value={opt.value}
                checked={localSortBy === opt.value}
                onChange={() => setLocalSortBy(opt.value)}
                className="accent-primary h-4 w-4"
              />
              <span className="font-body-md text-on-surface">{opt.label}</span>
            </label>
          ))}
        </div>
      </fieldset>

      <div className="mb-6">
        <label htmlFor="filter-cuisine" className="font-ui text-xs font-semibold text-on-surface-variant uppercase tracking-wide mb-2 block">
          Cuisine
        </label>
        <select
          id="filter-cuisine"
          value={localCuisine}
          onChange={(e) => setLocalCuisine(e.target.value)}
          className="w-full h-11 px-4 rounded-xl bg-surface text-on-surface font-body-md focus:outline-none focus:ring-2 focus:ring-primary-container"
        >
          <option value="">All cuisines</option>
          {cuisines.map((c) => (
            <option key={c} value={c}>
              {c}
            </option>
          ))}
        </select>
      </div>

      <div className="mb-6">
        <label htmlFor="filter-max-time" className="font-ui text-xs font-semibold text-on-surface-variant uppercase tracking-wide mb-2 block">
          Max time (minutes)
        </label>
        <input
          id="filter-max-time"
          type="number"
          min={1}
          value={localMaxTimeMin}
          onChange={(e) => setLocalMaxTimeMin(e.target.value)}
          placeholder="No limit"
          className="w-full h-11 px-4 rounded-xl bg-surface text-on-surface font-body-md focus:outline-none focus:ring-2 focus:ring-primary-container"
        />
      </div>

      <div className="flex gap-3">
        <button
          onClick={clearFilters}
          className="flex-1 h-11 rounded-full bg-surface-container text-on-surface-variant font-ui text-sm font-semibold"
        >
          Clear filters
        </button>
        <button
          onClick={apply}
          className="flex-1 h-11 rounded-full bg-primary text-on-primary font-ui text-sm font-semibold"
        >
          Apply
        </button>
      </div>
    </div>
  );
}