import { Bookmark, Clock, Sparkles } from 'lucide-react';
import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { AddToCollectionModal } from './AddToCollectionModal';
import { DishTile } from './DishTile';

/** The minimum shape a card needs -- satisfied directly by RecipeListItemOut
 * (GET /api/recipes) and by a small literal built from RecipeDetailOut where
 * a card is shown for an already-fetched detail (e.g. Discovery's featured
 * picks), so both real data sources work without a conversion layer. */
export interface RecipeCardData {
  id: string;
  name_en: string;
  name_native?: string | null;
  cuisine: string;
  course: string | null;
  image_url?: string | null;
  servings?: number | null;
  total_time_min?: number | null;
}

interface Props {
  recipe: RecipeCardData;
  /** 0-100, only shown when known (i.e. we've already fetched live detail for this card) */
  pantryMatchPct?: number;
  badge?: string;
  className?: string;
}

export function RecipeCard({ recipe, pantryMatchPct, badge, className = '' }: Props) {
  const navigate = useNavigate();
  const totalTime = recipe.total_time_min ?? 0;
  const [showModal, setShowModal] = useState(false);

  return (
    <div
      role="button"
      tabIndex={0}
      onClick={() => navigate(`/recipe/${recipe.id}`)}
      onKeyDown={(e) => e.key === 'Enter' && navigate(`/recipe/${recipe.id}`)}
      className={`tilt-card glass-card rounded-lg overflow-hidden p-2 cursor-pointer text-left ${className}`}
    >
      <div className="relative h-48 rounded-lg overflow-hidden mb-3">
        <DishTile course={recipe.course} imageUrl={recipe.image_url} className="w-full h-full" />
        {badge && (
          <div className="absolute top-3 left-3 bg-tertiary text-white px-3 py-1 rounded-full text-[10px] font-bold uppercase tracking-wider flex items-center gap-1">
            <Sparkles size={12} /> {badge}
          </div>
        )}
        <button
          aria-label="Save to collection"
          onClick={(e) => {
            e.stopPropagation();
            setShowModal(true);
          }}
          className="absolute top-3 right-3 bg-black/50 backdrop-blur-md text-white p-1.5 rounded-full hover:bg-black/70 transition-colors"
        >
          <Bookmark size={14} />
        </button>
        <div className="absolute bottom-3 right-3 flex gap-2">
          {totalTime > 0 && (
            <span className="bg-black/50 backdrop-blur-md text-white px-2 py-1 rounded text-[10px] font-medium">
              {totalTime} min
            </span>
          )}
          {pantryMatchPct !== undefined && (
            <span className="bg-primary/90 text-white px-2 py-1 rounded text-[10px] font-medium">
              {Math.round(pantryMatchPct)}% Pantry Match
            </span>
          )}
        </div>
      </div>
      <div className="px-2 pb-2">
        <h4 className="font-heading text-base text-on-surface mb-1 line-clamp-1">{recipe.name_en}</h4>
        <div className="flex items-center gap-2 text-on-surface-variant text-xs">
          <Clock size={13} /> {recipe.course || recipe.cuisine}
          {recipe.servings ? ` • Serves ${recipe.servings}` : ''}
        </div>
      </div>
      {showModal && <AddToCollectionModal recipeId={recipe.id} onClose={() => setShowModal(false)} />}
    </div>
  );
}