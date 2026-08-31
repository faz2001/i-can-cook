import { CheckCircle2, Loader2, Mail, X } from 'lucide-react';
import { useState } from 'react';
import { ApiError, authApi } from '../lib/api';
import { useAuth } from '../lib/auth';

type SendState = 'idle' | 'sending' | 'sent' | 'error';

/** Informational-only nudge -- never gates a route or feature. Renders nothing
 * once the user is verified (or before we know who they are), and can be
 * dismissed for the rest of this page's lifetime. */
export function VerifyEmailBanner() {
  const { user } = useAuth();
  const [dismissed, setDismissed] = useState(false);
  const [state, setState] = useState<SendState>('idle');
  const [error, setError] = useState<string | null>(null);

  if (!user || user.is_verified || dismissed) return null;

  const handleResend = async () => {
    setState('sending');
    setError(null);
    try {
      await authApi.resendVerification();
      setState('sent');
      setTimeout(() => setState('idle'), 4000);
    } catch (e) {
      setState('error');
      setError(e instanceof ApiError ? e.message : 'Something went wrong. Please try again.');
    }
  };

  return (
    <div
      role="status"
      className="fixed top-24 left-1/2 -translate-x-1/2 z-40 w-[calc(100%-2rem)] max-w-md animate-fade-in
                 flex flex-wrap items-center gap-3 rounded-2xl bg-primary-container text-on-primary-container
                 px-4 py-3 text-sm font-ui shadow-md"
    >
      <Mail size={16} className="shrink-0" />
      <span className="flex-1 min-w-0">Verify your email to unlock all features</span>

      <button
        onClick={handleResend}
        disabled={state === 'sending'}
        className="flex items-center gap-1.5 rounded-full bg-primary text-on-primary px-4 py-1.5 text-xs
                   font-medium shadow-sm hover:shadow-md transition-shadow disabled:opacity-60 shrink-0"
      >
        {state === 'sending' && <Loader2 size={14} className="animate-spin" />}
        {state === 'sent' && <CheckCircle2 size={14} />}
        {state === 'sending' ? 'Sending…' : state === 'sent' ? 'Verification email sent' : 'Resend email'}
      </button>

      <button
        aria-label="Dismiss"
        onClick={() => setDismissed(true)}
        className="text-on-primary-container/70 hover:text-on-primary-container transition-colors shrink-0"
      >
        <X size={16} />
      </button>

      {state === 'error' && error && (
        <span className="w-full flex items-start gap-2 rounded-xl bg-error-container text-on-error-container px-3 py-2 text-xs font-ui">
          {error}
        </span>
      )}
    </div>
  );
}
