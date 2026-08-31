import { AlertTriangle, RotateCw } from 'lucide-react';

export function LoadingBlock({ label }: { label: string }) {
  return (
    <div className="flex items-center gap-3 py-12 justify-center">
      <div className="w-5 h-5 rounded-full border-2 border-ember-container border-t-ember animate-spin" />
      <p className="font-mono-ticket text-sm text-ticket-dim">{label}</p>
    </div>
  );
}

export function ErrorBlock({ message, onRetry }: { message: string; onRetry: () => void }) {
  return (
    <div className="chit p-8 flex flex-col items-center text-center gap-3">
      <AlertTriangle className="text-rust" size={22} />
      <p className="font-body text-sm text-ticket-dim max-w-sm">{message}</p>
      <button
        onClick={onRetry}
        className="flex items-center gap-1.5 mt-1 px-4 py-2 rounded-full bg-backstage-high text-ticket font-mono-ticket text-xs hover:bg-line transition-colors"
      >
        <RotateCw size={13} /> Retry
      </button>
    </div>
  );
}

export function InlineError({ message }: { message: string }) {
  return (
    <div className="flex items-start gap-2 rounded-lg bg-rust-container border border-rust/30 px-4 py-2.5">
      <AlertTriangle size={14} className="text-rust mt-0.5 shrink-0" />
      <p className="font-body text-xs text-ticket">{message}</p>
    </div>
  );
}
