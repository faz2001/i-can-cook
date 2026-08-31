import { ChefHat } from 'lucide-react';
import React, { useState } from 'react';
import { Navigate } from 'react-router-dom';
import { InlineError } from '../components/StatusBlocks';
import { ApiError } from '../lib/api';
import { useAuth } from '../lib/auth';

export default function LoginPage() {
  const { user, login } = useAuth();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (user) return <Navigate to="/" replace />;

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      await login(email, password);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Could not sign in. Check your details and try again.');
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="min-h-screen bg-backstage flex items-center justify-center px-5">
      <div className="w-full max-w-sm">
        <div className="flex flex-col items-center text-center mb-8">
          <ChefHat className="text-ember mb-3" size={30} />
          <h1 className="font-display text-2xl font-semibold text-ticket">The Pass</h1>
          <p className="font-mono-ticket text-[11px] text-ticket-faint tracking-wide mt-1">I CAN COOK · ADMIN ACCESS</p>
        </div>

        <form onSubmit={handleSubmit} className="chit p-7 space-y-4">
          {error && <InlineError message={error} />}

          <div>
            <label className="block font-mono-ticket text-[10px] uppercase tracking-wide text-ticket-faint mb-1.5">
              Email
            </label>
            <input
              type="email"
              required
              autoFocus
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="w-full h-11 px-4 rounded-lg bg-backstage border border-line text-ticket font-body text-sm focus:outline-none focus:ring-2 focus:ring-ember/40"
              placeholder="you@icancook.app"
            />
          </div>

          <div>
            <label className="block font-mono-ticket text-[10px] uppercase tracking-wide text-ticket-faint mb-1.5">
              Password
            </label>
            <input
              type="password"
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full h-11 px-4 rounded-lg bg-backstage border border-line text-ticket font-body text-sm focus:outline-none focus:ring-2 focus:ring-ember/40"
              placeholder="••••••••"
            />
          </div>

          <button
            type="submit"
            disabled={submitting}
            className="w-full h-11 rounded-lg bg-ember text-backstage font-body text-sm font-semibold disabled:opacity-50 hover:bg-ember-dim transition-colors"
          >
            {submitting ? 'Signing in…' : 'Sign in'}
          </button>
        </form>

        <p className="font-body text-xs text-ticket-faint text-center mt-5">
          Admin accounts are provisioned separately -- there's no sign-up here.
        </p>
      </div>
    </div>
  );
}
