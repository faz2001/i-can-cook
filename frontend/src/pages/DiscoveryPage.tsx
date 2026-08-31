import { ArrowRight, ChefHat, Plus, Sparkles, UtensilsCrossed } from 'lucide-react';
import React, { useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { DishTile } from '../components/DishTile';
import { LivingBackground } from '../components/LivingBackground';
import { MainHeader } from '../components/MainHeader';
import { MobileBottomNav } from '../components/MobileBottomNav';
import { RecipeCard } from '../components/RecipeCard';
import { recipesApi } from '../lib/api';
import { useAuth } from '../lib/auth';
import type { RecipeDetailOut } from '../lib/types';

// A small curated slice, fetched live below for pantry-aware "Recommended
// for you" cards -- these are real recipe ids (SL-Cook100 here, but any
// imported id works the same way since recipesApi.detail doesn't care about
// source_type).
const FEATURED_IDS = ['sl_013', 'sl_012', 'sl_050'];

function pantryMatchPct(recipe: RecipeDetailOut): number {
  if (recipe.ingredients.length === 0) return 0;
  const score = recipe.ingredients.reduce((sum, ing) => {
    if (ing.pantry_status === 'have') return sum + 1;
    if (ing.pantry_status === 'partial') return sum + 0.5;
    return sum;
  }, 0);
  return (score / recipe.ingredients.length) * 100;
}

// Client-side time-of-day greeting -- no server clock involved, just the
// visitor's local hour, so it drifts naturally with wherever they are.
function timeOfDayGreeting(): string {
  const hour = new Date().getHours();
  if (hour < 12) return 'Good morning';
  if (hour < 18) return 'Good afternoon';
  return 'Good evening';
}

export default function DiscoveryPage() {
  const navigate = useNavigate();
  const { user } = useAuth();
  const [query, setQuery] = useState('');
  const [featured, setFeatured] = useState<RecipeDetailOut[]>([]);
  const [featuredLoading, setFeaturedLoading] = useState(true);
  const [greeting] = useState(timeOfDayGreeting);

  // Live course list -- was `COURSES` from the static, SL-only 99-recipe
  // CATALOG snapshot (see data/catalog.ts), so "Browse by course" could
  // never surface a course that only exists among imported/International
  // rows in the DB.
  const [courses, setCourses] = useState<string[]>([]);
  useEffect(() => {
    let cancelled = false;
    recipesApi
      .facets()
      .then((res) => {
        if (!cancelled) setCourses(res.courses);
      })
      .catch(() => {
        // Non-critical: rest of the Discovery page still renders.
      });
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    let cancelled = false;
    setFeaturedLoading(true);
    Promise.allSettled(FEATURED_IDS.map((id) => recipesApi.detail(id))).then((results) => {
      if (cancelled) return;
      const ok = results
        .filter((r): r is PromiseFulfilledResult<RecipeDetailOut> => r.status === 'fulfilled')
        .map((r) => r.value);
      setFeatured(ok);
      setFeaturedLoading(false);
    });
    return () => {
      cancelled = true;
    };
  }, []);

  function submitSearch(e: React.FormEvent) {
    e.preventDefault();
    navigate(`/explore${query.trim() ? `?q=${encodeURIComponent(query.trim())}` : ''}`);
  }

  const firstName = user?.full_name?.split(' ')[0];

  // Highest pantry-match pick from the featured set becomes the hero image --
  // the one personalized thing we can show above the fold before the user
  // has done anything except log in.
  const ranked = useMemo(
    () => [...featured].sort((a, b) => pantryMatchPct(b) - pantryMatchPct(a)),
    [featured],
  );
  const heroRecipe = ranked[0];

  return (
    <div className="relative z-10 min-h-screen pb-32">
      <LivingBackground />
      <MainHeader />

      <section className="relative pt-32 md:pt-40 pb-14 px-5 md:px-20">
        <div className="max-w-[1440px] mx-auto grid md:grid-cols-[1.1fr_0.9fr] gap-10 items-center">
          <div className="text-center md:text-left">
            <p className="font-ui text-xs uppercase tracking-[0.2em] text-white/70 mb-3">
              {firstName ? `${greeting}, ${firstName}` : greeting}
            </p>
            <h2 className="font-display text-4xl md:text-6xl font-bold text-white mb-2 drop-shadow-lg">
              What shall we cook today?
            </h2>
            <p className="text-white/80 font-body-md mb-8">
              Real recipes, matched against what's actually in your pantry.
            </p>
            <form onSubmit={submitSearch} className="max-w-2xl mx-auto md:mx-0 saffron-glow group relative">
              <div className="absolute left-6 top-1/2 -translate-y-1/2 text-tertiary">
                <Sparkles size={20} />
              </div>
              <input
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                className="w-full h-16 pl-16 pr-32 rounded-full bg-white/20 border border-white/30 backdrop-blur-md text-white placeholder-white/70 focus:outline-none focus:ring-2 focus:ring-primary-container transition-all text-lg"
                placeholder="Search by dish, ingredient, or course…"
                type="text"
              />
              <button
                type="submit"
                className="absolute right-3 top-1/2 -translate-y-1/2 bg-primary hover:bg-primary-container text-white px-6 py-2.5 rounded-full transition-all font-ui text-sm font-semibold shadow-lg"
              >
                Search
              </button>
            </form>
          </div>

          <div className="mt-8 md:mt-0">
            {featuredLoading ? (
              <div className="h-64 md:h-96 rounded-lg glass-card animate-pulse" />
            ) : heroRecipe ? (
              <div
                role="button"
                tabIndex={0}
                onClick={() => navigate(`/recipe/${heroRecipe.id}`)}
                onKeyDown={(e) => e.key === 'Enter' && navigate(`/recipe/${heroRecipe.id}`)}
                className="tilt-card glass-card rounded-lg overflow-hidden cursor-pointer relative h-64 md:h-96"
              >
                <DishTile course={heroRecipe.course} imageUrl={heroRecipe.image_url} className="w-full h-full" />
                <div className="absolute inset-0 bg-gradient-to-t from-black/80 via-black/10 to-transparent" />
                <div className="absolute top-4 left-4 bg-primary/90 text-white px-3 py-1.5 rounded-full text-[11px] font-bold flex items-center gap-1.5">
                  <ChefHat size={13} /> {Math.round(pantryMatchPct(heroRecipe))}% Pantry Match
                </div>
                <div className="absolute bottom-0 left-0 right-0 p-6">
                  <p className="text-white/70 font-ui text-xs uppercase tracking-wide mb-1">
                    Best match for your pantry
                  </p>
                  <h3 className="font-heading text-2xl text-white mb-1 drop-shadow">{heroRecipe.name_en}</h3>
                  <div className="flex items-center gap-2 text-white/80 text-xs font-body-md">
                    {heroRecipe.course || heroRecipe.cuisine}
                    {heroRecipe.base_servings ? ` • Serves ${heroRecipe.base_servings}` : ''}
                  </div>
                </div>
              </div>
            ) : (
              <div className="h-64 md:h-96 rounded-lg glass-card flex items-center justify-center p-8 text-center text-white/80 font-body-md">
                Couldn't load a featured pick right now — the recipe service may be unreachable.
              </div>
            )}
          </div>
        </div>
      </section>

      <section className="relative px-5 md:px-20 space-y-6">
        <div className="flex justify-between items-end">
          <div>
            <h3 className="font-heading text-2xl text-white">Recommended for you</h3>
            <p className="text-white/70 font-body-md text-sm">Live pantry match, computed from your real pantry</p>
          </div>
          <button onClick={() => navigate('/explore')} className="text-primary-fixed-dim font-ui text-xs font-medium flex items-center gap-1.5 shrink-0">
            View all <ArrowRight size={14} />
          </button>
        </div>

        {featuredLoading ? (
          <div className="flex gap-6 overflow-x-hidden pb-2">
            {[0, 1, 2].map((i) => (
              <div key={i} className="h-72 w-72 md:w-80 shrink-0 rounded-lg glass-card animate-pulse" />
            ))}
          </div>
        ) : ranked.length === 0 ? (
          <div className="glass-card rounded-lg p-8 text-center text-white/80 font-body-md">
            Couldn't load recommendations right now — the recipe service may be unreachable.
          </div>
        ) : (
          <div className="flex gap-6 overflow-x-auto snap-x snap-mandatory pb-4 -mx-5 px-5 md:mx-0 md:px-0 scrollbar-hide">
            {ranked.map((recipe) => (
              <div key={recipe.id} className="w-72 md:w-80 shrink-0 snap-start">
                <RecipeCard
                  recipe={{
                    id: recipe.id,
                    name_en: recipe.name_en,
                    name_native: recipe.name_native,
                    cuisine: recipe.cuisine,
                    course: recipe.course,
                    image_url: recipe.image_url,
                    servings: recipe.base_servings,
                  }}
                  pantryMatchPct={pantryMatchPct(recipe)}
                  badge="AI Pick"
                />
              </div>
            ))}
          </div>
        )}
      </section>

      <section className="relative px-5 md:px-20 mt-14 space-y-4">
        <div>
          <h3 className="font-heading text-2xl text-white">Browse by course</h3>
          <p className="text-white/70 font-body-md text-sm">Jump straight to a course when you already know what you're after</p>
        </div>
        <div className="flex flex-wrap gap-3">
          {courses.map((course) => (
            <button
              key={course}
              onClick={() => navigate(`/explore?course=${encodeURIComponent(course)}`)}
              className="spring-scale glass-card px-5 py-2.5 rounded-full text-white font-ui text-xs font-medium flex items-center gap-2 border border-white/20 whitespace-nowrap"
            >
              <UtensilsCrossed size={14} /> {course}
            </button>
          ))}
        </div>
      </section>

      <button
        onClick={() => navigate('/pantry-add')}
        className="fixed bottom-24 md:bottom-12 right-5 md:right-12 z-[60] bg-primary text-white flex items-center gap-3 px-6 py-4 rounded-full shadow-[0_10px_30px_rgba(144,77,0,0.5)] hover:scale-105 active:scale-95 transition-all"
      >
        <Plus size={22} />
        <span className="font-ui text-sm font-bold">Add Ingredient</span>
      </button>
      <MobileBottomNav />
    </div>
  );
}