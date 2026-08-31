import { CheckCircle2, ChefHat, Loader2, XCircle } from 'lucide-react';
import { useEffect, useRef, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { ApiError, authApi } from '../lib/api';
import { useAuth } from '../lib/auth';

type VerifyState = 'verifying' | 'success' | 'error';

/** Landing page for the link inside verification emails
 * (FRONTEND_BASE_URL/verify-email?token=...). Deliberately not behind
 * ProtectedRoute -- someone opening this from their email on a different
 * device or browser won't have a session here. */
export default function VerifyEmailPage() {
  const [searchParams] = useSearchParams();
  const token = searchParams.get('token');
  const { user, refreshUser } = useAuth();

  const [state, setState] = useState<VerifyState>('verifying');
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const attempted = useRef(false);

  useEffect(() => {
    // Guards against double-firing in React StrictMode dev, which would
    // otherwise spend the (single-use) token on the first render and show
    // a spurious "already used" error on the second.
    if (attempted.current) return;
    attempted.current = true;

    if (!token) {
      setState('error');
      setErrorMessage('This link is missing a verification code. Check that you copied the whole link from the email.');
      return;
    }

    authApi
      .verifyEmail(token)
      .then(async () => {
        setState('success');
        // If they're logged in on this device, refresh so VerifyEmailBanner
        // disappears immediately instead of waiting for the next page load.
        if (user) await refreshUser();
      })
      .catch((err) => {
        setState('error');
        setErrorMessage(err instanceof ApiError ? err.message : 'Something went wrong. Please try again.');
      });
    // Deliberately omitting `user`/`refreshUser` -- this should run exactly
    // once per token, not re-run if those identities change.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token]);

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-primary-fixed via-background to-tertiary-fixed p-5">
      <div className="w-full max-w-md bg-surface/90 backdrop-blur-2xl rounded-xl shadow-2xl p-8 border border-white/40 text-center">
        <div className="flex flex-col items-center mb-6">
          <div className="w-14 h-14 rounded-full bg-primary flex items-center justify-center mb-4 shadow-lg">
            <ChefHat className="text-on-primary" size={28} />
          </div>
          <h1 className="font-display text-3xl text-on-surface">Verify your email</h1>
        </div>

        {state === 'verifying' && (
          <div className="flex flex-col items-center gap-3 py-4 text-on-surface-variant">
            <Loader2 className="animate-spin" size={28} />
            <p className="font-body-md text-sm">Verifying your email…</p>
          </div>
        )}

        {state === 'success' && (
          <div className="flex flex-col items-center gap-3 py-4">
            <div className="w-14 h-14 rounded-full bg-primary-container flex items-center justify-center">
              <CheckCircle2 className="text-primary" size={28} />
            </div>
            <p className="font-body-md text-on-surface-variant text-sm">
              Your email is verified. {user ? "You're all set." : 'You can now sign in.'}
            </p>
            <Link
              to={user ? '/' : '/login'}
              className="mt-2 inline-flex items-center justify-center h-12 px-8 rounded-full bg-primary text-on-primary font-ui font-semibold shadow-lg hover:shadow-xl transition-shadow"
            >
              {user ? 'Back to the app' : 'Go to sign in'}
            </Link>
          </div>
        )}

        {state === 'error' && (
          <div className="flex flex-col items-center gap-3 py-4">
            <div className="w-14 h-14 rounded-full bg-error-container flex items-center justify-center">
              <XCircle className="text-error" size={28} />
            </div>
            <p className="font-body-md text-on-error-container bg-error-container rounded-2xl px-4 py-3 text-sm">
              {errorMessage}
            </p>
            <p className="font-body-md text-on-surface-variant text-sm">
              You can request a new verification email from inside the app once you're signed in.
            </p>
            <Link
              to={user ? '/' : '/login'}
              className="mt-2 inline-flex items-center justify-center h-12 px-8 rounded-full bg-primary text-on-primary font-ui font-semibold shadow-lg hover:shadow-xl transition-shadow"
            >
              {user ? 'Back to the app' : 'Go to sign in'}
            </Link>
          </div>
        )}
      </div>
    </div>
  );
}
