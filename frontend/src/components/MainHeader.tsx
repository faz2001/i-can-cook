import { Search, ChefHat } from 'lucide-react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../lib/auth';

export function MainHeader({ transparent = false }: { transparent?: boolean }) {
  const navigate = useNavigate();
  const { user } = useAuth();
  const initial = (user?.full_name || user?.email || '?').trim().charAt(0).toUpperCase();

  return (
    <header
      className={`fixed top-0 left-0 w-full z-50 flex justify-between items-center px-5 md:px-20 h-20 transition-all ${
        transparent ? 'bg-white/10' : 'glass-nav'
      }`}
    >
      <button
        className="font-heading text-2xl font-bold text-on-surface flex items-center gap-2"
        onClick={() => navigate('/')}
      >
        <ChefHat className="text-primary" size={26} />
        I Can Cook
      </button>
      <div className="flex items-center gap-6">
        <nav className="hidden md:flex gap-8">
          <Link to="/" className="font-ui text-xs font-medium tracking-wide uppercase text-on-surface-variant hover:text-primary transition-colors">
            Home
          </Link>
          <Link to="/explore" className="font-ui text-xs font-medium tracking-wide uppercase text-on-surface-variant hover:text-primary transition-colors">
            Explore
          </Link>
          <Link to="/use-it-up" className="font-ui text-xs font-medium tracking-wide uppercase text-on-surface-variant hover:text-primary transition-colors">
            Cook
          </Link>
          <Link to="/pantry" className="font-ui text-xs font-medium tracking-wide uppercase text-on-surface-variant hover:text-primary transition-colors">
            Pantry
          </Link>
          <Link to="/bookmarks" className="font-ui text-xs font-medium tracking-wide uppercase text-on-surface-variant hover:text-primary transition-colors">
            Bookmarks
          </Link>
          
        </nav>
        <button aria-label="Search recipes" className="text-primary" onClick={() => navigate('/explore')}>
          <Search size={22} />
        </button>
        <button
          aria-label="Profile"
          className="w-10 h-10 rounded-full bg-primary text-on-primary border border-white/40 overflow-hidden shadow-sm flex items-center justify-center font-heading font-semibold"
          onClick={() => navigate('/profile')}
        >
          {initial}
        </button>
      </div>
    </header>
  );
}