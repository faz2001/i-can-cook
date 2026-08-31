import { ChefHat, Loader2, UserPlus } from 'lucide-react';
import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { InlineError } from '../components/StatusBlocks';
import { ApiError } from '../lib/api';
import { useAuth } from '../lib/auth';

export default function RegisterPage() {
  const { register } = useAuth();
  const navigate = useNavigate();

  const [fullName, setFullName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const passwordTooShort = password.length > 0 && password.length < 8;

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    if (password.length < 8) {
      setError('Password must be at least 8 characters.');
      return;
    }
    setSubmitting(true);
    try {
      await register(email, password, fullName);
      navigate('/', { replace: true });
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Something went wrong. Please try again.');
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-tertiary-fixed via-background to-primary-fixed p-5">
      <div className="w-full max-w-md bg-surface/90 backdrop-blur-2xl rounded-xl shadow-2xl p-8 border border-white/40">
        <div className="flex flex-col items-center mb-8">
          <div className="w-14 h-14 rounded-full bg-primary flex items-center justify-center mb-4 shadow-lg">
            <ChefHat className="text-on-primary" size={28} />
          </div>
          <h1 className="font-display text-3xl text-on-surface">Create your kitchen</h1>
          <p className="font-body-md text-on-surface-variant text-sm mt-1">Real pantry. Real recipes.</p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-5" noValidate>
          {error && <InlineError message={error} />}

          <div className="space-y-1.5">
            <label htmlFor="fullName" className="block font-ui text-[11px] uppercase tracking-wider text-on-surface-variant pl-1">
              Full name
            </label>
            <input
              id="fullName"
              type="text"
              autoComplete="name"
              value={fullName}
              onChange={(e) => setFullName(e.target.value)}
              className="w-full h-14 py-3.5 px-5 bg-white rounded-full border border-outline-variant/40 focus:outline-none focus:ring-2 focus:ring-primary-container transition-all"
              placeholder="Chef Julia"
            />
          </div>

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
              autoComplete="new-password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full h-14 py-3.5 px-5 bg-white rounded-full border border-outline-variant/40 focus:outline-none focus:ring-2 focus:ring-primary-container transition-all"
              placeholder="At least 8 characters"
            />
            {passwordTooShort && <p className="text-xs text-error pl-2">Needs at least 8 characters.</p>}
          </div>

          <button
            type="submit"
            disabled={submitting}
            className="w-full h-14 py-3.5 rounded-full bg-primary text-on-primary font-ui font-semibold shadow-lg hover:shadow-xl transition-shadow flex items-center justify-center gap-2 disabled:opacity-60"
          >
            {submitting ? <Loader2 className="animate-spin" size={18} /> : <UserPlus size={18} />}
            {submitting ? 'Creating account…' : 'Create account'}
          </button>
        </form>

        <p className="text-center font-body-md text-sm text-on-surface-variant mt-6">
          Already have an account?{' '}
          <Link to="/login" className="text-primary font-semibold hover:underline">
            Sign in
          </Link>
        </p>
      </div>
    </div>
  );
}
