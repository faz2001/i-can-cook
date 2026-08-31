import {
  ArrowLeft, Bookmark, CheckCircle2, Circle, Clock, Flame, Heart, Minus, Plus, ShoppingCart, Star,
  Timer, XCircle,
} from 'lucide-react';
import React, { useEffect, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { AddToCollectionModal } from '../components/AddToCollectionModal';
import { CommunitySection } from '../components/CommunitySection';
import { DishTile } from '../components/DishTile';
import { ErrorBlock, LoadingBlock } from '../components/StatusBlocks';
import { CATALOG } from '../data/catalog';
import { ApiError, favoritesApi, recipesApi } from '../lib/api';
import type { PantryStatus, RecipeDetailOut } from '../lib/types';

const STATUS_STYLE: Record<PantryStatus, { label: string; className: string; Icon: typeof CheckCircle2 }> = {
  have: { label: 'In pantry', className: 'text-tertiary bg-tertiary-container/20', Icon: CheckCircle2 },
  partial: { label: 'Not quite enough', className: 'text-primary bg-primary-container/20', Icon: Circle },
  missing: { label: 'Missing', className: 'text-error bg-error-container/60', Icon: XCircle },
  unmatched: { label: "Can't check", className: 'text-on-surface-variant bg-surface-container', Icon: Circle },
};

export default function RecipeDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();

  const [recipe, setRecipe] = useState<RecipeDetailOut | null>(null);
  const [servings, setServings] = useState<number | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [notFound, setNotFound] = useState(false);

  const [bookmarkState, setBookmarkState] = useState<'idle' | 'saved'>('idle');
  const [showCollectionModal, setShowCollectionModal] = useState(false);

  // Separate from bookmarks/collections on purpose -- a favorite is a quick
  // one-tap "I like this", while a bookmark saves the recipe into an
  // organized collection (e.g. for meal planning / shopping lists). Both
  // features exist server-side (Favorite and BookmarkCollection are
  // different tables), so both get their own toggle here rather than
  // conflating them into one button.
  const [favorited, setFavorited] = useState(false);
  const [favoriteBusy, setFavoriteBusy] = useState(false);

  const catalogEntry = CATALOG.find((c) => c.id === id);

  async function load(requestedServings?: number) {
    if (!id) return;
    setLoading(true);
    setError(null);
    setNotFound(false);
    try {
      const data = await recipesApi.detail(id, requestedServings);
      setRecipe(data);
      setServings(data.requested_servings);
      setFavorited(data.is_favorited);
    } catch (err) {
      if (err instanceof ApiError && err.status === 404) setNotFound(true);
      else setError(err instanceof ApiError ? err.message : 'Failed to load this recipe.');
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
    setBookmarkState('idle');
    setShowCollectionModal(false);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id]);

  async function toggleFavorite() {
    if (!id || favoriteBusy) return;
    setFavoriteBusy(true);
    const next = !favorited;
    setFavorited(next); // optimistic
    try {
      if (next) await favoritesApi.add(id);
      else await favoritesApi.remove(id);
    } catch {
      setFavorited(!next); // revert on failure
    } finally {
      setFavoriteBusy(false);
    }
  }

  function changeServings(delta: number) {
    const base = servings ?? recipe?.requested_servings ?? 1;
    const next = Math.min(100, Math.max(1, base + delta));
    setServings(next);
    load(next);
  }

  function startKitchenMode() {
    if (!id) return;
    navigate(`/recipe/${id}/cook${servings ? `?servings=${servings}` : ''}`);
  }

  if (loading && !recipe) {
    return (
      <div className="bg-surface min-h-screen pt-20">
        <LoadingBlock label="Loading recipe…" />
      </div>
    );
  }

  if (notFound) {
    return (
      <div className="bg-surface min-h-screen pt-20 px-5">
        <button onClick={() => navigate(-1)} className="flex items-center gap-2 text-on-surface-variant mb-8 mt-6">
          <ArrowLeft size={18} /> Back
        </button>
        <ErrorBlock message="This recipe doesn't exist, or isn't visible yet." />
      </div>
    );
  }

  if (error || !recipe) {
    return (
      <div className="bg-surface min-h-screen pt-20 px-5">
        <button onClick={() => navigate(-1)} className="flex items-center gap-2 text-on-surface-variant mb-8 mt-6">
          <ArrowLeft size={18} /> Back
        </button>
        <ErrorBlock message={error || 'Something went wrong.'} onRetry={() => load(servings ?? undefined)} />
      </div>
    );
  }

  const totalTime = catalogEntry?.totalTimeMin ?? null;
  const haveCount = recipe.ingredients.filter((i) => i.pantry_status === 'have').length;

  return (
    <div className="bg-surface font-body-md text-on-surface min-h-screen">
      <header className="fixed top-0 w-full z-50 bg-surface/80 backdrop-blur-xl shadow-sm">
        <div className="h-20 w-full px-5 md:px-20 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <button
              onClick={() => navigate(-1)}
              aria-label="Go back"
              className="w-10 h-10 rounded-full bg-surface-container flex items-center justify-center text-on-surface-variant hover:bg-surface-container-high transition-all"
            >
              <ArrowLeft size={18} />
            </button>
            <span className="font-display text-xl text-primary">I Can Cook</span>
          </div>
        </div>
      </header>

      <main className="w-full pt-20 min-h-screen">
        <div className="w-full h-[320px] md:h-[420px] relative overflow-hidden">
          <DishTile course={recipe.course} imageUrl={recipe.image_url} className="w-full h-full" />
          <div className="absolute inset-0 bg-gradient-to-t from-background via-background/30 to-transparent" />
          <div className="absolute bottom-0 left-0 w-full max-w-[1440px] mx-auto px-5 md:px-20 pb-8 z-10">
            <div className="flex flex-wrap gap-2 mb-4">
              {recipe.course && (
                <span className="px-4 py-1.5 rounded-full bg-surface-container-highest/70 backdrop-blur-md text-[11px] font-ui uppercase tracking-widest text-on-surface">
                  {recipe.course}
                </span>
              )}
              {recipe.tags.slice(0, 3).map((tag) => (
                <span key={tag} className="px-4 py-1.5 rounded-full bg-surface-container-highest/70 backdrop-blur-md text-[11px] font-ui uppercase tracking-widest text-on-surface">
                  {tag}
                </span>
              ))}
            </div>
            <h1 className="font-display text-3xl md:text-5xl text-on-surface mb-1 max-w-3xl leading-tight">{recipe.name_en}</h1>
            {recipe.name_native && <p className="font-heading text-xl text-on-surface-variant/80 tracking-wide font-light">{recipe.name_native}</p>}
          </div>
        </div>

        <div className="max-w-[1440px] mx-auto w-full px-5 md:px-20 grid grid-cols-1 lg:grid-cols-12 gap-6 relative z-20 pb-32">
          <div className="lg:col-span-4 -mt-16 lg:-mt-24 mb-8 lg:mb-0 order-1 lg:order-2">
            <div className="lg:sticky lg:top-28 bg-surface/95 backdrop-blur-2xl border border-surface-container-highest rounded-[36px] p-6 md:p-8 shadow-xl">
              <div className="flex items-center gap-6 pb-6 border-b border-outline-variant/20">
                <HealthGauge score={recipe.health_score} />
                <div>
                  <h3 className="font-heading text-lg text-on-surface mb-1">Epicurean Grade</h3>
                  <p className="font-body-md text-xs text-on-surface-variant">
                    {haveCount}/{recipe.ingredients.length} ingredients in your pantry
                  </p>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3 my-6">
                {totalTime !== null && (
                  <StatTile icon={<Clock className="text-primary" size={18} />} label="Total time" value={`${totalTime} min`} />
                )}
                {recipe.nutrition.available && recipe.nutrition.calories !== null && (
                  <StatTile icon={<Flame className="text-primary" size={18} />} label="Calories" value={`${Math.round(recipe.nutrition.calories)} kcal`} />
                )}
                <StatTile
                  icon={<Star className="text-primary" size={18} />}
                  label="Rating"
                  value={recipe.average_rating !== null ? `${recipe.average_rating.toFixed(1)} (${recipe.review_count})` : 'No reviews yet'}
                />
                <StatTile icon={<ShoppingCart className="text-primary" size={18} />} label="Servings" value={String(servings ?? recipe.requested_servings)} />
              </div>

              <div className="flex items-center justify-between bg-surface-container rounded-2xl px-4 py-3 mb-6">
                <span className="font-ui text-xs uppercase tracking-wide text-on-surface-variant">Servings</span>
                <div className="flex items-center gap-3">
                  <button
                    onClick={() => changeServings(-1)}
                    disabled={(servings ?? recipe.requested_servings) <= 1 || loading}
                    aria-label="Decrease servings"
                    className="w-8 h-8 rounded-full bg-surface-container-high flex items-center justify-center disabled:opacity-40"
                  >
                    <Minus size={14} />
                  </button>
                  <span className="font-heading w-6 text-center">{servings ?? recipe.requested_servings}</span>
                  <button
                    onClick={() => changeServings(1)}
                    disabled={(servings ?? recipe.requested_servings) >= 100 || loading}
                    aria-label="Increase servings"
                    className="w-8 h-8 rounded-full bg-surface-container-high flex items-center justify-center disabled:opacity-40"
                  >
                    <Plus size={14} />
                  </button>
                </div>
              </div>

              <div className="flex gap-3">
                <button
                  onClick={startKitchenMode}
                  className="flex-1 py-4 rounded-full bg-primary text-on-primary font-ui font-semibold shadow-lg"
                >
                  Start Kitchen Mode
                </button>
                <button
                  onClick={toggleFavorite}
                  disabled={favoriteBusy}
                  aria-label={favorited ? 'Remove from favorites' : 'Add to favorites'}
                  className={`w-14 h-14 shrink-0 rounded-full flex items-center justify-center border transition-colors disabled:opacity-60 ${
                    favorited
                      ? 'bg-error-container/40 border-error text-error'
                      : 'bg-surface-container border-outline-variant/40 text-on-surface-variant hover:text-error'
                  }`}
                >
                  <Heart size={20} fill={favorited ? 'currentColor' : 'none'} />
                </button>
                <button
                  onClick={() => setShowCollectionModal(true)}
                  disabled={bookmarkState === 'saved'}
                  aria-label="Bookmark this recipe"
                  className={`w-14 h-14 shrink-0 rounded-full flex items-center justify-center border transition-colors ${
                    bookmarkState === 'saved'
                      ? 'bg-tertiary-container/40 border-tertiary text-tertiary'
                      : 'bg-surface-container border-outline-variant/40 text-on-surface-variant hover:text-primary'
                  }`}
                >
                  <Bookmark size={20} fill={bookmarkState === 'saved' ? 'currentColor' : 'none'} />
                </button>
              </div>
              {showCollectionModal && id && (
                <AddToCollectionModal
                  recipeId={id}
                  onClose={() => setShowCollectionModal(false)}
                  onSaved={() => setBookmarkState('saved')}
                />
              )}
            </div>
          </div>

          <div className="lg:col-span-8 pt-4 lg:pt-0 order-2 lg:order-1">
            <section className="flex flex-col gap-6 mb-12">
              <h2 className="font-display text-2xl md:text-3xl text-on-surface">The Pantry</h2>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                {recipe.ingredients.map((ing, idx) => {
                  const style = STATUS_STYLE[ing.pantry_status];
                  return (
                    <div key={idx} className="bg-surface-container rounded-[20px] p-4 flex items-start gap-3 border border-transparent">
                      <style.Icon className={`mt-0.5 shrink-0 ${style.className.split(' ')[0]}`} size={18} />
                      <div className="min-w-0 flex-1">
                        <p className="font-heading text-sm text-on-surface truncate">{ing.name}</p>
                        <p className="font-body-md text-xs text-on-surface-variant">
                          {ing.quantity !== null ? `${formatQty(ing.quantity)} ${ing.unit || ''}`.trim() : ing.unit || ''}
                          {ing.notes ? ` · ${ing.notes}` : ''}
                        </p>
                        <span className={`inline-block mt-1.5 text-[10px] font-ui font-semibold uppercase tracking-wide px-2 py-0.5 rounded-full ${style.className}`}>
                          {style.label}
                        </span>
                      </div>
                      {(ing.pantry_status === 'missing' || ing.pantry_status === 'partial') && (
                        <button
                          onClick={() => navigate(`/pantry-add?name=${encodeURIComponent(ing.name)}`)}
                          className="text-[11px] font-ui font-semibold text-primary shrink-0 hover:underline"
                        >
                          + Add
                        </button>
                      )}
                    </div>
                  );
                })}
              </div>
            </section>

            <section className="flex flex-col gap-6">
              <h2 className="font-display text-2xl md:text-3xl text-on-surface">Steps</h2>
              <ol className="flex flex-col gap-4">
                {recipe.steps.map((step) => (
                  <li key={step.step_number} className="flex gap-4 bg-surface-container/60 rounded-[24px] p-5">
                    <div className="w-8 h-8 rounded-full bg-primary text-on-primary flex items-center justify-center font-heading text-sm shrink-0">
                      {step.step_number}
                    </div>
                    <div>
                      <p className="font-body-md text-on-surface leading-relaxed">{step.instruction}</p>
                      {step.duration_min !== null && (
                        <span className="inline-flex items-center gap-1 mt-2 text-xs text-on-surface-variant font-ui">
                          <Timer size={13} /> {step.duration_min} min
                        </span>
                      )}
                    </div>
                  </li>
                ))}
              </ol>
            </section>
          </div>
        </div>

        <div className="max-w-[1440px] mx-auto w-full px-5 md:px-20 pb-32">
          <CommunitySection recipeId={recipe.id} />
        </div>
      </main>

    </div>
  );
}

function formatQty(qty: number): string {
  return Number.isInteger(qty) ? String(qty) : qty.toFixed(2).replace(/0+$/, '').replace(/\.$/, '');
}

function HealthGauge({ score }: { score: number | null }) {
  const pct = score !== null ? Math.max(0, Math.min(100, score)) : null;
  const circumference = 2 * Math.PI * 45;
  const offset = pct !== null ? circumference * (1 - pct / 100) : circumference;
  return (
    <div className="relative w-16 h-16 flex items-center justify-center shrink-0">
      <svg className="absolute inset-0 w-full h-full -rotate-90" viewBox="0 0 100 100">
        <circle className="text-surface-container-high" cx="50" cy="50" fill="none" r="45" stroke="currentColor" strokeWidth="8" />
        {pct !== null && (
          <circle
            className="text-tertiary"
            cx="50"
            cy="50"
            fill="none"
            r="45"
            stroke="currentColor"
            strokeDasharray={circumference}
            strokeDashoffset={offset}
            strokeLinecap="round"
            strokeWidth="8"
          />
        )}
      </svg>
      <div className="flex flex-col items-center justify-center">
        <span className="font-heading text-base text-on-surface leading-none font-bold">{pct !== null ? Math.round(pct) : '—'}</span>
        <span className="font-ui text-[9px] text-on-surface-variant">/100</span>
      </div>
    </div>
  );
}

function StatTile({ icon, label, value }: { icon: React.ReactNode; label: string; value: string }) {
  return (
    <div className="bg-surface-container p-3 rounded-[16px] flex flex-col gap-1.5">
      {icon}
      <span className="font-ui text-[9px] text-on-surface-variant uppercase tracking-wide">{label}</span>
      <span className="font-heading text-sm text-on-surface">{value}</span>
    </div>
  );
}