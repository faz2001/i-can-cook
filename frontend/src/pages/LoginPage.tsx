import { ChefHat, Loader2, LogIn } from 'lucide-react';
import React, { useState } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { InlineError } from '../components/StatusBlocks';
import { ApiError } from '../lib/api';
import { useAuth } from '../lib/auth';

export default function LoginPage() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const from = (location.state as { from?: string } | null)?.from || '/';

  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      await login(email, password);
      navigate(from, { replace: true });
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Something went wrong. Please try again.');
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-primary-fixed via-background to-tertiary-fixed p-5">
      <div className="w-full max-w-md bg-surface/90 backdrop-blur-2xl rounded-xl shadow-2xl p-8 border border-white/40">
        <div className="flex flex-col items-center mb-8">
          <div className="w-14 h-14 rounded-full bg-primary flex items-center justify-center mb-4 shadow-lg">
            <ChefHat className="text-on-primary" size={28} />
          </div>
          <h1 className="font-display text-3xl text-on-surface">Welcome back</h1>
          <p className="font-body-md text-on-surface-variant text-sm mt-1">Sign in to your kitchen</p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-5" noValidate>
          {error && <InlineError message={error} />}

          <div className="space-y-1.5">
            <label htmlFor="email" className="block font-ui text-[11px] uppercase tracking-wider text-on-surface-variant pl-1">
              Email
            </label>
            <input
              id="email"
              type="email"
              required
              autoComplete="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="w-full h-14 py-3.5 px-5 bg-white rounded-full border border-outline-variant/40 focus:outline-none focus:ring-2 focus:ring-primary-container transition-all"
              placeholder="you@example.com"
            />
          </div>

          <div className="space-y-1.5">
            <label htmlFor="password" className="block font-ui text-[11px] uppercase tracking-wider text-on-surface-variant pl-1">
              Password
            </label>
            <input
              id="password"
              type="password"
              required
              autoComplete="current-password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full h-14 py-3.5 px-5 bg-white rounded-full border border-outline-variant/40 focus:outline-none focus:ring-2 focus:ring-primary-container transition-all"
              placeholder="••••••••"
            />
          </div>

          <button
            type="submit"
            disabled={submitting}
            className="w-full h-14 py-3.5 rounded-full bg-primary text-on-primary font-ui font-semibold shadow-lg hover:shadow-xl transition-shadow flex items-center justify-center gap-2 disabled:opacity-60"
          >
            {submitting ? <Loader2 className="animate-spin" size={18} /> : <LogIn size={18} />}
            {submitting ? 'Signing in…' : 'Sign in'}
          </button>
        </form>

        <p className="text-center font-body-md text-sm text-on-surface-variant mt-6">
          New here?{' '}
          <Link to="/register" className="text-primary font-semibold hover:underline">
            Create an account
          </Link>
        </p>
      </div>
    </div>
  );
}
