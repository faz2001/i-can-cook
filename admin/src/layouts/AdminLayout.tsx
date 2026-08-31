import {
  ChefHat,
  Database,
  Gauge,
  LayoutDashboard,
  LogOut,
  ShieldCheck,
  Tags as TagsIcon,
} from 'lucide-react';
import React from 'react';
import { NavLink } from 'react-router-dom';
import { useAuth } from '../lib/auth';

const NAV_ITEMS = [
  { to: '/', label: 'Overview', icon: LayoutDashboard, end: true },
  { to: '/moderation', label: 'Moderation', icon: ShieldCheck },
  { to: '/tags', label: 'Tags', icon: TagsIcon },
  { to: '/trust-scores', label: 'Trust scores', icon: Gauge },
  { to: '/dataset', label: 'Dataset', icon: Database },
];

export function AdminLayout({ children }: { children: React.ReactNode }) {
  const { user, logout } = useAuth();
  const initial = (user?.full_name || user?.email || '?').trim().charAt(0).toUpperCase();

  return (
    <div className="min-h-screen bg-backstage flex">
      <aside className="w-60 shrink-0 bg-rail border-r border-line flex flex-col">
        <div className="h-20 flex items-center gap-2.5 px-6 border-b border-line">
          <ChefHat className="text-ember" size={22} />
          <div>
            <p className="font-display text-base font-semibold text-ticket leading-tight">The Pass</p>
            <p className="font-mono-ticket text-[10px] text-ticket-faint tracking-wide">I CAN COOK · ADMIN</p>
          </div>
        </div>

        <nav className="flex-1 px-3 py-6 space-y-1">
          {NAV_ITEMS.map(({ to, label, icon: Icon, end }) => (
            <NavLink
              key={to}
              to={to}
              end={end}
              className={({ isActive }) =>
                `flex items-center gap-3 px-3.5 py-2.5 rounded-lg font-body text-sm transition-colors ${
                  isActive
                    ? 'bg-ember-container text-ember'
                    : 'text-ticket-dim hover:bg-backstage-raised hover:text-ticket'
                }`
              }
            >
              <Icon size={17} />
              {label}
            </NavLink>
          ))}
        </nav>

        <div className="px-3 py-4 border-t border-line">
          <div className="flex items-center gap-3 px-2 py-2">
            <div className="w-8 h-8 rounded-full bg-ember-container text-ember flex items-center justify-center font-display text-sm font-semibold shrink-0">
              {initial}
            </div>
            <div className="min-w-0">
              <p className="font-body text-xs text-ticket truncate">{user?.full_name || user?.email}</p>
              <p className="font-mono-ticket text-[10px] text-ticket-faint">admin</p>
            </div>
          </div>
          <button
            onClick={logout}
            className="w-full mt-2 flex items-center gap-2 px-3 py-2 rounded-lg text-ticket-dim hover:bg-backstage-raised hover:text-rust transition-colors font-body text-xs"
          >
            <LogOut size={14} /> Sign out
          </button>
        </div>
      </aside>

      <main className="flex-1 min-w-0 px-6 py-8 md:px-10 md:py-10 max-w-6xl">{children}</main>
    </div>
  );
}
