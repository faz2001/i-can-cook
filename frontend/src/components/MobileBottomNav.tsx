import { Home, Search, Soup, Boxes, User } from 'lucide-react';
import { NavLink } from 'react-router-dom';

const items = [
  { to: '/', label: 'Home', icon: Home, end: true },
  { to: '/explore', label: 'Explore', icon: Search, end: false },
  { to: '/use-it-up', label: 'Cook', icon: Soup, end: false },
  { to: '/pantry', label: 'Pantry', icon: Boxes, end: false },
  { to: '/profile', label: 'Profile', icon: User, end: false },
];

export function MobileBottomNav() {
  return (
    <nav className="md:hidden fixed bottom-0 left-0 w-full z-50 flex justify-around items-center h-20 px-4 glass-nav border-t shadow-lg rounded-t-lg">
      {items.map(({ to, label, icon: Icon, end }) => (
        <NavLink
          key={to}
          to={to}
          end={end}
          className={({ isActive }) =>
            `flex flex-col items-center justify-center gap-0.5 ${isActive ? 'text-primary' : 'text-on-surface-variant'}`
          }
        >
          <Icon size={22} />
          <span className="font-ui text-[10px]">{label}</span>
        </NavLink>
      ))}
    </nav>
  );
}
