import { ArrowRight, Leaf, Sparkles } from 'lucide-react';
import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { DishTile } from '../components/DishTile';
import { MainHeader } from '../components/MainHeader';
import { MobileBottomNav } from '../components/MobileBottomNav';
import { EmptyBlock, ErrorBlock, LoadingBlock } from '../components/StatusBlocks';
import { CATALOG } from '../data/catalog';
import { ApiError, zeroWasteApi } from '../lib/api';
import type { ZeroWasteSuggestion } from '../lib/types';

export default function UseItUpPage() {
  const navigate = useNavigate();
  const [suggestions, setSuggestions] = useState<ZeroWasteSuggestion[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  async function load() {
    setLoading(true);
    setError(null);
    try {
      const data = await zeroWasteApi.suggestions();
      setSuggestions(data);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Failed to load suggestions.');
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
  }, []);

  return (
    <div className="bg-surface min-h-screen">
      <MainHeader />
      <main className="pt-32 pb-24 max-w-[1440px] mx-auto px-5 md:px-20">
        <header className="mb-10 max-w-2xl">
          <h1 className="font-display text-3xl md:text-5xl text-on-surface tracking-tight">Use it up before it goes to waste.</h1>
          <p className="font-body-md text-on-surface-variant mt-2">
            Recipes ranked by how many of your soon-to-expire pantry items they use.
          </p>
        </header>

        {loading && <LoadingBlock label="Checking your pantry…" />}
        {!loading && error && <ErrorBlock message={error} onRetry={load} />}

        {!loading && !error && suggestions && suggestions.length === 0 && (
          <EmptyBlock
            icon={<Leaf className="text-tertiary" size={40} />}
            title="Nothing expiring soon"
            description="Your pantry is in good shape. Check back as things get closer to their expiry date."
            action={
              <button onClick={() => navigate('/explore')} className="mt-2 flex items-center gap-2 bg-primary text-on-primary px-6 py-3 rounded-full font-ui font-semibold shadow-md">
                Browse recipes <ArrowRight size={16} />
              </button>
            }
          />
        )}

        {!loading && !error && suggestions && suggestions.length > 0 && (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {suggestions.map((s) => {
              const catalogEntry = CATALOG.find((c) => c.id === s.recipe_id);
              return (
                <div
                  key={s.recipe_id}
                  role="button"
                  tabIndex={0}
                  onClick={() => navigate(`/recipe/${s.recipe_id}`)}
                  onKeyDown={(e) => e.key === 'Enter' && navigate(`/recipe/${s.recipe_id}`)}
                  className="group relative h-64 rounded-xl overflow-hidden shadow-md cursor-pointer"
                >
                  <DishTile course={catalogEntry?.course} className="absolute inset-0 w-full h-full group-hover:scale-105 transition-transform duration-700" />
                  <div className="absolute inset-0 bg-gradient-to-t from-black/85 via-black/30 to-transparent" />
                  <div className="absolute inset-0 p-6 flex flex-col justify-between">
                    <div className="self-start px-4 py-2 rounded-full bg-tertiary-container/90 text-on-tertiary-container text-[11px] font-bold flex items-center gap-1.5">
                      <Sparkles size={12} />
                      Uses {s.matched_ingredient_count} of your expiring item{s.matched_ingredient_count === 1 ? '' : 's'}
                    </div>
                    <div>
                      <h3 className="font-display text-2xl md:text-3xl text-white mb-2">{s.name_en}</h3>
                      <div className="flex flex-wrap gap-2">
                        {s.matched_ingredients.slice(0, 4).map((m) => (
                          <span key={m.canonical_id} className="text-[11px] font-ui bg-white/15 text-white px-2.5 py-1 rounded-full backdrop-blur-sm">
                            {m.pantry_item_name}
                          </span>
                        ))}
                      </div>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </main>
      <MobileBottomNav />
    </div>
  );
}
