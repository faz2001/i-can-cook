import { useState } from 'react';
import { Croissant, Cookie, Soup, UtensilsCrossed, Salad, CupSoda } from 'lucide-react';

const COURSE_STYLE: Record<string, { gradient: string; icon: typeof Soup }> = {
  Breakfast: { gradient: 'from-[#ffb77b] to-[#e8820c]', icon: Croissant },
  Dessert: { gradient: 'from-[#ffb2bd] to-[#b9134b]', icon: Cookie },
  Dinner: { gradient: 'from-[#904d00] to-[#512900]', icon: Soup },
  Main: { gradient: 'from-[#904d00] to-[#6d3900]', icon: UtensilsCrossed },
  Condiment: { gradient: 'from-[#ae86ff] to-[#732ee4]', icon: Salad },
  Snack: { gradient: 'from-[#ff4f7b] to-[#900036]', icon: CupSoda },
};

const DEFAULT_STYLE = { gradient: 'from-[#904d00] to-[#732ee4]', icon: Soup };

/** Renders the recipe's real image_url when set (every recipe has one now --
 * either a genuine photo or a course-based fallback chosen at ingest time).
 * Falls back to the gradient+icon tile only if the URL is missing or fails to
 * load (a 404'd local image file, for instance), so a broken path never shows
 * as a broken-image icon. */
export function DishTile({
  course,
  imageUrl,
  className = '',
}: {
  course?: string | null;
  imageUrl?: string | null;
  className?: string;
}) {
  const [failed, setFailed] = useState(false);
  const style = (course && COURSE_STYLE[course]) || DEFAULT_STYLE;
  const Icon = style.icon;

  if (imageUrl && !failed) {
    return (
      <img
        src={imageUrl}
        alt=""
        loading="lazy"
        onError={() => setFailed(true)}
        className={`object-cover ${className}`}
      />
    );
  }

  return (
    <div className={`bg-gradient-to-br ${style.gradient} flex items-center justify-center ${className}`}>
      <Icon className="text-white/90" size={40} strokeWidth={1.5} />
    </div>
  );
}
